from app.core.celery import celery_app
from app.core.logging import get_logger
from app.core.database import get_db
from app.models.bot import Bot
from app.models.activity import Activity
from app.trading.stop_loss import StopLossManager, StopLossConfig, StopLossType
from app.trading.data_service import data_service
from app.services import activity_service, bot_service
from sqlalchemy.orm import Session
import time
from datetime import datetime
from typing import Dict, Any
import pandas as pd
from app.models.strategy import Strategy
from app.services.exchange_service import ExchangeService
from app.services.strategy_service import StrategyService, Signal
from app.services.activity_service import activity_service
from decimal import Decimal
from app.models.trading import Trade, OrderStatus, Position
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.exchange import ExchangeConnection
from app.trading.trading_service import trading_service
from app.schemas.activity import ActivityCreate
from app.models.user import User

logger = get_logger(__name__)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Schedule the periodic position sync task
    sender.add_periodic_task(
        settings.POSITION_SYNC_INTERVAL_MINUTES * 60,
        sync_open_positions.s(),
        name='Sync open positions from exchange'
    )

@celery_app.task(name="tasks.sync_open_positions")
def sync_open_positions():
    """
    Periodically sync open positions from the exchange for all users and bots.
    Updates or closes DB records as needed to match the exchange.
    """
    db: Session = SessionLocal()
    try:
        bots = db.query(Bot).filter(Bot.is_active == True).all()
        for bot in bots:
            connection = db.query(ExchangeConnection).filter(ExchangeConnection.id == bot.exchange_connection_id).first()
            if not connection:
                logger.warning(f"No exchange connection for bot {bot.id}")
                continue
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # Fetch open positions from the exchange
                open_positions = loop.run_until_complete(trading_service.get_positions(connection.id))
                # Fetch current DB positions for this bot
                db_positions = db.query(Position).filter_by(bot_id=bot.id, is_open=True).all()
                # Map by symbol for easy comparison
                db_pos_map = {p.symbol: p for p in db_positions}
                ex_pos_map = {p.symbol: p for p in open_positions}
                # Update or create positions
                for symbol, ex_pos in ex_pos_map.items():
                    if symbol in db_pos_map:
                        db_pos = db_pos_map[symbol]
                        db_pos.quantity = float(getattr(ex_pos, 'size', ex_pos.quantity))
                        db_pos.entry_price = float(ex_pos.entry_price)
                        db_pos.current_price = float(getattr(ex_pos, 'mark_price', ex_pos.current_price or 0))
                        db_pos.unrealized_pnl = float(getattr(ex_pos, 'unrealized_pnl', 0))
                        db_pos.leverage = int(getattr(ex_pos, 'leverage', db_pos.leverage or 1))
                        db_pos.updated_at = datetime.utcnow()
                    else:
                        db.add(Position(
                            user_id=bot.user_id,
                            bot_id=bot.id,
                            exchange_connection_id=bot.exchange_connection_id,
                            symbol=ex_pos.symbol,
                            trade_type=ex_pos.trade_type if hasattr(ex_pos, 'trade_type') else 'spot',
                            side=ex_pos.side.value if hasattr(ex_pos.side, 'value') else ex_pos.side,
                            quantity=float(getattr(ex_pos, 'size', ex_pos.quantity)),
                            entry_price=float(ex_pos.entry_price),
                            current_price=float(getattr(ex_pos, 'mark_price', ex_pos.current_price or 0)),
                            leverage=int(getattr(ex_pos, 'leverage', 1)),
                            unrealized_pnl=float(getattr(ex_pos, 'unrealized_pnl', 0)),
                            is_open=True,
                            opened_at=datetime.utcnow(),
                        ))
                # Close positions that are no longer open on the exchange
                for symbol, db_pos in db_pos_map.items():
                    if symbol not in ex_pos_map:
                        db_pos.is_open = False
                        db_pos.closed_at = datetime.utcnow()
                        db_pos.updated_at = datetime.utcnow()
                db.commit()
            finally:
                loop.close()
    except Exception as e:
        logger.error(f"Error syncing open positions: {e}", exc_info=True)
    finally:
        db.close()

