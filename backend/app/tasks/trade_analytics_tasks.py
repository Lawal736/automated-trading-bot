"""
Trade Analytics Celery Tasks
Automated trade analytics processing and monitoring
"""

from celery import Celery
from app.core.celery import celery_app
from app.core.database import SessionLocal
from app.services.trade_analytics_service import TradeAnalyticsService
from app.models.user import User
from app.core.logging import get_logger
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any
import traceback

logger = get_logger(__name__)

@celery_app.task(bind=True, name="trade_analytics.update_real_time_metrics")
def update_real_time_metrics(self) -> Dict[str, Any]:
    """
    Update real-time trade metrics for all active users
    Runs every 2 minutes to maintain fresh analytics
    """
    
    task_id = self.request.id
    logger.info(f"🔄 Starting real-time metrics update - Task ID: {task_id}")
    
    db = SessionLocal()
    result = {
        "task_id": task_id,
        "status": "started",
        "users_processed": 0,
        "errors": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # Get all active users
        active_users = db.query(User).filter(User.is_active == True).all()
        
        analytics_service = TradeAnalyticsService(db)
        processed_count = 0
        
        for user in active_users:
            try:
                # Update real-time metrics for each user
                metrics = analytics_service.get_real_time_trade_metrics(user.id)
                
                if "error" not in metrics:
                    processed_count += 1
                    logger.debug(f"✅ Updated metrics for user {user.id}")
                else:
                    result["errors"].append(f"User {user.id}: {metrics['error']}")
                    
            except Exception as e:
                error_msg = f"User {user.id}: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(f"❌ Error processing user {user.id}: {e}")
        
        result.update({
            "status": "completed",
            "users_processed": processed_count,
            "total_users": len(active_users),
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Real-time metrics update completed - {processed_count}/{len(active_users)} users processed")
        return result
        
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        result.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.error(f"❌ Real-time metrics update failed: {e}\n{traceback.format_exc()}")
        return result
        
    finally:
        db.close()

@celery_app.task(bind=True, name="trade_analytics.generate_daily_reports")
def generate_daily_reports(self) -> Dict[str, Any]:
    """
    Generate daily trade analytics reports for all users
    Runs daily at 01:00 UTC
    """
    
    task_id = self.request.id
    logger.info(f"📊 Starting daily reports generation - Task ID: {task_id}")
    
    db = SessionLocal()
    result = {
        "task_id": task_id,
        "status": "started",
        "reports_generated": 0,
        "errors": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # Get all active users
        active_users = db.query(User).filter(User.is_active == True).all()
        
        analytics_service = TradeAnalyticsService(db)
        reports_generated = 0
        
        for user in active_users:
            try:
                # Generate comprehensive daily report
                daily_report = analytics_service.get_enhanced_trade_counts(user.id, 1)  # Last 24 hours
                
                if "error" not in daily_report:
                    reports_generated += 1
                    logger.debug(f"✅ Generated daily report for user {user.id}")
                    
                    # Log significant activity if any
                    if daily_report["summary"]["total_trades"] > 0:
                        logger.info(f"📈 User {user.id} daily activity: {daily_report['summary']['total_trades']} trades, "
                                  f"{daily_report['summary']['success_rate']:.1%} success rate")
                else:
                    result["errors"].append(f"User {user.id}: {daily_report['error']}")
                    
            except Exception as e:
                error_msg = f"User {user.id}: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(f"❌ Error generating report for user {user.id}: {e}")
        
        result.update({
            "status": "completed",
            "reports_generated": reports_generated,
            "total_users": len(active_users),
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Daily reports generation completed - {reports_generated}/{len(active_users)} reports generated")
        return result
        
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        result.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.error(f"❌ Daily reports generation failed: {e}\n{traceback.format_exc()}")
        return result
        
    finally:
        db.close()

@celery_app.task(bind=True, name="trade_analytics.activity_monitor")
def activity_monitor(self) -> Dict[str, Any]:
    """
    Monitor trading activity and send alerts for unusual patterns
    Runs every 15 minutes
    """
    
    task_id = self.request.id
    logger.info(f"🔍 Starting activity monitoring - Task ID: {task_id}")
    
    db = SessionLocal()
    result = {
        "task_id": task_id,
        "status": "started",
        "users_monitored": 0,
        "alerts_triggered": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # Get all active users
        active_users = db.query(User).filter(User.is_active == True).all()
        
        analytics_service = TradeAnalyticsService(db)
        monitored_count = 0
        
        for user in active_users:
            try:
                # Get real-time metrics
                metrics = analytics_service.get_real_time_trade_metrics(user.id)
                
                if "error" not in metrics:
                    monitored_count += 1
                    
                    # Check for unusual activity patterns
                    real_time_data = metrics["real_time_counts"]
                    
                    # Alert on high failure rate
                    recent_failures = real_time_data.get("recent_failures", 0)
                    trades_last_hour = real_time_data.get("trades_last_hour", 0)
                    
                    if trades_last_hour > 0 and recent_failures / trades_last_hour > 0.5:
                        alert = {
                            "user_id": user.id,
                            "type": "high_failure_rate",
                            "message": f"High failure rate: {recent_failures}/{trades_last_hour} trades failed in last hour",
                            "severity": "warning"
                        }
                        result["alerts_triggered"].append(alert)
                        logger.warning(f"⚠️ High failure rate for user {user.id}: {recent_failures}/{trades_last_hour}")
                    
                    # Alert on very high activity
                    if real_time_data.get("trades_last_5min", 0) > 10:
                        alert = {
                            "user_id": user.id,
                            "type": "very_high_activity",
                            "message": f"Very high activity: {real_time_data['trades_last_5min']} trades in last 5 minutes",
                            "severity": "info"
                        }
                        result["alerts_triggered"].append(alert)
                        logger.info(f"🚀 Very high activity for user {user.id}")
                    
                    # Alert on no activity for active users with open positions
                    if (real_time_data.get("trades_last_24h", 0) == 0 and 
                        real_time_data.get("active_positions", 0) > 0):
                        alert = {
                            "user_id": user.id,
                            "type": "inactive_with_positions",
                            "message": f"No trades in 24h but has {real_time_data['active_positions']} open positions",
                            "severity": "info"
                        }
                        result["alerts_triggered"].append(alert)
                        logger.info(f"🔒 Inactive user with positions: {user.id}")
                        
            except Exception as e:
                logger.error(f"❌ Error monitoring user {user.id}: {e}")
        
        result.update({
            "status": "completed",
            "users_monitored": monitored_count,
            "total_users": len(active_users),
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ Activity monitoring completed - {monitored_count}/{len(active_users)} users monitored, "
                   f"{len(result['alerts_triggered'])} alerts triggered")
        return result
        
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        result.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.error(f"❌ Activity monitoring failed: {e}\n{traceback.format_exc()}")
        return result
        
    finally:
        db.close()

@celery_app.task(bind=True, name="trade_analytics.system_health_check")
def system_health_check(self) -> Dict[str, Any]:
    """
    Perform comprehensive system health check for trade analytics
    Runs every hour
    """
    
    task_id = self.request.id
    logger.info(f"🏥 Starting system health check - Task ID: {task_id}")
    
    db = SessionLocal()
    result = {
        "task_id": task_id,
        "status": "started",
        "health_checks": {},
        "issues_found": [],
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        analytics_service = TradeAnalyticsService(db)
        
        # Check database connectivity
        try:
            db.execute("SELECT 1")
            result["health_checks"]["database"] = "healthy"
        except Exception as e:
            result["health_checks"]["database"] = "unhealthy"
            result["issues_found"].append(f"Database connectivity issue: {str(e)}")
        
        # Check analytics service functionality
        try:
            test_metrics = analytics_service.get_real_time_trade_metrics(None)
            if "error" not in test_metrics:
                result["health_checks"]["analytics_service"] = "healthy"
            else:
                result["health_checks"]["analytics_service"] = "degraded"
                result["issues_found"].append(f"Analytics service issue: {test_metrics['error']}")
        except Exception as e:
            result["health_checks"]["analytics_service"] = "unhealthy"
            result["issues_found"].append(f"Analytics service error: {str(e)}")
        
        # Check system performance metrics
        try:
            # Get system-wide stats
            system_stats = analytics_service.get_enhanced_trade_counts(None, 1)  # Last 24 hours
            
            if "error" not in system_stats:
                total_trades = system_stats["summary"]["total_trades"]
                success_rate = system_stats["summary"]["success_rate"]
                
                result["health_checks"]["trade_volume"] = "healthy" if total_trades >= 0 else "warning"
                result["health_checks"]["success_rate"] = "healthy" if success_rate >= 0.7 else "warning"
                
                if success_rate < 0.5:
                    result["issues_found"].append(f"Low system success rate: {success_rate:.1%}")
                    
            else:
                result["health_checks"]["system_stats"] = "unhealthy"
                result["issues_found"].append(f"System stats error: {system_stats['error']}")
                
        except Exception as e:
            result["health_checks"]["system_performance"] = "unhealthy"
            result["issues_found"].append(f"Performance check error: {str(e)}")
        
        # Determine overall health
        health_statuses = list(result["health_checks"].values())
        if all(status == "healthy" for status in health_statuses):
            overall_health = "healthy"
        elif any(status == "unhealthy" for status in health_statuses):
            overall_health = "unhealthy"
        else:
            overall_health = "degraded"
        
        result.update({
            "status": "completed",
            "overall_health": overall_health,
            "end_time": datetime.utcnow().isoformat()
        })
        
        if overall_health == "healthy":
            logger.info("✅ System health check passed - All systems healthy")
        else:
            logger.warning(f"⚠️ System health check completed - Status: {overall_health}, "
                          f"Issues: {len(result['issues_found'])}")
        
        return result
        
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        result.update({
            "status": "failed",
            "error": error_msg,
            "overall_health": "unknown",
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.error(f"❌ System health check failed: {e}\n{traceback.format_exc()}")
        return result
        
    finally:
        db.close()

@celery_app.task(bind=True, name="trade_analytics.cleanup_old_metrics")
def cleanup_old_metrics(self) -> Dict[str, Any]:
    """
    Clean up old metrics and temporary data
    Runs daily at 03:00 UTC
    """
    
    task_id = self.request.id
    logger.info(f"🧹 Starting metrics cleanup - Task ID: {task_id}")
    
    result = {
        "task_id": task_id,
        "status": "started",
        "items_cleaned": 0,
        "start_time": datetime.utcnow().isoformat()
    }
    
    try:
        # For now, this is a placeholder for future cleanup operations
        # Could include cleaning old temporary analytics data, cache cleanup, etc.
        
        result.update({
            "status": "completed",
            "items_cleaned": 0,
            "end_time": datetime.utcnow().isoformat(),
            "message": "Cleanup task placeholder - no items to clean currently"
        })
        
        logger.info("✅ Metrics cleanup completed")
        return result
        
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        result.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.utcnow().isoformat()
        })
        
        logger.error(f"❌ Metrics cleanup failed: {e}\n{traceback.format_exc()}")
        return result 