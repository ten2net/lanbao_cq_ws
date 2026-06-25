# 东方财富自选股 MCP Server

> 为揽宝量化提供东方财富自选股管理和行情监控的标准化接口

## 功能特性

### 📊 行情数据
- 实时行情查询（单只/批量）
- 自选股列表同步
- 行情概览统计

### 📁 自选股管理
- 分组管理（创建、删除、查询）
- 股票添加/移除（支持批量）
- 多分组支持

### 🚨 实时监控
- 价格异动预警（涨跌幅、快速变化）
- 成交量异动检测
- 分级预警（紧急/警告/提醒）
- 冷却期控制（避免重复预警）

## 安装

```bash
cd /root/lanbao/tools/eastmoney-mcp-server
pip install -e .
```

## 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env
```

必需配置：
- `EASTMONEY_APPKEY`: 东方财富 AppKey
- `EASTMONEY_COOKIE`: 登录 Cookie

获取方式：
1. 登录东方财富网页版 (https://quote.eastmoney.com)
2. F12 打开开发者工具 → Network
3. 刷新自选股页面，找到包含自选股数据的请求
4. 从请求头中提取 Cookie，从 URL 中提取 appkey

## 使用方式

### 方式一：MCP Server（推荐）

在 Hermes 配置中添加 MCP Server：

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  eastmoney:
    command: eastmoney-mcp
    env:
      EASTMONEY_APPKEY: "${EASTMONEY_APPKEY}"
      EASTMONEY_COOKIE: "${EASTMONEY_COOKIE}"
```

然后在 Hermes 中使用：
```
查看我的自选股行情
获取自选股概览
监控自选股异动
```

### 方式二：CLI 工具

```bash
# 查看分组
eastmoney-cli groups

# 列出自选股
eastmoney-cli list

# 查看行情
eastmoney-cli quotes

# 查看概览
eastmoney-cli summary

# 添加股票
eastmoney-cli add 600519,000858

# 启动监控
eastmoney-cli monitor --change-pct 3.0
```

### 方式三：Python API

```python
from eastmoney_mcp.api import EastMoneyAPI
from eastmoney_mcp.monitor import WatchlistMonitor
from eastmoney_mcp.models import AlertConfig

# 初始化 API
api = EastMoneyAPI(
    appkey="your_appkey",
    cookie="your_cookie"
)

# 获取自选股
stocks = api.get_watchlist()
print(f"共有 {len(stocks)} 只自选股")

# 获取行情
quotes = api.get_batch_quotes([s.full_code for s in stocks])
for q in quotes:
    print(f"{q.name}: {q.price} ({q.change_pct:+.2f}%)")

# 启动监控
config = AlertConfig(change_pct=5.0)
monitor = WatchlistMonitor(api, config)

monitor.add_callback(lambda alert: print(f"预警: {alert.message}"))
monitor.start()
```

## 揽宝量化集成

此 MCP Server 是揽宝量化系统的一部分，作为**数据源模块**提供：

1. **策略选股结果同步**：将策略筛选出的股票批量添加到自选股
2. **实时监控**：监控策略持仓的价格异动
3. **信号验证**：交叉验证自选股与策略信号

在揽宝量化中的使用示例：
```python
# 在揽宝策略中
from eastmoney_mcp.api import EastMoneyAPI

api = EastMoneyAPI()

# 将策略选出的股票添加到"策略信号"分组
candidates = strategy.select_stocks()
api.add_to_watchlist(
    codes=[s.code for s in candidates],
    group_id="策略信号"
)

# 获取行情用于回测/实盘
quotes = api.get_batch_quotes([s.code for s in candidates])
```

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     揽宝量化系统                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   策略层     │  │   数据层     │  │   监控层     │      │
│  │  Strategies │  │     Data    │  │   Monitor   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           ▼                                 │
│               ┌───────────────────────┐                    │
│               │   EastMoney MCP      │                    │
│               │   ┌─────────────┐    │                    │
│               │   │  API Client │    │                    │
│               │   ├─────────────┤    │                    │
│               │   │   Monitor   │    │                    │
│               │   ├─────────────┤    │                    │
│               │   │  MCP Tools  │◄───┼──── Hermes/其他    │
│               │   └─────────────┘    │      客户端        │
│               └───────────┬───────────┘                    │
│                           │                                 │
│                    东方财富服务器                            │
│                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 开发计划

- [x] 基础 API 封装
- [x] MCP Server 实现
- [x] CLI 工具
- [x] 实时监控
- [ ] WebSocket 实时推送
- [ ] 历史数据缓存
- [ ] 多数据源聚合

## License

MIT - 揽宝量化团队