@celery_app.task(name="tasks.run_trading_bot_strategy", bind=True)
def run_trading_bot_strategy(self, bot_id: int):
    """
    Celery task to execute a trading strategy for a given bot.
    
    This task runs continuously while the bot is active and implements:
    - Immediate signal search within first minute of startup
    - Continuous trading based on strategy conditions
    - Advanced dynamic stop loss management
    - Risk management and position sizing
    - Automatic stopping when limits are reached
    - Trade logging and activity tracking
    """
    db: Session = next(get_db())
    
    try:
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            logger.error(f"Bot {bot_id} not found.")
            return

        # Initialize services
        exchange_service = ExchangeService(db)
        strategy_service = StrategyService(
            strategy_name=bot.strategy_name,
            exchange_service=exchange_service,
            strategy_params={}
        )

        # Initialize trading service with exchange connections
        from app.trading.trading_service import trading_service
        from app.models.exchange import ExchangeConnection
        
        # Load the exchange connection for this bot
        connection = db.query(ExchangeConnection).filter(
            ExchangeConnection.id == bot.exchange_connection_id
        ).first()
        
        if connection:
            # Add the exchange connection to the trading service
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(trading_service.add_exchange_connection(connection))
                if not success:
                    logger.error(f"Failed to add exchange connection {connection.exchange_name} to trading service")
                    return
                logger.info(f"Successfully added exchange connection {connection.exchange_name} to trading service")
            finally:
                loop.close()
        else:
            logger.error(f"Exchange connection {bot.exchange_connection_id} not found for bot {bot.id}")
            return

        logger.info(f"Starting trading bot '{bot.name}' (ID: {bot.id}) with strategy '{bot.strategy_name}'.")

        # --- IMMEDIATE SIGNAL SEARCH (First minute after startup) ---
        logger.info(f"Performing immediate signal search for bot '{bot.name}' (ID: {bot.id})")
        
        # Track if we've done the initial scan
        initial_scan_completed = False
        
        for pair in bot.trading_pairs.split(','):
            symbol = pair.strip()
            
            try:
                # Generate signal immediately
                signal = strategy_service.generate_signal(symbol)
                
                # Log the signal result
                user = db.query(User).filter(User.id == bot.user_id).first()
                if user:
                    if signal == Signal.HOLD:
                        activity = ActivityCreate(
                            type="signal_generated",
                            description=f"Initial scan: Strategy '{bot.strategy_name}' generated HOLD signal for {symbol}",
                            amount=None
                        )
                    else:
                        activity = ActivityCreate(
                            type="signal_generated",
                            description=f"Initial scan: Strategy '{bot.strategy_name}' generated {signal.value} signal for {symbol}",
                            amount=None
                        )
                    activity_service.log_activity(db, user, activity)
                    logger.info(f"Initial signal scan for {symbol}: {signal.value}")
                
                # If we found a non-HOLD signal, execute it immediately
                if signal != Signal.HOLD:
                    logger.info(f"Executing immediate {signal.value} signal for {symbol} from initial scan")
                    _execute_trade(db, bot, symbol, signal)
                    
            except Exception as e:
                logger.error(f"Error during initial signal scan for {symbol}: {e}")
                user = db.query(User).filter(User.id == bot.user_id).first()
                if user:
                    activity = ActivityCreate(
                        type="error",
                        description=f"Error during initial signal scan for {symbol}: {e}",
                        amount=None
                    )
                    activity_service.log_activity(db, user, activity)
        
        initial_scan_completed = True
        logger.info(f"Initial signal scan completed for bot '{bot.name}' (ID: {bot.id})")

        while True:
            # Refresh bot state from DB
            db.refresh(bot)
            if not bot.is_active:
                logger.info(f"Bot '{bot.name}' (ID: {bot.id}) is no longer active. Stopping task.")
                break

            # --- Main Trading Loop ---
            try:
                # --- Risk Management Checks ---
                # 1. Check daily loss limit
                # NOTE: PnL tracking needs to be properly implemented for this to work.
                # daily_pnl = activity_service.get_daily_pnl(db, bot_id=bot.id)
                # if bot.max_daily_loss and daily_pnl < -abs(bot.max_daily_loss):
                #     logger.warning(f"Bot {bot.id} reached max daily loss. Stopping.")
                #     bot_service.update(db, db_obj=bot, obj_in={'is_active': False})
                #     break

                # 2. Check max trades per day
                # daily_trades = activity_service.get_daily_trade_count(db, bot_id=bot.id)
                # if bot.max_trades_per_day and daily_trades >= bot.max_trades_per_day:
                #     logger.info(f"Bot {bot.id} reached max trades for the day. Pausing until tomorrow.")
                #     time.sleep(3600) # Sleep for an hour before checking again
                #     continue
                
                # TODO: Re-integrate stop-loss management

                # --- Stoploss tracking state ---
                if not hasattr(bot, '_last_stoploss_levels'):
                    bot._last_stoploss_levels = {}

                for pair in bot.trading_pairs.split(','):
                    symbol = pair.strip()
                    
                    # --- Only check signals when a new bar is available (Cassava strategy) ---
                    if bot.strategy_name == 'cassava_trend_following':
                        # Determine timeframe from strategy_params or default to '4h'
                        strategy_params = getattr(bot, 'strategy_params', {}) or {}
                        timeframe = strategy_params.get('timeframe', '4h')
                        market_data = data_service.get_market_data_for_strategy(symbol, timeframe, lookback_periods=100)
                        if market_data.empty:
                            continue
                        latest_bar_time = market_data.index[-1] if hasattr(market_data, 'index') else None
                        if not hasattr(bot, '_last_checked_bar'):
                            bot._last_checked_bar = {}
                        last_checked = bot._last_checked_bar.get(symbol)
                        if last_checked == latest_bar_time:
                            # No new bar, skip signal check
                            continue
                        # Update last checked bar
                        bot._last_checked_bar[symbol] = latest_bar_time
                        strategy_service._calculate_indicators(market_data)
                        
                        # Check current position and exit conditions
                        position = db.query(Position).filter_by(bot_id=bot.id, symbol=symbol, is_open=True).first()
                        if position:
                            latest_signal = strategy_service._check_signal(market_data, len(market_data) - 1)
                            
                            # Execute exit if conditions are met
                            if position.side == 'buy' and latest_signal.get('exit_long'):
                                logger.info(f"Cassava strategy: Exiting LONG position for {symbol} due to EMA25 exit condition")
                                # Execute sell order to close long position
                                _execute_trade(db, bot, symbol, Signal.SELL)
                                continue
                            elif position.side == 'sell' and latest_signal.get('exit_short'):
                                logger.info(f"Cassava strategy: Exiting SHORT position for {symbol} due to EMA8 exit condition")
                                # Execute buy order to close short position
                                _execute_trade(db, bot, symbol, Signal.BUY)
                                continue
                    
                    signal = strategy_service.generate_signal(symbol)

                    # --- Stoploss adjustment logging ---
                    # For Cassava strategy, use its internal stoploss logic instead of generic bot stoploss
                    if bot.strategy_name == 'cassava_trend_following':
                        # Fetch market data for Cassava strategy stoploss calculation
                        market_data = data_service.get_market_data_for_strategy(symbol, '4h', lookback_periods=100)
                        
                        # Calculate indicators for Cassava strategy
                        strategy_service._calculate_indicators(market_data)
                        
                        # Get the latest signal with stoploss info from Cassava strategy
                        latest_signal = strategy_service._check_signal(market_data, len(market_data) - 1)
                        new_stoploss = latest_signal.get('stop_loss_price')
                        
                        if new_stoploss is not None:
                            last_stoploss = bot._last_stoploss_levels.get(symbol)
                            if new_stoploss != last_stoploss:
                                log_stoploss_adjustment(db, bot, symbol, new_stoploss)
                                bot._last_stoploss_levels[symbol] = new_stoploss
                                logger.info(f"Cassava strategy stoploss for {symbol}: {new_stoploss}")
                    else:
                        # Use generic bot stoploss for other strategies
                        # Fetch market data for stoploss calculation
                        market_data = data_service.get_market_data_for_strategy(symbol, bot.stop_loss_timeframe or '4h', lookback_periods=100)
                        # Assume bot.stop_loss_config is available and is a StopLossConfig
                        stop_loss_config = StopLossConfig(
                            stop_loss_type=StopLossType.FIXED_PERCENTAGE,  # Default, replace with actual config if available
                            percentage=getattr(bot, 'stop_loss_percent', 5.0)
                        )
                        stop_loss = DynamicStopLoss(stop_loss_config)
                        # For a real implementation, set position details from DB/position
                        # Here, we assume entry_price and side are available (mocked for now)
                        # You may want to fetch the actual open position for this symbol
                        position = db.query(Position).filter_by(bot_id=bot.id, symbol=symbol, is_open=True).first()
                        if position:
                            stop_loss.set_position(entry_price=position.entry_price, side=position.side, entry_time=position.opened_at)
                            new_stoploss = stop_loss.calculate_stop_loss(market_data)
                            last_stoploss = bot._last_stoploss_levels.get(symbol)
                            if new_stoploss is not None and new_stoploss != last_stoploss:
                                log_stoploss_adjustment(db, bot, symbol, new_stoploss)
                                bot._last_stoploss_levels[symbol] = new_stoploss

                    user = db.query(User).filter(User.id == bot.user_id).first()
                    activity = ActivityCreate(
                        type="signal_generated",
                        description=f"Strategy '{bot.strategy_name}' generated signal: {signal.value} for {symbol}",
                        amount=None
                    )
                    activity_service.log_activity(db, user, activity)

                    if signal != Signal.HOLD:
                        # Basic position check to avoid repeat actions
                        # Get the exchange name from the connection
                        connection = db.query(ExchangeConnection).filter(
                            ExchangeConnection.id == bot.exchange_connection_id
                        ).first()
                        
                        if connection:
                            import asyncio
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Get balance for the specific asset
                                balances = loop.run_until_complete(
                                    trading_service.get_balance(connection.exchange_name, symbol.split('/')[0])
                                )
                                
                                current_position = 0
                                if balances:
                                    # Find the balance for the specific asset
                                    for balance in balances:
                                        if balance.currency == symbol.split('/')[0]:
                                            current_position = float(balance.total)
                                            break
                                
                                if signal == Signal.BUY and current_position > 0:
                                    logger.info(f"BUY signal for {symbol}, but already in position. Holding.")
                                    continue
                                if signal == Signal.SELL and current_position == 0:
                                    logger.info(f"SELL signal for {symbol}, but no position to sell. Holding.")
                                    continue
                                    
                            finally:
                                loop.close()
                        else:
                            logger.error(f"Exchange connection {bot.exchange_connection_id} not found for bot {bot.id}")
                            continue

                        _execute_trade(db, bot, symbol, signal)

            except Exception as e:
                logger.error(f"Error in trading loop for bot {bot.id}: {e}", exc_info=True)
                user = db.query(User).filter(User.id == bot.user_id).first()
                activity = ActivityCreate(
                    type="error",
                    description=f"An error occurred in the trading loop: {e}",
                    amount=None
                )
                activity_service.log_activity(db, user, activity)

            time.sleep(bot.trade_interval_seconds)

    except Exception as e:
        logger.error(f"Fatal error in trading task for bot {bot_id}: {e}", exc_info=True)
        # Ensure bot is marked as inactive on fatal error
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if bot:
            bot.is_active = False
            db.commit()
    finally:
        db.close()

