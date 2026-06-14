from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import json

from app.main import app
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import check_rate_limit

# Create synchronous TestClient
client = TestClient(app)

class MockUser:
    """Mock User class mimicking Supabase user attributes."""
    def __init__(self, user_id="11111111-1111-1111-1111-111111111111", email="test@example.com"):
        self.id = user_id
        self.email = email

@pytest.fixture(autouse=True)
def override_dependencies():
    """Dependency override fixture for FastAPI routes requiring auth or rate limiting."""
    mock_user = MockUser()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[check_rate_limit] = lambda: mock_user
    yield
    app.dependency_overrides.clear()

def test_health_check():
    """Test health check route."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data

@patch("app.api.generate.orchestrator.run")
def test_generate_ui_success(mock_orchestrator_run):
    """Test successful stream response from POST /generate-ui endpoint."""
    async def mock_run(request, user_id):
        yield "data: {\"type\": \"plan\", \"content\": \"Planning UI architecture...\"}\n\n"
        yield "data: {\"type\": \"chunk\", \"content\": \"export function Test() {}\"}\n\n"
        yield "data: {\"type\": \"done\", \"project_id\": \"11111111-1111-1111-1111-111111111111\", \"total_tokens\": 100}\n\n"

    mock_orchestrator_run.side_effect = mock_run

    payload = {
        "prompt": "Build a landing page",
        "style": "minimal",
        "framework": "react-tailwind"
    }
    
    response = client.post("/generate-ui", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Read streamed event lines
    lines = [line for line in response.iter_lines() if line]
    assert len(lines) == 3
    assert "Planning UI architecture" in lines[0]
    assert "export function Test()" in lines[1]
    assert "done" in lines[2]
    assert "11111111-1111-1111-1111-111111111111" in lines[2]

def test_generate_ui_validation_error():
    """Test POST /generate-ui payload validation errors yield 422."""
    # prompt is missing
    payload = {
        "style": "minimal",
        "framework": "react-tailwind"
    }
    response = client.post("/generate-ui", json=payload)
    assert response.status_code == 422

def test_improve_ui_success():
    """Test POST /improve-ui stub route."""
    pid = str(uuid4())
    payload = {
        "project_id": pid,
        "instruction": "Make the header larger"
    }
    response = client.post("/improve-ui", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stub"
    assert data["received"]["project_id"] == pid
    assert data["received"]["instruction"] == "Make the header larger"

def test_improve_ui_validation_error():
    """Test POST /improve-ui yields 422 if project_id is invalid uuid."""
    payload = {
        "project_id": "invalid-uuid-string",
        "instruction": "Fix layout"
    }
    response = client.post("/improve-ui", json=payload)
    assert response.status_code == 422

def test_list_projects():
    """Test GET /projects stub route."""
    response = client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["title"] == "Stub Project"

def test_get_project():
    """Test GET /project/{project_id} stub route."""
    pid = str(uuid4())
    response = client.get(f"/project/{pid}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pid
    assert data["title"] == "Stub Project"

def test_delete_project():
    """Test DELETE /project/{project_id} stub route."""
    pid = str(uuid4())
    response = client.delete(f"/project/{pid}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "deleted_by" in data

def test_export_project():
    """Test POST /export-project stub route."""
    pid = str(uuid4())
    payload = {
        "project_id": pid
    }
    response = client.post("/export-project", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
    assert pid in data["download_url"]
