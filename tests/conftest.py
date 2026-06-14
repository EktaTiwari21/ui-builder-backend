import pytest
from unittest.mock import MagicMock
from app.models.requests import GenerateUIRequest

@pytest.fixture
def valid_jsx_code() -> str:
    """Sample valid JSX component code block for testing."""
    return (
        "import React from 'react';\n"
        "import { Sparkles } from 'lucide-react';\n\n"
        "export function PricingSection() {\n"
        "    return (\n"
        "        <div className=\"bg-slate-900 p-8 text-white\">\n"
        "            <Sparkles className=\"h-5 w-5 text-indigo-400\" />\n"
        "            <h2 className=\"text-2xl font-bold\">Choose your plan</h2>\n"
        "        </div>\n"
        "    );\n"
        "}"
    )

@pytest.fixture
def generate_ui_request() -> GenerateUIRequest:
    """Sample valid GenerateUIRequest fixture."""
    return GenerateUIRequest(
        prompt="Build a SaaS pricing page with 3 tiers",
        style="minimal",
        framework="react-tailwind"
    )

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client instance."""
    client = MagicMock()
    client.auth = MagicMock()
    return client

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client instance."""
    return MagicMock()

@pytest.fixture
def mock_gemini_client():
    """Mock Gemini SDK client instance."""
    return MagicMock()
