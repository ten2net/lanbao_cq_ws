#!/usr/bin/env python3
"""
测试东方财富 API
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from eastmoney_mcp.api import EastMoneyAPI
import json

print("=" * 60)
print("东方财富 API 测试")
print("=" * 60)

# 检查环境变量
print("\n1. 环境变量检查:")
print(f"   APPKEY: {os.getenv('EASTMONEY_APPKEY', '未设置')[:30]}...")
print(f"   COOKIE: {os.getenv('EASTMONEY_COOKIE', '未设置')[:50]}...")

# 初始化 API
print("\n2. 初始化 API 客户端...")
api = EastMoneyAPI(
    appkey=os.getenv('EASTMONEY_APPKEY'),
    cookie=os.getenv('EASTMONEY_COOKIE')
)
print("   ✓ 初始化成功")

# 测试获取分组
print("\n3. 测试获取分组列表...")
try:
    import requests
    
    # 直接测试原始 API
    url = api._build_url("ggdefstkindexinfos", {"g": 1})
    print(f"   URL: {url[:100]}...")
    
    resp = api.session.get(url, headers=api.HEADERS)
    print(f"   状态码: {resp.status_code}")
    print(f"   响应长度: {len(resp.text)}")
    print(f"   响应前200字符: {resp.text[:200]}")
    
    # 解析响应
    state, data = api._parse_jsonp(resp)
    print(f"   解析状态: {state}")
    print(f"   数据: {data}")
    
    if data:
        print(f"   分组数量: {len(data.get('ginfolist', []))}")
        for g in data.get('ginfolist', []):
            print(f"     - {g.get('gname')} (ID: {g.get('gid')}, 数量: {g.get('gcount')})")
    
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 测试行情接口
print("\n4. 测试行情接口...")
try:
    quote = api.get_quote("600519")
    if quote:
        print(f"   ✓ 获取成功:")
        print(f"     名称: {quote.name}")
        print(f"     价格: {quote.price}")
        print(f"     涨跌: {quote.change_pct}%")
    else:
        print("   ✗ 获取失败，返回 None")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 测试批量行情
print("\n5. 测试批量行情...")
try:
    quotes = api.get_batch_quotes(["600519", "000858", "300750"])
    print(f"   ✓ 获取到 {len(quotes)} 只股票")
    for q in quotes:
        print(f"     - {q.name}: {q.price} ({q.change_pct:+.2f}%)")
except Exception as e:
    print(f"   ✗ 错误: {e}")

# 测试自选股（如果有分组）
print("\n6. 测试自选股列表...")
try:
    groups = api.get_watchlist_groups()
    if groups:
        print(f"   找到 {len(groups)} 个分组")
        # 尝试获取第一个分组的自选股
        stocks = api.get_watchlist(groups[0].id)
        print(f"   第一个分组有 {len(stocks)} 只股票")
        for s in stocks[:5]:
            print(f"     - {s.name} ({s.code})")
    else:
        print("   没有分组")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
