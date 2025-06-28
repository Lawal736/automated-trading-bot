from celery import shared_task
from app.core.database import SessionLocal
from app.services.cassava_data_service import CassavaDataService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task(name="tasks.update_cassava_trend_data")
def update_cassava_trend_data():
    """Daily task to update Cassava trend data for all trading pairs"""
    db = SessionLocal()
    try:
        logger.info("Starting daily Cassava trend data update")
        
        # Get yesterday's date (UTC+0) for daily candle close
        yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        cassava_service = CassavaDataService(db)
        
        # Update data for yesterday
        cassava_service.update_daily_data(yesterday)
        
        # Clean up old data (keep only 50 days)
        cassava_service.cleanup_old_data()
        
        logger.info("Daily Cassava trend data update completed successfully")
        
    except Exception as e:
        logger.error(f"Error in daily Cassava trend data update: {e}")
    finally:
        db.close()

@shared_task(name="tasks.backfill_cassava_trend_data")
def backfill_cassava_trend_data(start_date: str = None, end_date: str = None):
    """Backfill Cassava trend data for a date range"""
    db = SessionLocal()
    try:
        logger.info("Starting Cassava trend data backfill")
        
        # Parse dates
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(days=50)
            
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_dt = datetime.utcnow() - timedelta(days=1)
        
        cassava_service = CassavaDataService(db)
        
        # Update data for each day in the range
        current_date = start_dt
        while current_date <= end_dt:
            logger.info(f"Backfilling data for {current_date.date()}")
            cassava_service.update_daily_data(current_date)
            current_date += timedelta(days=1)
        
        logger.info("Cassava trend data backfill completed successfully")
        
    except Exception as e:
        logger.error(f"Error in Cassava trend data backfill: {e}")
    finally:
        db.close()

@shared_task(name="tasks.cleanup_old_cassava_data")
def cleanup_old_cassava_data():
    """Clean up Cassava trend data older than 50 days"""
    db = SessionLocal()
    try:
        logger.info("Starting cleanup of old Cassava trend data")
        
        cassava_service = CassavaDataService(db)
        cassava_service.cleanup_old_data()
        
        logger.info("Cleanup of old Cassava trend data completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup of old Cassava trend data: {e}")
    finally:
        db.close() 