#!/usr/bin/env python3
"""
Script to print all trade IDs for XRP/USDT from Binance for debugging
"""

from app.core.database import get_db
from app.models.exchange import ExchangeConnection
from app.trading.trading_service import trading_service
import asyncio

async def print_trade_ids():
    db = next(get_db())
    try:
        connection = db.query(ExchangeConnection).first()
        if not connection:
            print("No exchange connection found in database")
            return
        print(f"Found exchange connection: {connection.exchange_name} (ID: {connection.id})")
        success = await trading_service.add_exchange_connection(connection)
        if not success:
            print(f"Failed to add exchange connection {connection.exchange_name}")
            return
        exchange = await trading_service.get_exchange_by_connection_id(connection.id)
        if not exchange:
            print("Could not get exchange instance from trading service")
            return
        trades = await exchange.client.fetch_my_trades('XRP/USDT')
        print(f"Fetched {len(trades)} trades for XRP/USDT")
        for t in trades:
            print(f"Trade: order={t['order']}, id={t['id']}, side={t['side']}, amount={t['amount']}, price={t['price']}, timestamp={t['timestamp']}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(print_trade_ids()) 