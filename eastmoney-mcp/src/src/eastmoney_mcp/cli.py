"""
CLI 命令行工具
方便在终端直接使用自选股功能
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

from .api import EastMoneyAPI
from .models import AlertConfig
from .monitor import WatchlistMonitor

# 加载环境变量
load_dotenv()


def print_table(headers: list, rows: list):
    """打印表格"""
    # 计算列宽
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # 打印表头
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("-" * (sum(widths) + 3 * (len(headers) - 1)))
    
    # 打印数据
    for row in rows:
        print(" | ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def cmd_groups(args):
    """列出分组"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    groups = api.get_watchlist_groups()
    
    if args.json:
        print(json.dumps([g.model_dump() for g in groups], ensure_ascii=False, indent=2))
    else:
        print_table(["ID", "名称", "数量"], [
            [g.id, g.name, g.count] for g in groups
        ])


def cmd_list(args):
    """列出自选股"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    stocks = api.get_watchlist(args.group)
    
    if args.json:
        print(json.dumps([s.model_dump() for s in stocks], ensure_ascii=False, indent=2))
    else:
        print(f"共 {len(stocks)} 只自选股:")
        for i, s in enumerate(stocks, 1):
            print(f"  {i}. {s.name} ({s.code}) [{s.market}]")


def cmd_quotes(args):
    """查看行情"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    if args.codes:
        codes = args.codes.split(",")
        quotes = api.get_batch_quotes(codes)
    else:
        stocks = api.get_watchlist(args.group)
        codes = [s.full_code for s in stocks if s.full_code]
        quotes = api.get_batch_quotes(codes)
    
    if args.json:
        print(json.dumps([q.model_dump() for q in quotes], ensure_ascii=False, indent=2))
    else:
        print_table(
            ["代码", "名称", "现价", "涨跌", "涨跌幅%", "换手率%"],
            [[
                q.code,
                q.name[:8],
                f"{q.price:.2f}",
                f"{q.change:+.2f}",
                f"{q.change_pct:+.2f}",
                f"{q.turnover:.2f}" if q.turnover else "-"
            ] for q in quotes]
        )


def cmd_summary(args):
    """查看概览"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    stocks = api.get_watchlist(args.group)
    codes = [s.full_code for s in stocks if s.full_code]
    quotes = api.get_batch_quotes(codes)
    
    up_count = sum(1 for q in quotes if q.change_pct > 0)
    down_count = sum(1 for q in quotes if q.change_pct < 0)
    flat_count = len(quotes) - up_count - down_count
    avg_change = sum(q.change_pct for q in quotes) / len(quotes) if quotes else 0
    
    top_gainer = max(quotes, key=lambda x: x.change_pct) if quotes else None
    top_loser = min(quotes, key=lambda x: x.change_pct) if quotes else None
    
    print(f"📊 自选股概览")
    print(f"━━━━━━━━━━━━━━")
    print(f"总数: {len(quotes)} 只")
    print(f"上涨: {up_count} 只 | 下跌: {down_count} 只 | 平盘: {flat_count} 只")
    print(f"平均涨跌幅: {avg_change:+.2f}%")
    
    if top_gainer:
        print(f"\n🏆 涨幅最大: {top_gainer.name} ({top_gainer.code}) +{top_gainer.change_pct:.2f}%")
    if top_loser:
        print(f"📉 跌幅最大: {top_loser.name} ({top_loser.code}) {top_loser.change_pct:.2f}%")


def cmd_add(args):
    """添加股票"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    codes = args.codes.split(",")
    success = api.add_to_watchlist(codes, args.group)
    
    if success:
        print(f"✅ 成功添加 {len(codes)} 只股票到自选股")
    else:
        print(f"❌ 添加失败")


def cmd_remove(args):
    """移除股票"""
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    codes = args.codes.split(",")
    success = api.remove_from_watchlist(codes, args.group)
    
    if success:
        print(f"✅ 成功移除 {len(codes)} 只股票")
    else:
        print(f"❌ 移除失败")


def cmd_monitor(args):
    """启动监控"""
    import asyncio
    
    api = EastMoneyAPI(
        appkey=os.getenv("EASTMONEY_APPKEY"),
        cookie=os.getenv("EASTMONEY_COOKIE")
    )
    
    config = AlertConfig(
        change_pct=args.change_pct,
        check_interval=args.interval
    )
    
    monitor = WatchlistMonitor(api, config)
    
    def on_alert(alert):
        emoji = {"emergency": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(alert.level, "ℹ️")
        print(f"\n{emoji} [{alert.level.upper()}] {alert.stock.name} ({alert.stock.code})")
        print(f"   价格: ¥{alert.current_price:.2f} ({alert.change_pct:+.2f}%)")
        print(f"   {alert.message}")
        print()
    
    monitor.add_callback(on_alert)
    
    print(f"🔍 启动自选股监控...")
    print(f"   涨跌幅阈值: ±{config.change_pct}%")
    print(f"   检查间隔: {config.check_interval} 秒")
    print(f"   按 Ctrl+C 停止\n")
    
    async def run():
        await monitor.start(args.group)
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await monitor.stop()
            print("\n✅ 监控已停止")
    
    asyncio.run(run())


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="eastmoney-cli",
        description="东方财富自选股 CLI 工具"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # groups
    p_groups = subparsers.add_parser("groups", help="列出分组")
    p_groups.set_defaults(func=cmd_groups)
    
    # list
    p_list = subparsers.add_parser("list", help="列出自选股")
    p_list.add_argument("-g", "--group", help="分组ID")
    p_list.set_defaults(func=cmd_list)
    
    # quotes
    p_quotes = subparsers.add_parser("quotes", help="查看行情")
    p_quotes.add_argument("-g", "--group", help="分组ID")
    p_quotes.add_argument("-c", "--codes", help="股票代码，逗号分隔")
    p_quotes.set_defaults(func=cmd_quotes)
    
    # summary
    p_summary = subparsers.add_parser("summary", help="查看概览")
    p_summary.add_argument("-g", "--group", help="分组ID")
    p_summary.set_defaults(func=cmd_summary)
    
    # add
    p_add = subparsers.add_parser("add", help="添加股票")
    p_add.add_argument("codes", help="股票代码，逗号分隔")
    p_add.add_argument("-g", "--group", help="分组ID")
    p_add.set_defaults(func=cmd_add)
    
    # remove
    p_remove = subparsers.add_parser("remove", help="移除股票")
    p_remove.add_argument("codes", help="股票代码，逗号分隔")
    p_remove.add_argument("-g", "--group", help="分组ID")
    p_remove.set_defaults(func=cmd_remove)
    
    # monitor
    p_monitor = subparsers.add_parser("monitor", help="启动监控")
    p_monitor.add_argument("-g", "--group", help="分组ID")
    p_monitor.add_argument("-p", "--change-pct", type=float, default=5.0, help="涨跌幅阈值")
    p_monitor.add_argument("-i", "--interval", type=int, default=5, help="检查间隔(秒)")
    p_monitor.set_defaults(func=cmd_monitor)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
