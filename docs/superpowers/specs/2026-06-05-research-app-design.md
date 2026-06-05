# 揽宝智能投研 Web App 设计文档

**日期**: 2026-06-05
**版本**: v1.0
**状态**: 待实现

---

## 1. 项目概述

基于 Vite + React 的前端智能投研应用，集成到现有揽宝 Docker Compose 栈中。用户通过点击预配置的投研提示词模板按钮，调用 Hermes Agent 执行投研任务，结果以 Markdown 流式渲染输出。

### 1.1 核心特性

- 三类市场环境提示词模板（牛市/熊市/震荡市）
- 基础模板手动维护 + 运行时扩展
- SSE 流式结果输出（打字机效果）
- 单用户本地历史记录（localStorage）
- 简洁专业的投研界面

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + Vite + Tailwind CSS + shadcn/ui |
| 后端 | Python 3.12 + FastAPI + uvicorn |
| 部署 | Docker Compose（集成到现有栈）|
| 数据 | YAML 文件（提示词配置）+ localStorage（历史记录）|

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    揽宝 Docker Compose                       │
├─────────────────────────────────────────────────────────────┤
│  research-app-frontend (nginx)                              │
│    └── 端口 3200，托管 Vite 构建产物                        │
├─────────────────────────────────────────────────────────────┤
│  research-app-backend (FastAPI + uvicorn)                   │
│    ├── /api/prompts      → 读取/保存 YAML 提示词配置       │
│    ├── /api/tasks        → 创建投研任务                     │
│    ├── /api/tasks/{id}   → 查询任务状态和结果               │
│    └── /api/stream/{id}  → SSE 流式输出 Hermes 响应        │
│    └── 端口 3201                                          │
├─────────────────────────────────────────────────────────────┤
│  hermes (host 网络)                                         │
│    └── 端口 8642 → backend 通过 192.168.15.131:8642 调用   │
├─────────────────────────────────────────────────────────────┤
│  vllm (桥接网络)                                            │
│    └── 端口 8500                                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 数据流

```
用户点击"执行"按钮
   │
   ▼
Frontend (React) ──POST /api/tasks──▶ Backend (FastAPI)
                                         │
                                         ├── 读取 YAML 找到对应提示词
                                         ├── 渲染模板变量（如 {{板块名称}}）
                                         └── 调用 Hermes API (192.168.15.131:8642)
                                                  │
                                                  ▼
                                          Hermes → vLLM (Gemma 4)
                                                  │
                                         ◄────────┘
                                         SSE 流式返回结果
                                         │
   ◄─────────────────────────────────────┘
Frontend 实时渲染 Markdown（打字机效果）
```

---

## 3. 后端设计（FastAPI）

### 3.1 数据模型

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PromptTemplate(BaseModel):
    id: str
    name: str
    category: str              # "bull" | "bear" | "oscillation"
    keywords: list[str]
    prompt: str                # 支持 {{变量}} 占位符
    variables: list[str]       # 变量名列表
    description: str
    created_at: datetime
    updated_at: datetime

class TaskCreate(BaseModel):
    prompt_id: str
    variables: dict[str, str]
    model: str = "gemma-4-12b"

class TaskResponse(BaseModel):
    id: str
    status: str                # "pending" | "running" | "completed" | "failed"
    prompt_id: str
    result: Optional[str]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
```

### 3.2 API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/prompts` | 获取所有提示词模板（按 category 分组返回） |
| GET | `/api/prompts/{id}` | 获取单个模板详情 |
| POST | `/api/prompts` | 新增模板（运行时扩展） |
| PUT | `/api/prompts/{id}` | 修改模板 |
| DELETE | `/api/prompts/{id}` | 删除模板 |
| POST | `/api/tasks` | 创建投研任务，返回 task_id |
| GET | `/api/tasks/{id}` | 查询任务状态和结果 |
| GET | `/api/stream/{id}` | SSE 流式获取 Hermes 响应 |

### 3.3 Hermes 代理逻辑

```python
import httpx
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

HERMES_BASE_URL = "http://192.168.15.131:8642"
HERMES_API_KEY = os.getenv("HERMES_API_KEY")

async def stream_hermes(prompt: str, model: str):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{HERMES_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {HERMES_API_KEY}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            },
            timeout=300
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]  # 去掉 "data: " 前缀
```

**网络说明**: backend 容器在 bridge 网络中，hermes 在 host 网络中。backend 通过宿主机 IP `192.168.15.131:8642` 访问 Hermes API。

### 3.4 模板渲染

```python
def render_prompt(template: PromptTemplate, variables: dict[str, str]) -> str:
    result = template.prompt
    for var_name in template.variables:
        placeholder = f"{{{{{var_name}}}}}"
        result = result.replace(placeholder, variables.get(var_name, ""))
    return result
```

---

## 4. 前端设计（React）

