from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum

class TradingCondition(str, Enum):
    BUY = "BUY"
    SHORT = "SHORT"
    HOLD = "HOLD"

class CassavaTrendDataBase(BaseModel):
    date: datetime
    symbol: str
    ema_10: float
    ema_8: float
    ema_20: float
    ema_15: float
    ema_25: float
    ema_5: float
    di_plus: float
    top_fractal: Optional[float] = None
    trading_condition: TradingCondition
    price: Optional[float] = None

class CassavaTrendDataCreate(CassavaTrendDataBase):
    pass

class CassavaTrendData(CassavaTrendDataBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CassavaTrendDataResponse(BaseModel):
    data: List[CassavaTrendData]
    total: int
    page: int
    size: int
    total_pages: int

class CassavaTrendDataFilter(BaseModel):
    symbol: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_condition: Optional[TradingCondition] = None
    page: int = 1
    size: int = 50 