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

class TradeStats(BaseModel):
    total_trades: int
    filled_trades: int
    rejected_trades: int
    pending_trades: int
    buy_trades: int
    sell_trades: int
    spot_trades: int
    futures_trades: int
    manual_trades: int
    bot_trades: int
    success_rate: float
    total_volume: float

class Report(BaseModel):
    daily_pnl_data: List[DailyPnl]
    total_pnl: float
    win_loss_ratio: float
    avg_profit: float
    avg_loss: float
    total_trades: int
    strategy_performance: List[StrategyPerformance]
    trade_stats: TradeStats

    class Config:
        orm_mode = True 