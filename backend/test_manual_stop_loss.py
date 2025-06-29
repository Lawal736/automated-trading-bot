#!/usr/bin/env python3
"""
Test script for manual trade EMA25 dynamic stop loss logic
This script will test the updated manual stop loss service with timeout handler.
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
from app.services.manual_stop_loss_service import ManualStopLossService
from app.core.logging import get_logger

logger = get_logger(__name__)

async def test_manual_stop_loss():
    """Test the manual stop loss service with EMA25 dynamic logic"""
    db = SessionLocal()
    
    try:
        print("🚀 Testing Manual Trade EMA25 Dynamic Stop Loss Logic...")
        
        # Get the manual stop loss service
        manual_service = ManualStopLossService(db)
        
        # Get manual trades with stop loss management
        managed_trades = manual_service.get_manual_trades_with_stop_loss_management()
        
        print(f"Found {len(managed_trades)} manual trades with stop loss management")
        
        if not managed_trades:
            print("No manual trades found for testing. Creating a test scenario...")
            
            # Create a test scenario by finding any manual trade
            test_trade = db.query(Trade).filter(
                Trade.bot_id.is_(None),  # Manual trade
                Trade.status == "filled"  # Successfully executed
            ).first()
            
            if test_trade:
                print(f"Using existing manual trade for testing: {test_trade.id} - {test_trade.symbol}")
                
                # Set up EMA25 trailing for this trade
                success = manual_service.setup_ema25_trailing_for_trade(test_trade.id, test_trade.user_id)
                if success:
                    print(f"✅ EMA25 trailing setup successful for trade {test_trade.id}")
                else:
                    print(f"❌ EMA25 trailing setup failed for trade {test_trade.id}")
                    return
            else:
                print("❌ No manual trades found for testing")
                return
        
        # Test the async update function
        print("\n🔄 Testing manual stop loss update with timeout handler...")
        
        results = await manual_service.update_manual_trade_stop_losses()
        
        print(f"\n📊 Manual Stop Loss Update Results:")
        print(f"   Total trades processed: {results['total_trades']}")
        print(f"   Trades updated: {results['updated_trades']}")
        print(f"   Errors: {results['errors']}")
        
        if results['details']:
            print(f"\n📋 Detailed Results:")
            for detail in results['details']:
                trade_id = detail.get('trade_id', 'N/A')
                symbol = detail.get('symbol', 'N/A')
                status = detail.get('status', 'N/A')
                
                if status == 'updated_with_exchange_order':
                    old_sl = detail.get('old_stop_loss', 'N/A')
                    new_sl = detail.get('new_stop_loss', 'N/A')
                    ema25 = detail.get('d1_ema25', 'N/A')
                    print(f"   ✅ Trade {trade_id} ({symbol}): {old_sl} → {new_sl} (D-1 EMA25: {ema25})")
                elif status == 'database_updated_exchange_failed':
                    old_sl = detail.get('old_stop_loss', 'N/A')
                    new_sl = detail.get('new_stop_loss', 'N/A')
                    print(f"   ⚠️  Trade {trade_id} ({symbol}): DB updated {old_sl} → {new_sl} but exchange order failed")
                elif status == 'unchanged':
                    current_sl = detail.get('current_stop_loss', 'N/A')
                    ema25 = detail.get('d1_ema25', 'N/A')
                    print(f"   ➡️  Trade {trade_id} ({symbol}): unchanged {current_sl} (D-1 EMA25: {ema25})")
                elif status == 'error':
                    error = detail.get('error', 'Unknown error')
                    print(f"   ❌ Trade {trade_id} ({symbol}): {error}")
        
        # Test individual trade stop loss placement
        if managed_trades:
            print(f"\n🧪 Testing individual stop loss placement for first trade...")
            first_trade_info = managed_trades[0]
            trade = db.query(Trade).filter(Trade.id == first_trade_info['trade_id']).first()
            
            if trade:
                # Test the exchange stop loss placement
                success = await manual_service._place_exchange_stop_loss_order(
                    trade, 
                    float(trade.stop_loss) * 0.95,  # Test with 95% of current stop loss
                    trade.user_id
                )
                
                if success:
                    print(f"✅ Individual stop loss placement test successful for trade {trade.id}")
                else:
                    print(f"❌ Individual stop loss placement test failed for trade {trade.id}")
        
        print("\n✅ Manual trade EMA25 dynamic stop loss test completed!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_manual_stop_loss()) 