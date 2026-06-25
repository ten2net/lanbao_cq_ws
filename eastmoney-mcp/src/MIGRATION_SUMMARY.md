# 东方财富自选股 Skill 迁移总结

## 迁移概况

已成功将 OpenClaw 中的两个东方财富自选股相关 skill 迁移到 Hermes/揽宝量化系统：

| 原 Skill | 新组件 | 功能 |
|---------|--------|------|
| `eastmoney-favor` | MCP Server + CLI | 自选股分组管理、股票增删改查 |
| `eastmoney-watchlist` | MCP Server + CLI | 实时行情监控、异动预警 |

## 迁移方式：MCP Server

选择 **MCP (Model Context Protocol)** 作为迁移方式，原因：

1. **标准化**: MCP 是 Anthropic 推动的开放标准
2. **跨平台**: 可同时被 Hermes、Claude Desktop、Cursor 使用
3. **实时性**: 支持订阅模式，适合行情监控
4. **与揽宝量化整合**: 可作为数据源模块为策略提供自选股数据

## 项目结构

```
/root/lanbao/tools/eastmoney-mcp-server/
├── src/eastmoney_mcp/
│   ├── __init__.py         # 包初始化
│   ├── models.py           # 数据模型 (Stock, Quote, Alert等)
│   ├── api.py              # 东方财富API客户端
│   ├── server.py           # MCP Server 主程序
│   ├── monitor.py          # 实时监控引擎
│   └── cli.py              # 命令行工具
├── scripts/                # 辅助脚本
├── pyproject.toml          # 项目配置
├── .env                    # 环境变量(已从OpenClaw迁移)
├── .env.example            # 环境变量模板
├── README.md               # 使用文档
├── mcp-config.json         # MCP配置示例
└── install.sh              # 安装脚本
```

## 安装状态

✅ **已完成**:
- [x] Python 包安装 (`pip install -e .`)
- [x] CLI 命令可用 (`eastmoney-cli`, `eastmoney-mcp`)
- [x] Hermes MCP 配置添加 (`~/.hermes/config.yaml`)
- [x] 环境变量迁移 (`.env` 文件)

## 可用工具 (MCP)

Hermes 现在可以通过 MCP 调用以下工具：

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `get_watchlist_groups` | 获取自选股分组列表 | - |
| `get_watchlist` | 获取指定分组的股票 | `group_id?` |
| `get_stock_quote` | 获取单只股票行情 | `code` |
| `get_batch_quotes` | 批量获取行情 | `codes` |
| `create_watchlist_group` | 创建分组 | `name` |
| `add_to_watchlist` | 添加股票 | `codes`, `group_id?` |
| `remove_from_watchlist` | 移除股票 | `codes`, `group_id?` |
| `get_watchlist_summary` | 获取概览统计 | `group_id?` |

## CLI 命令

```bash
# 查看分组
eastmoney-cli groups

# 列出自选股
eastmoney-cli list

# 查看行情
eastmoney-cli quotes
eastmoney-cli quotes -c 600519,000858

# 查看概览
eastmoney-cli summary

# 添加股票
eastmoney-cli add 600519,000858

# 移除股票
eastmoney-cli remove 600519

# 启动监控
eastmoney-cli monitor --change-pct 3.0
```

## 与揽宝量化集成

此 MCP Server 已成为揽宝量化的一部分，可用于：

1. **策略选股结果同步**
   ```python
   from eastmoney_mcp.api import EastMoneyAPI
   api = EastMoneyAPI()
   api.add_to_watchlist(codes=["600519", "000858"], group_id="策略信号")
   ```

2. **实时监控持仓**
   ```python
   from eastmoney_mcp.monitor import WatchlistMonitor
   monitor = WatchlistMonitor(api)
   monitor.add_callback(lambda alert: print(alert.message))
   monitor.start()
   ```

3. **数据获取用于回测**
   ```python
   quotes = api.get_batch_quotes(["sh600519", "sz000858"])
   ```

## 下一步建议

1. **测试连接**: 运行 `eastmoney-cli groups` 验证API连接正常
2. **揽宝整合**: 在策略中调用 `EastMoneyAPI` 同步选股结果
3. **定时任务**: 设置 cron job 自动同步数据
4. **监控启动**: 使用 `eastmoney-cli monitor` 启动实时预警

## 与原 Skill 对比

| 功能 | 原 OpenClaw Skill | 新 MCP Server |
|------|------------------|---------------|
| 分组管理 | ✅ | ✅ |
| 股票增删 | ✅ | ✅ |
| 行情查询 | ✅ | ✅ |
| 实时监控 | ✅ | ✅ |
| 飞书通知 | ✅ | ❌ (可扩展) |
| 分级预警 | ✅ | ✅ |
| 作为Hermes工具 | ❌ | ✅ |
| 跨平台支持 | ❌ | ✅ |

## 注意事项

1. **Cookie有效期**: 东方财富Cookie会过期，需要定期更新 `.env` 文件
2. **API限制**: 批量操作每次最多45只股票，超过会自动分批
3. **环境变量**: 已配置的 `EASTMONEY_APPKEY` 和 `EASTMONEY_COOKIE` 来自原OpenClaw
4. **重启Hermes**: 配置修改后需要重启 Hermes 以加载 MCP Server

---

*迁移完成时间: 2026-04-11*
*迁移者: Hermes Agent (揽宝量化团队)*