def _execute_trade(db: Session, bot: Bot, symbol: str, signal: Signal):
    """Calculates position size and executes a trade with Database First → Exchange → Update Database flow."""
    try:
        # Import the trading service
        from app.trading.trading_service import trading_service
        from app.trading.exchanges.base import OrderType, OrderSide
        
        # 1. Calculate position size
        # For now, we'll use a simple approach since we need to get balance from the exchange
        # In a real implementation, you'd want to get the actual balance from the exchange
        account_balance = bot.current_balance or 1000  # Default fallback
        position_size_usd = account_balance * (bot.max_position_size_percent / 100)
        
        # Get current price from the exchange
        # We need to get the exchange connection details first
        from app.models.exchange import ExchangeConnection
        connection = db.query(ExchangeConnection).filter(
            ExchangeConnection.id == bot.exchange_connection_id
        ).first()
        
        if not connection:
            logger.error(f"Exchange connection {bot.exchange_connection_id} not found for bot {bot.id}")
            return
            
        # Get current price using the trading service
        import asyncio
        try:
            # Create a simple event loop for this sync function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get ticker to get current price
            ticker = loop.run_until_complete(
                trading_service.get_ticker(symbol, connection.exchange_name)
            )
            
            if not ticker or not ticker.last_price:
                logger.error(f"Could not fetch current price for {symbol}. Skipping trade.")
                return
                
            current_price = float(ticker.last_price)
            amount_to_trade = position_size_usd / current_price

            # STEP 1: Create pending trade record in database FIRST
            order_side = OrderSide.BUY if signal == Signal.BUY else OrderSide.SELL
            
            try:
                pending_trade = Trade(
                    user_id=bot.user_id,
                    bot_id=bot.id,
                    exchange_connection_id=bot.exchange_connection_id,
                    symbol=symbol,
                    trade_type="spot",  # Assuming spot trading for now
                    order_type=OrderType.MARKET.value,
                    side=order_side.value,
                    quantity=amount_to_trade,
                    price=current_price,
                    executed_price=0.0,  # Will be updated after exchange execution
                    status=OrderStatus.PENDING.value,
                    exchange_order_id=None,  # Will be updated after exchange execution
                    executed_at=None  # Will be updated after exchange execution
                )
                
                db.add(pending_trade)
                db.commit()
                db.refresh(pending_trade)
                logger.info(f"Pending bot trade record created in database: {pending_trade.id}")
                
                # Log activity for pending trade
                user = db.query(User).filter(User.id == bot.user_id).first()
                if user:
                    activity = ActivityCreate(
                        type="BOT_TRADE_PENDING",
                        description=f"Bot '{bot.name}' generated {signal.value} signal for {amount_to_trade:.4f} {symbol.split('/')[0]} at market price. Status: PENDING (trade id: {pending_trade.id})",
                        amount=amount_to_trade
                    )
                    activity_service.log_activity(db, user, activity)
                    logger.info(f"Activity logged for pending bot trade: {pending_trade.id}")
                
            except Exception as db_error:
                logger.error(f"Failed to create pending bot trade record in database: {db_error}")
                raise Exception(f"Failed to log bot trade in system: {db_error}")

            # STEP 2: Execute trade on exchange
            logger.info(f"Executing {order_side.value} trade for {amount_to_trade:.4f} {symbol.split('/')[0]} on bot {bot.id}")

            order_result = loop.run_until_complete(
                trading_service.create_order(
                    connection_id=bot.exchange_connection_id,
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    side=order_side,
                    amount=Decimal(str(amount_to_trade)),
                    price=None  # Market order
                )
            )

            if not order_result:
                # Update database with failed status
                pending_trade.status = OrderStatus.REJECTED.value
                db.commit()
                
                error_message = f"Failed to create order for bot {bot.id} on {symbol}"
                logger.error(error_message)
                
                # Log failed trade activity
                if user:
                    activity = ActivityCreate(
                        type="BOT_TRADE_FAILED",
                        description=f"Bot '{bot.name}' failed to execute {signal.value} trade for {symbol}. Order creation failed. (trade id: {pending_trade.id})",
                        amount=amount_to_trade
                    )
                    activity_service.log_activity(db, user, activity)
                
                return

            # STEP 3: Update database with successful execution
            try:
                # Update main trade record
                pending_trade.status = OrderStatus.FILLED.value if order_result.status == "closed" else OrderStatus.OPEN.value
                pending_trade.executed_price = float(order_result.price) if order_result.price else current_price
                pending_trade.exchange_order_id = str(order_result.id)
                pending_trade.executed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Bot trade record updated in database: {pending_trade.id}")

                # Log successful trade activity
                if user:
                    status_text = "closed" if order_result.status == "closed" else "open"
                    activity = ActivityCreate(
                        type="BOT_TRADE",
                        description=f"Bot '{bot.name}' successfully executed {order_side.value} of {amount_to_trade:.4f} {symbol.split('/')[0]} at market price. Status: {status_text} (trade id: {pending_trade.id}, order id: {order_result.id})",
                        amount=amount_to_trade
                    )
                    activity_service.log_activity(db, user, activity)
                    logger.info(f"Activity logged for successful bot trade: {pending_trade.id}")

            except Exception as update_error:
                logger.error(f"Failed to update bot trade record in database: {update_error}")
                # Don't fail the entire operation if database update fails
                # The trade was successful on exchange, we just couldn't update our records

            # Update bot's current balance (simplified)
            bot.current_balance = account_balance
            db.commit()
            
            logger.info(f"Bot trade executed successfully: {order_result.id}")
            
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to execute trade for bot {bot.id} on {symbol}: {e}", exc_info=True)
        
        # Try to update database with failed status if we have a pending trade
        try:
            if 'pending_trade' in locals():
                pending_trade.status = OrderStatus.REJECTED.value
                db.commit()
                
                # Log failed trade activity
                user = db.query(User).filter(User.id == bot.user_id).first()
                if user:
                    activity = ActivityCreate(
                        type="BOT_TRADE_FAILED",
                        description=f"Bot '{bot.name}' failed to execute {signal.value} trade for {symbol}. Error: {e} (trade id: {pending_trade.id})",
                        amount=None
                    )
                    activity_service.log_activity(db, user, activity)
        except Exception as update_error:
            logger.error(f"Failed to update failed bot trade record: {update_error}")
        
        # Also log the general error
        user = db.query(User).filter(User.id == bot.user_id).first()
        if user:
            activity = ActivityCreate(
                type="error",
                description=f"Bot '{bot.name}' failed to execute {signal.value} trade for {symbol}: {e}",
                amount=None
            )
            activity_service.log_activity(db, user, activity)

