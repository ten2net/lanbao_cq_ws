# EastMoney MCP 服务集成

本目录用于将 [ten2net/lanbao-eastmoney-mcp](https://github.com/ten2net/lanbao-eastmoney-mcp.git) 以 Docker 容器形式接入到 `docker-compose.yml` 中。

## 启动服务

```bash
docker compose up -d eastmoney-mcp
```

服务将以 **SSE 模式**运行在容器内 `0.0.0.0:3000`，映射到宿主机 `localhost:8003`。

## 配置

东方财富 API 需要登录态，请在项目根目录 `.env` 中补充：

```bash
EASTMONEY_APPKEY=你的AppKey
EASTMONEY_COOKIE=你的Cookie字符串
```

获取方式：登录东方财富网页版 → F12 开发者工具 → Network → 刷新自选股页面 → 从请求头提取 Cookie，从 URL 中提取 appkey。

## 功能测试

在主机上执行：

```bash
# 1. 安装测试依赖
pip install -r scripts/requirements-test.txt

# 2. 运行详细功能测试
python3 scripts/test_eastmoney_mcp.py

# 3. 输出完整 JSON 报告
python3 scripts/test_eastmoney_mcp.py --json
```

测试脚本会验证：
- HTTP /sse 端点连通性
- MCP 工具列表
- 行情类工具调用（单只/批量行情）
- 自选股类工具调用（分组、列表、概览、创建分组、添加/移除）

若未配置 `EASTMONEY_APPKEY`/`EASTMONEY_COOKIE`，自选股相关测试会被跳过，但连接性和工具列表仍会被验证。
