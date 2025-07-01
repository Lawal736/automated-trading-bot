"""
Celery tasks for position management and real-time P&L calculations
"""

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, List
from datetime import datetime
import asyncio

from app.core.database import SessionLocal
from app.core.celery import celery_app
from app.models.trading import Position
from app.models.user import User
from app.services.position_service import PositionService
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="tasks.update_all_position_prices")
def update_all_position_prices() -> Dict[str, Any]:
    """
    Scheduled task to update current prices for all open positions across all users
    """
    db = SessionLocal()
    try:
        logger.info("Starting global position price update task")
        
        # Get all users with open positions
        users_with_positions = db.query(User.id).join(Position).filter(
            Position.is_open == True
        ).distinct().all()
        
        results = {
            'total_users': len(users_with_positions),
            'total_updated_positions': 0,
            'total_unrealized_pnl': 0.0,
            'user_results': [],
            'errors': 0
        }
        
        position_service = PositionService()
        
        for user_tuple in users_with_positions:
            user_id = user_tuple[0]
            try:
                # Run async function in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                update_result = loop.run_until_complete(
                    position_service.update_position_prices(db, user_id)
                )
                
                loop.close()
                
                user_result = {
                    'user_id': user_id,
                    'updated_positions': update_result.get('updated_positions', 0),
                    'unrealized_pnl': update_result.get('total_unrealized_pnl', 0.0),
                    'timestamp': update_result.get('timestamp')
                }
                
                results['user_results'].append(user_result)
                results['total_updated_positions'] += update_result.get('updated_positions', 0)
                results['total_unrealized_pnl'] += update_result.get('total_unrealized_pnl', 0.0)
                
                logger.info(f"Updated {update_result.get('updated_positions', 0)} positions for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error updating positions for user {user_id}: {e}")
                results['errors'] += 1
                results['user_results'].append({
                    'user_id': user_id,
                    'error': str(e),
                    'updated_positions': 0,
                    'unrealized_pnl': 0.0
                })
        
        logger.info(f"Global position update completed: {results['total_updated_positions']} positions updated across {results['total_users']} users")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in global position price update task: {e}")
        return {
            'total_users': 0,
            'total_updated_positions': 0,
            'total_unrealized_pnl': 0.0,
            'user_results': [],
            'errors': 1,
            'error_message': str(e)
        }
    finally:
        db.close()


@celery_app.task(name="tasks.update_user_position_prices")
def update_user_position_prices(user_id: int) -> Dict[str, Any]:
    """
    Update position prices for a specific user
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting position price update for user {user_id}")
        
        position_service = PositionService()
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        update_result = loop.run_until_complete(
            position_service.update_position_prices(db, user_id)
        )
        
        loop.close()
        
        logger.info(f"Position update completed for user {user_id}: {update_result.get('updated_positions', 0)} positions updated")
        
        return {
            'success': True,
            'user_id': user_id,
            'updated_positions': update_result.get('updated_positions', 0),
            'total_unrealized_pnl': update_result.get('total_unrealized_pnl', 0.0),
            'position_updates': update_result.get('position_updates', []),
            'timestamp': update_result.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Error updating positions for user {user_id}: {e}")
        return {
            'success': False,
            'user_id': user_id,
            'error': str(e),
            'updated_positions': 0,
            'total_unrealized_pnl': 0.0
        }
    finally:
        db.close()


@celery_app.task(name="tasks.calculate_daily_pnl_records")
def calculate_daily_pnl_records() -> Dict[str, Any]:
    """
    Daily task to calculate and store P&L records for all users
    """
    db = SessionLocal()
    try:
        logger.info("Starting daily P&L record calculation")
        
        # Get all users with positions or trades
        users = db.query(User).all()
        
        results = {
            'total_users': len(users),
            'records_created': 0,
            'errors': 0,
            'user_results': []
        }
        
        position_service = PositionService()
        today = datetime.utcnow().date()
        
        for user in users:
            try:
                # Get P&L summary for the user
                pnl_summary = position_service.get_portfolio_pnl_summary(db, user.id)
                
                # Check if record already exists for today
                from app.models.trading import PerformanceRecord
                existing_record = db.query(PerformanceRecord).filter(
                    and_(
                        PerformanceRecord.user_id == user.id,
                        PerformanceRecord.date == today
                    )
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.daily_pnl = pnl_summary.get('daily_pnl', 0.0)
                    existing_record.ending_balance = pnl_summary.get('total_pnl', 0.0)
                    logger.info(f"Updated existing P&L record for user {user.id}")
                else:
                    # Create new record
                    performance_record = PerformanceRecord(
                        user_id=user.id,
                        date=today,
                        starting_balance=0.0,  # Will be updated by exchange service
                        ending_balance=pnl_summary.get('total_pnl', 0.0),
                        daily_pnl=pnl_summary.get('daily_pnl', 0.0),
                        total_trades=0,  # Will be calculated separately
                        winning_trades=0,
                        losing_trades=0,
                        win_rate=0.0
                    )
                    db.add(performance_record)
                    results['records_created'] += 1
                    logger.info(f"Created new P&L record for user {user.id}")
                
                results['user_results'].append({
                    'user_id': user.id,
                    'daily_pnl': pnl_summary.get('daily_pnl', 0.0),
                    'total_pnl': pnl_summary.get('total_pnl', 0.0),
                    'active_positions': pnl_summary.get('active_positions_count', 0)
                })
                
            except Exception as e:
                logger.error(f"Error calculating P&L record for user {user.id}: {e}")
                results['errors'] += 1
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Daily P&L calculation completed: {results['records_created']} records created/updated")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in daily P&L calculation task: {e}")
        db.rollback()
        return {
            'total_users': 0,
            'records_created': 0,
            'errors': 1,
            'error_message': str(e),
            'user_results': []
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cleanup_old_performance_records")
def cleanup_old_performance_records(days_to_keep: int = 365) -> Dict[str, Any]:
    """
    Clean up old performance records to maintain database size
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting cleanup of performance records older than {days_to_keep} days")
        
        from app.models.trading import PerformanceRecord
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow().date() - timedelta(days=days_to_keep)
        
        # Delete old records
        deleted_count = db.query(PerformanceRecord).filter(
            PerformanceRecord.date < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup completed: {deleted_count} old performance records deleted")
        
        return {
            'success': True,
            'deleted_records': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'days_kept': days_to_keep
        }
        
    except Exception as e:
        logger.error(f"Error in performance records cleanup: {e}")
        db.rollback()
        return {
            'success': False,
            'error': str(e),
            'deleted_records': 0
        }
    finally:
        db.close() 