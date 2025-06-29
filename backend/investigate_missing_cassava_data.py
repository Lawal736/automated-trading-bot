#!/usr/bin/env python3
"""
Investigate missing Cassava data for June 28, 2025
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import func, and_

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import get_db
from app.models.trading import CassavaTrendData
from app.services.cassava_data_service import CassavaDataService

def investigate_missing_data():
    """Investigate the missing June 28, 2025 data"""
    print("🔍 Investigating Missing Cassava Data for June 28, 2025")
    print("=" * 60)
    
    db = next(get_db())
    try:
        # Check what dates we actually have
        print("📅 Checking actual dates in database...")
        
        # Get all unique dates
        dates = db.query(CassavaTrendData.date).distinct().order_by(CassavaTrendData.date).all()
        actual_dates = [d[0].date() for d in dates]
        
        print(f"Found {len(actual_dates)} unique dates:")
        for date in actual_dates:
            print(f"  - {date}")
        
        # Check for June 28, 2025 specifically
        target_date = datetime(2025, 6, 28).date()
        print(f"\n🎯 Looking for {target_date}...")
        
        if target_date in actual_dates:
            print(f"✅ {target_date} EXISTS in database")
            
            # Count records for this date
            count = db.query(CassavaTrendData).filter(
                func.date(CassavaTrendData.date) == target_date
            ).count()
            print(f"   Records for {target_date}: {count}")
            
            # Show sample records
            records = db.query(CassavaTrendData).filter(
                func.date(CassavaTrendData.date) == target_date
            ).limit(5).all()
            
            print("   Sample records:")
            for record in records:
                print(f"     {record.symbol}: {record.trading_condition} (EMA25: {record.ema_25})")
        else:
            print(f"❌ {target_date} is MISSING from database")
        
        # Check what the expected date range should be
        print(f"\n📊 Expected date range analysis:")
        
        # Get the date range we have
        min_date = db.query(func.min(CassavaTrendData.date)).scalar()
        max_date = db.query(func.max(CassavaTrendData.date)).scalar()
        
        if min_date and max_date:
            print(f"   Current range: {min_date.date()} to {max_date.date()}")
            days_span = (max_date - min_date).days + 1
            print(f"   Days span: {days_span}")
            
            # Calculate what the range should be for 50 days
            today = datetime.utcnow().date()
            expected_start = today - timedelta(days=49)  # 50 days including today
            print(f"   Expected range for 50 days: {expected_start} to {today}")
            
            # Check if June 28 should be in the expected range
            if expected_start <= target_date <= today:
                print(f"   ✅ {target_date} should be in the expected range")
            else:
                print(f"   ❌ {target_date} is outside the expected range")
        
        # Check per symbol for June 28
        print(f"\n🔍 Checking per symbol for {target_date}:")
        
        cassava_service = CassavaDataService(db)
        trading_pairs = cassava_service.get_trading_pairs()
        
        missing_symbols = []
        present_symbols = []
        
        for symbol in trading_pairs:
            record = db.query(CassavaTrendData).filter(
                and_(
                    CassavaTrendData.symbol == symbol,
                    func.date(CassavaTrendData.date) == target_date
                )
            ).first()
            
            if record:
                present_symbols.append(symbol)
                print(f"   ✅ {symbol}: {record.trading_condition}")
            else:
                missing_symbols.append(symbol)
                print(f"   ❌ {symbol}: MISSING")
        
        print(f"\n📈 Summary:")
        print(f"   Present: {len(present_symbols)} symbols")
        print(f"   Missing: {len(missing_symbols)} symbols")
        
        if missing_symbols:
            print(f"   Missing symbols: {', '.join(missing_symbols)}")
        
        # Check if the daily task ran
        print(f"\n🤖 Checking if daily task should have run:")
        
        # The task runs at 00:05 UTC daily
        # For June 28 data, it should have run on June 29 at 00:05 UTC
        task_run_date = datetime(2025, 6, 29, 0, 5, 0)  # June 29, 00:05 UTC
        print(f"   Task should have run: {task_run_date}")
        
        # Check if we have any data after June 28
        later_data = db.query(CassavaTrendData).filter(
            CassavaTrendData.date > datetime(2025, 6, 28, 23, 59, 59)
        ).first()
        
        if later_data:
            print(f"   ✅ Found data after June 28: {later_data.date}")
        else:
            print(f"   ❌ No data found after June 28")
        
        # Check the most recent data
        latest_data = db.query(CassavaTrendData).order_by(CassavaTrendData.date.desc()).first()
        if latest_data:
            print(f"   Latest data: {latest_data.date} ({latest_data.symbol})")
        
        print(f"\n💡 Investigation complete!")
        
    except Exception as e:
        print(f"❌ Error during investigation: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    investigate_missing_data() 