#!/usr/bin/env python3
"""
Force test script for Cassava bot stop loss logic
This script will manually trigger a test trade to verify the stop loss creation works correctly.
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.trading.trading_service import trading_service
from app.trading.exchanges.base import OrderType, OrderSide
from app.services.stop_loss_timeout_handler import create_stop_loss_safe
from app.services.activity_service import activity_service
from app.schemas.activity import ActivityCreate
from app.core.logging import get_logger

logger = get_logger(__name__)

async def force_cassava_test():
    """Force test the Cassava bot stop loss logic"""
    db = SessionLocal()
    
    try:
        # Get the first active Cassava bot
        bot = db.query(Bot).filter(
            Bot.strategy_name == 'cassava_trend_following',
            Bot.is_active == True
        ).first()
        
        if not bot:
            print("No active Cassava bot found!")
            return
        
        print(f"Testing bot: {bot.name} (ID: {bot.id})")
        
        # Get the exchange connection
        connection = db.query(ExchangeConnection).filter(
            ExchangeConnection.id == bot.exchange_connection_id
        ).first()
        
        if not connection:
            print(f"Exchange connection {bot.exchange_connection_id} not found!")
            return
        
        print(f"Using exchange: {connection.exchange_name}")
        
        # Get the user
        user = db.query(User).filter(User.id == bot.user_id).first()
        if not user:
            print(f"User {bot.user_id} not found!")
            return
        
        # Add exchange connection to trading service
        success = await trading_service.add_exchange_connection(connection)
        if not success:
            print("Failed to add exchange connection to trading service!")
            return
        
        # Test with a small trade on BTC/USDT
        test_symbol = "BTC/USDT"
        test_amount = Decimal("0.001")  # Very small amount for testing
        
        print(f"Testing with symbol: {test_symbol}, amount: {test_amount}")
        
        # Get current price
        ticker = await trading_service.get_ticker(test_symbol, connection.exchange_name)
        if not ticker:
            print(f"Could not get ticker for {test_symbol}")
            return
        
        current_price = ticker.last_price
        print(f"Current price: {current_price}")
        
        # Create a mock trade order object
        class MockTradeOrder:
            def __init__(self, symbol, side, amount, stop_loss):
                self.symbol = symbol
                self.side = side
                self.amount = amount
                self.stop_loss = stop_loss
        
        # Calculate stop loss at D-1 EMA25 (for testing, use 95% of current price)
        stop_loss_price = current_price * Decimal("0.95")
        
        trade_order = MockTradeOrder(
            symbol=test_symbol,
            side="buy",
            amount=test_amount,
            stop_loss=stop_loss_price
        )
        
        print(f"Stop loss price: {stop_loss_price}")
        
        # Get exchange instance
        exchange = await trading_service.get_exchange(connection.exchange_name)
        if not exchange:
            print("Failed to get exchange instance!")
            return
        
        # Test the stop loss creation with timeout handler
        print("Testing stop loss creation with timeout handler...")
        
        stop_loss_order = await create_stop_loss_safe(
            trade_order, 
            bot.user_id, 
            connection, 
            user, 
            activity_service, 
            exchange, 
            db
        )
        
        if stop_loss_order:
            print("✅ SUCCESS: Stop loss order created successfully!")
            print(f"Stop loss order ID: {stop_loss_order.id}")
            print(f"Stop loss price: {stop_loss_order.price}")
            print(f"Stop loss status: {stop_loss_order.status}")
        else:
            print("❌ FAILED: Stop loss order creation failed!")
        
        # Clean up - close exchange connections
        await trading_service.close_all_connections()
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting Cassava bot stop loss test...")
    asyncio.run(force_cassava_test())
    print("✅ Test completed!") 