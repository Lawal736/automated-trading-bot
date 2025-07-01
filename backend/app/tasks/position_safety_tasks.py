import asyncio
from datetime import datetime
from celery import current_app as celery_app
import structlog

from app.services.position_safety_service import position_safety_service

logger = structlog.get_logger()


@celery_app.task(bind=True, name="position_safety_monitor")
def position_safety_monitor_task(self):
    """
    Comprehensive position safety monitor that runs every 15 minutes
    Handles:
    1. Stop loss retry attempts
    2. Force closure safety net
    3. Database session issue prevention
    """
    try:
        logger.info("🛡️ Starting position safety monitor...")
        
        # Run the safety monitoring
        results = asyncio.run(position_safety_service.scan_and_protect_positions())
        
        logger.info(
            "🛡️ Position safety monitor completed",
            retries_attempted=results["retries_attempted"],
            retries_successful=results["retries_successful"],
            force_closures=results["force_closures"],
            errors_count=len(results["errors"])
        )
        
        if results["errors"]:
            logger.error(
                "Position safety monitor encountered errors",
                errors=results["errors"]
            )
        
        return {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Critical error in position safety monitor: {e}")
        import traceback
        traceback.print_exc()
        
        # Retry the task
        raise self.retry(
            countdown=300,  # Retry in 5 minutes
            max_retries=3,
            exc=e
        )


@celery_app.task(bind=True, name="emergency_position_scan")
def emergency_position_scan_task(self):
    """
    Emergency position scan for immediate safety checks
    Can be triggered manually or automatically when issues are detected
    """
    try:
        logger.warning("🚨 EMERGENCY position safety scan initiated...")
        
        # Run emergency scan
        results = asyncio.run(position_safety_service.scan_and_protect_positions())
        
        # Log critical results
        if results["force_closures"] > 0:
            logger.critical(
                f"🚨 EMERGENCY: {results['force_closures']} positions force closed!",
                results=results
            )
        
        if results["retries_successful"] > 0:
            logger.warning(
                f"⚠️ EMERGENCY: {results['retries_successful']} stop losses created",
                results=results
            )
        
        return {
            "status": "emergency_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "results": results,
            "critical": results["force_closures"] > 0
        }
        
    except Exception as e:
        logger.critical(f"CRITICAL: Emergency position scan failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Don't retry emergency scans, log and alert
        return {
            "status": "emergency_failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@celery_app.task(name="check_unprotected_position")
def check_unprotected_position_task(trade_id: int):
    """
    Check a specific position for safety issues
    Used for immediate checking after trade creation failures
    """
    try:
        logger.info(f"🔍 Checking position safety for Trade ID: {trade_id}")
        
        from app.core.database import get_db
        from app.models.trading import Trade
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.error(f"Trade not found: {trade_id}")
                return {"status": "trade_not_found", "trade_id": trade_id}
            
            # Check if this position needs immediate attention
            age_hours = (datetime.utcnow() - trade.created_at.replace(tzinfo=None)).total_seconds() / 3600
            
            if trade.stop_loss_failed and age_hours > 0.25:  # 15 minutes
                logger.warning(f"Position needs immediate attention - Trade ID: {trade_id}, Age: {age_hours:.2f}h")
                
                # Trigger emergency scan
                emergency_position_scan_task.delay()
                
                return {
                    "status": "needs_attention",
                    "trade_id": trade_id,
                    "age_hours": age_hours,
                    "emergency_scan_triggered": True
                }
            
            return {
                "status": "position_ok",
                "trade_id": trade_id,
                "age_hours": age_hours
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking position safety for Trade ID {trade_id}: {e}")
        return {
            "status": "check_failed",
            "trade_id": trade_id,
            "error": str(e)
        } 