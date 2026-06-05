import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_tasks_store():
    """Reset tasks_store before each test."""
    with patch.dict("routers.tasks.tasks_store", {}, clear=True):
        yield


@pytest.fixture
def mock_yaml_service():
    """Mock YAMLService to avoid file I/O."""
    with patch("routers.tasks.yaml_service") as mock:
        mock.get_template.return_value = MagicMock(
            id="test-prompt",
            prompt="Hello {{name}}",
            variables=["name"],
        )
        mock.render_prompt.return_value = "Hello Alice"
        yield mock


@pytest.fixture
def mock_hermes_service():
    """Mock HermesService.stream_completion."""
    with patch("routers.tasks.hermes_service") as mock:
        async def fake_stream(*args, **kwargs):
            yield "Hello"
            yield " "
            yield "World"

        mock.stream_completion = fake_stream
        yield mock


class TestCreateTask:
    def test_create_task_success(self, mock_yaml_service, mock_hermes_service):
        response = client.post("/api/tasks", json={
            "prompt_id": "test-prompt",
            "variables": {"name": "Alice"},
            "model": "gemma-4-12b"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["prompt_id"] == "test-prompt"
        assert "id" in data

    def test_create_task_prompt_not_found(self, mock_yaml_service):
        mock_yaml_service.get_template.return_value = None
        response = client.post("/api/tasks", json={
            "prompt_id": "nonexistent",
            "variables": {}
        })
        assert response.status_code == 404
        assert "nonexistent" in response.json()["detail"]

    def test_create_task_render_error(self, mock_yaml_service):
        mock_yaml_service.render_prompt.side_effect = ValueError("bad var")
        response = client.post("/api/tasks", json={
            "prompt_id": "test-prompt",
            "variables": {}
        })
        assert response.status_code == 400
        assert "Failed to render prompt" in response.json()["detail"]


class TestGetTask:
    def test_get_task_success(self, mock_yaml_service, mock_hermes_service):
        # Create a task first
        create_resp = client.post("/api/tasks", json={
            "prompt_id": "test-prompt",
            "variables": {"name": "Alice"}
        })
        task_id = create_resp.json()["id"]

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id

    def test_get_task_not_found(self):
        response = client.get("/api/tasks/nonexistent-id")
        assert response.status_code == 404
        assert "nonexistent-id" in response.json()["detail"]


class TestStreamTask:
    def test_stream_task_not_found(self):
        response = client.get("/api/tasks/stream/nonexistent-id")
        assert response.status_code == 404

    def test_stream_task_success(self, mock_yaml_service, mock_hermes_service):
        # Create a task
        create_resp = client.post("/api/tasks", json={
            "prompt_id": "test-prompt",
            "variables": {"name": "Alice"}
        })
        task_id = create_resp.json()["id"]

        response = client.get(f"/api/tasks/stream/{task_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
