import json
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior React and Tailwind CSS developer.\n"
    "Your task is to generate complete, high-quality, production-ready React component code based on the provided UI design plan.\n\n"
    "Rules for your output:\n"
    "1. Output ONLY the React component code. Do NOT wrap the code in markdown code blocks (such as ```jsx or ```). Output raw JSX code directly.\n"
    "2. Use named exports for all functional components (e.g. export function HeroSection() { ... }). Do NOT use default exports.\n"
    "3. Use Tailwind CSS utility classes exclusively for all styling, layout, spacing, and design. Do NOT use any inline style attributes (such as style={{...}}).\n"
    "4. Do NOT use any external dependencies beyond standard React hooks, Tailwind classes, and icons from the 'lucide-react' package (e.g. import { ArrowRight } from 'lucide-react';).\n"
    "5. The generated file must be completely self-contained and compile out-of-the-box. Include all necessary imports at the top of the file."
)

async def generate(plan: dict) -> AsyncGenerator[str, None]:
    """Stream React components generated from the layout plan using GPT-4o.
    
    Args:
        plan: The UI architecture and styling plan dict returned by planner.
        
    Yields:
        str: Server-Sent Event (SSE) strings of format 'data: {json_str}\n\n'.
    """
    # 1. Emit start event
    start_event = {"type": "plan", "content": "Generating components..."}
    yield f"data: {json.dumps(start_event)}\n\n"

    # Verify API Key is configured
    if not settings.openai_api_key or settings.openai_api_key == "dummy-openai-key":
        logger.error("OpenAI API key is missing or is the dummy placeholder.")
        error_event = {"type": "error", "message": "OpenAI API key is not configured in environment."}
        yield f"data: {json.dumps(error_event)}\n\n"
        return

    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # 2. Call OpenAI Chat Completions streaming endpoint
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Here is the UI design plan:\n{json.dumps(plan, indent=2)}"}
            ],
            stream=True,
            max_tokens=4000,
            stream_options={"include_usage": True}
        )

        total_tokens = 0

        # 3. Stream chunks to client
        async for chunk in response:
            # Check token usage
            if getattr(chunk, "usage", None) is not None:
                total_tokens = chunk.usage.total_tokens

            # Check delta text content
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                chunk_event = {"type": "chunk", "content": content}
                yield f"data: {json.dumps(chunk_event)}\n\n"

        # 4. Emit complete event
        done_event = {"type": "done", "total_tokens": total_tokens}
        yield f"data: {json.dumps(done_event)}\n\n"

    except Exception as e:
        logger.error(f"OpenAI generation stream failed: {e}")
        error_event = {"type": "error", "message": f"Generation failed: {str(e)}"}
        yield f"data: {json.dumps(error_event)}\n\n"
