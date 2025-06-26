#!/usr/bin/env python3
"""
Script to create missing position records for executed trades
"""
import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import SessionLocal
from app.models.trading import Position, Trade, OrderStatus

def fix_missing_positions():
    """Create missing position records for executed trades"""
    db = SessionLocal()
    try:
        # Get all filled buy trades that should have positions
        filled_buy_trades = db.query(Trade).filter(
            Trade.status == OrderStatus.FILLED.value,
            Trade.side == 'buy',
            Trade.trade_type == 'spot'
        ).all()
        
        print(f"Found {len(filled_buy_trades)} filled buy trades")
        
        created_positions = 0
        skipped_positions = 0
        
        for trade in filled_buy_trades:
            # Check if position already exists for this trade
            existing_position = db.query(Position).filter(
                Position.exchange_order_id == trade.exchange_order_id,
                Position.symbol == trade.symbol,
                Position.user_id == trade.user_id
            ).first()
            
            if existing_position:
                print(f"Position already exists for trade {trade.id} (order ID: {trade.exchange_order_id}) - skipping")
                skipped_positions += 1
                continue
            
            # Check if position exists by symbol and user (without order ID)
            existing_position_by_symbol = db.query(Position).filter(
                Position.symbol == trade.symbol,
                Position.user_id == trade.user_id,
                Position.is_open == True
            ).first()
            
            if existing_position_by_symbol:
                print(f"Open position already exists for {trade.symbol} (user {trade.user_id}) - updating order ID")
                existing_position_by_symbol.exchange_order_id = trade.exchange_order_id
                existing_position_by_symbol.updated_at = datetime.utcnow()
                created_positions += 1
                continue
            
            # Create new position record
            try:
                position = Position(
                    user_id=trade.user_id,
                    bot_id=trade.bot_id,
                    exchange_connection_id=trade.exchange_connection_id,
                    symbol=trade.symbol,
                    trade_type=trade.trade_type,
                    side=trade.side,
                    quantity=trade.quantity,
                    entry_price=trade.executed_price or trade.price,
                    current_price=trade.executed_price or trade.price,
                    leverage=1,  # Spot trading has leverage of 1
                    exchange_order_id=trade.exchange_order_id,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    total_pnl=0.0,
                    is_open=True,
                    opened_at=trade.executed_at or trade.created_at
                )
                
                db.add(position)
                db.commit()
                print(f"✅ Created position {position.id} for trade {trade.id} ({trade.symbol}) - order ID: {trade.exchange_order_id}")
                created_positions += 1
                
            except Exception as e:
                print(f"❌ Failed to create position for trade {trade.id}: {e}")
                db.rollback()
                continue
        
        print(f"\n=== SUMMARY ===")
        print(f"Total filled buy trades: {len(filled_buy_trades)}")
        print(f"Positions created: {created_positions}")
        print(f"Positions skipped (already exist): {skipped_positions}")
        
        # Verify results
        total_positions = db.query(Position).filter(Position.is_open == True).count()
        print(f"Total open positions after fix: {total_positions}")
        
    except Exception as e:
        print(f"Error fixing missing positions: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Fixing missing position records...")
    fix_missing_positions() 