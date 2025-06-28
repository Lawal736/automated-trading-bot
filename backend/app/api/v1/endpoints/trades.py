from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Dict, Any
from datetime import datetime, timedelta

from app.api import deps
from app.models.user import User
from app.models.trading import Trade, OrderStatus
from app.services.manual_stop_loss_service import ManualStopLossService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/")
def get_user_trades(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    side: str = None,
    trade_type: str = None
) -> Dict[str, Any]:
    """
    Get user's trades with filtering options
    """
    try:
        query = db.query(Trade).filter(Trade.user_id == current_user.id)
        
        # Apply filters
        if status:
            query = query.filter(Trade.status == status)
        if side:
            query = query.filter(Trade.side == side)
        if trade_type:
            query = query.filter(Trade.trade_type == trade_type)
        
        # Get total count
        total_count = query.count()
        
        # Get paginated results
        trades = query.order_by(desc(Trade.created_at)).offset(skip).limit(limit).all()
        
        # Format trades
        formatted_trades = []
        for trade in trades:
            formatted_trade = {
                "id": trade.id,
                "user_id": trade.user_id,
                "bot_id": trade.bot_id,
                "symbol": trade.symbol,
                "side": trade.side,
                "trade_type": trade.trade_type,
                "order_type": trade.order_type,
                "quantity": trade.quantity,
                "price": trade.price,
                "executed_price": trade.executed_price,
                "status": trade.status,
                "fee": trade.fee,
                "created_at": trade.created_at,
                "executed_at": trade.executed_at,
                "is_manual": trade.bot_id is None
            }
            formatted_trades.append(formatted_trade)
        
        return {
            "trades": formatted_trades,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting user trades: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trades")

@router.get("/stats")
def get_user_trade_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Dict[str, Any]:
    """
    Get comprehensive trade statistics for the user
    """
    try:
        # Base query for user's trades
        user_trades_query = db.query(Trade).filter(Trade.user_id == current_user.id)
        
        # Total trades
        total_trades = user_trades_query.count()
        
        # Status breakdown
        filled_trades = user_trades_query.filter(Trade.status == OrderStatus.FILLED.value).count()
        rejected_trades = user_trades_query.filter(Trade.status == OrderStatus.REJECTED.value).count()
        pending_trades = user_trades_query.filter(Trade.status == OrderStatus.PENDING.value).count()
        
        # Side breakdown
        buy_trades = user_trades_query.filter(Trade.side == 'buy').count()
        sell_trades = user_trades_query.filter(Trade.side == 'sell').count()
        
        # Type breakdown
        spot_trades = user_trades_query.filter(Trade.trade_type == 'spot').count()
        futures_trades = user_trades_query.filter(Trade.trade_type == 'futures').count()
        
        # Manual vs Bot trades
        manual_trades = user_trades_query.filter(Trade.bot_id.is_(None)).count()
        bot_trades = user_trades_query.filter(Trade.bot_id.isnot(None)).count()
        
        # Calculate success rate (filled trades / total trades)
        success_rate = filled_trades / total_trades if total_trades > 0 else 0
        
        # Calculate total volume (sum of executed prices * quantities for filled trades)
        volume_result = db.query(
            func.sum(Trade.executed_price * Trade.quantity)
        ).filter(
            Trade.user_id == current_user.id,
            Trade.status == OrderStatus.FILLED.value,
            Trade.executed_price.isnot(None)
        ).scalar()
        
        total_volume = float(volume_result) if volume_result else 0
        
        # Calculate P&L statistics (this would need to be implemented based on your P&L calculation logic)
        # For now, we'll use a placeholder
        total_pnl = 0  # This should be calculated based on your P&L logic
        avg_profit = 0  # This should be calculated based on your P&L logic
        avg_loss = 0    # This should be calculated based on your P&L logic
        win_loss_ratio = 0  # This should be calculated based on your P&L logic
        
        return {
            "total_trades": total_trades,
            "filled_trades": filled_trades,
            "rejected_trades": rejected_trades,
            "pending_trades": pending_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "spot_trades": spot_trades,
            "futures_trades": futures_trades,
            "manual_trades": manual_trades,
            "bot_trades": bot_trades,
            "success_rate": success_rate,
            "total_volume": total_volume,
            "total_pnl": total_pnl,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "win_loss_ratio": win_loss_ratio
        }
    except Exception as e:
        logger.error(f"Error getting user trade stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trade statistics")

@router.get("/manual-stop-loss-status")
def get_manual_stop_loss_status(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Dict[str, Any]:
    """
    Get status of manual trade stop loss management for the current user
    """
    try:
        manual_service = ManualStopLossService(db)
        managed_trades = manual_service.get_manual_trades_with_stop_loss_management()
        
        # Filter for current user's trades
        user_trades = [trade for trade in managed_trades if trade['user_id'] == current_user.id]
        
        # Get recent stop loss update activities
        from app.models.activity import Activity
        recent_activities = db.query(Activity).filter(
            and_(
                Activity.user_id == current_user.id,
                Activity.type.in_(['MANUAL_STOP_LOSS_UPDATE', 'MANUAL_EMA25_SETUP', 'MANUAL_EMA25_SETUP_SCHEDULED'])
            )
        ).order_by(desc(Activity.timestamp)).limit(10).all()
        
        return {
            "managed_trades_count": len(user_trades),
            "managed_trades": user_trades,
            "recent_activities": [
                {
                    "type": activity.type,
                    "description": activity.description,
                    "amount": activity.amount,
                    "timestamp": activity.timestamp
                } for activity in recent_activities
            ]
        }
    except Exception as e:
        logger.error(f"Error getting manual stop loss status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get manual stop loss status")

@router.post("/{trade_id}/enable-ema25-trailing")
def enable_ema25_trailing_for_trade(
    trade_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Dict[str, Any]:
    """
    Enable EMA25 trailing stop loss management for a specific manual trade
    """
    try:
        from app.tasks.manual_stop_loss_tasks import setup_manual_ema25_trailing
        
        # Schedule the EMA25 trailing setup task
        setup_task = setup_manual_ema25_trailing.delay(trade_id, current_user.id)
        
        return {
            "success": True,
            "trade_id": trade_id,
            "task_id": setup_task.id,
            "message": "EMA25 trailing stop loss management setup scheduled"
        }
    except Exception as e:
        logger.error(f"Error enabling EMA25 trailing for trade {trade_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to enable EMA25 trailing") 