#!/usr/bin/env python3
"""
Script to update existing positions with exchange order IDs from trades
"""

from app.core.database import get_db
from app.models.trading import Position, Trade

def update_position_order_ids():
    """Update existing positions with exchange order IDs from trades"""
    db = next(get_db())
    
    try:
        # Get all open positions
        positions = db.query(Position).filter(Position.is_open == True).all()
        print(f"Found {len(positions)} open positions")
        
        # Get all filled buy trades
        trades = db.query(Trade).filter(Trade.status == 'filled', Trade.side == 'buy').all()
        print(f"Found {len(trades)} filled buy trades")
        
        updated = 0
        
        for position in positions:
            # Find matching trade by symbol and user_id
            matching_trade = None
            for trade in trades:
                if (trade.symbol == position.symbol and 
                    trade.user_id == position.user_id and 
                    trade.exchange_order_id):
                    matching_trade = trade
                    break
            
            if matching_trade:
                position.exchange_order_id = matching_trade.exchange_order_id
                updated += 1
                print(f"Updated position {position.id} ({position.symbol}) with order ID {matching_trade.exchange_order_id}")
            else:
                print(f"No matching trade found for position {position.id} ({position.symbol})")
        
        db.commit()
        print(f"\nSuccessfully updated {updated} positions with exchange order IDs")
        
    except Exception as e:
        print(f"Error updating positions: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_position_order_ids() 