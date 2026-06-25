---
name: eastmoney-favor
description: 东方财富自选股管理工具。支持 MCP 服务器方式调用，提供行情查询、自选股分组管理、批量操作等功能。适用于需要程序化维护东方财富自选股的场景。
author: lanbaoxia
version: 1.1.0
tags: [mcp, eastmoney, 自选股, 行情, 股票]
---

# 东方财富自选股管理 (eastmoney-favor)

基于东方财富网页版API的自选股管理工具，支持完整的自选股CRUD操作。

## 功能特性

| 功能 | 说明 |
|------|------|
| 分组管理 | 创建、删除、重命名自选股分组 |
| 股票添加 | 单只或批量添加股票到指定分组 |
| 股票删除 | 单只或批量删除股票 |
| 分组清空 | 一键清空整个分组 |
| 列表查询 | 查看分组中的股票列表 |

## 前置要求

1. **获取 Cookie**：登录东方财富网页版，从浏览器开发者工具中获取 Cookie
2. **获取 AppKey**：从东方财富网页版 localStorage 中提取 `em_appkey`

## 环境配置

### 方式1: 环境变量（推荐）

添加到 `~/.hermes/.env` 或系统环境变量：

```bash
# 东方财富 MCP 服务器配置
EASTMONEY_APPKEY=your_appkey_here
EASTMONEY_COOKIE=ct=xxx; ut=xxx;
```

**Cookie 格式说明**：
- `ct`: 从 Cookie 中提取的 ct 字段
- `ut`: 从 Cookie 中提取的 ut 字段
- 完整格式: `ct=xxx; ut=xxx;`

### 方式2: MCP 服务器配置

在 `~/.hermes/config.yaml` 中配置：

```yaml
mcp_servers:
  eastmoney:
    command: eastmoney-mcp
    env:
      EASTMONEY_APPKEY: ${EASTMONEY_APPKEY}
      EASTMONEY_COOKIE: ${EASTMONEY_COOKIE}
```

### 多账户配置

支持同时管理多个东方财富账户：

```bash
# 默认账户
EASTMONEY_APPKEY=xxx
EASTMONEY_COOKIE=xxx

# 第二个账户
ACCOUNT2_EASTMONEY_APPKEY=yyy
ACCOUNT2_EASTMONEY_COOKIE=yyy
```

## 使用方法

### MCP 工具（推荐）

通过 Hermes Agent 直接调用 MCP 工具：

```
# 获取自选股分组列表
get_watchlist_groups

# 获取指定分组股票
get_watchlist(group_id="8")

# 获取股票行情
get_stock_quote(code="000001")

# 批量获取行情
get_batch_quotes(codes=["300750", "002594", "600519"])

# 获取分组概览统计
get_watchlist_summary(group_id="8")

# 创建分组
create_watchlist_group(name="强势股跟踪")

# 添加股票到分组
add_to_watchlist(codes=["300750", "002594"], group_id="8")

# 从分组移除股票
remove_from_watchlist(codes=["300750"], group_id="8")
```

### 命令行接口

```bash
# 查看帮助
python3 scripts/favor_cli.py --help

# 列出所有分组
python3 scripts/favor_cli.py list-groups

# 创建新分组
python3 scripts/favor_cli.py create-group "强势股跟踪"

# 添加股票到分组
python3 scripts/favor_cli.py add --group "强势股跟踪" --codes 300489,301181,000889

# 批量添加股票
python3 scripts/favor_cli.py add --group "强势股跟踪" --codes 600519,000858,300750

# 查看分组中的股票
python3 scripts/favor_cli.py list --group "强势股跟踪"

# 从分组删除股票
python3 scripts/favor_cli.py del --group "强势股跟踪" --codes 300489

# 清空整个分组
python3 scripts/favor_cli.py clear --group "强势股跟踪"

# 删除分组
python3 scripts/favor_cli.py del-group "强势股跟踪"
```

### Python API

```python
from scripts.favor import FavorForEM

# 初始化
favor = FavorForEM(appkey="your_appkey", token="your_cookie")

# 获取所有分组
groups = favor.get_groups()

# 创建分组
favor.create_group("强势股跟踪")

# 批量添加股票
codes = ["300489", "301181", "000889", "002328"]
favor.add_symbols_to_group(codes, group_name="强势股跟踪")

# 获取分组股票
stocks = favor.get_symbols(group_name="强势股跟踪")

# 清空分组
favor.del_all_from_group(group_name="强势股跟踪")
```

## 股票代码格式

- **A股**：6位数字代码（如 600519、000858、300750）
- **港股**：5位数字代码（如 00700）
- **美股**：代码（如 AAPL、TSLA）

代码会自动转换为东方财富内部格式：
- 沪市股票: `1${code}`
- 深市股票: `0${code}`
- 港股: `116${code}`
- 美股: `105${code}`

## 注意事项

1. **Cookie有效期**：东方财富Cookie会过期，需要定期更新
2. **API限制**：批量操作每次最多45只股票，超过会自动分批处理
3. **分组名称**：支持中文，但建议不要过长
4. **网络要求**：需要能访问东方财富网站 (quote.eastmoney.com)

## MCP 服务器测试

测试 MCP 服务器是否正常工作：

```bash
# 列出 MCP 服务器
hermes mcp list

# 测试 eastmoney 连接
hermes mcp test eastmoney
```

预期输出：
```
Testing 'eastmoney'...
  Transport: stdio → eastmoney-mcp
  Auth: none
  ✓ Connected (1195ms)
  ✓ Tools discovered: 8
```

## 已知问题与修复记录

### 2026-04-12 修复

| 问题 | 原因 | 修复方案 | 状态 |
|------|------|----------|------|
| `stdio_server()` 参数错误 | MCP SDK 1.26.0 接口变更，`server` 参数被移除 | 改为 `stdio_server()` 返回 `(read_stream, write_stream)` | ✅ 已修复 |
| datetime JSON 序列化错误 | `StockQuote` 模型含 `timestamp: datetime` 字段 | 使用 `model_dump(mode='json')` 序列化 | ✅ 已修复 |
| 批量行情价格为0 | `fltt=2` 模式下 API 返回浮点数，代码仍除以1000 | 添加 `_safe_float()` 方法直接使用原始值 | ✅ 已修复 |

修复文件位置：
- `/root/lanbao/tools/eastmoney-mcp-server/src/eastmoney_mcp/server.py`
- `/root/lanbao/tools/eastmoney-mcp-server/src/eastmoney_mcp/api.py`

## 错误处理

常见错误及解决方案：

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 分组不存在 | 分组名称错误或已被删除 | 使用 list-groups 查看可用分组 |
| Cookie失效 | 登录态过期 | 重新登录东方财富获取新Cookie |
| 股票代码错误 | 代码格式不正确 | 检查是否为6位数字 |
| 网络错误 | 无法连接东方财富 | 检查网络连接 |
| MCP 连接失败 | 环境变量未设置 | 检查 EASTMONEY_APPKEY 和 EASTMONEY_COOKIE |

## 数据来源

- **API地址**: http://myfavor.eastmoney.com/v4/webouter/
- **数据安全**: 仅操作自选股数据，不涉及交易密码等敏感信息
- **传输安全**: 使用HTTPS加密传输
