import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from models import TaskCreate, TaskResponse
from services.yaml_service import YAMLService
from services.hermes_service import HermesService
import asyncio

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

yaml_service = YAMLService()
hermes_service = HermesService()
tasks_store: dict[str, TaskResponse] = {}


@router.post("", response_model=TaskResponse)
async def create_task(task_create: TaskCreate):
    template = yaml_service.get_template(task_create.prompt_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Prompt '{task_create.prompt_id}' not found")

    try:
        rendered_prompt = yaml_service.render_prompt(template, task_create.variables)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to render prompt: {str(e)}")

    task_id = str(uuid.uuid4())
    task = TaskResponse(
        id=task_id,
        status="pending",
        prompt_id=task_create.prompt_id,
    )
    tasks_store[task_id] = task
    asyncio.create_task(_run_task(task_id, rendered_prompt, task_create.model))
    return task


async def _run_task(task_id: str, prompt: str, model: str):
    task = tasks_store.get(task_id)
    if not task:
        return
    task.status = "running"
    result_parts = []
    try:
        async for chunk in hermes_service.stream_completion(prompt, model):
            result_parts.append(chunk)
        task.result = "".join(result_parts)
        task.status = "completed"
    except Exception as e:
        task.error = str(e)
        task.status = "failed"
    finally:
        task.completed_at = datetime.now()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@router.get("/stream/{task_id}")
async def stream_task(task_id: str):
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    async def event_generator():
        while task.status == "pending":
            await asyncio.sleep(0.1)
        if task.status == "failed":
            yield {"event": "error", "data": task.error}
            return
        last_length = 0
        while task.status == "running":
            if task.result and len(task.result) > last_length:
                new_content = task.result[last_length:]
                last_length = len(task.result)
                yield {"event": "message", "data": new_content}
            await asyncio.sleep(0.1)
        if task.result and len(task.result) > last_length:
            yield {"event": "message", "data": task.result[last_length:]}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())
