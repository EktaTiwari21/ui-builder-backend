import json
import logging
from google import genai
from google.genai import types
from app.config import settings
from app.services.prompt_parser import ParsedPrompt

logger = logging.getLogger(__name__)

class PlannerError(Exception):
    """Exception raised when the Gemini planning service fails."""
    pass

async def plan(parsed_prompt: ParsedPrompt) -> dict:
    """Generate a detailed UI planning structure using Gemini 1.5 Pro.
    
    Args:
        parsed_prompt: Parsed metadata of the prompt from prompt_parser.
        
    Returns:
        dict: The planned layout, components list, color palette, and typography configurations.
        
    Raises:
        PlannerError: If the Gemini client config is missing, API fails, or response is invalid.
    """
    if not settings.gemini_api_key or settings.gemini_api_key == "dummy-gemini-key":
        raise PlannerError("Gemini API key is not configured in environment variables.")

    try:
        # Initialize the new google-genai Client
        client = genai.Client(api_key=settings.gemini_api_key)

        system_instruction = (
            "You are an expert UI architect specializing in React and Tailwind CSS.\n"
            "Given a parsed user prompt and its architectural metadata, design the UI layout, component hierarchy, color palette, and typography.\n"
            "Your response must be a single, valid JSON object with the following schema:\n"
            "{\n"
            "  \"layout\": \"String describing the overall layout (container, alignment, responsiveness)\",\n"
            "  \"components\": [\n"
            "    { \"name\": \"ComponentName\", \"description\": \"Description\", \"tailwind_hints\": \"recommended tailwind classes\" }\n"
            "  ],\n"
            "  \"color_palette\": {\n"
            "    \"primary\": \"primary class/color\",\n"
            "    \"secondary\": \"secondary class/color\",\n"
            "    \"accent\": \"accent class/color\",\n"
            "    \"background\": \"bg class/color\",\n"
            "    \"text\": \"text class/color\"\n"
            "  },\n"
            "  \"typography\": {\n"
            "    \"heading_font\": \"Font name\",\n"
            "    \"body_font\": \"Font name\",\n"
            "    \"scale\": \"typographic scale\"\n"
            "  }\n"
            "}"
        )

        prompt_input = (
            f"UI Type: {parsed_prompt.ui_type}\n"
            f"Color Style: {parsed_prompt.color_style}\n"
            f"Sections: {', '.join(parsed_prompt.sections)}\n"
            f"Complexity: {parsed_prompt.complexity_level}\n"
            f"User Prompt: {parsed_prompt.raw_prompt}\n"
        )

        # Query the API asynchronously using the new Client.aio namespace
        response = await client.aio.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt_input,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                max_output_tokens=2000
            )
        )

        if not response or not response.text:
            raise PlannerError("Gemini API returned an empty response.")

        plan_data = json.loads(response.text)

        # Validate layout structure response
        required_keys = ["layout", "components", "color_palette", "typography"]
        for key in required_keys:
            if key not in plan_data:
                raise PlannerError(f"Planner output missing key: '{key}'")

        return plan_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode planner response as JSON: {e}")
        raise PlannerError(f"Invalid JSON format in planner output: {str(e)}")
    except Exception as e:
        logger.error(f"Planning agent execution failed: {e}")
        raise PlannerError(f"Planning agent execution failed: {str(e)}")
