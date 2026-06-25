#!/usr/bin/env python3
"""
东方财富自选股 MCP Server 详细功能测试脚本
=================================================
用途：在主机上验证通过 docker-compose 启动的 eastmoney-mcp 服务是否正常工作。

运行前请确保：
1. 已执行 `docker compose up -d eastmoney-mcp` 启动服务
2. 已安装依赖：`pip install -r scripts/requirements-test.txt`
3. 如需测试需要登录态的接口（自选股相关），请在项目根目录 .env 中配置：
   EASTMONEY_APPKEY=你的AppKey
   EASTMONEY_COOKIE=你的Cookie字符串

常用命令：
    # 简洁报告
    python3 scripts/test_eastmoney_mcp.py

    # 完整 JSON 报告
    python3 scripts/test_eastmoney_mcp.py --json

    # 指定 URL 或超时
    python3 scripts/test_eastmoney_mcp.py --url http://localhost:8003/sse --timeout 60
"""

import argparse
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# 加载项目根目录 .env（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", verbose=False)
except ImportError:
    pass

try:
    from mcp.client.sse import sse_client
    from mcp import ClientSession
    import httpx
except ImportError as e:
    print(f"缺少依赖: {e}", file=sys.stderr)
    print("请先执行: pip install -r scripts/requirements-test.txt", file=sys.stderr)
    sys.exit(2)

DEFAULT_SSE_URL = "http://localhost:8003/sse"

# 所有需要验证的工具及其测试参数
TOOL_TEST_CASES = [
    {
        "name": "get_stock_quote",
        "arguments": {"code": "600519"},
        "needs_credential": True,
    },
    {
        "name": "get_batch_quotes",
        "arguments": {"codes": ["600519", "000858", "300750"]},
        "needs_credential": True,
    },
    {
        "name": "get_watchlist_groups",
        "arguments": {},
        "needs_credential": True,
    },
    {
        "name": "get_watchlist_summary",
        "arguments": {},
        "needs_credential": True,
    },
    {
        "name": "get_watchlist",
        "arguments": {},
        "needs_credential": True,
    },
    {
        "name": "create_watchlist_group",
        "arguments": {"name": "mcp-test-group"},
        "needs_credential": True,
        "write_operation": True,
    },
    {
        "name": "add_to_watchlist",
        "arguments": {"codes": ["600519"]},
        "needs_credential": True,
        "write_operation": True,
    },
    {
        "name": "remove_from_watchlist",
        "arguments": {"codes": ["600519"]},
        "needs_credential": True,
        "write_operation": True,
    },
    # 按 group_name 查询/操作的补充用例
    {
        "name": "get_watchlist",
        "display_name": "get_watchlist_by_name",
        "arguments": {"group_name": "自选股"},
        "needs_credential": True,
    },
    {
        "name": "get_watchlist_summary",
        "display_name": "get_watchlist_summary_by_name",
        "arguments": {"group_name": "自选股"},
        "needs_credential": True,
    },
]


def _has_credentials() -> bool:
    return bool(os.getenv("EASTMONEY_APPKEY") and os.getenv("EASTMONEY_COOKIE"))


def _extract_text(result) -> str:
    """从 CallToolResult 中提取第一个 TextContent 文本。"""
    for content in result.content:
        if hasattr(content, "text"):
            return content.text
    return ""


