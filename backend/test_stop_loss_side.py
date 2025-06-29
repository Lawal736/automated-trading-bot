#!/usr/bin/env python3
"""
Test script to verify stop loss orders are created with correct side
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import SessionLocal
from app.models.trading import Trade
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.services.stop_loss_timeout_handler import create_stop_loss_safe
from app.services.activity_service import ActivityService
from app.trading.exchanges.factory import ExchangeFactory
from app.core.logging import get_logger

logger = get_logger(__name__)

async def test_stop_loss_side():
    """Test that stop loss orders are created with correct side"""
    db = SessionLocal()
    
    try:
        # Get a recent buy trade that doesn't have a stop loss
        recent_buy_trade = db.query(Trade).filter(
            Trade.side == "buy",
            Trade.status == "filled",
            Trade.trade_type.in_(["spot", "futures"]),
            Trade.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).order_by(Trade.created_at.desc()).first()
        
        if not recent_buy_trade:
            print("No recent buy trades found for testing")
            return
        
        print(f"Testing with trade ID: {recent_buy_trade.id}")
        print(f"Symbol: {recent_buy_trade.symbol}")
        print(f"Side: {recent_buy_trade.side}")
        print(f"Quantity: {recent_buy_trade.quantity}")
        print(f"Executed price: {recent_buy_trade.executed_price}")
        
        # Check if this trade already has a stop loss
        existing_stop_loss = db.query(Trade).filter(
            Trade.trade_type == "STOP_LOSS",
            Trade.symbol == recent_buy_trade.symbol,
            Trade.user_id == recent_buy_trade.user_id,
            Trade.created_at > recent_buy_trade.created_at
        ).first()
        
        if existing_stop_loss:
            print(f"Trade already has stop loss ID: {existing_stop_loss.id}")
            print(f"Stop loss side: {existing_stop_loss.side}")
            if existing_stop_loss.side == "sell":
                print("✅ Stop loss has correct side (sell)")
            else:
                print("❌ Stop loss has wrong side (should be sell)")
            return
        
        # Get exchange connection
        conn = db.query(ExchangeConnection).filter(
            ExchangeConnection.id == recent_buy_trade.exchange_connection_id
        ).first()
        
        if not conn:
            print("No exchange connection found")
            return
        
        # Get user
        user = db.query(User).filter(User.id == recent_buy_trade.user_id).first()
        if not user:
            print("User not found")
            return
        
        # Create activity service
        activity_service = ActivityService()
        
        # Create mock trade order
        class MockTradeOrder:
            def __init__(self, symbol, side, amount, stop_loss):
                self.symbol = symbol
                self.side = side
                self.amount = amount
                self.stop_loss = stop_loss
        
        # Calculate stop loss price (95% of executed price for testing)
        stop_loss_price = float(recent_buy_trade.executed_price) * 0.95
        
        trade_order = MockTradeOrder(
            symbol=recent_buy_trade.symbol,
            side="sell",  # Stop loss should be sell for buy trades
            amount=recent_buy_trade.quantity,
            stop_loss=stop_loss_price
        )
        
        print(f"Creating stop loss with side: {trade_order.side}")
        print(f"Stop loss price: {stop_loss_price}")
        
        # Create exchange instance
        exchange = ExchangeFactory.create_exchange(
            exchange_name=conn.exchange_name,
            api_key=conn.api_key,
            api_secret=conn.api_secret,
            is_testnet=conn.is_testnet
        )
        
        # Create stop loss using timeout handler
        stop_loss_order = await create_stop_loss_safe(
            trade_order,
            recent_buy_trade.user_id,
            conn,
            user,
            activity_service,
            exchange,
            db
        )
        
        if stop_loss_order:
            print("✅ Stop loss order created successfully")
            
            # Check the created trade record
            created_stop_loss = db.query(Trade).filter(
                Trade.trade_type == "STOP_LOSS",
                Trade.symbol == recent_buy_trade.symbol,
                Trade.user_id == recent_buy_trade.user_id,
                Trade.created_at > recent_buy_trade.created_at
            ).order_by(Trade.created_at.desc()).first()
            
            if created_stop_loss:
                print(f"Created stop loss trade ID: {created_stop_loss.id}")
                print(f"Stop loss side: {created_stop_loss.side}")
                print(f"Stop loss status: {created_stop_loss.status}")
                
                if created_stop_loss.side == "sell":
                    print("✅ Stop loss created with correct side (sell)")
                else:
                    print("❌ Stop loss created with wrong side (should be sell)")
            else:
                print("❌ No stop loss trade record found in database")
        else:
            print("❌ Stop loss order creation failed")
            
    except Exception as e:
        print(f"Error testing stop loss side: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_stop_loss_side()) 