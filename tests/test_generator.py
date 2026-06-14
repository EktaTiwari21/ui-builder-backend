from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import json
from app.services.generator import generate

# Helper class to mock asynchronous iterators
class AsyncIteratorMock:
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

def make_chunk(content=None, usage_tokens=None):
    """Create a mock ChatCompletionChunk object."""
    chunk = MagicMock()
    if content is not None:
        choice = MagicMock()
        choice.delta.content = content
        chunk.choices = [choice]
    else:
        chunk.choices = []
        
    if usage_tokens is not None:
        usage = MagicMock()
        usage.total_tokens = usage_tokens
        chunk.usage = usage
    else:
        chunk.usage = None
    return chunk

@pytest.mark.asyncio
@patch("app.services.generator.AsyncOpenAI")
async def test_generate_success(mock_openai_class):
    """Test successful JSX code generation stream and SSE events formatting."""
    with patch("app.config.settings.openai_api_key", "real-like-openai-key"):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        chunks = [
            make_chunk(content="export function "),
            make_chunk(content="PricingSection() {"),
            make_chunk(content=" return <div>Pricing</div>; }"),
            make_chunk(usage_tokens=150)
        ]
        
        mock_client.chat.completions.create = AsyncMock(return_value=AsyncIteratorMock(chunks))
        
        events = []
        async for event in generate({"layout": "grid"}):
            events.append(event)
            
        # Should yield: 1 start event + 3 content chunks + 1 done event = 5 events
        assert len(events) == 5
        
        # Check start event
        event_0 = json.loads(events[0].replace("data: ", "").strip())
        assert event_0["type"] == "plan"
        assert "Generating" in event_0["content"]
        
        # Check chunk events
        event_1 = json.loads(events[1].replace("data: ", "").strip())
        assert event_1["type"] == "chunk"
        assert event_1["content"] == "export function "
        
        event_3 = json.loads(events[3].replace("data: ", "").strip())
        assert event_3["content"] == " return <div>Pricing</div>; }"
        
        # Check done event
        event_4 = json.loads(events[4].replace("data: ", "").strip())
        assert event_4["type"] == "done"
        assert event_4["total_tokens"] == 150

@pytest.mark.asyncio
async def test_generate_missing_api_key():
    """Test that generator yields error event when API key is missing/dummy."""
    with patch("app.config.settings.openai_api_key", None):
        events = []
        async for event in generate({"layout": "grid"}):
            events.append(event)
            
        assert len(events) == 2  # Plan start event + Error event
        error_event = json.loads(events[1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "API key is not configured" in error_event["message"]

@pytest.mark.asyncio
@patch("app.services.generator.AsyncOpenAI")
async def test_generate_api_failure(mock_openai_class):
    """Test that generator yields error event if OpenAI API call fails."""
    with patch("app.config.settings.openai_api_key", "mock-openai-key"):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Rate limit reached"))
        
        events = []
        async for event in generate({"layout": "grid"}):
            events.append(event)
            
        assert len(events) == 2  # Plan start event + Error event
        error_event = json.loads(events[1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Rate limit reached" in error_event["message"]