async def check_http_connectivity(url: str, timeout: float = 5.0) -> dict:
    """检查 SSE HTTP 端点是否可访问（只读取响应头，不等待流结束）。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url) as resp:
                # 只确认状态码和响应头，SSE 流本身不会结束
                return {
                    "ok": resp.status_code == 200,
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("content-type"),
                    "error": None,
                }
    except Exception as e:
        return {"ok": False, "status_code": None, "content_type": None, "error": str(e)}


async def run_tool_tests(session: ClientSession, timeout: int) -> list:
    """依次调用所有工具测试用例。"""
    results = []
    has_credential = _has_credentials()

    for case in TOOL_TEST_CASES:
        name = case["name"]
        display_name = case.get("display_name", name)
        item = {"name": display_name, "status": "pending", "detail": None}

        if case.get("needs_credential") and not has_credential:
            item["status"] = "skipped"
            item["detail"] = "缺少 EASTMONEY_APPKEY/EASTMONEY_COOKIE"
            results.append(item)
            continue

        try:
            call_result = await asyncio.wait_for(
                session.call_tool(name, case["arguments"]),
                timeout=timeout,
            )
            text = _extract_text(call_result)
            data = json.loads(text) if text else {}

            if isinstance(data, dict) and data.get("error"):
                item["status"] = "failed"
                item["detail"] = data["error"]
            else:
                item["status"] = "passed"
                # 保留关键摘要，避免报告过大
                if isinstance(data, dict):
                    summary = {k: v for k, v in data.items() if k != "quotes" and k != "stocks"}
                    if "count" in data:
                        summary["count"] = data["count"]
                    item["detail"] = summary or {"response": text[:200]}
                else:
                    item["detail"] = {"response": text[:200]}
        except asyncio.TimeoutError:
            item["status"] = "failed"
            item["detail"] = f"调用超时（>{timeout}s）"
        except Exception as e:
            item["status"] = "failed"
            item["detail"] = f"{type(e).__name__}: {e}"

        results.append(item)

    return results


async def run_tests(url: str, timeout: int) -> dict:
    """执行完整测试并生成报告。"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "target_url": url,
        "environment": {
            "EASTMONEY_APPKEY": "已设置" if os.getenv("EASTMONEY_APPKEY") else "未设置",
            "EASTMONEY_COOKIE": "已设置" if os.getenv("EASTMONEY_COOKIE") else "未设置",
        },
        "connectivity": None,
        "tool_list": [],
        "tool_tests": [],
        "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
    }

    # 1. HTTP 连通性
    conn = await check_http_connectivity(url)
    report["connectivity"] = conn
    if not conn["ok"]:
        report["summary"]["total"] += 1
        report["summary"]["failed"] += 1
        return report

    # 2. MCP 会话与工具列表
    try:
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)

                tools_result = await session.list_tools()
                report["tool_list"] = [t.name for t in tools_result.tools]

                # 3. 工具调用测试
                report["tool_tests"] = await run_tool_tests(session, timeout)
    except Exception as e:
        report["mcp_session_error"] = f"{type(e).__name__}: {e}"
        report["summary"]["total"] += 1
        report["summary"]["failed"] += 1
        return report

    # 汇总
    report["summary"]["total"] = 1 + len(report["tool_tests"])  # 1 表示 list_tools
    for item in report["tool_tests"]:
        report["summary"][item["status"]] += 1
    report["summary"]["passed"] += 1  # list_tools 通过

    return report


def print_report(report: dict, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("=" * 70)
    print("东方财富 MCP Server 功能测试报告")
    print("=" * 70)
    print(f"测试时间 : {report['timestamp']}")
    print(f"目标 URL : {report['target_url']}")
    print("环境变量 :")
    for k, v in report["environment"].items():
        print(f"  - {k}: {v}")

    print("-" * 70)
    conn = report["connectivity"]
    if conn["ok"]:
        print(f"✅ HTTP 连通性: OK (HTTP {conn['status_code']}, {conn['content_type']})")
    else:
        print(f"❌ HTTP 连通性: 失败 - {conn['error']}")

    if report.get("mcp_session_error"):
        print(f"❌ MCP 会话建立失败: {report['mcp_session_error']}")
        return

    print(f"🔧 发现工具 ({len(report['tool_list'])}): {', '.join(report['tool_list'])}")

    print("-" * 70)
    for item in report["tool_tests"]:
        status = item["status"]
        if status == "passed":
            print(f"✅ {item['name']}: 通过")
            if item.get("detail"):
                print(f"   摘要: {json.dumps(item['detail'], ensure_ascii=False)}")
        elif status == "skipped":
            print(f"⏭️  {item['name']}: 跳过 - {item['detail']}")
        else:
            print(f"❌ {item['name']}: 失败 - {item['detail']}")

    print("-" * 70)
    s = report["summary"]
    print(f"总计: {s['total']} | 通过: {s['passed']} | 失败: {s['failed']} | 跳过: {s['skipped']}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="东方财富 MCP Server 功能测试")
    parser.add_argument("--url", default=DEFAULT_SSE_URL, help=f"SSE URL (默认: {DEFAULT_SSE_URL})")
    parser.add_argument("--timeout", type=int, default=30, help="单次 MCP 调用超时（秒）")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON 报告")
    args = parser.parse_args()

    report = asyncio.run(run_tests(args.url, args.timeout))
    print_report(report, args.json)

    sys.exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
