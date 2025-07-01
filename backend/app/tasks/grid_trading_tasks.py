"""
Grid Trading Strategy Celery Tasks
Automated execution and management of grid trading strategies
"""

from celery import Celery
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.celery import celery_app
from app.models.bot import Bot
from app.models.trading import Trade
from app.services.grid_trading_service import GridTradingService, GridState
from app.services.exchange_service import ExchangeService
from app.core.logging import get_logger
from typing import Dict, Any, List
import traceback
from datetime import datetime, timedelta

logger = get_logger(__name__)

@celery_app.task(bind=True, name="grid_trading.process_active_grids")
def process_active_grids(self) -> Dict[str, Any]:
    """
    Process all active grid trading bots
    Runs every 1 minute to check for filled orders and manage grid levels
    """
    logger.info("🔲 Processing active grid trading bots...")
    
    results = {
        "processed_bots": 0,
        "successful_operations": 0,
        "errors": [],
        "summary": {}
    }
    
    try:
        db = next(get_db())
        
        # Get all active grid trading bots
        active_bots = db.query(Bot).filter(
            Bot.is_active == True,
            Bot.strategy_name == "grid_trading"
        ).all()
        
        logger.info(f"Found {len(active_bots)} active grid trading bots")
        
        for bot in active_bots:
            try:
                # Initialize services
                exchange_service = ExchangeService(bot.exchange_connection)
                grid_service = GridTradingService(db, bot, exchange_service)
                
                # Process grid for each trading pair
                if bot.trading_pairs:
                    for symbol in bot.trading_pairs:
                        result = grid_service.process_grid_orders(symbol)
                        
                        if result.get("success"):
                            results["successful_operations"] += 1
                            results["summary"][f"{bot.id}_{symbol}"] = {
                                "orders_processed": result.get("orders_processed", 0),
                                "profit_realized": result.get("profit_realized", 0),
                                "grid_state": result.get("grid_state", "unknown")
                            }
                        else:
                            error_msg = f"Bot {bot.id} ({symbol}): {result.get('error', 'Unknown error')}"
                            results["errors"].append(error_msg)
                            logger.error(error_msg)
                
                results["processed_bots"] += 1
                
            except Exception as e:
                error_msg = f"Error processing bot {bot.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        logger.info(f"✅ Grid processing complete: {results['successful_operations']} operations, {len(results['errors'])} errors")
        
    except Exception as e:
        error_msg = f"Critical error in process_active_grids: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return results

@celery_app.task(bind=True, name="grid_trading.initialize_new_grids")
def initialize_new_grids(self) -> Dict[str, Any]:
    """
    Initialize grid trading for newly created bots
    Runs every 5 minutes to check for bots that need grid setup
    """
    logger.info("🔲 Initializing new grid trading bots...")
    
    results = {
        "initialized_bots": 0,
        "successful_initializations": 0,
        "errors": [],
        "summary": {}
    }
    
    try:
        db = next(get_db())
        
        # Get grid trading bots that are active but haven't been initialized
        new_bots = db.query(Bot).filter(
            Bot.is_active == True,
            Bot.strategy_name == "grid_trading",
            Bot.created_at >= datetime.utcnow() - timedelta(minutes=10)  # Recently created
        ).all()
        
        for bot in new_bots:
            try:
                # Check if grid is already initialized (has recent trades)
                recent_trades = db.query(Trade).filter(
                    Trade.bot_id == bot.id,
                    Trade.created_at >= datetime.utcnow() - timedelta(minutes=5)
                ).count()
                
                if recent_trades > 0:
                    continue  # Already initialized
                
                # Initialize services
                exchange_service = ExchangeService(bot.exchange_connection)
                grid_service = GridTradingService(db, bot, exchange_service)
                
                # Initialize grid for each trading pair
                if bot.trading_pairs:
                    for symbol in bot.trading_pairs:
                        result = grid_service.initialize_grid(symbol)
                        
                        if result.get("success"):
                            results["successful_initializations"] += 1
                            results["summary"][f"{bot.id}_{symbol}"] = {
                                "grid_levels": result.get("grid_levels", 0),
                                "base_price": result.get("base_price", 0),
                                "orders_created": result.get("orders_created", 0)
                            }
                            logger.info(f"✅ Grid initialized for bot {bot.id} on {symbol}")
                        else:
                            error_msg = f"Failed to initialize grid for bot {bot.id} ({symbol}): {result.get('error')}"
                            results["errors"].append(error_msg)
                            logger.error(error_msg)
                
                results["initialized_bots"] += 1
                
            except Exception as e:
                error_msg = f"Error initializing bot {bot.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        logger.info(f"✅ Grid initialization complete: {results['successful_initializations']} grids initialized")
        
    except Exception as e:
        error_msg = f"Critical error in initialize_new_grids: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return results

