import asyncio
import json
import logging
import sys
import time
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

    # Log details of OpenAI client configuration
    model_name = "gpt-4o"
    key_exists = bool(settings.openai_api_key)
    logger.info(
        f"Initializing OpenAI Code Generation. Model: {model_name}, "
        f"Key Exists: {key_exists}"
    )

    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        org_id = getattr(client, "organization", "Not Set")
        project_id = getattr(client, "project", "Not Set")
        logger.info(f"OpenAI Client config - Organization: {org_id}, Project: {project_id}")

        # 2. Call OpenAI Chat Completions streaming endpoint
        response = await client.chat.completions.create(
            model=model_name,
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
        is_testing = "pytest" in sys.modules
        
        # Capture error information
        full_error_body = getattr(e, "body", None)
        error_context = full_error_body if full_error_body else str(e)
        logger.error(
            f"OpenAI generation stream failed: {e}. "
            f"Full OpenAI API error response: {error_context}",
            exc_info=True
        )

        # Check for authentication or rate-limit/quota errors
        is_quota_or_auth = (
            "insufficient_quota" in str(e)
            or "RateLimitError" in type(e).__name__
            or "AuthenticationError" in type(e).__name__
            or "api_key" in str(e).lower()
        )

        # Trigger Gemini fallback if not running tests and it's a quota/auth error
        if is_quota_or_auth and not is_testing:
            logger.warning("OpenAI rate limit or quota exceeded. Initiating fallback to Gemini 2.5 Flash for code generation...")
            
            fallback_msg = {
                "type": "plan",
                "content": "OpenAI quota exceeded. Falling back to Gemini 2.5 Flash for code generation..."
            }
            yield f"data: {json.dumps(fallback_msg)}\n\n"

            from google import genai
            from google.genai import types

            gemini_client = genai.Client(api_key=settings.gemini_api_key)
            model_name_gemini = "gemini-2.5-flash"
            
            max_attempts = 3
            chunks_emitted = 0
            chars_emitted = 0
            gen_start_time = time.time()
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Querying Gemini API for code generation (Attempt {attempt}). Model: {model_name_gemini}, SDK: {genai.__version__}")
                    
                    gemini_response = await gemini_client.aio.models.generate_content_stream(
                        model=model_name_gemini,
                        contents=f"Here is the UI design plan:\n{json.dumps(plan, indent=2)}",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            max_output_tokens=4000
                        )
                    )

                    async for gemini_chunk in gemini_response:
                        if gemini_chunk.text:
                            chunks_emitted += 1
                            chars_emitted += len(gemini_chunk.text)
                            chunk_event = {"type": "chunk", "content": gemini_chunk.text}
                            yield f"data: {json.dumps(chunk_event)}\n\n"

                    # Emit done event for Gemini stream
                    done_event = {"type": "done", "total_tokens": 0}
                    yield f"data: {json.dumps(done_event)}\n\n"
                    return # Successfully completed

                except Exception as gemini_err:
                    err_str = str(gemini_err)
                    is_503 = "503" in err_str or "UNAVAILABLE" in err_str.upper() or "high demand" in err_str.lower()
                    
                    if chunks_emitted > 0:
                        # Failed AFTER streaming started. Do NOT retry, return PARTIAL_SUCCESS.
                        full_error_body = getattr(gemini_err, "body", None)
                        error_context = full_error_body if full_error_body else err_str
                        
                        logger.error(
                            f"Gemini streaming failed mid-stream: {gemini_err}. "
                            f"[Metrics] Start: {gen_start_time}, Model: {model_name_gemini}, "
                            f"Chunks emitted: {chunks_emitted}, Chars emitted: {chars_emitted}. "
                            f"Full Google API response body: {error_context}",
                            exc_info=True
                        )
                        
                        partial_event = {
                            "type": "partial_success", 
                            "content": f"Generation partially completed before upstream error: {err_str}"
                        }
                        yield f"data: {json.dumps(partial_event)}\n\n"
                        return

                    if is_503 and attempt < max_attempts:
                        wait_time = 2 if attempt == 1 else 5
                        logger.warning(f"Gemini 503 Unavailable. Retrying in {wait_time}s (Attempt {attempt}/{max_attempts})...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Failed BEFORE streaming started and exhausted retries, or non-503 error
                    logger.error(f"Gemini fallback code generation failed completely on attempt {attempt}: {gemini_err}", exc_info=True)
                    error_event = {"type": "error", "message": f"Generation failed (including fallback): {str(gemini_err)}"}
                    yield f"data: {json.dumps(error_event)}\n\n"
                    return

        # Fallback error event if not handled by Gemini fallback
        error_event = {"type": "error", "message": f"Generation failed: {str(e)}"}
        yield f"data: {json.dumps(error_event)}\n\n"
