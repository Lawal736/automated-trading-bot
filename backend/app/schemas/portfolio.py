from pydantic import BaseModel

class Portfolio(BaseModel):
    total_balance: float
    available_balance: float
    total_pnl: float
    daily_pnl: float
    active_positions: int
    total_trades: int

    class Config:
        orm_mode = True 