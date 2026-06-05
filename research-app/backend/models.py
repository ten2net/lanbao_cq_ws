from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    id: str
    name: str
    category: str = Field(pattern=r"^(bull|bear|oscillation)$")
    keywords: list[str]
    prompt: str
    variables: list[str] = []
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PromptsConfig(BaseModel):
    version: str
    metadata: dict
    categories: dict
    templates: list[PromptTemplate]


class TaskCreate(BaseModel):
    prompt_id: str
    variables: dict[str, str] = {}
    model: str = "gemma-4-12b"


class TaskResponse(BaseModel):
    id: str
    status: str = Field(pattern=r"^(pending|running|completed|failed)$")
    prompt_id: str
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
