# 东方财富自选股 MCP Server（SSE 模式）
# 源码来源：https://github.com/ten2net/lanbao-eastmoney-mcp.git
FROM python:3.12-slim

WORKDIR /app

# 复制本目录下的源码（由外部仓库同步而来）
COPY src /app

# 安装项目依赖与入口脚本
RUN pip install --no-cache-dir -e .

# SSE 模式默认端口
EXPOSE 3000

# 以 SSE 传输方式启动 MCP Server
CMD ["eastmoney-mcp", "--transport", "sse", "--port", "3000"]
