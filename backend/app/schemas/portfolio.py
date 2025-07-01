from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Portfolio(BaseModel):
    total_balance: float
    available_balance: float
    total_pnl: float
    daily_pnl: float
    active_positions: int
    total_trades: int
    
    # Enhanced P&L metrics
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    position_updates_count: Optional[int] = None
    last_update_timestamp: Optional[datetime] = None

    class Config:
        orm_mode = True 