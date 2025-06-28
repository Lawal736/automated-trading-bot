#!/usr/bin/env python3
"""
Monitoring script for Cassava trend data automation
Checks record counts per symbol and overall status
"""

from app.core.database import SessionLocal
from app.services.cassava_data_service import CassavaDataService
from app.models.trading import CassavaTrendData
from datetime import datetime, timedelta
import sys

def check_cassava_data_status():
    """Check the status of Cassava trend data"""
    db = SessionLocal()
    try:
        cassava_service = CassavaDataService(db)
        
        # Get counts per symbol
        counts = cassava_service.get_records_count_per_symbol()
        
        print("=== Cassava Trend Data Status ===")
        print(f"Checked at: {datetime.utcnow()}")
        print()
        
        # Display counts
        print("Records per symbol:")
        print("-" * 40)
        
        total_records = 0
        symbols_with_issues = []
        
        for symbol, count in sorted(counts.items()):
            status = "✅" if count == 50 else "⚠️" if count > 0 else "❌"
            print(f"{status} {symbol}: {count} records")
            total_records += count
            
            if count != 50 and count > 0:
                symbols_with_issues.append((symbol, count))
        
        print("-" * 40)
        print(f"Total records: {total_records}")
        print(f"Expected total: {len(counts) * 50}")
        
        # Check date range
        from sqlalchemy import func
        date_range = db.query(
            func.min(CassavaTrendData.date),
            func.max(CassavaTrendData.date)
        ).first()
        
        if date_range[0] and date_range[1]:
            days_span = (date_range[1] - date_range[0]).days + 1
            print(f"Date range: {date_range[0].date()} to {date_range[1].date()} ({days_span} days)")
        
        # Summary
        print()
        if symbols_with_issues:
            print("⚠️  Issues found:")
            for symbol, count in symbols_with_issues:
                if count < 50:
                    print(f"   - {symbol}: Only {count} records (expected 50)")
                elif count > 50:
                    print(f"   - {symbol}: {count} records (expected 50) - needs cleanup")
        else:
            print("✅ All symbols have exactly 50 records")
        
        # Check if cleanup is needed
        needs_cleanup = any(count > 50 for count in counts.values())
        if needs_cleanup:
            print("\n🔄 Cleanup needed - run: docker-compose exec backend python -c 'from app.tasks.cassava_data_tasks import cleanup_old_cassava_data; cleanup_old_cassava_data()'")
        
        return len(symbols_with_issues) == 0
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = check_cassava_data_status()
    sys.exit(0 if success else 1) 