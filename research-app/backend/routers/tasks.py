import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from models import TaskCreate, TaskResponse
from services.yaml_service import YAMLService
from services.hermes_service import HermesService
import asyncio
import threading

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

yaml_service = YAMLService()
hermes_service = HermesService()
tasks_store: dict[str, TaskResponse] = {}


def _run_task_sync(task_id: str, prompt: str, model: str):
    """在独立的 event loop 中运行异步任务"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_task_async(task_id, prompt, model))
    except Exception as e:
        print(f"[_run_task_sync {task_id}] ERROR: {e}")
    finally:
        loop.close()


async def _run_task_async(task_id: str, prompt: str, model: str):
    print(f"[_run_task {task_id}] Starting, prompt_len={len(prompt)}, model={model}")
    task = tasks_store.get(task_id)
    if not task:
        print(f"[_run_task {task_id}] ERROR: Task not found in store")
        return
    task.status = "running"
    print(f"[_run_task {task_id}] Status set to running")
    try:
        from services.hermes_service import HermesService
        local_hermes = HermesService()
        chunk_count = 0
        async for chunk in local_hermes.stream_completion(prompt, model):
            chunk_count += 1
            if chunk_count <= 3:
                print(f"[_run_task {task_id}] Chunk {chunk_count}: {repr(chunk[:50])}")
            if task.result is None:
                task.result = chunk
            else:
                task.result += chunk
        print(f"[_run_task {task_id}] Completed with {chunk_count} chunks")
        task.status = "completed"
    except Exception as e:
        print(f"[_run_task {task_id}] ERROR: {type(e).__name__}: {e}")
        task.error = str(e)
        task.status = "failed"
    finally:
        task.completed_at = datetime.now()
        print(f"[_run_task {task_id}] Finished with status={task.status}")


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
    print(f"[create_task] Created task {task_id}")

    thread = threading.Thread(target=_run_task_sync, args=(task_id, rendered_prompt, task_create.model))
    thread.start()
    print(f"[create_task] Background thread started: {thread.ident}")

    return task


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
