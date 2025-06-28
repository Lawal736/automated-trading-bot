import os
import sys
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.services.cassava_data_service import CassavaDataService

def main():
    session = SessionLocal()
    cassava_service = CassavaDataService(session)
    
    # Get yesterday's date (no data for today)
    yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    # Backfill from 50 days ago up to yesterday
    for i in range(50, 0, -1):  # 50 days ago to yesterday
        date = yesterday - timedelta(days=i-1)
        print(f"Backfilling Cassava data for {date.date()}...")
        cassava_service.update_daily_data(date)
    
    # Remove data older than 50 days (FIFO)
    cassava_service.cleanup_old_data()
    session.close()
    print("Backfill complete.")

if __name__ == "__main__":
    main() 