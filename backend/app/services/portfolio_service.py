from datetime import datetime
from sqlalchemy.orm import Session
from ..services import bot_service, activity_service, exchange_service
from ..schemas.portfolio import Portfolio
from ..core.cache import cache_client, get_cache_key_for_user_portfolio
from ..core.logging import get_logger
from app.models.trading import Position, Trade

logger = get_logger(__name__)

def clear_portfolio_cache(user_id: int):
    """Clear the portfolio cache for a specific user"""
    cache_key = get_cache_key_for_user_portfolio(user_id)
    cache_client.delete(cache_key)
    logger.info(f"Portfolio cache cleared for user {user_id}")

def get_portfolio_data(db: Session, *, user_id: int) -> Portfolio:
    """
    Calculates and returns portfolio data, using a cache to improve performance.
    """
    # Clear cache to ensure fresh data (temporary fix for development)
    clear_portfolio_cache(user_id)
    
    # 1. Try to fetch from cache first
    cache_key = get_cache_key_for_user_portfolio(user_id)
    cached_portfolio = cache_client.get(cache_key)
    if cached_portfolio:
        logger.info(f"Portfolio cache hit for user {user_id}")
        # Pydantic models expect dicts, so we construct from the cached dict
        return Portfolio(**cached_portfolio)

    logger.info(f"Portfolio cache miss for user {user_id}. Fetching from sources.")

    # 2. If not in cache, fetch from sources (DB and exchanges)
    bots = bot_service.get_multi_by_owner(db=db, owner_id=user_id)
    activities = activity_service.get_all_activities_by_user_id(db=db, user_id=user_id)

    # This is the slow part we are caching
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

    # Count active positions from positions table (open positions)
    active_positions = db.query(Position).filter(Position.user_id == user_id, Position.is_open == True).count()
    
    # Count total trades from trades table (unique trade operations)
    # This counts each trade operation, not individual buy/sell orders
    total_trades = db.query(Trade).filter(Trade.user_id == user_id).count()

    portfolio = Portfolio(
        total_balance=total_balance,
        available_balance=available_balance,
        total_pnl=total_pnl,
        daily_pnl=daily_pnl,
        active_positions=active_positions,
        total_trades=total_trades,
    )

    # 3. Store the newly fetched data in the cache
    # The portfolio object is converted to a dict for JSON serialization
    cache_client.set(cache_key, portfolio.model_dump(), ttl_seconds=300)  # Cache for 5 minutes

    return portfolio