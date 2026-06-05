from fastapi import APIRouter, HTTPException
from models import PromptTemplate, PromptsConfig
from services.yaml_service import YAMLService

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

yaml_service = YAMLService()

@router.get("", response_model=dict)
def list_prompts():
    config = yaml_service.get_config()
    templates = yaml_service.get_templates()
    grouped = {}
    for cat_key, cat_info in config.categories.items():
        grouped[cat_key] = {
            "info": cat_info,
            "templates": [t for t in templates if t.category == cat_key]
        }
    return {
        "version": config.version,
        "metadata": config.metadata,
        "categories": grouped
    }

@router.get("/{prompt_id}", response_model=PromptTemplate)
def get_prompt(prompt_id: str):
    template = yaml_service.get_template(prompt_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return template

@router.post("", response_model=PromptTemplate)
def create_prompt(template: PromptTemplate):
    try:
        return yaml_service.add_template(template)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.put("/{prompt_id}", response_model=PromptTemplate)
def update_prompt(prompt_id: str, template: PromptTemplate):
    updated = yaml_service.update_template(prompt_id, template)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return updated

@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str):
    deleted = yaml_service.delete_template(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return {"message": f"Prompt '{prompt_id}' deleted"}
