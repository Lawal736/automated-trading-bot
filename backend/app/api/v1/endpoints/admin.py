from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.api import deps
from app.models.user import User
from app.models.trading import Trade, Position, OrderStatus
from app.models.bot import Bot
from app.models.exchange import ExchangeConnection
from app.models.strategy import Strategy
from app.models.activity import Activity
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

def require_admin(current_user: User = Depends(deps.get_current_active_user)):
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
    return current_user

@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive system overview for admin dashboard
    """
    try:
        # User statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Exchange connections
        total_connections = db.query(ExchangeConnection).count()
        active_connections = db.query(ExchangeConnection).filter(ExchangeConnection.is_active == True).count()
        
        # Bot statistics
        total_bots = db.query(Bot).count()
        active_bots = db.query(Bot).filter(Bot.is_active == True).count()
        
        # Strategy statistics
        total_strategies = db.query(Strategy).count()
        
        # Trade statistics
        total_trades = db.query(Trade).count()
        filled_trades = db.query(Trade).filter(Trade.status == OrderStatus.FILLED.value).count()
        rejected_trades = db.query(Trade).filter(Trade.status == OrderStatus.REJECTED.value).count()
        
        # Manual vs Bot trades
        manual_trades = db.query(Trade).filter(Trade.bot_id.is_(None)).count()
        bot_trades = db.query(Trade).filter(Trade.bot_id.isnot(None)).count()
        
        # Position statistics
        total_positions = db.query(Position).count()
        open_positions = db.query(Position).filter(Position.is_open == True).count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_trades = db.query(Trade).filter(Trade.created_at >= week_ago).count()
        recent_activities = db.query(Activity).filter(Activity.timestamp >= week_ago).count()
        
        # Trade breakdown by side
        buy_trades = db.query(Trade).filter(Trade.side == 'buy').count()
        sell_trades = db.query(Trade).filter(Trade.side == 'sell').count()
        
        # Trade breakdown by type
        spot_trades = db.query(Trade).filter(Trade.trade_type == 'spot').count()
        futures_trades = db.query(Trade).filter(Trade.trade_type == 'futures').count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "exchanges": {
                "total_connections": total_connections,
                "active_connections": active_connections
            },
            "bots": {
                "total": total_bots,
                "active": active_bots
            },
            "strategies": {
                "total": total_strategies
            },
            "trades": {
                "total": total_trades,
                "filled": filled_trades,
                "rejected": rejected_trades,
                "manual": manual_trades,
                "bot_trades": bot_trades,
                "buy": buy_trades,
                "sell": sell_trades,
                "spot": spot_trades,
                "futures": futures_trades,
                "recent_7_days": recent_trades
            },
            "positions": {
                "total": total_positions,
                "open": open_positions
            },
            "activity": {
                "recent_7_days": recent_activities
            }
        }
    except Exception as e:
        logger.error(f"Error getting admin overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get admin overview")

@router.get("/trades")
def get_admin_trades(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    side: str = None,
    trade_type: str = None
) -> Dict[str, Any]:
    """
    Get all trades with filtering options for admin
    """
    try:
        query = db.query(Trade)
        
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
        logger.error(f"Error getting admin trades: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trades")

@router.get("/users")
def get_admin_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get all users for admin
    """
    try:
        total_users = db.query(User).count()
        users = db.query(User).offset(skip).limit(limit).all()
        
        formatted_users = []
        for user in users:
            # Get user statistics
            user_trades = db.query(Trade).filter(Trade.user_id == user.id).count()
            user_bots = db.query(Bot).filter(Bot.user_id == user.id).count()
            user_connections = db.query(ExchangeConnection).filter(ExchangeConnection.user_id == user.id).count()
            
            formatted_user = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "role": user.role,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "statistics": {
                    "trades": user_trades,
                    "bots": user_bots,
                    "connections": user_connections
                }
            }
            formatted_users.append(formatted_user)
        
        return {
            "users": formatted_users,
            "total": total_users,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting admin users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@router.delete("/users/{user_id}")
def delete_admin_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, str]:
    """
    Delete a user by ID (admin only)
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Find the user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete associated data first (optional - you might want to cascade delete)
        # Delete user's trades
        db.query(Trade).filter(Trade.user_id == user_id).delete()
        
        # Delete user's bots
        db.query(Bot).filter(Bot.user_id == user_id).delete()
        
        # Delete user's exchange connections
        db.query(ExchangeConnection).filter(ExchangeConnection.user_id == user_id).delete()
        
        # Delete user's activities
        db.query(Activity).filter(Activity.user_id == user_id).delete()
        
        # Delete the user
        db.delete(user)
        db.commit()
        
        logger.info(f"Admin {current_user.email} deleted user {user.email} (ID: {user_id})")
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

@router.get("/users/{user_id}")
def get_admin_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get detailed user information by ID (admin only)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user statistics
        user_trades = db.query(Trade).filter(Trade.user_id == user_id).count()
        user_bots = db.query(Bot).filter(Bot.user_id == user_id).count()
        user_connections = db.query(ExchangeConnection).filter(ExchangeConnection.user_id == user_id).count()
        user_positions = db.query(Position).filter(Position.user_id == user_id).count()
        
        # Get recent trades (last 10)
        recent_trades = db.query(Trade).filter(Trade.user_id == user_id).order_by(desc(Trade.created_at)).limit(10).all()
        
        # Get recent activities (last 10)
        recent_activities = db.query(Activity).filter(Activity.user_id == user_id).order_by(desc(Activity.timestamp)).limit(10).all()
        
        formatted_user = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "is_active": user.is_active,
            "role": user.role,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "statistics": {
                "trades": user_trades,
                "bots": user_bots,
                "connections": user_connections,
                "positions": user_positions
            },
            "recent_trades": [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "status": trade.status,
                    "created_at": trade.created_at
                } for trade in recent_trades
            ],
            "recent_activities": [
                {
                    "id": activity.id,
                    "type": activity.type,
                    "description": activity.description,
                    "amount": activity.amount,
                    "pnl": activity.pnl,
                    "timestamp": activity.timestamp
                } for activity in recent_activities
            ]
        }
        
        return formatted_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user")

@router.put("/users/{user_id}")
def update_admin_user(
    user_id: int,
    user_update: dict,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update user information by ID (admin only)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Admin {current_user.email} (ID: {current_user.id}) updating user {user.email} (ID: {user_id})")
        logger.info(f"Update data: {user_update}")
        
        # Prevent admin from changing their own role (but allow other fields)
        if user_id == current_user.id and "role" in user_update:
            logger.warning(f"Admin {current_user.email} attempted to change their own role")
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        
        # Update allowed fields
        allowed_fields = ["username", "subscription_tier", "is_active", "role"]
        updated_fields = []
        for field, value in user_update.items():
            if field in allowed_fields:
                setattr(user, field, value)
                updated_fields.append(field)
        
        logger.info(f"Updated fields: {updated_fields}")
        db.commit()
        
        logger.info(f"Admin {current_user.email} successfully updated user {user.email} (ID: {user_id})")
        
        # Return updated user data
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "is_active": user.is_active,
            "role": user.role,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@router.get("/bots")
def get_admin_bots(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get all bots for admin
    """
    try:
        total_bots = db.query(Bot).count()
        bots = db.query(Bot).offset(skip).limit(limit).all()
        
        formatted_bots = []
        for bot in bots:
            # Get bot statistics
            bot_trades = db.query(Trade).filter(Trade.bot_id == bot.id).count()
            bot_positions = db.query(Position).filter(Position.bot_id == bot.id).count()
            
            formatted_bot = {
                "id": bot.id,
                "name": bot.name,
                "user_id": bot.user_id,
                "strategy_name": bot.strategy_name,
                "trade_type": bot.trade_type,
                "direction": bot.direction,
                "is_active": bot.is_active,
                "initial_balance": bot.initial_balance,
                "current_balance": bot.current_balance,
                "created_at": bot.created_at,
                "stats": {
                    "trades": bot_trades,
                    "positions": bot_positions
                }
            }
            formatted_bots.append(formatted_bot)
        
        return {
            "bots": formatted_bots,
            "total": total_bots,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting admin bots: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get bots")

@router.get("/activities")
def get_admin_activities(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get all activities for admin
    """
    try:
        total_activities = db.query(Activity).count()
        activities = db.query(Activity).order_by(desc(Activity.timestamp)).offset(skip).limit(limit).all()
        
        formatted_activities = []
        for activity in activities:
            formatted_activity = {
                "id": activity.id,
                "user_id": activity.user_id,
                "type": activity.type,
                "description": activity.description,
                "amount": activity.amount,
                "pnl": activity.pnl,
                "timestamp": activity.timestamp
            }
            formatted_activities.append(formatted_activity)
        
        return {
            "activities": formatted_activities,
            "total": total_activities,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting admin activities: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get activities") 