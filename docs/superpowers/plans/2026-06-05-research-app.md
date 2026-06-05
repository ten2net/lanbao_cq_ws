# 揽宝智能投研 Web App 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 Vite + React + FastAPI 的智能投研 Web 应用，集成到现有 Docker Compose 栈中，支持提示词模板驱动的投研任务执行和 Markdown 流式输出。

**Architecture:** FastAPI 后端提供 Prompts/Tasks API 并代理 Hermes 请求，React 前端通过 SSE 流式接收结果，YAML 文件持久化提示词配置，localStorage 持久化历史记录。

**Tech Stack:** React 19 + Vite + Tailwind CSS + shadcn/ui + FastAPI + uvicorn + PyYAML + httpx

---

## 文件结构

```
research-app/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置常量
│   ├── models.py            # Pydantic 模型
│   ├── services/
│   │   ├── yaml_service.py  # YAML 读写服务
│   │   └── hermes_service.py # Hermes API 代理
│   └── routers/
│       ├── prompts.py       # 提示词 CRUD API
│       └── tasks.py         # 任务管理 + SSE 流式
├── frontend/
│   ├── Dockerfile           # 多阶段构建: Node → nginx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── components.json      # shadcn/ui 配置
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── components/
│       │   ├── Header.tsx
│       │   ├── MarketTabs.tsx
│       │   ├── PromptCard.tsx
│       │   ├── ResultPanel.tsx
│       │   └── HistoryDrawer.tsx
│       ├── context/
│       │   └── AppContext.tsx
│       ├── types/
│       │   └── index.ts
│       └── lib/
│           ├── api.ts       # API 客户端
│           └── utils.ts     # 工具函数
└── data/
    └── prompts.yaml         # 提示词模板库
```

---

### Task 1: 项目目录结构和 Docker 基础

**Files:**
- Create: `research-app/backend/Dockerfile`
- Create: `research-app/backend/requirements.txt`
- Create: `research-app/frontend/Dockerfile`
- Create: `research-app/data/prompts.yaml`
- Modify: `docker-compose.yml`

- [ ] **Step 1: 创建 backend Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 backend requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.0
pyyaml==6.0.2
httpx==0.27.0
sse-starlette==2.1.0
python-multipart==0.0.17
```

- [ ] **Step 3: 创建 frontend Dockerfile（多阶段构建）**

```dockerfile
# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: 创建 frontend nginx.conf**

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://research-app-backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 5: 创建初始 prompts.yaml**

```yaml
version: "1.0"
metadata:
  last_updated: "2026-06-05"
  author: "揽宝投研团队"

categories:
  bull:
    name: 牛市环境
    icon: "trending-up"
    color: "#ef4444"
  bear:
    name: 熊市环境
    icon: "trending-down"
    color: "#22c55e"
  oscillation:
    name: 震荡市环境
    icon: "activity"
    color: "#f59e0b"

templates:
  - id: hot-sector-bull
    name: 热门板块提示词
    category: bull
    keywords: ["景气度", "政策溢价", "资金抱团"]
    description: 寻找轮动热点，分析资金高度活跃的板块
    variables: []
    prompt: |
      请作为一名超短线交易员，分析当前处于"高频换手"和"宽幅震荡"特征的热门板块。
      要求：
      ① 找出近期资金高度活跃、换手率处于上升通道的2-3个板块；
      ② 分析这些板块目前是在"缩量震荡"还是"放量波动"；
      ③ 总结这些板块的轮动规律（例如是政策联动还是题材变频）。

  - id: dragon-stock-bull
    name: 龙头个股提示词
    category: bull
    keywords: ["资金抱团", "趋势突破", "量能放大"]
    description: 寻找牛市中强势龙头
    variables: ["板块名称"]
    prompt: |
      请帮我扫描[{{板块名称}}]中处于"趋势加速"或"量价齐升"特征的龙头个股。
      要求：
      ① 列出突破关键压力位的标的；
      ② 给出支撑位、压力位及技术面关键信号；
      ③ 评估短线弹性。

  - id: defensive-sector-bear
    name: 防御板块提示词
    category: bear
    keywords: ["避险资产", "高股息", "护城河", "估值底"]
    description: 寻找熊市中的防御性机会
    variables: []
    prompt: |
      请作为一名价值投资者，在当前熊市环境下寻找具有"高股息+低估值+强护城河"特征的防御性板块...

  - id: swing-trade-osc
    name: 波段交易提示词
    category: oscillation
    keywords: ["换手率", "区间变动", "量能异动"]
    description: 捕捉震荡市中的波段机会
    variables: ["时间周期", "标的类型"]
    prompt: |
      请分析近{{时间周期}}内{{标的类型}}中处于"区间震荡+量能异动"特征的标的...
```

- [ ] **Step 6: 修改 docker-compose.yml 添加服务**

在现有 services 下追加：

