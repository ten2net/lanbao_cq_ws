import os
import pytest
from datetime import datetime
from pathlib import Path
from models import PromptTemplate, PromptsConfig
from services.yaml_service import YAMLService


@pytest.fixture
def temp_yaml_path(tmp_path):
    return str(tmp_path / "test_prompts.yaml")


@pytest.fixture
def yaml_service(temp_yaml_path):
    return YAMLService(yaml_path=temp_yaml_path)


@pytest.fixture
def sample_template():
    return PromptTemplate(
        id="test-1",
        name="Test Template",
        category="bull",
        keywords=["test", "bull"],
        prompt="Analyze {{stock}} for bullish signals.",
        variables=["stock"],
        description="A test template"
    )


class TestYAMLService:
    def test_init_creates_default_config(self, temp_yaml_path):
        service = YAMLService(yaml_path=temp_yaml_path)
        assert Path(temp_yaml_path).exists()
        config = service.get_config()
        assert config.version == "1.0"
        assert config.templates == []
        assert config.metadata == {}
        assert config.categories == {}

    def test_add_template(self, yaml_service, sample_template):
        result = yaml_service.add_template(sample_template)
        assert result.id == "test-1"
        templates = yaml_service.get_templates()
        assert len(templates) == 1
        assert templates[0].name == "Test Template"

    def test_add_duplicate_template_raises(self, yaml_service, sample_template):
        yaml_service.add_template(sample_template)
        with pytest.raises(ValueError, match="already exists"):
            yaml_service.add_template(sample_template)

    def test_get_template(self, yaml_service, sample_template):
        yaml_service.add_template(sample_template)
        found = yaml_service.get_template("test-1")
        assert found is not None
        assert found.name == "Test Template"

    def test_get_template_not_found(self, yaml_service):
        assert yaml_service.get_template("nonexistent") is None

    def test_update_template(self, yaml_service, sample_template):
        yaml_service.add_template(sample_template)
        updated = PromptTemplate(
            id="test-1",
            name="Updated Template",
            category="bear",
            keywords=["updated"],
            prompt="Updated prompt.",
            variables=[],
            description="Updated description"
        )
        result = yaml_service.update_template("test-1", updated)
        assert result is not None
        assert result.name == "Updated Template"
        assert result.category == "bear"

    def test_update_template_not_found(self, yaml_service, sample_template):
        result = yaml_service.update_template("nonexistent", sample_template)
        assert result is None

    def test_delete_template(self, yaml_service, sample_template):
        yaml_service.add_template(sample_template)
        assert yaml_service.delete_template("test-1") is True
        assert yaml_service.get_template("test-1") is None

    def test_delete_template_not_found(self, yaml_service):
        assert yaml_service.delete_template("nonexistent") is False

    def test_render_prompt(self, sample_template):
        service = YAMLService(yaml_path="/tmp/dummy.yaml")
        result = service.render_prompt(sample_template, {"stock": "AAPL"})
        assert result == "Analyze AAPL for bullish signals."

    def test_render_prompt_missing_variable(self, sample_template):
        service = YAMLService(yaml_path="/tmp/dummy.yaml")
        result = service.render_prompt(sample_template, {})
        assert result == "Analyze  for bullish signals."
