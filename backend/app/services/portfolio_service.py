from datetime import datetime
from sqlalchemy.orm import Session
from ..services import bot_service, activity_service, exchange_service
from ..schemas.portfolio import Portfolio
from ..core.cache import cache_client, get_cache_key_for_user_portfolio
from ..core.logging import get_logger
from app.models.trading import Position, Trade
from app.services.position_service import PositionService

logger = get_logger(__name__)

def clear_portfolio_cache(user_id: int):
    """Clear the portfolio cache for a specific user"""
    cache_key = get_cache_key_for_user_portfolio(user_id)
    cache_client.delete(cache_key)
    logger.info(f"Portfolio cache cleared for user {user_id}")

async def get_portfolio_data_realtime(db: Session, *, user_id: int) -> Portfolio:
    """
    Get real-time portfolio data with live position updates
    This is the new enhanced version with accurate P&L calculations
    """
    try:
        # Initialize position service
        position_service = PositionService()
        
        # Update all position prices first
        position_update_result = await position_service.update_position_prices(db, user_id)
        
        # Get comprehensive P&L summary
        pnl_summary = position_service.get_portfolio_pnl_summary(db, user_id)
        
        # Get exchange balance data
        exchange_balance_data = exchange_service.get_total_balance(db=db, user_id=user_id)
        total_balance_from_exchange = exchange_balance_data.get("total_usd_value", 0.0)
        
        # Calculate available balance (total - unrealized positions value)
        unrealized_position_value = 0.0
        open_positions = db.query(Position).filter(
            Position.user_id == user_id, 
            Position.is_open == True
        ).all()
        
        for position in open_positions:
            current_price = position.current_price or position.entry_price
            position_value = current_price * position.quantity
            unrealized_position_value += position_value
        
        available_balance = max(0, total_balance_from_exchange - unrealized_position_value)
        
        # Get trade counts (both from trades table and activities)
        total_trades = db.query(Trade).filter(Trade.user_id == user_id).count()
        
        # Enhanced daily P&L calculation
        today = datetime.utcnow().date()
        daily_pnl = pnl_summary.get('daily_pnl', 0.0)
        
        # If no daily P&L from positions, check activities as fallback
        if daily_pnl == 0.0:
            activities = activity_service.get_all_activities_by_user_id(db=db, user_id=user_id)
            daily_pnl = sum(
                activity.pnl
                for activity in activities
                if activity.pnl is not None and activity.timestamp.date() == today
            )
        
        portfolio = Portfolio(
            total_balance=total_balance_from_exchange,
            available_balance=available_balance,
            total_pnl=pnl_summary.get('total_pnl', 0.0),
            daily_pnl=daily_pnl,
            active_positions=pnl_summary.get('active_positions_count', 0),
            total_trades=total_trades,
            # Additional metrics from enhanced calculation
            unrealized_pnl=pnl_summary.get('total_unrealized_pnl', 0.0),
            realized_pnl=pnl_summary.get('total_realized_pnl', 0.0),
            position_updates_count=position_update_result.get('updated_positions', 0),
            last_update_timestamp=position_update_result.get('timestamp', datetime.utcnow())
        )
        
        # Cache the enhanced portfolio data (shorter TTL for real-time data)
        cache_client.set(cache_key, portfolio.model_dump(), ttl_seconds=60)  # 1 minute cache
        
        logger.info(f"Enhanced portfolio calculated for user {user_id}: "
                   f"Total P&L: {portfolio.total_pnl}, Daily P&L: {portfolio.daily_pnl}, "
                   f"Active Positions: {portfolio.active_positions}")
        
        return portfolio
        
    except Exception as e:
        logger.error(f"Error calculating enhanced portfolio for user {user_id}: {e}")
        # Fallback to basic calculation
        return await get_portfolio_data_basic(db, user_id=user_id)

async def get_portfolio_data_basic(db: Session, *, user_id: int) -> Portfolio:
    """
    Basic portfolio calculation (fallback method)
    """
    try:
        bots = bot_service.get_multi_by_owner(db=db, owner_id=user_id)
        activities = activity_service.get_all_activities_by_user_id(db=db, user_id=user_id)

        exchange_balance_data = exchange_service.get_total_balance(db=db, user_id=user_id)
        total_balance_from_exchange = exchange_balance_data.get("total_usd_value", 0.0)

        total_balance = total_balance_from_exchange
        available_balance = total_balance

        total_pnl = sum(activity.pnl for activity in activities if activity.pnl is not None)

        today = datetime.utcnow().date()
        daily_pnl = sum(
            activity.pnl
            for activity in activities
            if activity.pnl is not None and activity.timestamp.date() == today
        )

        active_positions = db.query(Position).filter(Position.user_id == user_id, Position.is_open == True).count()
        total_trades = db.query(Trade).filter(Trade.user_id == user_id).count()
        
        portfolio = Portfolio(
            total_balance=total_balance,
            available_balance=available_balance,
            total_pnl=total_pnl,
            daily_pnl=daily_pnl,
            active_positions=active_positions,
            total_trades=total_trades,
        )

        return portfolio
        
    except Exception as e:
        logger.error(f"Error in basic portfolio calculation for user {user_id}: {e}")
        # Return empty portfolio as last resort
        return Portfolio(
            total_balance=0.0,
            available_balance=0.0,
            total_pnl=0.0,
            daily_pnl=0.0,
            active_positions=0,
            total_trades=0,
        )

def get_portfolio_data(db: Session, *, user_id: int) -> Portfolio:
    """
    Main portfolio data method - tries cache first, then real-time calculation
    """
    # Try cache first
    cache_key = get_cache_key_for_user_portfolio(user_id)
    cached_portfolio = cache_client.get(cache_key)
    if cached_portfolio:
        logger.info(f"Portfolio cache hit for user {user_id}")
        return Portfolio(**cached_portfolio)

    logger.info(f"Portfolio cache miss for user {user_id}. Fetching fresh data.")
    
    # For synchronous compatibility, use basic calculation
    # In async endpoints, use get_portfolio_data_realtime directly
    try:
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(get_portfolio_data_basic(db, user_id=user_id))
    except Exception as e:
        logger.error(f"Error in portfolio calculation for user {user_id}: {e}")
        return Portfolio(
            total_balance=0.0,
            available_balance=0.0,
            total_pnl=0.0,
            daily_pnl=0.0,
            active_positions=0,
            total_trades=0,
        )