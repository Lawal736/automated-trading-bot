#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.trading import Trade
from sqlalchemy import and_

def fix_rejected_stop_losses():
    db = SessionLocal()
    try:
        print("=== FIXING REJECTED STOP LOSSES ===\n")
        
        # Find rejected stop losses without retry tracking
        rejected_stop_losses = db.query(Trade).filter(
            and_(
                Trade.trade_type == 'STOP_LOSS',
                Trade.status == 'rejected',
                Trade.stop_loss_retry_count.is_(None)
            )
        ).all()
        
        print(f'Found {len(rejected_stop_losses)} rejected stop losses without retry tracking')
        
        for trade in rejected_stop_losses:
            print(f'Fixing trade ID: {trade.id}, Symbol: {trade.symbol}')
            
            # Set retry tracking fields
            trade.stop_loss_retry_count = 0
            trade.stop_loss_failed = False
            trade.stop_loss_last_attempt = None
            
            # If it has an error message, keep it for debugging
            if not trade.error_message:
                trade.error_message = "Previously rejected stop loss - retry mechanism will attempt to place again"
        
        db.commit()
        print(f'Fixed {len(rejected_stop_losses)} rejected stop losses')
        
        # Now check if any should be retried
        pending_retries = db.query(Trade).filter(
            and_(
                Trade.trade_type == 'STOP_LOSS',
                Trade.status == 'rejected',
                Trade.stop_loss_failed == False,
                Trade.stop_loss_retry_count < 5
            )
        ).all()
        
        print(f'\nFound {len(pending_retries)} stop losses that can be retried')
        for trade in pending_retries:
            print(f'  Trade ID: {trade.id}, Symbol: {trade.symbol}, Retry Count: {trade.stop_loss_retry_count}')
            
    finally:
        db.close()

if __name__ == "__main__":
    fix_rejected_stop_losses() 