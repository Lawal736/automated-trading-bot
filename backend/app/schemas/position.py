from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Position(BaseModel):
    id: int
    user_id: int
    bot_id: Optional[int]
    strategy_id: Optional[int]
    exchange_connection_id: int
    symbol: str
    trade_type: str  # spot, futures
    side: str  # buy, sell
    quantity: float
    entry_price: float
    current_price: Optional[float]
    leverage: int = 1
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    stop_loss: Optional[float]
    take_profit: Optional[float]
    liquidation_price: Optional[float]
    is_open: bool = True
    opened_at: datetime
    closed_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True 