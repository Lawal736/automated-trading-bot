from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date


class BacktestRequest(BaseModel):
    strategy_name: str
    strategy_params: Dict[str, Any]
    symbol: str
    exchange_connection_id: int
    timeframe: str
    start_date: date
    end_date: date
    initial_balance: float


class TradeResult(BaseModel):
    entry_date: date
    exit_date: date | None
    entry_price: float
    exit_price: float | None
    pnl: float
    pnl_percent: float
    side: str
    condition_met: Optional[bool] = None


class BacktestResult(BaseModel):
    total_return: float
    total_trades: int
    win_rate: float
    max_drawdown: float
    start_date: date
    end_date: date
    trades: List[TradeResult]
    indicator_data: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True 