### 4.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  揽宝智能投研                    [历史记录 ▼]  [设置]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │  🐂 牛市 │  │  🐻 熊市 │  │  📊 震荡 │  ← 市场类型 Tab    │
│  └─────────┘  └─────────┘  └─────────┘                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 热门板块提示词                    [执行] [编辑 ✏️]   │   │
│  │ 关键词：景气度、政策溢价、资金抱团                   │   │
│  │ 寻找轮动热点...                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 龙头个股提示词                    [执行] [编辑 ✏️]   │   │
│  │ 关键词：...                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  执行结果                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ## 热门板块分析                                      │   │
│  │  1. **半导体板块** ...                               │   │
│  │  [正在生成...]  ← 流式显示                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 组件树

```
App
├── Header
│   ├── Title
│   ├── HistoryDropdown
│   └── SettingsButton
├── MarketTabs
│   └── Tab (bull / bear / oscillation)
├── PromptList
│   └── PromptCard
│       ├── PromptHeader (name + keywords)
│       ├── PromptPreview (可展开)
│       ├── VariableInputs (动态输入框)
│       └── ActionBar (执行 + 编辑)
├── ResultPanel
│   ├── ResultHeader (状态 + 耗时)
│   ├── MarkdownRenderer
│   └── StreamingIndicator
└── HistoryDrawer (Sheet 组件)
    └── HistoryItem
```

### 4.3 状态管理

使用 React Context + useReducer（足够简单，无需 Redux/Zustand）：

```typescript
type AppState = {
  activeCategory: 'bull' | 'bear' | 'oscillation';
  prompts: PromptTemplate[];
  activeTask: Task | null;
  history: Task[];
  isStreaming: boolean;
};
```

### 4.4 依赖库

| 库 | 版本 | 用途 |
|------|------|------|
| react | ^19.0 | UI 框架 |
| vite | ^6.0 | 构建工具 |
| tailwindcss | ^4.0 | 样式 |
| shadcn/ui | latest | 组件库 |
| react-markdown | ^10.0 | Markdown 渲染 |
| remark-gfm | ^4.0 | GitHub Flavored Markdown |
| lucide-react | ^0.400 | 图标 |

---

## 5. YAML 配置结构

### 5.1 文件路径

宿主机: `./research-app/data/prompts.yaml`
容器内: `/app/data/prompts.yaml`（挂载卷）

### 5.2 完整示例

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
      ③ 总结这些板块的轮动规律。

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

---

## 6. Docker 集成

### 6.1 docker-compose.yml 新增服务

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

### 6.2 项目目录结构

```
research-app/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   └── routers/
│       ├── prompts.py
│       └── tasks.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── components.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
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
│           └── api.ts
└── data/
    └── prompts.yaml
```

### 6.3 构建说明

- **Frontend Dockerfile**: 多阶段构建，Node 构建静态文件 → nginx 托管
- **Backend Dockerfile**: Python 3.12 slim，uvicorn 启动
- **数据卷**: `./research-app/data:/app/data:rw` 持久化 YAML 配置

---

## 7. 错误处理

### 7.1 后端错误处理

| 场景 | HTTP 状态 | 响应 |
|------|-----------|------|
| 模板不存在 | 404 | `{ "error": "模板已删除或不存在" }` |
| YAML 解析失败 | 500 | 启动时校验，失败则容器退出 |
| Hermes 429/503 | 503 | `{ "error": "投研服务繁忙，请稍后重试" }` |
| Hermes 连接超时 | 504 | `{ "error": "连接超时，请检查网络" }` |
| 模板变量缺失 | 400 | `{ "error": "缺少必需变量: 板块名称" }` |

### 7.2 前端错误处理

| 场景 | 处理 |
|------|------|
| SSE 断开 | 指数退避重连，最多 3 次，保留已接收内容 |
| API 请求失败 | Toast 提示 + 重试按钮 |
| Markdown 渲染失败 | 降级为纯文本显示 |
| localStorage 满 | 清理最旧的历史记录 |

---

## 8. 测试策略

### 8.1 后端测试（pytest）

- `test_prompts.py`: YAML 读写、模板渲染、CRUD API
- `test_tasks.py`: 任务创建、SSE 流式输出、错误处理
- `test_hermes_proxy.py`: Hermes API 调用模拟、超时处理

### 8.2 前端测试（Vitest）

- `PromptCard.test.tsx`: 渲染、变量输入、执行按钮
- `AppContext.test.tsx`: 状态管理、历史记录持久化
- `ResultPanel.test.tsx`: Markdown 渲染、流式更新

### 8.3 E2E 测试（Playwright）

- 完整流程：选择模板 → 输入变量 → 执行 → 结果展示
- 历史记录：执行后刷新页面 → 历史存在 → 点击加载

---

## 9. 实现顺序

1. 初始化项目结构（backend + frontend 目录 + Dockerfile）
2. 实现后端：YAML 读写 + Prompts API
3. 实现后端：Tasks API + Hermes 代理 + SSE
4. 实现前端：基础布局 + MarketTabs + PromptCard
5. 实现前端：ResultPanel + SSE 流式渲染
6. 实现前端：HistoryDrawer + localStorage
7. 集成 Docker Compose + 联调测试
