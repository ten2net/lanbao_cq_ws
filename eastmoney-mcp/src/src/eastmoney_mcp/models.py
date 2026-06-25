"""
数据模型定义
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Stock(BaseModel):
    """股票信息"""
    code: str = Field(..., description="股票代码，如 600519")
    name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场类型: sh/sz/bj/hk/us")
    full_code: Optional[str] = Field(None, description="完整代码，如 sh600519")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "600519",
                "name": "贵州茅台",
                "market": "sh",
                "full_code": "sh600519"
            }
        }


class StockQuote(BaseModel):
    """股票行情"""
    code: str
    name: str
    price: float = Field(..., description="当前价格")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    prev_close: float = Field(..., description="昨收价")
    change: float = Field(..., description="涨跌额")
    change_pct: float = Field(..., description="涨跌幅%")
    volume: int = Field(..., description="成交量(手)")
    amount: float = Field(..., description="成交额(万元)")
    turnover: float = Field(..., description="换手率%")
    volume_ratio: Optional[float] = Field(None, description="量比")
    pe: Optional[float] = Field(None, description="市盈率")
    pb: Optional[float] = Field(None, description="市净率")
    market_cap: Optional[float] = Field(None, description="总市值(亿元)")
    circulating_cap: Optional[float] = Field(None, description="流通市值(亿元)")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "600519",
                "name": "贵州茅台",
                "price": 1588.00,
                "open": 1570.00,
                "high": 1595.00,
                "low": 1568.00,
                "prev_close": 1570.00,
                "change": 18.00,
                "change_pct": 1.15,
                "volume": 25000,
                "amount": 39700.00,
                "turnover": 0.20
            }
        }


class WatchlistGroup(BaseModel):
    """自选股分组"""
    id: str = Field(..., description="分组ID")
    name: str = Field(..., description="分组名称")
    count: int = Field(0, description="股票数量")
    stocks: List[Stock] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "1001",
                "name": "短线关注",
                "count": 5,
                "stocks": []
            }
        }


class Alert(BaseModel):
    """预警信息"""
    stock: Stock
    alert_type: str = Field(..., description="预警类型: price_change/volume/breakout/rapid")
    level: str = Field(..., description="级别: emergency/warning/info")
    message: str = Field(..., description="预警消息")
    current_price: float
    change_pct: float
    trigger_time: datetime = Field(default_factory=datetime.now)
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock": {"code": "300750", "name": "宁德时代", "market": "sz"},
                "alert_type": "rapid",
                "level": "emergency",
                "message": "5分钟内快速拉升 3.2%",
                "current_price": 208.50,
                "change_pct": 5.2
            }
        }


class AlertConfig(BaseModel):
    """预警配置"""
    change_pct: float = Field(5.0, description="日内涨跌幅阈值%")
    volume_surge: float = Field(2.0, description="成交量倍数阈值")
    rapid_change_pct: float = Field(2.0, description="快速变化阈值%(5分钟)")
    rapid_time_window: int = Field(300, description="快速变化时间窗口(秒)")
    check_interval: int = Field(5, description="检查间隔(秒)")
    cooldown_seconds: int = Field(1800, description="同类预警冷却时间(秒)")


class WatchlistSummary(BaseModel):
    """自选股概览"""
    total_stocks: int
    up_count: int
    down_count: int
    flat_count: int
    avg_change_pct: float
    top_gainer: Optional[StockQuote] = None
    top_loser: Optional[StockQuote] = None
    alerts_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