@celery_app.task(bind=True, name="grid_trading.grid_rebalancing")
def grid_rebalancing(self) -> Dict[str, Any]:
    """
    Check and perform grid rebalancing when market conditions change significantly
    Runs every 15 minutes to assess rebalancing needs
    """
    logger.info("🔲 Checking grid rebalancing requirements...")
    
    results = {
        "checked_bots": 0,
        "rebalanced_grids": 0,
        "errors": [],
        "summary": {}
    }
    
    try:
        db = next(get_db())
        
        # Get all active grid trading bots
        active_bots = db.query(Bot).filter(
            Bot.is_active == True,
            Bot.strategy_name == "grid_trading"
        ).all()
        
        for bot in active_bots:
            try:
                # Initialize services
                exchange_service = ExchangeService(bot.exchange_connection)
                grid_service = GridTradingService(db, bot, exchange_service)
                
                # Check rebalancing for each trading pair
                if bot.trading_pairs:
                    for symbol in bot.trading_pairs:
                        # Get grid status to check if rebalancing is needed
                        status = grid_service.get_grid_status(symbol)
                        
                        if status.get("needs_rebalancing", False):
                            logger.info(f"🔄 Rebalancing needed for bot {bot.id} on {symbol}")
                            
                            # Get current market data and perform rebalancing
                            market_data = grid_service._get_market_data(symbol)
                            if not market_data.empty:
                                current_price = market_data['close'].iloc[-1]
                                rebalance_result = grid_service._rebalance_grid(symbol, current_price)
                                
                                if rebalance_result.get("success"):
                                    results["rebalanced_grids"] += 1
                                    results["summary"][f"{bot.id}_{symbol}"] = {
                                        "old_levels": rebalance_result.get("old_levels", 0),
                                        "new_levels": rebalance_result.get("new_levels", 0),
                                        "price_change": rebalance_result.get("price_change_percent", 0)
                                    }
                                    logger.info(f"✅ Grid rebalanced for bot {bot.id} on {symbol}")
                                else:
                                    error_msg = f"Failed to rebalance grid for bot {bot.id} ({symbol}): {rebalance_result.get('error')}"
                                    results["errors"].append(error_msg)
                
                results["checked_bots"] += 1
                
            except Exception as e:
                error_msg = f"Error checking rebalancing for bot {bot.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        logger.info(f"✅ Grid rebalancing check complete: {results['rebalanced_grids']} grids rebalanced")
        
    except Exception as e:
        error_msg = f"Critical error in grid_rebalancing: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return results

