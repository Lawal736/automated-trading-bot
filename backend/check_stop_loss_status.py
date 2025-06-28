#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.trading import Trade
from sqlalchemy import and_
from datetime import datetime, timedelta

def check_stop_loss_status():
    db = SessionLocal()
    try:
        print("=== STOP LOSS STATUS CHECK ===\n")
        
        # Check for trades that need stop loss retry
        pending_stop_losses = db.query(Trade).filter(
            and_(
                Trade.trade_type == 'STOP_LOSS',
                Trade.status.in_(['pending', 'open']),
                Trade.stop_loss_failed == False
            )
        ).all()
        
        print(f'Pending stop losses: {len(pending_stop_losses)}')
        for trade in pending_stop_losses:
            print(f'  Trade ID: {trade.id}, Symbol: {trade.symbol}, Status: {trade.status}, Retry Count: {trade.stop_loss_retry_count}')
            if trade.stop_loss_last_attempt:
                print(f'    Last attempt: {trade.stop_loss_last_attempt}')
        
        # Check for failed stop losses
        failed_stop_losses = db.query(Trade).filter(
            and_(
                Trade.trade_type == 'STOP_LOSS',
                Trade.stop_loss_failed == True
            )
        ).all()
        
        print(f'\nFailed stop losses: {len(failed_stop_losses)}')
        for trade in failed_stop_losses:
            print(f'  Trade ID: {trade.id}, Symbol: {trade.symbol}, Status: {trade.status}, Retry Count: {trade.stop_loss_retry_count}')
            if trade.error_message:
                print(f'    Error: {trade.error_message[:100]}...')
        
        # Check for recent trades that might need stop loss
        recent_trades = db.query(Trade).filter(
            and_(
                Trade.trade_type == 'MARKET',
                Trade.status == 'filled',
                Trade.side == 'buy'
            )
        ).order_by(Trade.created_at.desc()).limit(10).all()
        
        print(f'\nRecent filled buy trades: {len(recent_trades)}')
        for trade in recent_trades:
            # Check if this trade has a corresponding stop loss
            stop_loss = db.query(Trade).filter(
                and_(
                    Trade.trade_type == 'STOP_LOSS',
                    Trade.symbol == trade.symbol,
                    Trade.user_id == trade.user_id,
                    Trade.created_at > trade.created_at
                )
            ).first()
            
            has_stop_loss = "✅" if stop_loss else "❌"
            print(f'  {has_stop_loss} Trade ID: {trade.id}, Symbol: {trade.symbol}, Executed Price: {trade.executed_price}, Created: {trade.created_at}')
            if stop_loss:
                print(f'    Stop Loss ID: {stop_loss.id}, Status: {stop_loss.status}')
        
        # Check for trades with retry attempts
        retry_trades = db.query(Trade).filter(
            and_(
                Trade.stop_loss_retry_count > 0
            )
        ).all()
        
        print(f'\nTrades with retry attempts: {len(retry_trades)}')
        for trade in retry_trades:
            print(f'  Trade ID: {trade.id}, Symbol: {trade.symbol}, Retry Count: {trade.stop_loss_retry_count}, Failed: {trade.stop_loss_failed}')
            if trade.stop_loss_last_attempt:
                print(f'    Last attempt: {trade.stop_loss_last_attempt}')
        
        # Check for trades created in last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_trades_24h = db.query(Trade).filter(
            Trade.created_at > yesterday
        ).all()
        
        print(f'\nTrades in last 24 hours: {len(recent_trades_24h)}')
        for trade in recent_trades_24h:
            print(f'  {trade.trade_type}: {trade.symbol}, Status: {trade.status}, Created: {trade.created_at}')
            
    finally:
        db.close()

if __name__ == "__main__":
    check_stop_loss_status() 