import asyncio
import json
import pandas as pd
from fastmcp import Client

# client = Client("http://localhost:8000/mcp")
client = Client("http://localhost:8002/mcp")


async def call_tool(name: str):
    async with client:
        result = await client.call_tool("greet", {"name": name})
        print(result)


async def call_tool_hot(filter_by_turnover: bool = False):
    async with client:
        result = await client.call_tool(
            "stock_hot_rank_em", {"filter_by_turnover": filter_by_turnover}
        )
        text = getattr(result.content[0], "text", "") if result.content else ""
        data = json.loads(text) if text else []
        df = pd.DataFrame(data)
        print(df)


asyncio.run(call_tool("Ford"))
print("=== 人气榜（未过滤） ===")
asyncio.run(call_tool_hot(filter_by_turnover=False))
print("=== 人气榜 ∩ 成交额前100 ===")
asyncio.run(call_tool_hot(filter_by_turnover=True))
