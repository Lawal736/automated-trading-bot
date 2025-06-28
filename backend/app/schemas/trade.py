from pydantic import BaseModel, Field
from typing import Optional, Literal

class TradeOrder(BaseModel):
    symbol: str = Field(..., description="The symbol to trade, e.g., BTC/USDT")
    side: Literal["buy", "sell"] = Field(..., description="The order side")
    order_type: Literal["market", "limit"] = Field(..., description="The order type")
    trade_type: Literal["spot", "futures"] = Field(default="spot", description="The trade type")
    amount: float = Field(..., description="The amount to trade")
    price: Optional[float] = Field(None, description="The price for limit orders")
    stop_loss: Optional[float] = Field(None, description="Stop loss price for the order")

class TradeResult(BaseModel):
    id: str
    symbol: str
    price: float
    amount: float
    status: str 