def _execute_strategy(bot: Bot, market_data: pd.DataFrame, current_price: float, stop_loss_manager: StopLossManager) -> Dict[str, Any]:
    """Execute the trading strategy and return signals"""
    try:
        # Get latest market data
        latest_data = market_data.tail(20)  # Last 20 periods
        
        # Calculate basic indicators
        sma_20 = latest_data['close'].rolling(window=20).mean().iloc[-1]
        sma_50 = latest_data['close'].rolling(window=50).mean().iloc[-1]
        rsi = latest_data['rsi'].iloc[-1] if 'rsi' in latest_data.columns else 50
        
        # Simple strategy logic (can be enhanced)
        should_trade = False
        trade_type = None
        trade_size = 0
        
        if bot.strategy_name == "simple_strategy":
            # Simple moving average crossover strategy
            if sma_20 > sma_50 and rsi < 70:  # Bullish signal
                should_trade = True
                trade_type = "long"
            elif sma_20 < sma_50 and rsi > 30:  # Bearish signal
                should_trade = True
                trade_type = "short"
            
            if should_trade:
                # Calculate position size based on bot's risk settings
                trade_size = min(bot.current_balance * (bot.max_position_size_percent / 100), 100)
        
        return {
            "should_trade": should_trade,
            "trade_type": trade_type,
            "trade_size": trade_size,
            "indicators": {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "rsi": rsi,
                "current_price": current_price
            }
        }
        
    except Exception as e:
        logger.error(f"Error executing strategy: {e}")
        return {"should_trade": False, "error": str(e)}

