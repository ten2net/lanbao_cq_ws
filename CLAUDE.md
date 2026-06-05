# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

揽宝智能投研交易平台 —— 基于 Docker Compose 部署的 LLM 推理与 Agent 网关服务栈。

## 常用命令

```bash
# 构建并启动所有服务
docker compose up -d

# 查看所有服务日志
docker compose logs -f

# 查看指定服务日志
docker compose logs -f vllm
docker compose logs -f hermes
docker compose logs -f open-webui

# 停止并移除服务
docker compose down

# 重启单个服务
docker compose restart hermes

# 检查服务健康状态
docker compose ps
```

## 服务架构

三个服务通过 `lanbao-network` 桥接网络通信：

| 服务 | 镜像 | 宿主端口 | 职责 |
|------|------|----------|------|
| vllm | `vllm/vllm-openai:latest` | 8001 | LLM 推理服务，运行 Qwen/Qwen2.5-7B-Instruct，提供 OpenAI 兼容 API |
| hermes | `nousresearch/hermes-agent:latest` | 8642, 9119 | Agent 网关，连接 vLLM 作为推理后端 |
| open-webui | `ghcr.io/open-webui/open-webui:main` | 3100 | Web UI 前端，通过 vLLM 的 OpenAI 兼容 API 与模型交互 |

### 启动依赖

- hermes 与 open-webui 均依赖 vllm 健康检查通过后才启动
- vllm 首次启动时会从 Hugging Face 下载模型（配置了 `HF_ENDPOINT=https://hf-mirror.com` 镜像）
- vllm 的 `start_period: 3600s` 允许模型下载和加载有充足时间

### 关键配置

- **vLLM**: 模型挂载宿主 `~/.cache/huggingface` 到容器 `/root/.cache/huggingface` 以缓存模型权重
- **Hermes**: 挂载宿主 `~/.hermes` 到容器 `/opt/data` 持久化数据；环境变量 `HERMES_INFERENCE_PROVIDER=vllm` 指定推理后端
- **Open WebUI**: 数据持久化在 Docker 卷 `open-webui` 中；`OPENAI_API_BASE_URL=http://vllm:8000/v1` 指向内部 vLLM 服务
