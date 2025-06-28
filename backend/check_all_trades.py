#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.trading import Trade
from sqlalchemy import and_, desc
from datetime import datetime, timedelta

def check_all_trades():
    db = SessionLocal()
    try:
        print("=== COMPREHENSIVE TRADE ANALYSIS ===\n")
        
        # Get all trades from the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        all_recent_trades = db.query(Trade).filter(
            Trade.created_at > yesterday
        ).order_by(desc(Trade.created_at)).all()
        
        print(f'All trades in last 24 hours: {len(all_recent_trades)}')
        for trade in all_recent_trades:
            print(f'  ID: {trade.id}, Type: {trade.trade_type}, Symbol: {trade.symbol}, Side: {trade.side}, Status: {trade.status}')
            print(f'    Price: {trade.price}, Executed: {trade.executed_price}, Quantity: {trade.quantity}')
            print(f'    Created: {trade.created_at}')
            if trade.exchange_order_id:
                print(f'    Exchange Order ID: {trade.exchange_order_id}')
            if trade.error_message:
                print(f'    Error: {trade.error_message[:100]}...')
            print()
        
        # Check for different trade types
        trade_types = db.query(Trade.trade_type).distinct().all()
        print(f'Available trade types: {[t[0] for t in trade_types]}')
        
        # Check for buy trades that should have stop losses
        buy_trades = db.query(Trade).filter(
            and_(
                Trade.side == 'buy',
                Trade.status == 'filled'
            )
        ).order_by(desc(Trade.created_at)).limit(10).all()
        
        print(f'\nRecent buy trades: {len(buy_trades)}')
        for trade in buy_trades:
            # Look for corresponding stop loss
            stop_loss = db.query(Trade).filter(
                and_(
                    Trade.trade_type == 'STOP_LOSS',
                    Trade.symbol == trade.symbol,
                    Trade.user_id == trade.user_id,
                    Trade.created_at > trade.created_at
                )
            ).first()
            
            has_stop_loss = "✅" if stop_loss else "❌"
            print(f'  {has_stop_loss} {trade.trade_type}: {trade.symbol}, Price: {trade.executed_price}, Created: {trade.created_at}')
            if stop_loss:
                print(f'    Stop Loss: ID {stop_loss.id}, Status: {stop_loss.status}')
        
        # Check for any stop loss trades
        stop_loss_trades = db.query(Trade).filter(
            Trade.trade_type == 'STOP_LOSS'
        ).order_by(desc(Trade.created_at)).all()
        
        print(f'\nAll stop loss trades: {len(stop_loss_trades)}')
        for trade in stop_loss_trades:
            print(f'  ID: {trade.id}, Symbol: {trade.symbol}, Status: {trade.status}, Retry Count: {trade.stop_loss_retry_count}')
            print(f'    Failed: {trade.stop_loss_failed}, Last Attempt: {trade.stop_loss_last_attempt}')
            if trade.error_message:
                print(f'    Error: {trade.error_message[:100]}...')
            print()
            
    finally:
        db.close()

if __name__ == "__main__":
    check_all_trades() 