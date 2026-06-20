import asyncio
import json
import logging
import sys
import time
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior UI engineer and visual designer specialising in React and 
Tailwind CSS. You create stunning, high-fidelity frontend components that look
like they were designed by a top-tier design agency.

LAYOUT RULES:
1. For FULL PAGES (e.g., landing pages, dashboard views, multi-section pages, websites):
   - Design a complete, premium page layout matching the aesthetic of top-tier SaaS companies.
   - Include a beautiful header/navbar, a high-converting hero section with modern copy, multiple feature/content sections with generous padding (py-16 px-6), and a footer.
   - Use dynamic grids, card grids, pricing toggles, testimonials, and clear call-to-action blocks.
   - Wrap the page in a clean background structure (e.g. bg-slate-50 or bg-gray-950).
2. For INDIVIDUAL COMPONENTS (e.g., buttons, input fields, cards, simple widgets, modals, navigation menus):
   - DO NOT wrap the component in a full-screen, min-h-screen, or bg-gray-900 wrapper that takes up the entire browser canvas.
   - Generate the component as a clean, reusable element.
   - Wrap it inside a compact, elegant centering card container (e.g., p-8 bg-white border border-slate-100 rounded-2xl shadow-sm flex items-center justify-center max-w-sm mx-auto my-4) so that the component itself is the focus and does not look like a full-screen page.

STRICT STYLING RULES:
- Use rich Tailwind gradients: bg-gradient-to-br, from-, via-, to-
- Use shadows: shadow-xl, shadow-2xl, drop-shadow
- Use hover states on every interactive element: hover:scale-105, hover:shadow-xl
- Use transitions: transition-all duration-300 ease-in-out
- Use rounded corners: rounded-2xl, rounded-full for avatars/badges
- Add visual hierarchy with font sizes: text-5xl for headlines, text-lg for body
- Use real placeholder content — real product names, real copy, real numbers
- Include at least one gradient background section
- Use ring utilities for focus states: focus:ring-2 focus:ring-purple-500
- Add CSS animations via Tailwind: animate-pulse for loading, animate-bounce for CTAs
- Use a cohesive color palette — pick one accent color and use it consistently
- Include micro-interactions: group hover effects using group and group-hover:
- For images, always use premium high-quality Unsplash URLs (e.g. from https://images.unsplash.com/...) with descriptive topic keywords (e.g. product, technology, coffee, modern office, profile avatar) rather than local assets.
- All components must be fully self-contained with imports included

OUTPUT: Valid JSX only. No markdown. No explanation. No backticks."""


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

    # If OpenAI key is missing/dummy, skip directly to Gemini fallback
    openai_key = settings.openai_api_key or ""
    skip_openai = not openai_key or openai_key.startswith("dummy") or openai_key == "sk-placeholder"
    if skip_openai:
        logger.warning("OpenAI API key is missing/dummy — skipping directly to Gemini fallback for generation.")

    is_quota_or_auth = skip_openai  # Start as True if we're skipping OpenAI

    if not skip_openai:
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
                max_tokens=8192,
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

            # 4. Emit internal complete event
            done_event = {"type": "generator_done", "total_tokens": total_tokens}
            yield f"data: {json.dumps(done_event)}\n\n"
            return  # OpenAI succeeded — done

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

            if not is_quota_or_auth or is_testing:
                error_event = {"type": "error", "message": f"Generation failed: {str(e)}"}
                yield f"data: {json.dumps(error_event)}\n\n"
                return

    # --- Gemini Fallback Path (reached when OpenAI skipped or quota/auth failed) ---
    if is_quota_or_auth:
        logger.warning("Initiating Gemini fallback for code generation...")

        fallback_msg = {
            "type": "plan",
            "content": "Falling back to Gemini for code generation..."
        }
        yield f"data: {json.dumps(fallback_msg)}\n\n"

        from google import genai
        from google.genai import types

        try:
            if not settings.gemini_api_key:
                raise ValueError("Gemini API key is not configured.")
            gemini_client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as init_err:
            logger.error(f"Failed to initialize Gemini client: {init_err}")
            error_event = {"type": "error", "message": f"Gemini client initialization failed: {str(init_err)}"}
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-flash-latest",
            "gemini-2.5-pro",
        ]


        for model_name_gemini in fallback_models:
            logger.info(f"Initiating fallback to {model_name_gemini} for code generation...")

            status_msg = {"type": "plan", "content": f"Trying {model_name_gemini}..."}
            yield f"data: {json.dumps(status_msg)}\n\n"

            max_attempts = 3
            chunks_emitted = 0
            chars_emitted = 0
            gen_start_time = time.time()
            model_success = False

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"Querying Gemini API for code generation (Attempt {attempt}). Model: {model_name_gemini}, SDK: {genai.__version__}")

                    gemini_response = await gemini_client.aio.models.generate_content_stream(
                        model=model_name_gemini,
                        contents=f"Here is the UI design plan:\n{json.dumps(plan, indent=2)}",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            max_output_tokens=8192
                        )
                    )

                    async for gemini_chunk in gemini_response:
                        if gemini_chunk.text:
                            chunks_emitted += 1
                            chars_emitted += len(gemini_chunk.text)
                            chunk_event = {"type": "chunk", "content": gemini_chunk.text}
                            yield f"data: {json.dumps(chunk_event)}\n\n"

                    # Emit internal done event (orchestrator reads it, client ignores it)
                    done_event = {"type": "generator_done", "total_tokens": 0}
                    yield f"data: {json.dumps(done_event)}\n\n"
                    model_success = True
                    return  # Successfully completed

                except Exception as gemini_err:
                    err_str = str(gemini_err)

                    # 1. Failed mid-stream
                    if chunks_emitted > 0:
                        logger.error(f"Gemini streaming failed mid-stream: {gemini_err}", exc_info=True)
                        partial_event = {
                            "type": "partial_success",
                            "content": f"Generation partially completed before upstream error: {err_str}"
                        }
                        yield f"data: {json.dumps(partial_event)}\n\n"
                        return

                    # 2. Check for Quota / Rate limit (429)
                    is_quota = "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str or "NOT_FOUND" in err_str
                    if is_quota:
                        logger.warning(f"Quota/not-found for {model_name_gemini}. Trying next fallback model.")
                        quota_msg = {"type": "plan", "content": f"{model_name_gemini} unavailable, trying next..."}
                        yield f"data: {json.dumps(quota_msg)}\n\n"
                        break  # Break inner loop, try next fallback model

                    # 3. Check for 503 / Unavailable
                    is_503 = "503" in err_str or "UNAVAILABLE" in err_str.upper() or "high demand" in err_str.lower()
                    if is_503 and attempt < max_attempts:
                        wait_time = 2 if attempt == 1 else 5
                        logger.warning(f"Gemini 503 Unavailable. Retrying {model_name_gemini} in {wait_time}s (Attempt {attempt}/{max_attempts})...")
                        await asyncio.sleep(wait_time)
                        continue

                    # Failed completely for other reasons
                    logger.error(f"Gemini code generation failed on attempt {attempt}: {gemini_err}", exc_info=True)
                    break  # Break inner loop, try next fallback model

        # If all fallback models failed
        quota_error_event = {
            "type": "error",
            "code": "MODEL_QUOTA_EXCEEDED",
            "message": "AI generation quota exhausted. Please try again later."
        }
        yield f"data: {json.dumps(quota_error_event)}\n\n"
