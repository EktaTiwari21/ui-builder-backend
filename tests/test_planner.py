from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import json
from app.services.planner import plan, PlannerError
from app.services.prompt_parser import ParsedPrompt

@pytest.fixture
def sample_parsed_prompt():
    return ParsedPrompt(
        ui_type="landing_page",
        color_style="minimal",
        sections=["hero", "pricing"],
        complexity_level="medium",
        raw_prompt="Build a landing page with hero and pricing"
    )

@pytest.fixture
def mock_valid_planner_response():
    return {
        "layout": "flex flex-col min-h-screen",
        "components": [
            {
                "name": "HeroSection",
                "description": "Large hero section with CTA",
                "tailwind_hints": "bg-slate-950 text-white py-20"
            },
            {
                "name": "PricingTable",
                "description": "3-tier pricing structure",
                "tailwind_hints": "grid grid-cols-3 gap-6 py-12"
            }
        ],
        "color_palette": {
            "primary": "bg-indigo-600",
            "secondary": "bg-slate-800",
            "accent": "text-pink-500",
            "background": "bg-white",
            "text": "text-slate-900"
        },
        "typography": {
            "heading_font": "Inter",
            "body_font": "Roboto",
            "scale": "major-third"
        }
    }

@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_planner_success(mock_client_class, sample_parsed_prompt, mock_valid_planner_response):
    """Test successful UI planning flow when Gemini API returns valid JSON."""
    with patch("app.config.settings.gemini_api_key", "valid_key"):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_valid_planner_response)
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await plan(sample_parsed_prompt)

        assert result["layout"] == mock_valid_planner_response["layout"]
        assert result["color_palette"]["primary"] == "bg-indigo-600"
        assert len(result["components"]) == 2
        mock_client.aio.models.generate_content.assert_called_once()
        mock_client_class.assert_called_once_with(api_key="valid_key")

@pytest.mark.asyncio
async def test_planner_missing_api_key(sample_parsed_prompt):
    """Test that plan raises PlannerError when API key is missing or dummy."""
    with patch("app.config.settings.gemini_api_key", None):
        with pytest.raises(PlannerError) as exc_info:
            await plan(sample_parsed_prompt)
        assert "Gemini API key is not configured" in str(exc_info.value)

@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_planner_api_failure(mock_client_class, sample_parsed_prompt):
    """Test that plan raises PlannerError on SDK/network exceptions."""
    with patch("app.config.settings.gemini_api_key", "valid_key"):
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API limit exceeded"))
        mock_client_class.return_value = mock_client

        with pytest.raises(PlannerError) as exc_info:
            await plan(sample_parsed_prompt)
        assert "Planning agent execution failed" in str(exc_info.value)

@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_planner_malformed_json(mock_client_class, sample_parsed_prompt):
    """Test that plan raises PlannerError when the response text is not valid JSON."""
    with patch("app.config.settings.gemini_api_key", "valid_key"):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is not JSON text content"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(PlannerError) as exc_info:
            await plan(sample_parsed_prompt)
        assert "Invalid JSON format in planner output" in str(exc_info.value)

@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_planner_missing_keys(mock_client_class, sample_parsed_prompt):
    """Test that plan raises PlannerError if required keys are missing in the JSON response."""
    with patch("app.config.settings.gemini_api_key", "valid_key"):
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Missing "typography" key
        mock_response.text = json.dumps({
            "layout": "flex",
            "components": [],
            "color_palette": {}
        })
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(PlannerError) as exc_info:
            await plan(sample_parsed_prompt)
        assert "Planner output missing key" in str(exc_info.value)
