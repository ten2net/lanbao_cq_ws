import yaml
from pathlib import Path
from typing import Optional
from models import PromptsConfig, PromptTemplate
from config import YAML_PATH


class YAMLService:
    def __init__(self, yaml_path: str = YAML_PATH):
        self.yaml_path = Path(yaml_path)
        self._ensure_exists()

    def _ensure_exists(self):
        if not self.yaml_path.exists():
            self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
            self._save(PromptsConfig(
                version="1.0",
                metadata={},
                categories={},
                templates=[]
            ))

    def _load_raw(self) -> dict:
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _save(self, config: PromptsConfig):
        with open(self.yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False)

    def get_config(self) -> PromptsConfig:
        raw = self._load_raw()
        return PromptsConfig(**raw)

    def get_templates(self) -> list[PromptTemplate]:
        return self.get_config().templates

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        for t in self.get_templates():
            if t.id == template_id:
                return t
        return None

    def add_template(self, template: PromptTemplate) -> PromptTemplate:
        config = self.get_config()
        if any(t.id == template.id for t in config.templates):
            raise ValueError(f"Template with id '{template.id}' already exists")
        config.templates.append(template)
        self._save(config)
        return template

    def update_template(self, template_id: str, template: PromptTemplate) -> Optional[PromptTemplate]:
        config = self.get_config()
        for i, t in enumerate(config.templates):
            if t.id == template_id:
                config.templates[i] = template
                self._save(config)
                return template
        return None

    def delete_template(self, template_id: str) -> bool:
        config = self.get_config()
        original_len = len(config.templates)
        config.templates = [t for t in config.templates if t.id != template_id]
        if len(config.templates) < original_len:
            self._save(config)
            return True
        return False

    def render_prompt(self, template: PromptTemplate, variables: dict[str, str]) -> str:
        result = template.prompt
        for var_name in template.variables:
            placeholder = f"{{{{{var_name}}}}}"
            result = result.replace(placeholder, variables.get(var_name, ""))
        return result
