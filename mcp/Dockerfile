# syntax=docker/dockerfile:1

# 阶段 1：使用 uv 镜像解析并安装依赖
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# 仅复制清单文件，最大化利用构建缓存
COPY pyproject.toml uv.lock ./
ENV UV_HTTP_TIMEOUT=300
RUN uv sync --frozen --no-install-project --no-dev

# 阶段 2：最小化生产镜像
FROM python:3.13-slim

WORKDIR /app

# 从构建阶段复制已安装好的虚拟环境
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 复制应用代码
COPY my_server.py ./

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('127.0.0.1', 8002)); s.close()" || exit 1

CMD ["python", "my_server.py"]
