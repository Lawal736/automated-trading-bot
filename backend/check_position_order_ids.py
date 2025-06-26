#!/usr/bin/env python3
"""
Check position order IDs in the database
"""
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import SessionLocal
from app.models.trading import Position, Trade

def check_position_order_ids():
    """Check order IDs in positions and trades"""
    db = SessionLocal()
    try:
        target_order_id = "5918585316"
        found = False
        # Check positions
        positions = db.query(Position).filter(Position.exchange_order_id == target_order_id).all()
        if positions:
            print(f"Order ID {target_order_id} found in positions:")
            for pos in positions:
                print(f"  Position ID: {pos.id}, Symbol: {pos.symbol}, Is Open: {pos.is_open}, Quantity: {pos.quantity}, Updated: {pos.updated_at}")
            found = True
        else:
            print(f"Order ID {target_order_id} NOT found in positions.")
        # Check trades
        trades = db.query(Trade).filter(Trade.exchange_order_id == target_order_id).all()
        if trades:
            print(f"Order ID {target_order_id} found in trades:")
            for trade in trades:
                print(f"  Trade ID: {trade.id}, Symbol: {trade.symbol}, Type: {trade.trade_type}, Status: {trade.status}, Amount: {getattr(trade, 'amount', 'N/A')}, Price: {getattr(trade, 'price', 'N/A')}, Created: {getattr(trade, 'created_at', 'N/A')}")
            found = True
        else:
            print(f"Order ID {target_order_id} NOT found in trades.")
        if not found:
            print(f"Order ID {target_order_id} was not found in either positions or trades.")
    finally:
        db.close()

if __name__ == "__main__":
    check_position_order_ids() 