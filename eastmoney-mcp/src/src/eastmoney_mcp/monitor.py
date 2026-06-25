"""
自选股监控模块
实时监控自选股价格异动
"""

import asyncio
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from collections import deque

from .api import EastMoneyAPI
from .models import Stock, StockQuote, Alert, AlertConfig

logger = logging.getLogger(__name__)


class WatchlistMonitor:
    """
    自选股监控器
    实时监控价格异动并触发预警
    """
    
    def __init__(self, api: EastMoneyAPI, config: Optional[AlertConfig] = None):
        self.api = api
        self.config = config or AlertConfig()
        self.running = False
        self.price_history: Dict[str, deque] = {}  # 价格历史
        self.alert_cooldown: Dict[str, datetime] = {}  # 预警冷却
        self.callbacks: List[Callable[[Alert], None]] = []
        self._task: Optional[asyncio.Task] = None
    
    def add_callback(self, callback: Callable[[Alert], None]):
        """添加预警回调函数"""
        self.callbacks.append(callback)
    
    async def start(self, group_id: Optional[str] = None):
        """启动监控"""
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop(group_id))
        logger.info(f"监控已启动，分组: {group_id or '默认'}")
    
    async def stop(self):
        """停止监控"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("监控已停止")
    
    async def _monitor_loop(self, group_id: Optional[str]):
        """监控主循环"""
        while self.running:
            try:
                await self._check_once(group_id)
                await asyncio.sleep(self.config.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(5)
    
    async def _check_once(self, group_id: Optional[str]):
        """执行一次检查"""
        # 获取自选股列表
        stocks = self.api.get_watchlist(group_id)
        if not stocks:
            return
        
        codes = [s.full_code for s in stocks if s.full_code]
        quotes = self.api.get_batch_quotes(codes)
        
        for quote in quotes:
            await self._check_quote(quote)
    
    async def _check_quote(self, quote: StockQuote):
        """检查单只股票的异动"""
        code = quote.code
        now = datetime.now()
        
        # 初始化价格历史
        if code not in self.price_history:
            self.price_history[code] = deque(maxlen=100)
        
        self.price_history[code].append({
            "price": quote.price,
            "volume": quote.volume,
            "time": now
        })
        
        # 检查各类预警条件
        alerts = []
        
        # 1. 日内涨跌幅预警
        if abs(quote.change_pct) >= self.config.change_pct:
            level = "emergency" if abs(quote.change_pct) >= 7 else "warning"
            alerts.append(Alert(
                stock=Stock(code=quote.code, name=quote.name, market=""),
                alert_type="price_change",
                level=level,
                message=f"日内涨跌幅 {quote.change_pct:+.2f}%，超过阈值 {self.config.change_pct}%",
                current_price=quote.price,
                change_pct=quote.change_pct
            ))
        
        # 2. 快速变化预警（5分钟内）
        history = self.price_history[code]
        if len(history) >= 2:
            # 找到5分钟前的价格
            cutoff_time = now - timedelta(seconds=self.config.rapid_time_window)
            old_prices = [h for h in history if h["time"] <= cutoff_time]
            
            if old_prices:
                old_price = old_prices[-1]["price"]
                rapid_change = (quote.price - old_price) / old_price * 100
                
                if abs(rapid_change) >= self.config.rapid_change_pct:
                    level = "emergency" if abs(rapid_change) >= 3 else "warning"
                    alerts.append(Alert(
                        stock=Stock(code=quote.code, name=quote.name, market=""),
                        alert_type="rapid",
                        level=level,
                        message=f"{self.config.rapid_time_window//60}分钟内快速{'拉升' if rapid_change > 0 else '跳水'} {rapid_change:+.2f}%",
                        current_price=quote.price,
                        change_pct=quote.change_pct,
                        extra_data={"rapid_change": rapid_change}
                    ))
        
        # 3. 成交量异动（需要昨日成交量对比，简化实现）
        # TODO: 实现成交量对比
        
        # 触发预警（带冷却）
        for alert in alerts:
            await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: Alert):
        """触发预警（带冷却检查）"""
        code = alert.stock.code
        alert_key = f"{code}:{alert.alert_type}"
        now = datetime.now()
        
        # 检查冷却
        if alert_key in self.alert_cooldown:
            last_alert = self.alert_cooldown[alert_key]
            if (now - last_alert).seconds < self.config.cooldown_seconds:
                return  # 仍在冷却期
        
        # 更新冷却时间
        self.alert_cooldown[alert_key] = now
        
        # 执行回调
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"预警回调出错: {e}")
        
        logger.info(f"预警触发: {alert.stock.name} - {alert.message}")
    
    def get_summary(self, group_id: Optional[str] = None) -> Dict:
        """获取监控摘要"""
        stocks = self.api.get_watchlist(group_id)
        codes = [s.full_code for s in stocks if s.full_code]
        
        if not codes:
            return {"error": "自选股列表为空"}
        
        quotes = self.api.get_batch_quotes(codes)
        
        up_count = sum(1 for q in quotes if q.change_pct > 0)
        down_count = sum(1 for q in quotes if q.change_pct < 0)
        avg_change = sum(q.change_pct for q in quotes) / len(quotes) if quotes else 0
        
        return {
            "total": len(quotes),
            "up": up_count,
            "down": down_count,
            "avg_change_pct": round(avg_change, 2),
            "monitoring": self.running,
            "check_interval": self.config.check_interval
        }
