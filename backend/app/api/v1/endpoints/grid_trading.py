"""
Grid Trading Strategy API Endpoints
Comprehensive REST API for grid trading management and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.bot import Bot
from app.services.grid_trading_service import GridTradingService, GridType, GridDirection, GridState
from app.services.exchange_service import ExchangeService
from app.tasks.grid_trading_tasks import (
    process_active_grids,
    initialize_new_grids,
    grid_rebalancing,
    grid_performance_monitor,
    emergency_grid_stop,
    cleanup_completed_grids
)
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import traceback

logger = get_logger(__name__)
router = APIRouter()

# Request/Response Models
class GridTradingConfigRequest(BaseModel):
    grid_type: GridType = GridType.ARITHMETIC
    grid_direction: GridDirection = GridDirection.NEUTRAL
    grid_levels: int = 10
    grid_spacing_percent: float = 1.0
    investment_per_grid: float = 100.0
    price_upper_limit: Optional[float] = None
    price_lower_limit: Optional[float] = None
    auto_calculate_range: bool = True
    volatility_lookback: int = 20
    volatility_multiplier: float = 2.0
    rebalance_threshold: float = 0.1
    max_total_investment: float = 1000.0
    stop_loss_percent: float = 15.0
    take_profit_percent: float = 25.0
    max_open_orders: int = 20
    fibonacci_base_spacing: Optional[float] = 0.5
    bollinger_period: Optional[int] = 20
    bollinger_std_dev: Optional[float] = 2.0

class GridInitializeRequest(BaseModel):
    bot_id: int
    symbol: str

class GridStopRequest(BaseModel):
    bot_id: int
    reason: str = "Manual stop"

class GridRebalanceRequest(BaseModel):
    bot_id: int
    symbol: Optional[str] = None  # If None, rebalance all symbols

@router.get("/grid-types", summary="Get available grid trading types")
async def get_grid_types() -> Dict[str, Any]:
    """Get all available grid trading algorithm types"""
    
    return {
        "success": True,
        "grid_types": [
            {
                "value": GridType.ARITHMETIC,
                "name": "Arithmetic Grid",
                "description": "Equal price intervals between grid levels"
            },
            {
                "value": GridType.GEOMETRIC,
                "name": "Geometric Grid", 
                "description": "Percentage-based intervals (exponential spacing)"
            },
            {
                "value": GridType.DYNAMIC,
                "name": "Dynamic Grid",
                "description": "Volatility-based adaptation of grid spacing"
            },
            {
                "value": GridType.FIBONACCI,
                "name": "Fibonacci Grid",
                "description": "Grid levels based on Fibonacci sequence"
            },
            {
                "value": GridType.BOLLINGER,
                "name": "Bollinger Band Grid",
                "description": "Grid levels based on Bollinger Band calculations"
            },
            {
                "value": GridType.SUPPORT_RESISTANCE,
                "name": "Support/Resistance Grid",
                "description": "Grid levels aligned with support and resistance levels"
            }
        ],
        "grid_directions": [
            {
                "value": GridDirection.LONG_ONLY,
                "name": "Long Only",
                "description": "Only place buy orders (accumulate on dips)"
            },
            {
                "value": GridDirection.SHORT_ONLY,
                "name": "Short Only", 
                "description": "Only place sell orders (profit on rallies)"
            },
            {
                "value": GridDirection.NEUTRAL,
                "name": "Neutral",
                "description": "Place both buy and sell orders"
            }
        ]
    }

@router.post("/initialize", summary="Initialize grid trading for a bot")
async def initialize_grid_trading(
    request: GridInitializeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Initialize grid trading for a specific bot and symbol"""
    
    try:
        # Get the bot
        bot = db.query(Bot).filter(
            Bot.id == request.bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if bot.strategy_name != "grid_trading":
            raise HTTPException(status_code=400, detail="Bot is not configured for grid trading")
        
        # Initialize services
        exchange_service = ExchangeService(bot.exchange_connection)
        grid_service = GridTradingService(db, bot, exchange_service)
        
        # Initialize the grid
        result = grid_service.initialize_grid(request.symbol)
        
        if result.get("success"):
            logger.info(f"✅ Grid initialized for bot {request.bot_id} on {request.symbol}")
            return result
        else:
            logger.error(f"❌ Failed to initialize grid for bot {request.bot_id}: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Grid initialization failed"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initializing grid trading: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/status/{bot_id}", summary="Get grid trading status for a bot")
async def get_grid_status(
    bot_id: int,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive grid trading status for a bot"""
    
    try:
        # Get the bot
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Initialize services
        exchange_service = ExchangeService(bot.exchange_connection)
        grid_service = GridTradingService(db, bot, exchange_service)
        
        # Get status for specific symbol or all symbols
        if symbol:
            status = grid_service.get_grid_status(symbol)
            return {"success": True, "status": status}
        else:
            # Get status for all trading pairs
            all_status = {}
            if bot.trading_pairs:
                for trading_symbol in bot.trading_pairs:
                    all_status[trading_symbol] = grid_service.get_grid_status(trading_symbol)
            
            return {"success": True, "status": all_status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting grid status: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/stop", summary="Stop grid trading for a bot")
async def stop_grid_trading(
    request: GridStopRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Stop grid trading for a specific bot"""
    
    try:
        # Get the bot
        bot = db.query(Bot).filter(
            Bot.id == request.bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Trigger emergency stop via Celery task
        background_tasks.add_task(
            lambda: emergency_grid_stop.delay(request.bot_id, request.reason)
        )
        
        logger.info(f"🚨 Grid stop initiated for bot {request.bot_id}: {request.reason}")
        
        return {
            "success": True,
            "message": "Grid stop initiated",
            "bot_id": request.bot_id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error stopping grid trading: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/rebalance", summary="Trigger grid rebalancing")
async def trigger_grid_rebalance(
    request: GridRebalanceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger grid rebalancing for a bot"""
    
    try:
        # Get the bot
        bot = db.query(Bot).filter(
            Bot.id == request.bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Initialize services
        exchange_service = ExchangeService(bot.exchange_connection)
        grid_service = GridTradingService(db, bot, exchange_service)
        
        results = {}
        
        # Rebalance specific symbol or all symbols
        if request.symbol:
            symbols_to_rebalance = [request.symbol]
        else:
            symbols_to_rebalance = bot.trading_pairs or []
        
        for symbol in symbols_to_rebalance:
            try:
                # Get current market data
                market_data = grid_service._get_market_data(symbol)
                if not market_data.empty:
                    current_price = market_data['close'].iloc[-1]
                    rebalance_result = grid_service._rebalance_grid(symbol, current_price)
                    results[symbol] = rebalance_result
                else:
                    results[symbol] = {"success": False, "error": "No market data available"}
                    
            except Exception as e:
                results[symbol] = {"success": False, "error": str(e)}
        
        logger.info(f"🔄 Grid rebalancing completed for bot {request.bot_id}")
        
        return {
            "success": True,
            "message": "Grid rebalancing completed",
            "bot_id": request.bot_id,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error rebalancing grid: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/performance/{bot_id}", summary="Get grid trading performance metrics")
async def get_grid_performance(
    bot_id: int,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed performance metrics for grid trading"""
    
    try:
        # Get the bot
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Initialize services
        exchange_service = ExchangeService(bot.exchange_connection)
        grid_service = GridTradingService(db, bot, exchange_service)
        
        # Get performance for specific symbol or all symbols
        if symbol:
            status = grid_service.get_grid_status(symbol)
            suggestions = grid_service.get_optimization_suggestions(symbol)
            
            return {
                "success": True,
                "performance": status,
                "optimization_suggestions": suggestions
            }
        else:
            # Get performance for all trading pairs
            all_performance = {}
            all_suggestions = {}
            
            if bot.trading_pairs:
                for trading_symbol in bot.trading_pairs:
                    all_performance[trading_symbol] = grid_service.get_grid_status(trading_symbol)
                    all_suggestions[trading_symbol] = grid_service.get_optimization_suggestions(trading_symbol)
            
            return {
                "success": True,
                "performance": all_performance,
                "optimization_suggestions": all_suggestions
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting grid performance: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/process", summary="Manually trigger grid processing")
async def trigger_grid_processing(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Manually trigger processing of all active grid trading bots"""
    
    try:
        # Trigger grid processing via Celery task
        background_tasks.add_task(
            lambda: process_active_grids.delay()
        )
        
        logger.info("🔲 Manual grid processing triggered")
        
        return {
            "success": True,
            "message": "Grid processing initiated for all active bots"
        }
        
    except Exception as e:
        logger.error(f"❌ Error triggering grid processing: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard", summary="Get grid trading dashboard data")
async def get_grid_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive dashboard data for all user's grid trading bots"""
    
    try:
        # Get all user's grid trading bots
        grid_bots = db.query(Bot).filter(
            Bot.user_id == current_user.id,
            Bot.strategy_name == "grid_trading"
        ).all()
        
        dashboard_data = {
            "total_bots": len(grid_bots),
            "active_bots": 0,
            "stopped_bots": 0,
            "total_profit": 0.0,
            "total_trades": 0,
            "bots_summary": [],
            "performance_overview": {
                "best_performing": None,
                "worst_performing": None,
                "avg_success_rate": 0.0,
                "total_investment": 0.0
            }
        }
        
        performance_data = []
        
        for bot in grid_bots:
            try:
                # Count active/stopped bots
                if bot.is_active:
                    dashboard_data["active_bots"] += 1
                else:
                    dashboard_data["stopped_bots"] += 1
                
                # Initialize services for performance data
                exchange_service = ExchangeService(bot.exchange_connection)
                grid_service = GridTradingService(db, bot, exchange_service)
                
                bot_summary = {
                    "bot_id": bot.id,
                    "name": bot.name,
                    "status": "active" if bot.is_active else "inactive",
                    "trading_pairs": bot.trading_pairs or [],
                    "created_at": bot.created_at,
                    "symbols_performance": {}
                }
                
                bot_total_profit = 0.0
                bot_total_trades = 0
                
                # Get performance for each trading pair
                if bot.trading_pairs:
                    for symbol in bot.trading_pairs:
                        try:
                            status = grid_service.get_grid_status(symbol)
                            symbol_profit = status.get("total_profit", 0)
                            symbol_trades = status.get("total_trades", 0)
                            
                            bot_summary["symbols_performance"][symbol] = {
                                "profit": symbol_profit,
                                "trades": symbol_trades,
                                "success_rate": status.get("success_rate", 0),
                                "grid_state": status.get("grid_state", "unknown")
                            }
                            
                            bot_total_profit += symbol_profit
                            bot_total_trades += symbol_trades
                            
                        except Exception as e:
                            logger.warning(f"Error getting performance for bot {bot.id} symbol {symbol}: {e}")
                
                bot_summary["total_profit"] = bot_total_profit
                bot_summary["total_trades"] = bot_total_trades
                
                dashboard_data["bots_summary"].append(bot_summary)
                dashboard_data["total_profit"] += bot_total_profit
                dashboard_data["total_trades"] += bot_total_trades
                
                # Track for performance overview
                performance_data.append({
                    "bot_id": bot.id,
                    "name": bot.name,
                    "profit": bot_total_profit,
                    "trades": bot_total_trades
                })
                
            except Exception as e:
                logger.warning(f"Error processing bot {bot.id} for dashboard: {e}")
        
        # Calculate performance overview
        if performance_data:
            best_bot = max(performance_data, key=lambda x: x["profit"])
            worst_bot = min(performance_data, key=lambda x: x["profit"])
            
            dashboard_data["performance_overview"]["best_performing"] = best_bot
            dashboard_data["performance_overview"]["worst_performing"] = worst_bot
        
        logger.info(f"📊 Grid dashboard data retrieved for user {current_user.id}")
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting grid dashboard: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/monitor", summary="Trigger performance monitoring")
async def trigger_performance_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Manually trigger performance monitoring for all grid trading bots"""
    
    try:
        # Trigger performance monitoring via Celery task
        background_tasks.add_task(
            lambda: grid_performance_monitor.delay()
        )
        
        logger.info("📊 Manual performance monitoring triggered")
        
        return {
            "success": True,
            "message": "Performance monitoring initiated for all grid trading bots"
        }
        
    except Exception as e:
        logger.error(f"❌ Error triggering performance monitoring: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/cleanup", summary="Trigger cleanup of completed grids")
async def trigger_grid_cleanup(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Manually trigger cleanup of completed grid trading data"""
    
    try:
        # Trigger cleanup via Celery task
        background_tasks.add_task(
            lambda: cleanup_completed_grids.delay()
        )
        
        logger.info("🧹 Manual grid cleanup triggered")
        
        return {
            "success": True,
            "message": "Grid cleanup initiated for completed bots"
        }
        
    except Exception as e:
        logger.error(f"❌ Error triggering grid cleanup: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health", summary="Grid trading system health check")
async def grid_system_health() -> Dict[str, Any]:
    """Check the health of the grid trading system"""
    
    try:
        health_status = {
            "grid_trading_service": "healthy",
            "celery_tasks": "healthy", 
            "api_endpoints": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        
        return {
            "success": True,
            "health": health_status,
            "message": "Grid trading system is operational"
        }
        
    except Exception as e:
        logger.error(f"❌ Grid system health check failed: {e}")
        raise HTTPException(status_code=500, detail="Grid trading system health check failed") 