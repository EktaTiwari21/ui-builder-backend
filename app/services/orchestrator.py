import asyncio
import json
import logging
import time
from typing import TypedDict, List, Optional, AsyncGenerator
from langgraph.graph import StateGraph, END

from app.models.requests import GenerateUIRequest
from app.services import prompt_parser, planner, generator, validator
from app.services.prompt_parser import ParsedPrompt
from app.services.planner import PlannerError
from app.db import supabase

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """The State of the LangGraph agent orchestrator."""
    prompt: str
    parsed: Optional[ParsedPrompt]
    plan: Optional[dict]
    code: Optional[str]
    is_valid: bool
    errors: List[str]
    retries: int
    user_id: str
    project_id: Optional[str]
    total_tokens: int
    latency_ms: int
    event_queue: asyncio.Queue

# Node 1: Parse prompt
async def parse_node(state: AgentState) -> dict:
    """Parse, sanitize, and classify the user's prompt."""
    parsed = prompt_parser.parse(state["prompt"])
    return {"parsed": parsed}

# Node 2: Design UI architecture layout plan
async def plan_node(state: AgentState) -> dict:
    """Call the Gemini agent to design the UI component architecture and plan."""
    # Emit layout planning status to client
    plan_status = {"type": "plan", "content": "Planning UI architecture layout..."}
    await state["event_queue"].put(f"data: {json.dumps(plan_status)}\n\n")

    try:
        plan_data = await planner.plan(state["parsed"])
        return {"plan": plan_data}
    except PlannerError as pe:
        logger.error(f"Planning failed inside node: {pe}")
        # Put error directly in event queue and raise to abort graph flow
        error_msg = {"type": "error", "message": f"Planning failed: {str(pe)}"}
        await state["event_queue"].put(f"data: {json.dumps(error_msg)}\n\n")
        raise pe

# Node 3: Generate React / Tailwind component code
async def generate_node(state: AgentState) -> dict:
    """Call OpenAI component generator to write code, with error repair prompt if retrying."""
    plan_to_use = state["plan"].copy()
    
    if state["retries"] > 0 and state["errors"]:
        # Put error repair/retry notification in queue
        retry_msg = {
            "type": "plan",
            "content": f"Errors found. Retrying and attempting to auto-repair component code (attempt {state['retries'] + 1}/3)..."
        }
        await state["event_queue"].put(f"data: {json.dumps(retry_msg)}\n\n")
        
        # Inject fix instructions and previous code into the plan for GPT-4o context
        plan_to_use["fix_instructions"] = (
            "The previously generated React component code failed validation checks with the following errors:\n"
            + "\n".join(f"- {e}" for e in state["errors"])
            + "\n\nPlease rewrite the React component to fully fix all these errors."
        )
        plan_to_use["previous_code"] = state["code"]

    start_time = time.time()
    full_code = ""
    total_tokens = 0

    # Stream the chunks directly from generator into the event queue
    async for event in generator.generate(plan_to_use):
        await state["event_queue"].put(event)
        
        if event.startswith("data: "):
            try:
                data = json.loads(event[6:-2])
                if data["type"] == "chunk":
                    full_code += data["content"]
                elif data["type"] == "done":
                    total_tokens = data.get("total_tokens", 0)
            except Exception:
                pass

    latency_ms = int((time.time() - start_time) * 1000)
    
    return {
        "code": full_code,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms
    }

# Node 4: Validate JSX component correctness
async def validate_node(state: AgentState) -> dict:
    """Validate component code using structural, safety, and package import checks."""
    result = validator.validate(state["code"])
    
    if result.is_valid:
        return {
            "is_valid": True,
            "errors": []
        }
    else:
        new_retries = state["retries"] + 1
        return {
            "is_valid": False,
            "errors": result.errors,
            "retries": new_retries
        }

# Node 5: Handle maximum retry failures
async def error_node(state: AgentState) -> dict:
    """Emit final failure message when all retries are exhausted."""
    err_msg = f"Generation failed after maximum retries. Validation errors: {', '.join(state['errors'])}"
    error_event = {"type": "error", "message": err_msg}
    await state["event_queue"].put(f"data: {json.dumps(error_event)}\n\n")
    return {}

# ----------------- Build LangGraph Workflow -----------------

workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("parse", parse_node)
workflow.add_node("plan", plan_node)
workflow.add_node("generate", generate_node)
workflow.add_node("validate", validate_node)
workflow.add_node("error", error_node)

# Set links and logic transitions
workflow.set_entry_point("parse")
workflow.add_edge("parse", "plan")
workflow.add_edge("plan", "generate")
workflow.add_edge("generate", "validate")

# Define conditional routing from validate
def should_continue(state: AgentState):
    if state["is_valid"]:
        return "end"
    elif state["retries"] < 2:
        return "generate"
    else:
        return "error"

workflow.add_conditional_edges(
    "validate",
    should_continue,
    {
        "end": END,
        "generate": "generate",
        "error": "error"
    }
)
workflow.add_edge("error", END)

# Compile graph
graph = workflow.compile()

# ----------------- Run Orchestrator Generator -----------------

async def run(request: GenerateUIRequest, user_id: str) -> AsyncGenerator[str, None]:
    """Execute the full agentic UI generation pipeline and yield SSE events to the client.
    
    On pipeline validation success, saves the project record to Supabase and logs generation metrics.
    
    Args:
        request: UI generation requests containing prompt, style, and framework settings.
        user_id: Authenticated UUID string of the requesting user.
        
    Yields:
        str: Server-Sent Event (SSE) JSON strings ('data: {json}\n\n').
    """
    event_queue = asyncio.Queue()

    initial_state = {
        "prompt": request.prompt,
        "parsed": None,
        "plan": None,
        "code": "",
        "is_valid": False,
        "errors": [],
        "retries": 0,
        "user_id": user_id,
        "project_id": None,
        "total_tokens": 0,
        "latency_ms": 0,
        "event_queue": event_queue
    }

    # Start the LangGraph execution in a background task
    task = asyncio.create_task(graph.ainvoke(initial_state))

    # Consume and yield SSE events from the queue while the task is executing
    while not task.done() or not event_queue.empty():
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
            # Yield event to FastAPI StreamingResponse
            yield event
            event_queue.task_done()
        except asyncio.TimeoutError:
            continue

    # Await task completion to fetch final state and trigger any potential exceptions
    try:
        final_state = await task
    except Exception as graph_err:
        logger.error(f"LangGraph execution encountered an unhandled exception: {graph_err}")
        err_msg = {"type": "error", "message": f"Execution error: {str(graph_err)}"}
        yield f"data: {json.dumps(err_msg)}\n\n"
        return

    # On generation success: save project and log audit generation records
    if final_state["is_valid"]:
        try:
            title = final_state["parsed"].raw_prompt[:50] if final_state["parsed"] else "Generated UI"
            
            # Save the project to Supabase
            project = await supabase.create_project(
                user_id=user_id,
                title=title,
                prompt=request.prompt
            )
            
            if project:
                project_id = project["id"]
                # Save generated React component JSX code
                await supabase.update_project_code(project_id, final_state["code"])
                
                # Log successful generation audit metrics
                await supabase.log_generation(
                    project_id=project_id,
                    model="gpt-4o",
                    tokens=final_state.get("total_tokens", 0),
                    latency=final_state.get("latency_ms", 0),
                    status="completed"
                )
                
                # Increment daily count for user
                await supabase.increment_generations(user_id)
                
                # Emit final done SSE event containing project_id
                done_event = {
                    "type": "done",
                    "project_id": project_id,
                    "total_tokens": final_state.get("total_tokens", 0)
                }
                yield f"data: {json.dumps(done_event)}\n\n"
            else:
                logger.error("Supabase failed to return the created project record.")
                err_event = {"type": "error", "message": "Failed to create project record in database."}
                yield f"data: {json.dumps(err_event)}\n\n"
        
        except Exception as db_err:
            logger.error(f"Orchestrator failed to perform Supabase DB updates: {db_err}")
            err_event = {"type": "error", "message": f"Database transaction failed: {str(db_err)}"}
            yield f"data: {json.dumps(err_event)}\n\n"
    else:
        # On ultimate failure (all retries failed)
        try:
            # Log failed generation record to Supabase (nullable project_id)
            await supabase.log_generation(
                project_id=None,
                model="gpt-4o",
                tokens=final_state.get("total_tokens", 0),
                latency=final_state.get("latency_ms", 0),
                status="failed"
            )
        except Exception as db_err:
            logger.error(f"Failed to log generation failure audit record: {db_err}")
