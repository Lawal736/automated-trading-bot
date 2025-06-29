from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from datetime import datetime

from app.api import deps
from app.models.user import User
from app.models.exchange import ExchangeConnection as ExchangeConnectionModel
from app.schemas.exchanges import (
    ExchangeConnectionCreate,
    ExchangeConnectionRead,
    ExchangeConnectionUpdate,
)
from app.services import exchange_service
from app.core.logging import get_logger
from app.trading.exchanges.factory import ExchangeFactory
from app.trading.trading_service import TradingService
from app.core.cache import price_cache, cache_client
from app.schemas.bot import Bot, BotCreate, BotUpdate
from app.schemas.ticker import Ticker
from app.schemas.trade import TradeOrder, TradeResult
from app.services.exchange_service import ExchangeService
from app.core.config import settings
import asyncio
import aiohttp
import ccxt.async_support as ccxt

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=List[ExchangeConnectionRead])
async def get_exchanges(
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    return await exchange_service.get_user_exchanges(user_id=current_user.id)


@router.post("", response_model=ExchangeConnectionRead)
async def add_exchange_connection(
    conn_in: ExchangeConnectionCreate,
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    return await exchange_service.create_exchange_connection(
        user_id=current_user.id, conn_in=conn_in
    )


@router.delete("/{conn_id}")
async def delete_exchange_connection(
    conn_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    await exchange_service.delete_exchange_connection(
        user_id=current_user.id, conn_id=conn_id
    )
    return {"message": "Exchange connection deleted successfully"}


@router.put("/{conn_id}", response_model=ExchangeConnectionRead)
async def update_exchange_connection(
    conn_id: int,
    conn_in: ExchangeConnectionUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    """Update an exchange connection"""
    return await exchange_service.update_exchange_connection(
        user_id=current_user.id, conn_id=conn_id, conn_in=conn_in
    )


@router.get("/{exchange_name}/ticker", response_model=Ticker)
async def get_ticker(
    exchange_name: str,
    symbol: str,
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    """
    Get the current ticker price for a symbol on a given exchange.
    """
    # Convert symbol format for different exchanges
    if exchange_name.lower() == "binance":
        # Binance uses BTCUSDT format (no separators)
        ccxt_symbol = symbol.replace("-", "").replace("/", "")
    else:
        # Other exchanges use BTC/USDT format
        ccxt_symbol = symbol.replace("-", "/")
    
    ticker = await exchange_service.get_ticker(
        user_id=current_user.id, exchange_name=exchange_name, symbol=ccxt_symbol
    )
    if not ticker:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return ticker


@router.post("/{exchange_name}/trade", response_model=TradeResult)
async def execute_trade(
    exchange_name: str,
    trade_order: TradeOrder,
    current_user: User = Depends(deps.get_current_active_user),
    exchange_service: ExchangeService = Depends(deps.get_exchange_service),
):
    """
    Execute a manual trade on a given exchange.
    """
    try:
        trade_result = await exchange_service.execute_trade(
            user_id=current_user.id,
            exchange_name=exchange_name,
            trade_order=trade_order,
        )
        return trade_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binance/top-pairs", response_model=List[str])
async def get_binance_top_pairs(clear_cache: bool = False):
    """
    Return a static list of the top 25 USDT pairs as provided by the user.
    """
    top_25_pairs = [
        "SUI/USDT",
        "ETH/USDT",
        "BTC/USDT",
        "XRP/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "TRX/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "XLM/USDT",
        "BCH/USDT",
        "AVAX/USDT",
        "HBAR/USDT",
        "TON/USDT",
        "LTC/USDT",
        "AAVE/USDT",
        "UNI/USDT",
        "DOT/USDT",
        "ONDO/USDT",
        "TAO/USDT",
        "WLD/USDT",
        "APT/USDT",
        "ARB/USDT",
        "FET/USDT",
        "OP/USDT",
    ]
    return top_25_pairs