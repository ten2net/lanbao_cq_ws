"""
东方财富 API 客户端
基于 OpenClaw 原始代码重构
"""

import re
import json
import time
import logging
from typing import List, Dict, Optional, Any, Tuple, Union
from datetime import datetime
from urllib.parse import urlencode, quote
from pathlib import Path

import requests
from requests import Response

from .models import Stock, StockQuote, WatchlistGroup

logger = logging.getLogger(__name__)


class EastMoneyAPI:
    """
    东方财富 API 客户端
    """
    
    # API 基础地址
    BASE_URL = "http://myfavor.eastmoney.com/v4/webouter"
    QUOTE_URL = "http://push2.eastmoney.com/api/qt/stock/get"
    ULIST_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/zixuan/',
    }
    
    def __init__(self, appkey: Optional[str] = None, cookie: Optional[str] = None, token: Optional[str] = None):
        """
        初始化 API 客户端
        
        Args:
            appkey: 东方财富 AppKey
            cookie: 完整 Cookie 字符串
            token: em_token（可选，从 cookie 中解析）
        """
        self.appkey = appkey
        self.cookie = cookie
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        
        if cookie:
            self._parse_cookie(cookie)
    
    def _parse_cookie(self, cookie_str: str):
        """解析 Cookie 字符串"""
        cookie_str = cookie_str.strip()

        # 如果是文件路径，读取文件
        if cookie_str.startswith('/') or len(cookie_str) < 100:
            if Path(cookie_str).exists():
                with open(cookie_str, 'r') as f:
                    cookie_str = f.read().strip()

        # 解析 key=value 对
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()

        self.session.cookies.update(cookies)

        # 提取常用 token（优先 ut，其次 em_token）
        if 'ut' in cookies:
            self.token = cookies['ut']
        elif 'em_token' in cookies:
            self.token = cookies['em_token']
    
    def _build_url(self, action: str, params: Dict) -> str:
        """构建 API URL（JSONP 格式）"""
        ts = int(time.time() * 1000) - 10

        # 添加 ut 参数用于认证（EastMoney 部分接口需要）
        if self.token and 'ut' not in params:
            params['ut'] = self.token

        if self.appkey:
            url = f"{self.BASE_URL}/{action}?appkey={self.appkey}&cb=jQuery_{ts}&"
        else:
            url = f"{self.BASE_URL}/{action}?cb=jQuery_{ts}&"

        # 添加参数
        param_str = urlencode(params)
        url += param_str + f"&_={ts}"

        # 修复 URL 编码问题（东方财富特殊处理：要求 $ 不被编码）
        url = url.replace("%24", "$")

        return url
    
    def _parse_jsonp(self, resp: Response) -> Tuple[bool, Any]:
        """解析 JSONP 响应"""
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.content}")
        
        text = resp.text.strip()
        
        # 提取 JSON 部分
        if '(' in text and ')' in text:
            try:
                # 找到最外层的括号
                start = text.index('(')
                end = text.rindex(')')
                json_text = text[start + 1:end]
                data = json.loads(json_text)
                # 东方财富 API: state=0 表示成功
                return data.get("state", 0) == 0, data.get("data")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"JSON 解析错误: {e}, text: {text[:200]}")
                return False, None
        else:
            # 尝试直接解析 JSON
            try:
                data = json.loads(text)
                # 东方财富 API: state=0 表示成功
                return data.get("state", 0) == 0, data.get("data")
            except json.JSONDecodeError:
                return False, None
    
    # ============ 自选股分组管理 ============
    
    def _ensure_cutm_token(self):
        """确保 CUToken cookie 存在，如果不存在则尝试获取"""
        if 'CUToken' in self.session.cookies:
            return

        # 使用独立请求获取 CUToken，避免污染 session 连接池
        try:
            ut = self.token or self.session.cookies.get('ut', '')
            if not ut:
                return

            # 独立请求，不共享 session
            headers = {
                'User-Agent': self.HEADERS['User-Agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': self.HEADERS['Accept-Language'],
                'Cookie': f'ut={ut}',
            }
            resp = requests.get(
                f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?ut={ut}",
                headers=headers, timeout=10, allow_redirects=True
            )
            # 从响应 cookies 中提取 CUToken
            if 'CUToken' in resp.cookies:
                self.session.cookies.set('CUToken', resp.cookies['CUToken'])
        except Exception as e:
            logger.debug(f"获取 CUToken 失败（非致命）: {e}")

    def get_watchlist_groups(self) -> List[WatchlistGroup]:
        """获取所有自选股分组"""
        self._ensure_cutm_token()
        url = self._build_url("ggdefstkindexinfos", {"g": 1})
        resp = self.session.get(url, headers=self.HEADERS)

        state, data = self._parse_jsonp(resp)
        # 东方财富 API: state=0 表示成功
        if data is None:
            return []

        groups = []
        for g in data.get("ginfolist", []):
            groups.append(WatchlistGroup(
                id=str(g.get("gid", "")),
                name=g.get("gname", ""),
                count=0  # API 不返回 count，需要单独获取
            ))

        return groups
    
    def create_group(self, name: str) -> bool:
        """创建分组"""
        self._ensure_cutm_token()
        url = self._build_url("ag", {"gn": name})
        resp = self.session.get(url, headers=self.HEADERS)
        state, data = self._parse_jsonp(resp)
        return state

    def delete_group(self, group_id: str) -> bool:
        """删除分组"""
        self._ensure_cutm_token()
        url = self._build_url("dg", {"g": group_id})
        resp = self.session.get(url, headers=self.HEADERS)
        state, data = self._parse_jsonp(resp)
        return state
    
    def get_group_id(self, name: str) -> Optional[str]:
        """根据名称获取分组 ID"""
        groups = self.get_watchlist_groups()
        for g in groups:
            if g.name == name:
                return g.id
        return None
    
    # ============ 自选股管理 ============
    
    def get_watchlist(self, group_id: Optional[str] = None, group_name: Optional[str] = None) -> List[Stock]:
        """
        获取自选股列表

        Args:
            group_id: 分组 ID
            group_name: 分组名称（与 group_id 二选一）
        """
        self._ensure_cutm_token()
        if not group_id and group_name:
            group_id = self.get_group_id(group_name)

        if not group_id:
            logger.warning(f"未找到分组: {group_name}")
            return []

        url = self._build_url("gstkinfos", {"g": group_id})
        resp = self.session.get(url, headers=self.HEADERS)

        state, result = self._parse_jsonp(resp)
        if result is None:
            return []

        stocks = []
        for item in result.get("stkinfolist", []):
            # security 字段格式: "1$600519" 或 "0$000001" 或 "0$002491$10096287127286"
            security = item.get("security", "")
            if "$" in security:
                parts = security.split("$")
                market_code = parts[0]
                code = parts[1]
                market = {"1": "sh", "0": "sz", "116": "hk", "105": "us", "90": "block",
                         "112": "commodity", "102": "futures"}.get(market_code, "sz")
                stocks.append(Stock(
                    code=code,
                    name=item.get("stockName", ""),
                    market=market,
                    full_code=f"{market}{code}"
                ))

        return stocks
    
    def add_to_watchlist(self, codes: List[str], group_id: Optional[str] = None,
                        group_name: Optional[str] = None) -> bool:
        """
        添加股票到自选股

        Args:
            codes: 股票代码列表（6位数字）
            group_id: 分组 ID
            group_name: 分组名称
        """
        self._ensure_cutm_token()
        if not group_id and group_name:
            group_id = self.get_group_id(group_name)
            if not group_id:
                # 尝试创建分组
                self.create_group(group_name)
                group_id = self.get_group_id(group_name)

        if not group_id:
            logger.error("未找到或创建分组")
            return False

        # 转换代码格式
        em_codes = [self._to_eastmoney_code(c) for c in codes]

        # 分批添加（每批最多45只）
        for i in range(0, len(em_codes), 45):
            batch = em_codes[i:i+45]
            params = {
                "g": group_id,
                "scs": ",".join(batch)  # 批量添加参数
            }
            url = self._build_url("aslot", params)
            resp = self.session.get(url, headers=self.HEADERS)

            # 直接解析完整响应以获取 state 和 message
            try:
                text = resp.text.strip()
                if '(' in text and ')' in text:
                    start = text.index('(')
                    end = text.rindex(')')
                    json_text = text[start + 1:end]
                    result = json.loads(json_text)
                else:
                    result = json.loads(text)
                state = result.get("state", 0)
                if state == 0:
                    continue
                # state=-217 表示"该证券代码已存在"，视为成功
                if state == -217:
                    logger.debug(f"股票已存在（无需添加）: {batch}")
                    continue
                logger.error(f"批量添加失败: {batch}, state={state}, message={result.get('message', 'unknown')}")
                return False
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析响应失败: {e}, text: {resp.text[:200]}")
                return False

        return True
    
    def remove_from_watchlist(self, codes: List[str], group_id: Optional[str] = None,
                             group_name: Optional[str] = None) -> bool:
        """从自选股中移除股票"""
        self._ensure_cutm_token()
        if not group_id and group_name:
            group_id = self.get_group_id(group_name)

        if not group_id:
            return False

        # 转换代码格式
        em_codes = [self._to_eastmoney_code(c) for c in codes]

        for code in em_codes:
            params = {"g": group_id, "sc": code}
            url = self._build_url("ds", params)
            resp = self.session.get(url, headers=self.HEADERS)

            state, data = self._parse_jsonp(resp)
            if not state:
                logger.error(f"删除失败: {code}")

        return True

    def clear_watchlist(self, group_id: Optional[str] = None, group_name: Optional[str] = None) -> bool:
        """清空分组"""
        stocks = self.get_watchlist(group_id, group_name)
        if not stocks:
            return True

        codes = [s.code for s in stocks]
        return self.remove_from_watchlist(codes, group_id, group_name)
    
    def _to_eastmoney_code(self, code: str) -> str:
        """
        将股票代码转换为东方财富格式
        600519 -> 1$600519 (上海)
        000001 -> 0$000001 (深圳)
        """
        # 去除市场前缀
        if code.startswith(('sh', 'sz', 'bj', 'hk', 'us')):
            code = code[2:]

        # 根据代码判断市场
        try:
            code_int = int(code)
            if 600000 <= code_int < 800000 or code_int >= 880000:
                return f"1${code}"  # 上海
            else:
                return f"0${code}"  # 深圳
        except ValueError:
            # 可能是港股或美股
            if len(code) == 5:
                return f"116${code}"  # 港股
            else:
                return f"105${code}"  # 美股
    
    # ============ 行情接口 ============
    
    def get_quote(self, code: str) -> Optional[StockQuote]:
        """获取单只股票行情"""
        # 处理带市场前缀的代码
        if code.startswith(('sh', 'sz', 'bj', 'hk', 'us')):
            market = code[:2]
            code_num = code[2:]
        else:
            code_num = code
            market = self._detect_market(code)
        
        secid = self._get_secid(f"{market}{code_num}")
        
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f169,f168"
        }
        
        try:
            resp = self.session.get(self.QUOTE_URL, params=params, timeout=10)
            data = resp.json().get("data", {})
            
            if not data:
                return None
            
            # 解析字段（东方财富字段编码，需要除以100）
            return StockQuote(
                code=code_num,
                name=data.get("f58", ""),
                price=self._safe_div100(data.get("f43")),
                open=self._safe_div100(data.get("f46")),
                high=self._safe_div100(data.get("f44")),
                low=self._safe_div100(data.get("f45")),
                prev_close=self._safe_div100(data.get("f60")),
                change=self._safe_div100(data.get("f169")),
                change_pct=self._safe_div100(data.get("f170")),
                volume=self._safe_int(data.get("f47")),
                amount=self._safe_div10000(data.get("f48")),  # 成交额：元->万元
                turnover=self._safe_div100(data.get("f168")),
            )
        except Exception as e:
            logger.error(f"获取行情失败 {code}: {e}")
            return None
    
    def get_batch_quotes(self, codes: List[str]) -> List[StockQuote]:
        """批量获取行情"""
        results = []
        
        # 标准化代码
        full_codes = []
        for code in codes:
            if code.startswith(('sh', 'sz', 'bj', 'hk', 'us')):
                full_codes.append(code)
            else:
                market = self._detect_market(code)
                full_codes.append(f"{market}{code}")
        
        # 分批处理（每批最多 100 只）
        for i in range(0, len(full_codes), 100):
            batch = full_codes[i:i+100]
            secids = [self._get_secid(c) for c in batch]
            
            params = {
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fields": "f12,f14,f2,f3,f4,f5,f6,f8,f10,f15,f16,f17,f18,f20,f21",
                "secids": ",".join(secids)
            }
            
            try:
                resp = self.session.get(self.ULIST_URL, params=params, timeout=10)
                data = resp.json()
                
                for item in data.get("data", {}).get("diff", []):
                    quote = self._parse_ulist_item(item)
                    if quote:
                        results.append(quote)
            except Exception as e:
                logger.error(f"批量获取行情失败: {e}")
        
        return results
    
    def _parse_ulist_item(self, item: Dict) -> Optional[StockQuote]:
        """解析 ulist 接口数据
        
        注意: 使用 fltt=2 时 API 直接返回浮点数，不需要再除以 100/1000
        字段说明:
            f20 = 总市值（元）
            f21 = 流通市值（元）
        """
        try:
            code = item.get("f12", "")
            market = self._detect_market(code)
            
            # 计算市值（元 -> 亿元）
            total_cap = self._safe_div100000000(item.get("f20"))  # 总市值
            circulating_cap_yi = self._safe_div100000000(item.get("f21"))  # 流通市值

            return StockQuote(
                code=code,
                name=item.get("f14", ""),
                price=self._safe_float(item.get("f2")),
                open=self._safe_float(item.get("f17")),
                high=self._safe_float(item.get("f15")),
                low=self._safe_float(item.get("f16")),
                prev_close=self._safe_float(item.get("f18")),
                change=self._safe_float(item.get("f4")),
                change_pct=self._safe_float(item.get("f3")),
                volume=self._safe_int(item.get("f5")),
                amount=self._safe_div10000(item.get("f6")),  # 金额保持除以10000(元->万元)
                turnover=self._safe_float(item.get("f8")),
                volume_ratio=self._safe_float(item.get("f10")),  # f10 = 量比
                market_cap=total_cap if total_cap > 0 else None,
                circulating_cap=circulating_cap_yi if circulating_cap_yi > 0 else None,
            )
        except Exception as e:
            logger.error(f"解析行情数据失败: {e}")
            return None
    
    def _safe_float(self, val) -> float:
        """安全转浮点数"""
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    
    # ============ 工具方法 ============
    
    def _detect_market(self, code: str) -> str:
        """检测市场类型"""
        if len(code) == 5:
            return "hk"
        if code.isalpha():
            return "us"
        
        try:
            code_int = int(code)
            if 600000 <= code_int < 800000:
                return "sh"
            elif code_int >= 880000:
                return "sh"  # 板块指数
            else:
                return "sz"
        except ValueError:
            return "sz"
    
    def _get_secid(self, full_code: str) -> str:
        """
        获取东方财富 secid
        格式: 0.{code} 深市, 1.{code} 沪市, 105.{code} 美股, 116.{code} 港股
        """
        market = full_code[:2]
        code = full_code[2:]
        
        mapping = {
            "sz": "0",
            "sh": "1",
            "bj": "0",
            "us": "105",
            "hk": "116"
        }
        
        return f"{mapping.get(market, '0')}.{code}"
    
    def _safe_div100(self, val) -> float:
        """安全除以100"""
        if val is None:
            return 0.0
        try:
            return float(val) / 100
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_div1000(self, val) -> float:
        """安全除以1000"""
        if val is None:
            return 0.0
        try:
            return float(val) / 1000
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_div10000(self, val) -> float:
        """安全除以10000"""
        if val is None:
            return 0.0
        try:
            return float(val) / 10000
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_div100000000(self, val) -> float:
        """安全除以100000000（元转亿元）"""
        if val is None:
            return 0.0
        try:
            return float(val) / 100000000
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, val) -> int:
        """安全转整数"""
        if val is None:
            return 0
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0
