from unittest.mock import MagicMock, AsyncMock, patch, ANY
import pytest
import json
from app.models.requests import GenerateUIRequest

from app.services.orchestrator import run
from app.services.prompt_parser import ParsedPrompt
from app.services.validator import ValidationResult

class AsyncGenMock:
    def __init__(self, events):
        self.events = list(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)

def make_mock_stream(code_content="export function Comp() {}", tokens=100):
    events = [
        'data: {"type": "plan", "content": "Generating components..."}\n\n',
        f'data: {{"type": "chunk", "content": "{code_content}"}}\n\n',
        f'data: {{"type": "done", "total_tokens": {tokens}}}\n\n'
    ]
    return AsyncGenMock(events)

@pytest.fixture
def mock_request():
    return GenerateUIRequest(prompt="Build a landing page", style="minimal", framework="react-tailwind")

@pytest.fixture
def dummy_parsed_prompt():
    return ParsedPrompt(
        ui_type="landing_page",
        color_style="minimal",
        sections=["hero"],
        complexity_level="simple",
        raw_prompt="Build a landing page"
    )

@pytest.mark.asyncio
@patch("app.services.prompt_parser.parse")
@patch("app.services.planner.plan")
@patch("app.services.generator.generate")
@patch("app.services.validator.validate")
@patch("app.db.supabase.create_project")
@patch("app.db.supabase.update_project_code")
@patch("app.db.supabase.log_generation")
async def test_orchestrator_success_path(
    mock_log_gen,
    mock_update_code,
    mock_create_project,
    mock_validate,
    mock_generate,
    mock_plan,
    mock_parse,
    mock_request,
    dummy_parsed_prompt
):
    """Test successful generation path with 1 parse, plan, generate, validate, and db save."""
    mock_parse.return_value = dummy_parsed_prompt
    mock_plan.return_value = {"layout": "flex", "components": []}
    mock_generate.return_value = make_mock_stream("export function SuccessComp() {}", tokens=80)
    mock_validate.return_value = ValidationResult(is_valid=True, errors=[])
    
    mock_create_project.return_value = {"id": "11111111-1111-1111-1111-111111111111"}
    mock_update_code.return_value = {"id": "11111111-1111-1111-1111-111111111111"}
    mock_log_gen.return_value = {"id": "log-id"}

    events = []
    async for event in run(mock_request, user_id="user-id"):
        events.append(event)

    # 1 (plan node start) + 1 (gen start) + 1 (chunk) + 1 (gen done) + 1 (orchestrator done) = 5 events
    assert len(events) == 5
    
    # Assert last event is 'done' with project_id
    done_data = json.loads(events[-1].replace("data: ", "").strip())
    assert done_data["type"] == "done"
    assert done_data["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert done_data["total_tokens"] == 80

    mock_parse.assert_called_once()
    mock_plan.assert_called_once()
    mock_generate.assert_called_once()
    mock_validate.assert_called_once()
    mock_create_project.assert_called_once_with(user_id="user-id", title="Build a landing page", prompt=mock_request.prompt)
    mock_update_code.assert_called_once_with("11111111-1111-1111-1111-111111111111", "export function SuccessComp() {}")
    mock_log_gen.assert_called_once_with(
        project_id="11111111-1111-1111-1111-111111111111",
        model="gpt-4o",
        tokens=80,
        latency=ANY,
        status="completed"
    )

@pytest.mark.asyncio
@patch("app.services.prompt_parser.parse")
@patch("app.services.planner.plan")
@patch("app.services.generator.generate")
@patch("app.services.validator.validate")
@patch("app.db.supabase.create_project")
@patch("app.db.supabase.update_project_code")
@patch("app.db.supabase.log_generation")
async def test_orchestrator_repair_path(
    mock_log_gen,
    mock_update_code,
    mock_create_project,
    mock_validate,
    mock_generate,
    mock_plan,
    mock_parse,
    mock_request,
    dummy_parsed_prompt
):
    """Test validation failure triggers a retry generation and succeeds on second attempt."""
    mock_parse.return_value = dummy_parsed_prompt
    mock_plan.return_value = {"layout": "flex"}
    
    # First generate returns broken code, second returns fixed code
    mock_generate.side_effect = [
        make_mock_stream("export function Bad() {", tokens=50),
        make_mock_stream("export function Fixed() {}", tokens=90)
    ]
    
    # First validation fails, second succeeds
    mock_validate.side_effect = [
        ValidationResult(is_valid=False, errors=["Mismatched tags"]),
        ValidationResult(is_valid=True, errors=[])
    ]
    
    mock_create_project.return_value = {"id": "project-id"}
    mock_update_code.return_value = {"id": "project-id"}

    events = []
    async for event in run(mock_request, user_id="user-id"):
        events.append(event)

    # 2 calls to generate
    assert mock_generate.call_count == 2
    assert mock_validate.call_count == 2
    mock_create_project.assert_called_once()
    mock_update_code.assert_called_once_with("project-id", "export function Fixed() {}")

@pytest.mark.asyncio
@patch("app.services.prompt_parser.parse")
@patch("app.services.planner.plan")
@patch("app.services.generator.generate")
@patch("app.services.validator.validate")
@patch("app.db.supabase.create_project")
@patch("app.db.supabase.log_generation")
async def test_orchestrator_max_retries_failure(
    mock_log_gen,
    mock_create_project,
    mock_validate,
    mock_generate,
    mock_plan,
    mock_parse,
    mock_request,
    dummy_parsed_prompt
):
    """Test that validating fails twice leads to maximum retries, errors out, and logs failure."""
    mock_parse.return_value = dummy_parsed_prompt
    mock_plan.return_value = {"layout": "flex"}
    mock_generate.side_effect = lambda *args, **kwargs: make_mock_stream("export function Broken() {", tokens=40)
    
    # Both attempts fail validation
    mock_validate.return_value = ValidationResult(is_valid=False, errors=["Mismatched tags"])

    events = []
    async for event in run(mock_request, user_id="user-id"):
        events.append(event)

    # validate called twice (attempt 1 and attempt 2)
    assert mock_validate.call_count == 2
    assert mock_generate.call_count == 2
    
    # Should not save project on complete failure
    mock_create_project.assert_not_called()
    
    # Log failed generation record
    mock_log_gen.assert_called_once_with(
        project_id=None,
        model="gpt-4o",
        tokens=40,
        latency=ANY,
        status="failed"
    )
    
    # Last event from generator is error
    error_event = json.loads(events[-1].replace("data: ", "").strip())
    assert error_event["type"] == "error"
    assert "maximum retries" in error_event["message"]
