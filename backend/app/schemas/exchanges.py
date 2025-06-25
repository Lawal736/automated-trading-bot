from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, Field
from decimal import Decimal
from datetime import datetime
from pydantic import ConfigDict

from app.trading.exchanges.base import OrderType, OrderSide, TradeType


# --- Base Schemas ---
class ExchangeConnectionBase(BaseModel):
    exchange_name: str = Field(..., description="Name of the exchange (e.g., 'binance')")
    api_key: str
    api_secret: str


# --- Schemas for Creating Data ---
class ExchangeConnectionCreate(ExchangeConnectionBase):
    """Schema for creating an exchange connection"""
    password: Optional[str] = None
    is_testnet: bool = False
    can_trade: bool = True
    can_withdraw: bool = False
    can_read: bool = True


class ExchangeConnectionUpdate(ExchangeConnectionCreate):
    pass


# --- Schemas for Reading Data ---
class ExchangeConnectionRead(BaseModel):
    id: int
    exchange_name: str
    api_key: str
    is_testnet: bool
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExchangeConnectionResponse(BaseModel):
    """Schema for exchange connection response"""
    id: int
    exchange_name: str
    is_active: bool
    is_testnet: bool
    can_trade: bool
    can_withdraw: bool
    can_read: bool
    connection_status: str
    last_verified: Optional[datetime] = None
    created_at: datetime


class TickerResponse(BaseModel):
    """Schema for ticker response"""
    symbol: str
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    timestamp: Optional[str] = None


class OrderBookEntry(BaseModel):
    """Schema for order book entry"""
    price: float
    amount: float


class OrderBookResponse(BaseModel):
    """Schema for order book response"""
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    timestamp: Optional[str] = None


class BalanceResponse(BaseModel):
    """Schema for balance response"""
    currency: str
    free: float
    used: float
    total: float


class OrderCreate(BaseModel):
    """Schema for creating an order"""
    connection_id: int
    symbol: str
    order_type: OrderType
    side: OrderSide
    amount: float
    price: Optional[float] = None
    trade_type: TradeType = TradeType.SPOT
    extra_params: Dict[str, Any] = {}

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return v


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: str
    symbol: str
    side: str
    order_type: str
    amount: float
    price: Optional[float] = None
    filled_amount: float
    remaining_amount: float
    status: str
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    timestamp: Optional[str] = None


class TradeResponse(BaseModel):
    """Schema for trade response"""
    id: str
    symbol: str
    side: str
    amount: float
    price: float
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    timestamp: Optional[str] = None


class PositionResponse(BaseModel):
    """Schema for position response"""
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    leverage: Optional[int] = None
    liquidation_price: Optional[float] = None


class ExchangeInfoResponse(BaseModel):
    """Schema for exchange information response"""
    name: str
    timezone: Optional[str] = None
    server_time: Optional[int] = None
    rate_limits: Optional[List[Dict[str, Any]]] = None
    symbols_count: Optional[int] = None
    status: Optional[str] = None


class Ticker(BaseModel):
    symbol: str
    last_price: Optional[Decimal] = Field(None, alias="last")
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None

    class Config:
        from_attributes = True
        populate_by_name = True 