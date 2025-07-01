"""
Advanced Stop Loss API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from .... import models
from ....api import deps
from ....services.advanced_stop_loss_service import AdvancedStopLossService, AdvancedStopLossType
from ....tasks.advanced_stop_loss_tasks import (
    update_advanced_stop_losses,
    update_bot_advanced_stop_losses,
    analyze_stop_loss_performance,
    optimize_stop_loss_parameters
)
from ....core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/types")
def get_stop_loss_types() -> Dict[str, Any]:
    """
    Get all available stop loss types and their descriptions
    """
    return {
        "basic_types": {
            "fixed_percentage": "Fixed percentage stop loss",
            "trailing_max_price": "Trailing stop based on maximum price",
            "ema_based": "EMA-based stop loss", 
            "atr_based": "ATR-based stop loss",
            "support_level": "Support/resistance level stop loss"
        },
        "advanced_types": {
            "adaptive_atr": "Adaptive ATR that adjusts to market volatility",
            "volatility_based": "Volatility-based stop using standard deviation",
            "fibonacci_retracement": "Fibonacci retracement level stop loss",
            "supertrend": "SuperTrend indicator based stop loss",
            "parabolic_sar": "Parabolic SAR based stop loss",
            "bollinger_band": "Bollinger Band based stop loss",
            "risk_reward_ratio": "Risk/reward ratio based stop loss",
            "time_decay": "Time-based stop loss that tightens over time",
            "momentum_divergence": "RSI momentum divergence based stop loss"
        }
    }


@router.post("/update-all")
async def trigger_advanced_stop_loss_update(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger advanced stop loss update for all positions
    """
    try:
        # Only allow admin users to trigger global updates
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Trigger the task
        task = update_advanced_stop_losses.delay()
        
        return {
            "success": True,
            "message": "Advanced stop loss update triggered",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error triggering advanced stop loss update: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger update")


@router.post("/update-bot/{bot_id}")
async def trigger_bot_stop_loss_update(
    bot_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger advanced stop loss update for a specific bot
    """
    try:
        # Verify bot belongs to user or user is admin
        bot = db.query(models.Bot).filter(models.Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update this bot")
        
        # Trigger the task
        task = update_bot_advanced_stop_losses.delay(bot_id)
        
        return {
            "success": True,
            "message": f"Advanced stop loss update triggered for bot {bot_id}",
            "task_id": task.id,
            "bot_id": bot_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering bot stop loss update: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger update")


@router.get("/performance-analysis")
async def get_stop_loss_performance_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get stop loss performance analysis across different algorithms
    """
    try:
        # Trigger analysis task
        task = analyze_stop_loss_performance.delay()
        
        return {
            "success": True,
            "message": "Stop loss performance analysis triggered",
            "task_id": task.id,
            "note": "Analysis results will be available after task completion"
        }
        
    except Exception as e:
        logger.error(f"Error triggering performance analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger analysis")


@router.post("/optimize-bot/{bot_id}")
async def optimize_bot_stop_loss_parameters(
    bot_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Optimize stop loss parameters for a specific bot based on historical performance
    """
    try:
        # Verify bot belongs to user or user is admin
        bot = db.query(models.Bot).filter(models.Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to optimize this bot")
        
        # Trigger optimization task
        task = optimize_stop_loss_parameters.delay(bot_id)
        
        return {
            "success": True,
            "message": f"Stop loss parameter optimization triggered for bot {bot_id}",
            "task_id": task.id,
            "bot_id": bot_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering parameter optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger optimization")


@router.get("/bot/{bot_id}/configuration")
def get_bot_stop_loss_configuration(
    bot_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get the current stop loss configuration for a bot
    """
    try:
        # Verify bot belongs to user or user is admin
        bot = db.query(models.Bot).filter(models.Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to view this bot")
        
        return {
            "bot_id": bot.id,
            "bot_name": bot.name,
            "stop_loss_type": bot.stop_loss_type,
            "stop_loss_percentage": bot.stop_loss_percentage,
            "stop_loss_timeframe": bot.stop_loss_timeframe,
            "stop_loss_ema_period": bot.stop_loss_ema_period,
            "stop_loss_atr_period": bot.stop_loss_atr_period,
            "stop_loss_atr_multiplier": bot.stop_loss_atr_multiplier,
            "stop_loss_support_lookback": bot.stop_loss_support_lookback,
            "is_advanced_type": bot.stop_loss_type in [t.value for t in AdvancedStopLossType]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot stop loss configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration")


@router.put("/bot/{bot_id}/configuration")
def update_bot_stop_loss_configuration(
    bot_id: int,
    stop_loss_type: str,
    stop_loss_percentage: Optional[float] = None,
    stop_loss_timeframe: Optional[str] = None,
    stop_loss_ema_period: Optional[int] = None,
    stop_loss_atr_period: Optional[int] = None,
    stop_loss_atr_multiplier: Optional[float] = None,
    stop_loss_support_lookback: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Update stop loss configuration for a bot
    """
    try:
        # Verify bot belongs to user or user is admin
        bot = db.query(models.Bot).filter(models.Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to update this bot")
        
        # Validate stop loss type
        valid_types = [t.value for t in AdvancedStopLossType] + [
            "fixed_percentage", "trailing_max_price", "ema_based", "atr_based", "support_level"
        ]
        
        if stop_loss_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid stop loss type. Valid types: {valid_types}")
        
        # Update bot configuration
        bot.stop_loss_type = stop_loss_type
        
        if stop_loss_percentage is not None:
            bot.stop_loss_percentage = stop_loss_percentage
        if stop_loss_timeframe is not None:
            bot.stop_loss_timeframe = stop_loss_timeframe
        if stop_loss_ema_period is not None:
            bot.stop_loss_ema_period = stop_loss_ema_period
        if stop_loss_atr_period is not None:
            bot.stop_loss_atr_period = stop_loss_atr_period
        if stop_loss_atr_multiplier is not None:
            bot.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        if stop_loss_support_lookback is not None:
            bot.stop_loss_support_lookback = stop_loss_support_lookback
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Stop loss configuration updated for bot {bot_id}",
            "bot_id": bot.id,
            "stop_loss_type": bot.stop_loss_type,
            "updated_fields": {
                "stop_loss_type": stop_loss_type,
                "stop_loss_percentage": stop_loss_percentage,
                "stop_loss_timeframe": stop_loss_timeframe,
                "stop_loss_ema_period": stop_loss_ema_period,
                "stop_loss_atr_period": stop_loss_atr_period,
                "stop_loss_atr_multiplier": stop_loss_atr_multiplier,
                "stop_loss_support_lookback": stop_loss_support_lookback
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot stop loss configuration: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.get("/user/positions-summary")
async def get_user_stop_loss_positions_summary(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get summary of user's positions with their stop loss status
    """
    try:
        service = AdvancedStopLossService(db)
        
        # Get user's open positions
        from app.models.trading import Position, Trade
        from sqlalchemy import and_
        
        positions = db.query(Position).join(Trade).filter(
            and_(
                Trade.user_id == current_user.id,
                Position.is_open == True
            )
        ).all()
        
        summary = {
            "total_open_positions": len(positions),
            "positions_with_stop_loss": 0,
            "positions_without_stop_loss": 0,
            "stop_loss_types_count": {},
            "total_position_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "positions": []
        }
        
        for position in positions:
            trade = db.query(Trade).filter(
                Trade.exchange_order_id == position.exchange_order_id
            ).first()
            
            if not trade:
                continue
                
            bot = db.query(models.Bot).filter(models.Bot.id == trade.bot_id).first() if trade.bot_id else None
            
            has_stop_loss = trade.stop_loss is not None
            stop_loss_type = bot.stop_loss_type if bot else "manual"
            
            if has_stop_loss:
                summary["positions_with_stop_loss"] += 1
            else:
                summary["positions_without_stop_loss"] += 1
            
            if stop_loss_type not in summary["stop_loss_types_count"]:
                summary["stop_loss_types_count"][stop_loss_type] = 0
            summary["stop_loss_types_count"][stop_loss_type] += 1
            
            current_value = (position.current_price or position.entry_price) * position.quantity
            summary["total_position_value"] += current_value
            summary["total_unrealized_pnl"] += position.unrealized_pnl or 0.0
            
            summary["positions"].append({
                "position_id": position.id,
                "symbol": position.symbol,
                "side": position.side,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "current_value": current_value,
                "unrealized_pnl": position.unrealized_pnl,
                "has_stop_loss": has_stop_loss,
                "stop_loss_price": trade.stop_loss,
                "stop_loss_type": stop_loss_type,
                "bot_name": bot.name if bot else "Manual Trade",
                "opened_at": position.opened_at
            })
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting user stop loss positions summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get positions summary") 