import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(Path(__file__).parent.parent / ".env")

mcp = FastMCP("My MCP Server")

EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://guba.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://guba.eastmoney.com",
}

SINA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn",
}

_CACHE = {}
CACHE_TTL_SECONDS = 60


def _normalize_code(code: str) -> str:
    """统一归一化为 6 位数字代码。"""
    c = code.strip().lower()
    c = c.replace(".sz", "").replace(".sh", "").replace(".bj", "")
    if c.startswith("sz") or c.startswith("sh") or c.startswith("bj"):
        c = c[2:]
    return c[-6:] if len(c) >= 6 else c


def _get_cache(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["time"] < CACHE_TTL_SECONDS):
        return entry["value"]
    return None


def _set_cache(key: str, value):
    _CACHE[key] = {"time": time.time(), "value": value}


def _fetch_rank_list(session: requests.Session, page_size: int = 100) -> pd.DataFrame:
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    payload = {
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": page_size,
    }
    resp = session.post(url, json=payload, headers=EASTMONEY_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return pd.DataFrame(data.get("data", []))


def _fetch_sina_quotes(codes: list[str]) -> pd.DataFrame:
    sina_codes = [code.lower() for code in codes]
    url = "https://hq.sinajs.cn/list=" + ",".join(sina_codes)
    resp = requests.get(url, headers=SINA_HEADERS, timeout=15)
    resp.raise_for_status()

    rows = []
    for line in resp.text.strip().split(";"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r'var hq_str_(\w+)="(.*)"', line)
        if not match:
            continue
        code, content = match.groups()
        parts = content.split(",")
        if len(parts) < 4:
            continue
        rows.append(
            {
                "sina_code": code,
                "股票名称": parts[0],
                "昨收": float(parts[2]) if parts[2] else 0.0,
                "最新价": float(parts[3]) if parts[3] else 0.0,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["涨跌幅"] = (df["最新价"] - df["昨收"]) / df["昨收"] * 100
    return df


def _iwencai_claw_headers(call_type: str = "normal") -> dict:
    return {
        "X-Claw-Call-Type": call_type,
        "X-Claw-Skill-Id": "stock-search",
        "X-Claw-Skill-Version": "2.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }


def _fetch_turnover_top100_iwencai() -> set[str]:
    """通过 iwencai NL 查询获取成交额排名前 100 的股票代码。"""
    key = os.environ.get("IWENCAI_API_KEY", "")
    base_url = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com")
    if not key:
        return set()

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        **_iwencai_claw_headers(),
    }
    payload = {
        "query": "A股成交额排名前100",
        "page": "1",
        "limit": "100",
        "is_cache": "1",
        "expand_index": "true",
    }
    resp = requests.post(
        f"{base_url}/v1/query2data",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status_code", 0) != 0:
        return set()

    codes = set()
    for row in data.get("datas") or []:
        code = row.get("股票代码") or row.get("code") or row.get("证券代码")
        if code:
            codes.add(_normalize_code(str(code)))
    return codes


def _fetch_turnover_top100_eastmoney() -> set[str]:
    """通过东财 clist 接口获取成交额排名前 100 的股票代码（iwencai 不可用时 fallback）。"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f12",
        "fid": "f6",
    }
    resp = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", {}).get("diff", [])
    return {_normalize_code(item.get("f12", "")) for item in items if item.get("f12")}


def _get_top_turnover_codes() -> set[str]:
    """获取当日成交额排名前 100 代码，优先 iwencai，失败或无 key 时回退东财。"""
    cached = _get_cache("top_turnover_codes")
    if cached is not None:
        return cached

    codes = set()
    source = "iwencai"
    try:
        codes = _fetch_turnover_top100_iwencai()
    except Exception as e:
        print(f"[WARN] iwencai turnover query failed: {e}")
        codes = set()
    if not codes:
        source = "eastmoney"
        try:
            codes = _fetch_turnover_top100_eastmoney()
        except Exception as e:
            print(f"[WARN] eastmoney turnover fallback failed: {e}")
            codes = set()
    print(f"[INFO] top turnover loaded from {source}: {len(codes)} codes")

    _set_cache("top_turnover_codes", codes)
    return codes


def _get_stock_hot_rank_em(filter_by_turnover: bool = False) -> pd.DataFrame:
    cached_key = f"stock_hot_rank_em:{filter_by_turnover}"
    cached = _get_cache(cached_key)
    if cached is not None:
        return cached

    with requests.Session() as session:
        rank_df = _fetch_rank_list(session, page_size=100)

    if rank_df.empty:
        return pd.DataFrame()

    if filter_by_turnover:
        top_turnover = _get_top_turnover_codes()
        rank_df["norm_code"] = rank_df["sc"].apply(_normalize_code)
        rank_df = rank_df[rank_df["norm_code"].isin(top_turnover)].copy()
        rank_df = rank_df.drop(columns=["norm_code"])

    if rank_df.empty:
        return pd.DataFrame()

    quotes_df = _fetch_sina_quotes(rank_df["sc"].tolist())
    if quotes_df.empty:
        return pd.DataFrame()

    rank_df["sina_code"] = rank_df["sc"].str.lower()
    merged = rank_df.merge(quotes_df, on="sina_code", how="inner")
    merged["涨跌额"] = merged["最新价"] * merged["涨跌幅"] / 100
    merged["当前排名"] = pd.to_numeric(merged["rk"], errors="coerce")
    merged = merged.rename(columns={"sc": "代码"})
    merged = merged[
        [
            "当前排名",
            "代码",
            "股票名称",
            "最新价",
            "涨跌额",
            "涨跌幅",
        ]
    ]

    _set_cache(cached_key, merged)
    return merged


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


@mcp.tool
def stock_hot_rank_em(filter_by_turnover: bool = False) -> Any:
    hot_rank_df = _get_stock_hot_rank_em(filter_by_turnover=filter_by_turnover)
    print(hot_rank_df)
    return hot_rank_df.head(20).to_dict(orient="records")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8002)
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
