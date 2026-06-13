# Agent Instructions

## 强制使用 kimi-datasource 获取外部数据

当用户询问或任务涉及以下任何外部数据时，**必须**使用 `kimi-datasource` skill，并通过其 MCP server 工具获取数据：

- A股、港股、美股实时行情或历史价格
- 股票财报、股东信息、分析师评级
- 宏观经济数据（GDP、通胀、人口等）
- 中国企业工商信息
- arXiv / Google Scholar 学术论文
- 自选股行情

### 标准工作流

1. 调用 `Skill` 工具加载 `kimi-datasource` skill。
2. 使用 `mcp__plugin-kimi-datasource-data__get_data_source_desc` 获取对应数据源的接口文档。
3. 阅读接口文档后，使用 `mcp__plugin-kimi-datasource-data__call_data_source_tool` 调用具体 API。
4. 将结果返回给用户；如需进一步处理，读取 CSV 文件后再分析。

### 禁止行为

- **禁止**使用 `WebSearch`、`FetchURL`、Bash 脚本、Python 脚本或其他工具绕过 `kimi-datasource` 获取上述数据。
- **禁止**凭记忆猜测股票代码或企业全称；股票代码必须先通过联网工具核对，或让用户确认。
- **禁止**在没有读取数据源描述的情况下直接硬编码 `api_name`。

### 例外

如果 `kimi-datasource` 明确返回错误表示该数据无法提供，可以将错误原因告知用户，并询问是否需要使用其他方式。
