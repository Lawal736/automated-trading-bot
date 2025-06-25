from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class Ticker(BaseModel):
    symbol: str
    last_price: Decimal
    timestamp: datetime

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True 