```yaml
  research-app-backend:
    build: ./research-app/backend
    container_name: research-app-backend
    restart: unless-stopped
    ports:
      - "3201:8000"
    networks:
      - lanbao-network
    environment:
      - HERMES_API_KEY=${HERMES_API_KEY}
      - HERMES_BASE_URL=http://192.168.15.131:8642
      - YAML_PATH=/app/data/prompts.yaml
    volumes:
      - ./research-app/data:/app/data:rw
    depends_on:
      hermes:
        condition: service_healthy

  research-app-frontend:
    build: ./research-app/frontend
    container_name: research-app-frontend
    restart: unless-stopped
    ports:
      - "3200:80"
    networks:
      - lanbao-network
    depends_on:
      - research-app-backend
```

- [ ] **Step 7: 验证目录结构**

Run:
```bash
mkdir -p research-app/backend/services research-app/backend/routers
mkdir -p research-app/frontend/src/components research-app/frontend/src/context research-app/frontend/src/types research-app/frontend/src/lib
ls -R research-app/
```

Expected: 显示完整的目录结构

- [ ] **Step 8: Commit**

```bash
git add research-app/ docker-compose.yml
git commit -m "chore: initialize research-app project structure with Docker setup"
```

---

### Task 2: 后端数据模型和 YAML 服务

**Files:**
- Create: `research-app/backend/models.py`
- Create: `research-app/backend/config.py`
- Create: `research-app/backend/services/yaml_service.py`
- Create: `research-app/backend/tests/test_yaml_service.py`

- [ ] **Step 1: 创建 config.py**

```python
import os

HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://192.168.15.131:8642")
YAML_PATH = os.getenv("YAML_PATH", "/app/data/prompts.yaml")
```

- [ ] **Step 2: 创建 models.py**

```python
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
```

- [ ] **Step 3: 创建 yaml_service.py**

```python
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
```

- [ ] **Step 4: 写 YAML 服务测试**

```python
import pytest
import tempfile
import os
from pathlib import Path
from models import PromptTemplate
from services.yaml_service import YAMLService

@pytest.fixture
def temp_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
version: "1.0"
metadata: {}
categories: {}
templates:
  - id: test-1
    name: Test Template
    category: bull
    keywords: ["test"]
    prompt: "Hello {{name}}"
    variables: ["name"]
    description: "A test template"
""")
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def service(temp_yaml):
    return YAMLService(temp_yaml)

def test_get_templates(service):
    templates = service.get_templates()
    assert len(templates) == 1
    assert templates[0].id == "test-1"

def test_get_template_found(service):
    template = service.get_template("test-1")
    assert template is not None
    assert template.name == "Test Template"

def test_get_template_not_found(service):
    template = service.get_template("nonexistent")
    assert template is None

def test_render_prompt(service):
    template = service.get_template("test-1")
    result = service.render_prompt(template, {"name": "World"})
    assert result == "Hello World"

def test_add_template(service):
    new_template = PromptTemplate(
        id="test-2",
        name="New Template",
        category="bear",
        keywords=["new"],
        prompt="Test prompt"
    )
    added = service.add_template(new_template)
    assert added.id == "test-2"
    assert len(service.get_templates()) == 2

def test_add_duplicate_raises(service):
    duplicate = PromptTemplate(
        id="test-1",
        name="Duplicate",
        category="bull",
        keywords=["dup"],
        prompt="Dup"
    )
    with pytest.raises(ValueError):
        service.add_template(duplicate)

def test_delete_template(service):
    result = service.delete_template("test-1")
    assert result is True
    assert len(service.get_templates()) == 0

def test_delete_template_not_found(service):
    result = service.delete_template("nonexistent")
    assert result is False
```

- [ ] **Step 5: 运行测试**

Run:
```bash
cd research-app/backend
python -m pytest tests/test_yaml_service.py -v
```

Expected: 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add research-app/backend/models.py research-app/backend/config.py research-app/backend/services/yaml_service.py research-app/backend/tests/
git commit -m "feat(backend): add data models and YAML service with tests"
```

---

### Task 3: 后端 Prompts API

**Files:**
- Create: `research-app/backend/routers/prompts.py`
- Create: `research-app/backend/tests/test_prompts_api.py`
- Modify: `research-app/backend/main.py`

- [ ] **Step 1: 创建 prompts.py router**

```python
from fastapi import APIRouter, HTTPException
from typing import Optional
from models import PromptTemplate, PromptsConfig
from services.yaml_service import YAMLService

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

yaml_service = YAMLService()

