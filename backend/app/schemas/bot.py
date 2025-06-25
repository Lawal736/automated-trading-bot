from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
import datetime

# --- Base Schemas ---
class BotBase(BaseModel):
    name: str
    strategy_name: str
    strategy_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    exchange_connection_id: int
    
    # Trading Configuration
    trading_pairs: str
    trade_type: str  # 'spot' or 'futures'
    direction: str   # 'long', 'short', or 'both'
    leverage: int = 1
    initial_balance: float
    
    # Risk Management & Limits
    max_trades_per_day: int = 10
    min_balance_threshold: float = 100.0
    max_daily_loss: float = 50.0
    max_position_size_percent: float = 10.0
    trade_interval_seconds: int = 60
    
    # Advanced Stop Loss Configuration
    stop_loss_type: str = "fixed_percentage"
    stop_loss_percentage: float = 5.0
    stop_loss_timeframe: str = "4h"
    stop_loss_ema_period: int = 7
    stop_loss_atr_period: int = 14
    stop_loss_atr_multiplier: float = 2.0
    stop_loss_support_lookback: int = 20

    # --- Validators to handle potential None values from the DB for old bots ---
    @field_validator(
        'trading_pairs', 'trade_type', 'direction', 'stop_loss_type', 'stop_loss_timeframe', 
        mode='before'
    )
    def default_str_for_none(cls, v: Optional[str], info) -> str:
        if v is None:
            # Provide a default based on the field name
            defaults = {
                'trading_pairs': '',
                'trade_type': 'spot',
                'direction': 'long',
                'stop_loss_type': 'fixed_percentage',
                'stop_loss_timeframe': '4h'
            }
            return defaults.get(info.field_name, '')
        return v

    @field_validator(
        'leverage', 'max_trades_per_day', 'trade_interval_seconds', 'stop_loss_ema_period', 
        'stop_loss_atr_period', 'stop_loss_support_lookback',
        mode='before'
    )
    def default_int_for_none(cls, v: Optional[int], info) -> int:
        if v is None:
            defaults = {
                'leverage': 1,
                'max_trades_per_day': 10,
                'trade_interval_seconds': 60,
                'stop_loss_ema_period': 7,
                'stop_loss_atr_period': 14,
                'stop_loss_support_lookback': 20
            }
            return defaults.get(info.field_name, 0)
        return v
    
    @field_validator(
        'initial_balance', 'min_balance_threshold', 'max_daily_loss', 'max_position_size_percent',
        'stop_loss_percentage', 'stop_loss_atr_multiplier',
        mode='before'
    )
    def default_float_for_none(cls, v: Optional[float], info) -> float:
        if v is None:
            defaults = {
                'initial_balance': 0.0,
                'min_balance_threshold': 100.0,
                'max_daily_loss': 50.0,
                'max_position_size_percent': 10.0,
                'stop_loss_percentage': 5.0,
                'stop_loss_atr_multiplier': 2.0
            }
            return defaults.get(info.field_name, 0.0)
        return v

# --- Schemas for Creating Data ---
class BotCreate(BotBase):
    pass

# --- Schemas for Updating Data ---
class BotUpdate(BaseModel):
    name: Optional[str] = None
    strategy_params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    exchange_connection_id: Optional[int] = None

    # Trading Configuration
    trading_pairs: Optional[str] = None
    trade_type: Optional[str] = None
    direction: Optional[str] = None
    leverage: Optional[int] = None
    
    # Risk Management & Limits
    max_trades_per_day: Optional[int] = None
    min_balance_threshold: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_position_size_percent: Optional[float] = None
    trade_interval_seconds: Optional[int] = None

    # Advanced Stop Loss Configuration
    stop_loss_type: Optional[str] = None
    stop_loss_percentage: Optional[float] = None
    stop_loss_timeframe: Optional[str] = None
    stop_loss_ema_period: Optional[int] = None
    stop_loss_atr_period: Optional[int] = None
    stop_loss_atr_multiplier: Optional[float] = None
    stop_loss_support_lookback: Optional[int] = None

# --- Schemas for Reading Data ---
class Bot(BotBase):
    id: int
    user_id: int
    current_balance: float
    is_active: bool
    celery_task_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True) 