def _execute_stop_loss(db: Session, bot: Bot, current_price: float, stop_loss_results: Dict[str, Any]) -> Dict[str, Any]:
    """Execute stop loss order"""
    try:
        # Simulate stop loss execution
        logger.info(f"Executing stop loss for bot {bot.id} at price {current_price}")
        
        # Update bot status (stop trading)
        bot.is_active = False
        db.commit()
        
        return {
            "success": True,
            "stop_loss_triggered": True,
            "price": current_price,
            "stop_loss_info": stop_loss_results
        }
        
    except Exception as e:
        logger.error(f"Error executing stop loss: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

def _log_activity(db: Session, bot: Bot, activity_type: str, details: Dict[str, Any]):
    """Log trading activity"""
    try:
        description = f"{activity_type.replace('_', ' ').title()}: {details}"
        
        activity = Activity(
            user_id=bot.user_id,
            bot_id=bot.id,
            type=activity_type,
            description=description,
            pnl=details.get('pnl'),
            amount=details.get('size')
        )
        
        db.add(activity)
        db.commit()
    except Exception as e:
        logger.error(f"Error logging activity for bot {bot.id}: {e}")
        db.rollback()

def log_stoploss_adjustment(db, bot, symbol, new_stoploss):
    user = db.query(User).filter(User.id == bot.user_id).first()
    activity = ActivityCreate(
        type="stoploss_adjusted",
        description=f"Stoploss for {symbol} adjusted to {new_stoploss}",
        amount=new_stoploss
    )
    activity_service.log_activity(db, user, activity) 