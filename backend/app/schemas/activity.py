from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime

class ActivityBase(BaseModel):
    type: str
    description: str
    amount: Optional[float] = None

class ActivityCreate(ActivityBase):
    pass

class Activity(ActivityBase):
    id: int
    user_id: int
    timestamp: datetime.datetime
    pnl: Optional[float] = None
    bot_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True) 