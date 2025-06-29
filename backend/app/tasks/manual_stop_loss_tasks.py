"""
Celery tasks for manual trade stop loss management
"""

import asyncio
from celery import current_task
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import SessionLocal
from app.core.celery import celery_app
from app.services.manual_stop_loss_service import ManualStopLossService
from app.core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task(name="tasks.update_manual_stop_losses")
def update_manual_stop_losses() -> Dict[str, Any]:
    """
    Daily task to update stop losses for manual trades using EMA25 trailing logic
    """
    db = SessionLocal()
    try:
        logger.info("Starting manual stop loss update task")
        
        manual_service = ManualStopLossService(db)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(manual_service.update_manual_trade_stop_losses())
        finally:
            loop.close()
        
        logger.info(f"Manual stop loss update completed: {results['updated_trades']} updated, {results['errors']} errors")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in manual stop loss update task: {e}")
        return {
            'total_trades': 0,
            'updated_trades': 0,
            'errors': 1,
            'details': [{'status': 'error', 'error': str(e)}]
        }
    finally:
        db.close()

@celery_app.task(name="tasks.setup_manual_ema25_trailing")
def setup_manual_ema25_trailing(trade_id: int, user_id: int) -> Dict[str, Any]:
    """
    Set up EMA25 trailing stop loss management for a specific manual trade
    """
    db = SessionLocal()
    try:
        logger.info(f"Setting up EMA25 trailing for manual trade {trade_id}")
        
        manual_service = ManualStopLossService(db)
        success = manual_service.setup_ema25_trailing_for_trade(trade_id, user_id)
        
        if success:
            logger.info(f"EMA25 trailing setup successful for trade {trade_id}")
            return {
                'success': True,
                'trade_id': trade_id,
                'message': 'EMA25 trailing stop loss management enabled'
            }
        else:
            logger.error(f"EMA25 trailing setup failed for trade {trade_id}")
            return {
                'success': False,
                'trade_id': trade_id,
                'message': 'Failed to enable EMA25 trailing stop loss management'
            }
        
    except Exception as e:
        logger.error(f"Error setting up EMA25 trailing for trade {trade_id}: {e}")
        return {
            'success': False,
            'trade_id': trade_id,
            'error': str(e)
        }
    finally:
        db.close() 