@celery_app.task(bind=True, name="grid_trading.grid_performance_monitor")
def grid_performance_monitor(self) -> Dict[str, Any]:
    """
    Monitor grid trading performance and generate optimization suggestions
    Runs every hour to analyze performance and suggest improvements
    """
    logger.info("📊 Monitoring grid trading performance...")
    
    results = {
        "monitored_bots": 0,
        "performance_reports": {},
        "optimization_suggestions": {},
        "errors": []
    }
    
    try:
        db = next(get_db())
        
        # Get all active grid trading bots
        active_bots = db.query(Bot).filter(
            Bot.is_active == True,
            Bot.strategy_name == "grid_trading"
        ).all()
        
        for bot in active_bots:
            try:
                # Initialize services
                exchange_service = ExchangeService(bot.exchange_connection)
                grid_service = GridTradingService(db, bot, exchange_service)
                
                # Generate performance report for each trading pair
                if bot.trading_pairs:
                    for symbol in bot.trading_pairs:
                        # Get comprehensive grid status
                        status = grid_service.get_grid_status(symbol)
                        
                        # Get optimization suggestions
                        suggestions = grid_service.get_optimization_suggestions(symbol)
                        
                        results["performance_reports"][f"{bot.id}_{symbol}"] = {
                            "total_profit": status.get("total_profit", 0),
                            "total_trades": status.get("total_trades", 0),
                            "success_rate": status.get("success_rate", 0),
                            "avg_profit_per_trade": status.get("avg_profit_per_trade", 0),
                            "grid_efficiency": status.get("grid_efficiency", 0),
                            "current_drawdown": status.get("current_drawdown", 0)
                        }
                        
                        results["optimization_suggestions"][f"{bot.id}_{symbol}"] = suggestions
                        
                        # Log performance metrics
                        logger.info(f"📈 Bot {bot.id} ({symbol}) - Profit: ${status.get('total_profit', 0):.2f}, "
                                  f"Trades: {status.get('total_trades', 0)}, "
                                  f"Success Rate: {status.get('success_rate', 0):.1f}%")
                
                results["monitored_bots"] += 1
                
            except Exception as e:
                error_msg = f"Error monitoring bot {bot.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        logger.info(f"✅ Performance monitoring complete: {results['monitored_bots']} bots analyzed")
        
    except Exception as e:
        error_msg = f"Critical error in grid_performance_monitor: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return results

@celery_app.task(bind=True, name="grid_trading.emergency_grid_stop")
def emergency_grid_stop(self, bot_id: int, reason: str = "Emergency stop") -> Dict[str, Any]:
    """
    Emergency stop for a specific grid trading bot
    Can be triggered manually or by risk management systems
    """
    logger.warning(f"🚨 Emergency stop triggered for bot {bot_id}: {reason}")
    
    result = {
        "bot_id": bot_id,
        "stopped": False,
        "reason": reason,
        "orders_cancelled": 0,
        "positions_closed": 0,
        "error": None
    }
    
    try:
        db = next(get_db())
        
        # Get the bot
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            result["error"] = f"Bot {bot_id} not found"
            return result
        
        # Initialize services
        exchange_service = ExchangeService(bot.exchange_connection)
        grid_service = GridTradingService(db, bot, exchange_service)
        
        # Stop grid for each trading pair
        if bot.trading_pairs:
            for symbol in bot.trading_pairs:
                stop_result = grid_service._stop_grid(symbol, reason)
                
                if stop_result.get("success"):
                    result["orders_cancelled"] += stop_result.get("orders_cancelled", 0)
                    result["positions_closed"] += stop_result.get("positions_closed", 0)
        
        # Update bot status
        bot.is_active = False
        db.commit()
        
        result["stopped"] = True
        logger.info(f"✅ Emergency stop completed for bot {bot_id}")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ Error in emergency stop for bot {bot_id}: {e}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return result

@celery_app.task(bind=True, name="grid_trading.cleanup_completed_grids")
def cleanup_completed_grids(self) -> Dict[str, Any]:
    """
    Clean up data for completed/stopped grid trading bots
    Runs daily to maintain database performance
    """
    logger.info("🧹 Cleaning up completed grid trading data...")
    
    results = {
        "cleaned_bots": 0,
        "cleaned_trades": 0,
        "errors": []
    }
    
    try:
        db = next(get_db())
        
        # Get completed/stopped grid trading bots older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        completed_bots = db.query(Bot).filter(
            Bot.strategy_name == "grid_trading",
            Bot.is_active == False,
            Bot.updated_at <= cutoff_date
        ).all()
        
        for bot in completed_bots:
            try:
                # Archive old trades (move to archive table or delete if needed)
                old_trades = db.query(Trade).filter(
                    Trade.bot_id == bot.id,
                    Trade.created_at <= cutoff_date
                ).count()
                
                # For now, we'll just log the cleanup opportunity
                # In production, you might want to archive to a separate table
                logger.info(f"Bot {bot.id} has {old_trades} old trades ready for cleanup")
                
                results["cleaned_bots"] += 1
                results["cleaned_trades"] += old_trades
                
            except Exception as e:
                error_msg = f"Error cleaning up bot {bot.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"✅ Cleanup complete: {results['cleaned_bots']} bots processed")
        
    except Exception as e:
        error_msg = f"Critical error in cleanup_completed_grids: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
    finally:
        if 'db' in locals():
            db.close()
    
    return results 