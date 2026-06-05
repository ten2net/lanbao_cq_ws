import os
import pytest
import tempfile
from fastapi.testclient import TestClient

# Set a temporary YAML path before importing anything that uses it
@pytest.fixture(scope="module", autouse=True)
def temp_yaml_path():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write('version: "1.0"\n')
        f.write('metadata: {}\n')
        f.write('categories:\n')
        f.write('  bull:\n')
        f.write('    name: 看涨\n')
        f.write('  bear:\n')
        f.write('    name: 看跌\n')
        f.write('  oscillation:\n')
        f.write('    name: 震荡\n')
        f.write('templates: []\n')
        temp_path = f.name

    os.environ["YAML_PATH"] = temp_path

    # Need to reload modules to pick up the new env var
    import importlib
    import config
    importlib.reload(config)

    import services.yaml_service
    importlib.reload(services.yaml_service)

    import routers.prompts
    importlib.reload(routers.prompts)

    import main
    importlib.reload(main)

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def client(temp_yaml_path):
    from main import app
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_prompts_empty(client):
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0"
    assert "categories" in data


def test_create_prompt(client):
    payload = {
        "id": "test-bull-1",
        "name": "Test Bull Prompt",
        "category": "bull",
        "keywords": ["test", "bull"],
        "prompt": "Analyze {{stock}} bullish trend.",
        "variables": ["stock"],
        "description": "A test prompt"
    }
    response = client.post("/api/prompts", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-bull-1"
    assert data["name"] == "Test Bull Prompt"
    assert data["category"] == "bull"


def test_get_prompt(client):
    response = client.get("/api/prompts/test-bull-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-bull-1"


def test_get_prompt_not_found(client):
    response = client.get("/api/prompts/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]


def test_delete_prompt(client):
    response = client.delete("/api/prompts/test-bull-1")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]

    # Verify it's gone
    response = client.get("/api/prompts/test-bull-1")
    assert response.status_code == 404
