from pydantic import BaseModel
from datetime import date
from typing import List

class DailyPnl(BaseModel):
    day: date
    pnl: float

class StrategyPerformance(BaseModel):
    strategy_name: str
    total_pnl: float
    total_trades: int
    win_loss_ratio: float

class Report(BaseModel):
    daily_pnl_data: List[DailyPnl]
    total_pnl: float
    win_loss_ratio: float
    avg_profit: float
    avg_loss: float
    total_trades: int
    strategy_performance: List[StrategyPerformance]

    class Config:
        orm_mode = True 