@router.get("", response_model=dict)
def list_prompts():
    """Get all prompts grouped by category"""
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
    """Get a single prompt by ID"""
    template = yaml_service.get_template(prompt_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return template

@router.post("", response_model=PromptTemplate)
def create_prompt(template: PromptTemplate):
    """Create a new prompt template"""
    try:
        return yaml_service.add_template(template)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.put("/{prompt_id}", response_model=PromptTemplate)
def update_prompt(prompt_id: str, template: PromptTemplate):
    """Update an existing prompt template"""
    updated = yaml_service.update_template(prompt_id, template)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return updated

@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str):
    """Delete a prompt template"""
    deleted = yaml_service.delete_template(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return {"message": f"Prompt '{prompt_id}' deleted"}
```

- [ ] **Step 2: 创建 main.py 入口**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import prompts

app = FastAPI(title="揽宝智能投研 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 3: 写 Prompts API 测试**

```python
from fastapi.testclient import TestClient
import pytest
import tempfile
import os

# Mock YAML path for tests
import config
config.YAML_PATH = tempfile.mktemp(suffix=".yaml")

from main import app
from services.yaml_service import YAMLService
from models import PromptTemplate

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_yaml():
    # Initialize empty YAML
    service = YAMLService(config.YAML_PATH)
    if os.path.exists(config.YAML_PATH):
        os.unlink(config.YAML_PATH)
    yield

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_list_prompts_empty():
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data

def test_create_prompt():
    template = {
        "id": "test-bull",
        "name": "Test Bull",
        "category": "bull",
        "keywords": ["test"],
        "prompt": "Test prompt",
        "variables": [],
        "description": "Test"
    }
    response = client.post("/api/prompts", json=template)
    assert response.status_code == 200
    assert response.json()["id"] == "test-bull"

def test_get_prompt():
    # First create
    template = {
        "id": "test-get",
        "name": "Test Get",
        "category": "bear",
        "keywords": ["test"],
        "prompt": "Test",
        "variables": [],
        "description": "Test"
    }
    client.post("/api/prompts", json=template)

    # Then get
    response = client.get("/api/prompts/test-get")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Get"

def test_get_prompt_not_found():
    response = client.get("/api/prompts/nonexistent")
    assert response.status_code == 404

def test_delete_prompt():
    template = {
        "id": "test-del",
        "name": "Test Del",
        "category": "oscillation",
        "keywords": ["test"],
        "prompt": "Test",
        "variables": [],
        "description": "Test"
    }
    client.post("/api/prompts", json=template)

    response = client.delete("/api/prompts/test-del")
    assert response.status_code == 200

    # Verify deleted
    response = client.get("/api/prompts/test-del")
    assert response.status_code == 404
```

- [ ] **Step 4: 运行测试**

Run:
```bash
cd research-app/backend
python -m pytest tests/test_prompts_api.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add research-app/backend/main.py research-app/backend/routers/prompts.py research-app/backend/tests/test_prompts_api.py
git commit -m "feat(backend): add Prompts CRUD API with tests"
```

---

### Task 4: 后端 Tasks API + Hermes 代理 + SSE

**Files:**
- Create: `research-app/backend/services/hermes_service.py`
- Create: `research-app/backend/routers/tasks.py`
- Create: `research-app/backend/tests/test_tasks_api.py`
- Modify: `research-app/backend/main.py`

- [ ] **Step 1: 创建 hermes_service.py**

```python
import json
import httpx
from typing import AsyncGenerator
from config import HERMES_API_KEY, HERMES_BASE_URL

class HermesService:
    def __init__(self):
        self.base_url = HERMES_BASE_URL.rstrip("/")
        self.api_key = HERMES_API_KEY

    async def stream_completion(self, prompt: str, model: str = "gemma-4-12b") -> AsyncGenerator[str, None]:
        """Stream completion from Hermes via SSE"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True
                },
                timeout=300
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Hermes API error {response.status_code}: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
```

- [ ] **Step 2: 创建 tasks.py router**

```python
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

# In-memory task store (single user, local only)
tasks_store: dict[str, TaskResponse] = {}

@router.post("", response_model=TaskResponse)
async def create_task(task_create: TaskCreate):
    """Create a new research task"""
    template = yaml_service.get_template(task_create.prompt_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Prompt '{task_create.prompt_id}' not found")

    # Render prompt with variables
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

    # Start task in background
    asyncio.create_task(_run_task(task_id, rendered_prompt, task_create.model))

    return task

async def _run_task(task_id: str, prompt: str, model: str):
    """Run the task against Hermes"""
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
    """Get task status and result"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task

@router.get("/stream/{task_id}")
async def stream_task(task_id: str):
    """Stream task result via SSE"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    async def event_generator():
        # Wait for task to start
        while task.status == "pending":
            await asyncio.sleep(0.1)

        if task.status == "failed":
            yield {"event": "error", "data": task.error}
            return

        # Stream result as it builds
        last_length = 0
        while task.status == "running":
            if task.result and len(task.result) > last_length:
                new_content = task.result[last_length:]
                last_length = len(task.result)
                yield {"event": "message", "data": new_content}
            await asyncio.sleep(0.1)

        # Send final content
        if task.result and len(task.result) > last_length:
            yield {"event": "message", "data": task.result[last_length:]}

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())
```

- [ ] **Step 3: 修改 main.py 添加 tasks router**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import prompts, tasks

app = FastAPI(title="揽宝智能投研 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts.router)
app.include_router(tasks.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 4: 写 Tasks API 测试（mock Hermes）**

```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pytest

# Need to import after config setup
import config
import tempfile
config.YAML_PATH = tempfile.mktemp(suffix=".yaml")

from main import app
from services.yaml_service import YAMLService

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_prompt():
    service = YAMLService(config.YAML_PATH)
    # Add a test prompt
    from models import PromptTemplate
    try:
        service.add_template(PromptTemplate(
            id="test-task",
            name="Test Task",
            category="bull",
            keywords=["test"],
            prompt: "Analyze market",
            variables=[],
            description="Test"
        ))
    except:
        pass
    yield

def test_create_task():
    with patch("routers.tasks.hermes_service") as mock_hermes:
        mock_hermes.stream_completion = AsyncMock(return_value=async_gen(["Hello ", "World"]))

        response = client.post("/api/tasks", json={
            "prompt_id": "test-task",
            "variables": {},
            "model": "gemma-4-12b"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data

async def async_gen(items):
    for item in items:
        yield item

def test_get_task():
    with patch("routers.tasks.hermes_service") as mock_hermes:
        mock_hermes.stream_completion = AsyncMock(return_value=async_gen(["Result"]))

        # Create task
        create_resp = client.post("/api/tasks", json={
            "prompt_id": "test-task",
            "variables": {},
        })
        task_id = create_resp.json()["id"]

        # Get task
        get_resp = client.get(f"//tasks/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == task_id

def test_get_task_not_found():
    response = client.get("/api/tasks/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 5: 运行测试**

Run:
```bash
cd research-app/backend
python -m pytest tests/test_tasks_api.py -v
```

Expected: 4 tests PASS (或更多，取决于测试数量)

- [ ] **Step 6: Commit**

```bash
git add research-app/backend/services/hermes_service.py research-app/backend/routers/tasks.py research-app/backend/tests/test_tasks_api.py research-app/backend/main.py
git commit -m "feat(backend): add Tasks API with Hermes proxy and SSE streaming"
```

---

### Task 5: 前端项目初始化 + shadcn/ui 配置

**Files:**
- Create: `research-app/frontend/package.json`
- Create: `research-app/frontend/vite.config.ts`
- Create: `research-app/frontend/tailwind.config.js`
- Create: `research-app/frontend/components.json`
- Create: `research-app/frontend/tsconfig.json`
- Create: `research-app/frontend/index.html`
- Create: `research-app/frontend/src/main.tsx`
- Create: `research-app/frontend/src/index.css`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "research-app-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-markdown": "^10.0.0",
    "remark-gfm": "^4.0.0",
    "lucide-react": "^0.460.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3201',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

- [ ] **Step 4: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 5: 创建 tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>揽宝智能投研</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: 创建 main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 8: 创建 index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 9: 安装依赖并验证构建**

Run:
```bash
cd research-app/frontend
npm install
npm run build
```

Expected: 构建成功，生成 `dist/` 目录

- [ ] **Step 10: Commit**

```bash
git add research-app/frontend/package.json research-app/frontend/vite.config.ts research-app/frontend/tailwind.config.js research-app/frontend/tsconfig.json research-app/frontend/tsconfig.node.json research-app/frontend/index.html research-app/frontend/src/main.tsx research-app/frontend/src/index.css
git commit -m "chore(frontend): initialize React + Vite + Tailwind project"
```

---

### Task 6: 前端类型定义 + API 客户端

**Files:**
- Create: `research-app/frontend/src/types/index.ts`
- Create: `research-app/frontend/src/lib/api.ts`
- Create: `research-app/frontend/src/lib/utils.ts`

- [ ] **Step 1: 创建类型定义**

```typescript
export interface PromptTemplate {
  id: string;
  name: string;
  category: 'bull' | 'bear' | 'oscillation';
  keywords: string[];
  prompt: string;
  variables: string[];
  description: string;
  created_at: string;
  updated_at: string;
}

export interface CategoryInfo {
  name: string;
  icon: string;
  color: string;
}

export interface PromptsResponse {
  version: string;
  metadata: Record<string, unknown>;
  categories: Record<string, {
    info: CategoryInfo;
    templates: PromptTemplate[];
  }>;
}

export interface Task {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  prompt_id: string;
  result: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskCreate {
  prompt_id: string;
  variables: Record<string, string>;
  model?: string;
}

export interface HistoryItem {
  task: Task;
  promptName: string;
  category: string;
}
```

- [ ] **Step 2: 创建 API 客户端**

```typescript
import type { PromptsResponse, PromptTemplate, Task, TaskCreate } from '@/types';

const API_BASE = '/api';

export async function getPrompts(): Promise<PromptsResponse> {
  const response = await fetch(`${API_BASE}/prompts`);
  if (!response.ok) throw new Error('Failed to fetch prompts');
  return response.json();
}

export async function getPrompt(id: string): Promise<PromptTemplate> {
  const response = await fetch(`${API_BASE}/prompts/${id}`);
  if (!response.ok) throw new Error('Failed to fetch prompt');
  return response.json();
}

export async function createTask(task: TaskCreate): Promise<Task> {
  const response = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  });
  if (!response.ok) throw new Error('Failed to create task');
  return response.json();
}

export async function getTask(id: string): Promise<Task> {
  const response = await fetch(`${API_BASE}/tasks/${id}`);
  if (!response.ok) throw new Error('Failed to fetch task');
  return response.json();
}

export function streamTask(taskId: string, onMessage: (chunk: string) => void, onDone: () => void, onError: (error: string) => void) {
  const eventSource = new EventSource(`${API_BASE}/stream/${taskId}`);

  eventSource.addEventListener('message', (event) => {
    onMessage(event.data);
  });

  eventSource.addEventListener('done', () => {
    eventSource.close();
    onDone();
  });

  eventSource.addEventListener('error', (event) => {
    eventSource.close();
    onError('Stream error');
  });

  return () => eventSource.close();
}
```

- [ ] **Step 3: 创建工具函数**

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('zh-CN');
}

export function saveHistory(history: HistoryItem[]) {
  localStorage.setItem('research_history', JSON.stringify(history));
}

export function loadHistory(): HistoryItem[] {
  const stored = localStorage.getItem('research_history');
  return stored ? JSON.parse(stored) : [];
}
```

- [ ] **Step 4: Commit**

```bash
git add research-app/frontend/src/types/index.ts research-app/frontend/src/lib/api.ts research-app/frontend/src/lib/utils.ts
git commit -m "feat(frontend): add type definitions and API client"
```

---

### Task 7: 前端 Header + MarketTabs 组件

**Files:**
- Create: `research-app/frontend/src/components/Header.tsx`
- Create: `research-app/frontend/src/components/MarketTabs.tsx`
- Modify: `research-app/frontend/src/App.tsx`

- [ ] **Step 1: 创建 Header.tsx**

```tsx
import { TrendingUp, History, Settings } from 'lucide-react';

interface HeaderProps {
  onHistoryClick: () => void;
}

export default function Header({ onHistoryClick }: HeaderProps) {
  return (
    <header className="border-b bg-white px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <TrendingUp className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-bold">揽宝智能投研</h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onHistoryClick}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md hover:bg-gray-100 transition-colors"
        >
          <History className="h-4 w-4" />
          历史记录
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: 创建 MarketTabs.tsx**

```tsx
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = [
  { key: 'bull' as const, label: '牛市环境', icon: TrendingUp, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-200', active: 'bg-red-100 border-red-300' },
  { key: 'bear' as const, label: '熊市环境', icon: TrendingDown, color: 'text-green-500', bg: 'bg-green-50', border: 'border-green-200', active: 'bg-green-100 border-green-300' },
  { key: 'oscillation' as const, label: '震荡市', icon: Activity, color: 'text-amber-500', bg: 'bg-amber-50', border: 'border-amber-200', active: 'bg-amber-100 border-amber-300' },
];

interface MarketTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function MarketTabs({ activeTab, onTabChange }: MarketTabsProps) {
  return (
    <div className="flex gap-3 px-6 py-4">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg border-2 font-medium transition-all',
              isActive ? `${tab.active} ${tab.color}` : `bg-white border-gray-200 text-gray-600 hover:bg-gray-50`
            )}
          >
            <Icon className="h-5 w-5" />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 3: 创建 App.tsx 骨架**

```tsx
import { useState } from 'react';
import Header from './components/Header';
import MarketTabs from './components/MarketTabs';

export default function App() {
  const [activeTab, setActiveTab] = useState('bull');
  const [historyOpen, setHistoryOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onHistoryClick={() => setHistoryOpen(true)} />
      <MarketTabs activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="px-6 pb-6">
        <p className="text-gray-500">Selected: {activeTab}</p>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: 验证构建**

Run:
```bash
cd research-app/frontend
npm run build
```

Expected: 构建成功

- [ ] **Step 5: Commit**

```bash
git add research-app/frontend/src/components/Header.tsx research-app/frontend/src/components/MarketTabs.tsx research-app/frontend/src/App.tsx
git commit -m "feat(frontend): add Header and MarketTabs components"
```

---

### Task 8: 前端 PromptCard 组件

**Files:**
- Create: `research-app/frontend/src/components/PromptCard.tsx`
- Modify: `research-app/frontend/src/App.tsx`

- [ ] **Step 1: 创建 PromptCard.tsx**

```tsx
import { useState } from 'react';
import { Play, Edit, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/types';

interface PromptCardProps {
  prompt: PromptTemplate;
  categoryColor: string;
  onExecute: (promptId: string, variables: Record<string, string>) => void;
}

export default function PromptCard({ prompt, categoryColor, onExecute }: PromptCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      await onExecute(prompt.id, variableValues);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">{prompt.name}</h3>
            <div className="flex flex-wrap gap-1 mt-2">
              {prompt.keywords.map((kw) => (
                <span
                  key={kw}
                  className={cn(
                    'px-2 py-0.5 text-xs rounded-full font-medium',
                    categoryColor
                  )}
                >
                  {kw}
                </span>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-2">{prompt.description}</p>
          </div>
          <div className="flex gap-2 ml-4">
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="inline-flex items-center gap-1 px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {isExecuting ? '执行中...' : '执行'}
            </button>
            <button className="inline-flex items-center gap-1 px-3 py-2 border rounded-md text-sm font-medium hover:bg-gray-50">
              <Edit className="h-4 w-4" />
            </button>
          </div>
        </div>

        {prompt.variables.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3">
            {prompt.variables.map((varName) => (
              <div key={varName} className="flex items-center gap-2">
                <label className="text-sm text-gray-600">{varName}:</label>
                <input
                  type="text"
                  value={variableValues[varName] || ''}
                  onChange={(e) => setVariableValues(prev => ({ ...prev, [varName]: e.target.value }))}
                  className="px-2 py-1 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder={`输入${varName}`}
                />
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 mt-3 text-sm text-gray-500 hover:text-gray-700"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          {expanded ? '收起' : '查看提示词'}
        </button>

        {expanded && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md text-sm text-gray-700 whitespace-pre-wrap">
            {prompt.prompt}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 更新 App.tsx 集成 PromptCard**

```tsx
import { useState, useEffect } from 'react';
import Header from './components/Header';
import MarketTabs from './components/MarketTabs';
import PromptCard from './components/PromptCard';
import { getPrompts } from '@/lib/api';
import type { PromptsResponse, PromptTemplate } from '@/types';

const CATEGORY_COLORS: Record<string, string> = {
  bull: 'bg-red-100 text-red-700',
  bear: 'bg-green-100 text-green-700',
  oscillation: 'bg-amber-100 text-amber-700',
};

export default function App() {
  const [activeTab, setActiveTab] = useState('bull');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [promptsData, setPromptsData] = useState<PromptsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPrompts().then(data => {
      setPromptsData(data);
      setLoading(false);
    });
  }, []);

  const handleExecute = async (promptId: string, variables: Record<string, string>) => {
    console.log('Execute:', promptId, variables);
    // Will be implemented in Task 9
  };

  const currentTemplates = promptsData?.categories[activeTab]?.templates || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onHistoryClick={() => setHistoryOpen(true)} />
      <MarketTabs activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="px-6 pb-6 max-w-4xl mx-auto">
        {loading ? (
          <p className="text-center text-gray-500 py-8">加载中...</p>
        ) : (
          <div className="space-y-4">
            {currentTemplates.map((prompt) => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                categoryColor={CATEGORY_COLORS[activeTab]}
                onExecute={handleExecute}
              />
            ))}
            {currentTemplates.length === 0 && (
              <p className="text-center text-gray-400 py-8">暂无该分类的提示词模板</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: 验证构建**

Run:
```bash
cd research-app/frontend
npm run build
```

Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add research-app/frontend/src/components/PromptCard.tsx research-app/frontend/src/App.tsx
git commit -m "feat(frontend): add PromptCard with variables and execute button"
```

---

### Task 9: 前端 ResultPanel + SSE 流式渲染

**Files:**
- Create: `research-app/frontend/src/components/ResultPanel.tsx`
- Modify: `research-app/frontend/src/App.tsx`

- [ ] **Step 1: 创建 ResultPanel.tsx**

```tsx
import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Task } from '@/types';

interface ResultPanelProps {
  task: Task | null;
  streaming: boolean;
  streamedContent: string;
  onClose: () => void;
}

export default function ResultPanel({ task, streaming, streamedContent, onClose }: ResultPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamedContent]);

  if (!task) return null;

  const displayContent = streaming ? streamedContent : (task.result || '');
  const hasError = task.status === 'failed';

  return (
    <div className="fixed inset-x-0 bottom-0 bg-white border-t shadow-lg z-50 max-h-[50vh] flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm">执行结果</h3>
          {streaming && (
            <span className="inline-flex items-center gap-1 text-xs text-blue-600">
              <Loader2 className="h-3 w-3 animate-spin" />
              生成中...
            </span>
          )}
          {task.status === 'completed' && (
            <span className="text-xs text-green-600">已完成</span>
          )}
          {hasError && (
            <span className="text-xs text-red-600">失败</span>
          )}
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-200 rounded">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {hasError ? (
          <div className="text-red-600 text-sm">{task.error}</div>
        ) : displayContent ? (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {displayContent}
            </ReactMarkdown>
          </div>
        ) : streaming ? (
          <div className="text-gray-400 text-sm">等待响应...</div>
        ) : (
          <div className="text-gray-400 text-sm">暂无结果</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 更新 App.tsx 集成 ResultPanel 和 SSE**

```tsx
import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import MarketTabs from './components/MarketTabs';
import PromptCard from './components/PromptCard';
import ResultPanel from './components/ResultPanel';
import { getPrompts, createTask, streamTask } from '@/lib/api';
import { saveHistory, loadHistory } from '@/lib/utils';
import type { PromptsResponse, PromptTemplate, Task, HistoryItem } from '@/types';

const CATEGORY_COLORS: Record<string, string> = {
  bull: 'bg-red-100 text-red-700',
  bear: 'bg-green-100 text-green-700',
  oscillation: 'bg-amber-100 text-amber-700',
};

export default function App() {
  const [activeTab, setActiveTab] = useState('bull');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [promptsData, setPromptsData] = useState<PromptsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory());

  useEffect(() => {
    getPrompts().then(data => {
      setPromptsData(data);
      setLoading(false);
    });
  }, []);

  const handleExecute = useCallback(async (promptId: string, variables: Record<string, string>) => {
    try {
      const task = await createTask({ prompt_id: promptId, variables });
      setActiveTask(task);
      setStreaming(true);
      setStreamedContent('');

      const prompt = promptsData?.categories[activeTab]?.templates.find((t: PromptTemplate) => t.id === promptId);

      streamTask(
        task.id,
        (chunk) => {
          setStreamedContent(prev => prev + chunk);
        },
        () => {
          setStreaming(false);
          // Refresh task to get final result
          fetch(`/api/tasks/${task.id}`)
            .then(r => r.json())
            .then((finalTask: Task) => {
              setActiveTask(finalTask);
              if (prompt) {
                const newHistory: HistoryItem = {
                  task: finalTask,
                  promptName: prompt.name,
                  category: activeTab,
                };
                const updated = [newHistory, ...history].slice(0, 50);
                setHistory(updated);
                saveHistory(updated);
              }
            });
        },
        (error) => {
          setStreaming(false);
          console.error('Stream error:', error);
        }
      );
    } catch (error) {
      console.error('Execute error:', error);
    }
  }, [activeTab, promptsData, history]);

  const handleCloseResult = () => {
    setActiveTask(null);
    setStreamedContent('');
  };

  const currentTemplates = promptsData?.categories[activeTab]?.templates || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onHistoryClick={() => setHistoryOpen(true)} />
      <MarketTabs activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="px-6 pb-6 max-w-4xl mx-auto">
        {loading ? (
          <p className="text-center text-gray-500 py-8">加载中...</p>
        ) : (
          <div className="space-y-4">
            {currentTemplates.map((prompt) => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                categoryColor={CATEGORY_COLORS[activeTab]}
                onExecute={handleExecute}
              />
            ))}
            {currentTemplates.length === 0 && (
              <p className="text-center text-gray-400 py-8">暂无该分类的提示词模板</p>
            )}
          </div>
        )}
      </main>

      <ResultPanel
        task={activeTask}
        streaming={streaming}
        streamedContent={streamedContent}
        onClose={handleCloseResult}
      />
    </div>
  );
}
```

- [ ] **Step 3: 安装 react-markdown 依赖**

Run:
```bash
cd research-app/frontend
npm install react-markdown remark-gfm
```

- [ ] **Step 4: 验证构建**

Run:
```bash
npm run build
```

Expected: 构建成功

- [ ] **Step 5: Commit**

```bash
git add research-app/frontend/src/components/ResultPanel.tsx research-app/frontend/src/App.tsx
git commit -m "feat(frontend): add ResultPanel with SSE streaming and Markdown rendering"
```

---

### Task 10: 前端 HistoryDrawer

**Files:**
- Create: `research-app/frontend/src/components/HistoryDrawer.tsx`
- Modify: `research-app/frontend/src/App.tsx`

- [ ] **Step 1: 创建 HistoryDrawer.tsx**

```tsx
import { X, Clock, Trash2 } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import type { HistoryItem, Task } from '@/types';

interface HistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  history: HistoryItem[];
  onSelectTask: (task: Task) => void;
  onClearHistory: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  bull: '牛市',
  bear: '熊市',
  oscillation: '震荡',
};

const CATEGORY_COLORS: Record<string, string> = {
  bull: 'text-red-600 bg-red-50',
  bear: 'text-green-600 bg-green-50',
  oscillation: 'text-amber-600 bg-amber-50',
};

export default function HistoryDrawer({ open, onClose, history, onSelectTask, onClearHistory }: HistoryDrawerProps) {
  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/30 z-50" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" />
            <h2 className="font-semibold">历史记录</h2>
            <span className="text-xs text-gray-400">({history.length})</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClearHistory}
              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
              title="清空历史"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Clock className="h-8 w-8 mb-2" />
              <p>暂无历史记录</p>
            </div>
          ) : (
            <div className="divide-y">
              {history.map((item, index) => (
                <button
                  key={`${item.task.id}-${index}`}
                  onClick={() => onSelectTask(item.task)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm truncate">{item.promptName}</span>
                    <span className={cn(
                      'text-xs px-2 py-0.5 rounded-full',
                      CATEGORY_COLORS[item.category]
                    )}>
                      {CATEGORY_LABELS[item.category]}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span>{formatDate(item.task.created_at)}</span>
                    <span>·</span>
                    <span className={cn(
                      item.task.status === 'completed' ? 'text-green-500' :
                      item.task.status === 'failed' ? 'text-red-500' :
                      'text-blue-500'
                    )}>
                      {item.task.status === 'completed' ? '已完成' :
                       item.task.status === 'failed' ? '失败' :
                       item.task.status === 'running' ? '进行中' : '等待中'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 2: 更新 App.tsx 集成 HistoryDrawer**

在 App.tsx 中添加 HistoryDrawer import 和 JSX：

```tsx
import HistoryDrawer from './components/HistoryDrawer';
// ... other imports

// 在组件内添加：
const handleSelectTask = (task: Task) => {
  setActiveTask(task);
  setStreamedContent(task.result || '');
  setHistoryOpen(false);
};

const handleClearHistory = () => {
  setHistory([]);
  saveHistory([]);
};

// 在 return 中添加：
<HistoryDrawer
  open={historyOpen}
  onClose={() => setHistoryOpen(false)}
  history={history}
  onSelectTask={handleSelectTask}
  onClearHistory={handleClearHistory}
/>
```

- [ ] **Step 3: 验证构建**

Run:
```bash
cd research-app/frontend
npm run build
```

Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add research-app/frontend/src/components/HistoryDrawer.tsx research-app/frontend/src/App.tsx
git commit -m "feat(frontend): add HistoryDrawer with task selection and clear"
```

---

### Task 11: Docker Compose 集成 + 联调测试

**Files:**
- Modify: `docker-compose.yml`
- Create: `research-app/frontend/.dockerignore`
- Create: `research-app/backend/.dockerignore`

- [ ] **Step 1: 创建 .dockerignore 文件**

```
# research-app/frontend/.dockerignore
node_modules
dist
.vite
*.log
```

```
# research-app/backend/.dockerignore
__pycache__
*.pyc
*.pyo
*.egg-info
.pytest_cache
.venv
```

- [ ] **Step 2: 确认 docker-compose.yml 已更新**

确认 Task 1 中添加的 `research-app-backend` 和 `research-app-frontend` 服务存在。

- [ ] **Step 3: 构建并启动服务**

Run:
```bash
cd /data/wangf/lanbao_cq_ws
docker compose build research-app-backend research-app-frontend
docker compose up -d research-app-backend research-app-frontend
```

Expected: 构建成功，服务启动

- [ ] **Step 4: 验证后端健康检查**

Run:
```bash
curl http://localhost:3201/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: 验证前端可访问**

Run:
```bash
curl -I http://localhost:3200
```

Expected: HTTP 200

- [ ] **Step 6: 端到端测试**

1. 打开浏览器访问 `http://localhost:3200`
2. 确认三分类 Tab 正常显示
3. 点击"执行"按钮，确认 SSE 流式输出正常
4. 检查历史记录是否正确保存到 localStorage

- [ ] **Step 7: Commit**

```bash
git add research-app/frontend/.dockerignore research-app/backend/.dockerignore
git commit -m "feat: complete Docker integration and end-to-end testing"
```

---

## 自审检查

### 1. Spec 覆盖检查

| Spec 要求 | 对应任务 |
|-----------|----------|
| Vite + React 前端 | Task 5, 7, 8, 9, 10 |
| FastAPI 后端 | Task 2, 3, 4 |
| YAML 提示词配置 | Task 2, 3 |
| 三分类市场类型 | Task 7, 8 |
| Hermes Agent 调用 | Task 4 |
| SSE 流式输出 | Task 4, 9 |
| Markdown 渲染 | Task 9 |
| localStorage 历史 | Task 9, 10 |
| Docker Compose 集成 | Task 1, 11 |
| 错误处理 | Task 4, 9 |

### 2. 占位符扫描

- [x] 无 TBD/TODO
- [x] 所有步骤包含完整代码
- [x] 所有命令包含预期输出

### 3. 类型一致性

- [x] `PromptTemplate` 模型前后端一致
- [x] `Task` 模型前后端一致
- [x] API 路径一致 (`/api/prompts`, `/api/tasks`)
- [x] SSE 事件名称一致 (`message`, `done`, `error`)

---

## 执行选项

**计划完成，保存到 `docs/superpowers/plans/2026-06-05-research-app.md`。两个执行选项：**

**1. Subagent-Driven（推荐）** — 每个任务派一个独立的子代理执行，我在任务间审查，快速迭代

**2. Inline Execution** — 在本会话中使用 executing-plans 顺序执行任务，批量执行并设置检查点

**选择哪种方式？**
