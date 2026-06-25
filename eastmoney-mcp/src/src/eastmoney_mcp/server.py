"""
东方财富自选股 MCP Server
提供自选股管理和行情监控的 MCP 工具接口
"""

import os
import sys
import json
import asyncio
import logging
from typing import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Tool,
    Resource,
    TextContent,
    ImageContent,
    LoggingLevel,
    EmbeddedResource,
)
from mcp.shared.exceptions import McpError

from .api import EastMoneyAPI
from .models import Stock, StockQuote, WatchlistGroup, Alert, AlertConfig
from .monitor import WatchlistMonitor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eastmoney-mcp")


@asynccontextmanager
async def app_lifespan(server: Server):
    """应用生命周期管理"""
    # 初始化
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    monitor = None
    
    try:
        yield {"api": api, "monitor": monitor}
    finally:
        # 清理
        if monitor:
            await monitor.stop()


# 创建 MCP Server
app = Server(
    "eastmoney-watchlist",
    lifespan=app_lifespan
)


@app.list_resources()
async def list_resources() -> Sequence[Resource]:
    """列出可用资源"""
    return [
        Resource(
            uri="watchlist://groups",
            name="自选股分组列表",
            mimeType="application/json",
            description="东方财富自选股分组信息"
        ),
        Resource(
            uri="watchlist://quotes",
            name="自选股实时行情",
            mimeType="application/json",
            description="自选股的实时行情数据"
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源"""
    api: EastMoneyAPI = app.request_context.lifespan_context["api"]
    
    if uri == "watchlist://groups":
        try:
            groups = api.get_watchlist_groups()
            return json.dumps([g.model_dump() for g in groups], ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    elif uri == "watchlist://quotes":
        try:
            # 获取默认分组的自选股行情
            stocks = api.get_watchlist()
            codes = [s.full_code for s in stocks if s.full_code]
            if codes:
                quotes = api.get_batch_quotes(codes)
                return json.dumps([q.model_dump() for q in quotes], ensure_ascii=False, indent=2)
            return json.dumps([])
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    raise McpError(f"未知资源: {uri}")


@app.list_tools()
async def list_tools() -> Sequence[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="get_watchlist_groups",
            description="获取东方财富自选股分组列表",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_watchlist",
            description="获取指定分组的自选股列表（支持按 group_id 或 group_name 查询）",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "分组ID，与 group_name 二选一"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "分组名称，与 group_id 二选一；若同时提供优先使用 group_id"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_stock_quote",
            description="获取单只股票的实时行情",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "股票代码，如 600519 或 sh600519"
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="get_batch_quotes",
            description="批量获取多只股票行情",
            inputSchema={
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表，如 [\"600519\", \"000858\"]"
                    }
                },
                "required": ["codes"]
            }
        ),
        Tool(
            name="create_watchlist_group",
            description="创建新的自选股分组",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "分组名称"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="add_to_watchlist",
            description="添加股票到自选股（支持按 group_id 或 group_name 指定分组，group_name 不存在时会自动创建）",
            inputSchema={
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表"
                    },
                    "group_id": {
                        "type": "string",
                        "description": "分组ID，与 group_name 二选一"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "分组名称，与 group_id 二选一；若同时提供优先使用 group_id"
                    }
                },
                "required": ["codes"]
            }
        ),
        Tool(
            name="remove_from_watchlist",
            description="从自选股中移除股票（支持按 group_id 或 group_name 指定分组）",
            inputSchema={
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表"
                    },
                    "group_id": {
                        "type": "string",
                        "description": "分组ID，与 group_name 二选一"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "分组名称，与 group_id 二选一；若同时提供优先使用 group_id"
                    }
                },
                "required": ["codes"]
            }
        ),
        Tool(
            name="get_watchlist_summary",
            description="获取自选股概览统计（支持按 group_id 或 group_name 查询）",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "分组ID，与 group_name 二选一"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "分组名称，与 group_id 二选一；若同时提供优先使用 group_id"
                    }
                },
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """调用工具"""
    api: EastMoneyAPI = app.request_context.lifespan_context["api"]
    
    try:
        if name == "get_watchlist_groups":
            groups = api.get_watchlist_groups()
            result = {
                "groups": [g.model_dump() for g in groups],
                "count": len(groups),
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "get_watchlist":
            group_id = arguments.get("group_id")
            group_name = arguments.get("group_name")
            stocks = api.get_watchlist(group_id, group_name)
            result = {
                "stocks": [s.model_dump() for s in stocks],
                "count": len(stocks),
                "group_id": group_id,
                "group_name": group_name,
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "get_stock_quote":
            code = arguments["code"]
            quote = api.get_quote(code)
            if quote:
                return [TextContent(type="text", text=json.dumps(quote.model_dump(mode='json'), ensure_ascii=False, indent=2))]
            else:
                return [TextContent(type="text", text=json.dumps({"error": f"无法获取 {code} 的行情"}))]
        
        elif name == "get_batch_quotes":
            codes = arguments["codes"]
            quotes = api.get_batch_quotes(codes)
            result = {
                "quotes": [q.model_dump(mode='json') for q in quotes],
                "count": len(quotes),
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "create_watchlist_group":
            name = arguments["name"]
            success = api.create_group(name)
            return [TextContent(type="text", text=json.dumps({
                "success": success,
                "name": name,
                "message": f"分组 '{name}' 创建{'成功' if success else '失败'}"
            }, ensure_ascii=False))]
        
        elif name == "add_to_watchlist":
            codes = arguments["codes"]
            group_id = arguments.get("group_id")
            group_name = arguments.get("group_name")
            success = api.add_to_watchlist(codes, group_id, group_name)
            return [TextContent(type="text", text=json.dumps({
                "success": success,
                "codes": codes,
                "group_id": group_id,
                "group_name": group_name,
                "message": f"成功添加 {len(codes)} 只股票" if success else "添加失败"
            }, ensure_ascii=False))]
        
        elif name == "remove_from_watchlist":
            codes = arguments["codes"]
            group_id = arguments.get("group_id")
            group_name = arguments.get("group_name")
            success = api.remove_from_watchlist(codes, group_id, group_name)
            return [TextContent(type="text", text=json.dumps({
                "success": success,
                "codes": codes,
                "group_id": group_id,
                "group_name": group_name,
                "message": f"成功移除 {len(codes)} 只股票" if success else "移除失败"
            }, ensure_ascii=False))]
        
        elif name == "get_watchlist_summary":
            group_id = arguments.get("group_id")
            group_name = arguments.get("group_name")
            stocks = api.get_watchlist(group_id, group_name)
            codes = [s.full_code for s in stocks if s.full_code]

            if not codes:
                # 分组存在但为空时返回正常的空统计，而不是 error
                result = {
                    "total_stocks": 0,
                    "up_count": 0,
                    "down_count": 0,
                    "flat_count": 0,
                    "avg_change_pct": 0.0,
                    "top_gainer": None,
                    "top_loser": None,
                    "group_id": group_id,
                    "group_name": group_name,
                    "note": "该分组下暂无自选股",
                    "timestamp": datetime.now().isoformat()
                }
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

            quotes = api.get_batch_quotes(codes)

            up_count = sum(1 for q in quotes if q.change_pct > 0)
            down_count = sum(1 for q in quotes if q.change_pct < 0)
            flat_count = len(quotes) - up_count - down_count
            avg_change = sum(q.change_pct for q in quotes) / len(quotes) if quotes else 0

            top_gainer = max(quotes, key=lambda x: x.change_pct) if quotes else None
            top_loser = min(quotes, key=lambda x: x.change_pct) if quotes else None

            result = {
                "total_stocks": len(quotes),
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "avg_change_pct": round(avg_change, 2),
                "top_gainer": top_gainer.model_dump(mode='json') if top_gainer else None,
                "top_loser": top_loser.model_dump(mode='json') if top_loser else None,
                "group_id": group_id,
                "group_name": group_name,
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        else:
            raise McpError(f"未知工具: {name}")
    
    except Exception as e:
        logger.error(f"工具调用失败 {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="东方财富自选股 MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                       help="传输方式 (默认: stdio)")
    parser.add_argument("--port", type=int, default=3000,
                       help="SSE 模式端口 (默认: 3000)")
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    else:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount

        transport = SseServerTransport("/messages")

        async def handle_sse(request):
            async with transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        async def handle_messages(scope, receive, send):
            await transport.handle_post_message(scope, receive, send)

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages", app=handle_messages),
            ]
        )

        import uvicorn
        config = uvicorn.Config(starlette_app, host="0.0.0.0", port=args.port)
        server = uvicorn.Server(config)
        await server.serve()


def main_sync():
    """同步入口 - 用于 CLI entry point"""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
