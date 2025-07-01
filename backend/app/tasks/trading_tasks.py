import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal
import pandas as pd

from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import SessionLocal
from app.core.celery import celery_app
from app.models.bot import Bot
from app.models.trading import Trade, Position, OrderStatus
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.services.activity_service import ActivityService, ActivityCreate
from app.services.strategy_service import StrategyService
from app.trading.stop_loss import StopLossManager, StopLossConfig, StopLossType
from app.core.logging import get_logger
from app.core.database import get_db
from app.trading.data_service import data_service
from app.services import activity_service, bot_service
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models.strategy import Strategy
from app.services.exchange_service import ExchangeService
from app.services.strategy_service import Signal
from app.services.activity_service import activity_service
from app.models.trading import Trade, OrderStatus, Position
from app.core.config import settings
from app.trading.trading_service import trading_service
from app.schemas.activity import ActivityCreate
from app.trading.exchanges.factory import ExchangeFactory
from app.trading.exchanges.base import OrderType
from app.services.stop_loss_timeout_handler import create_stop_loss_safe, safe_dynamic_stoploss_update

logger = get_logger(__name__)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Schedule the periodic position sync task
    sender.add_periodic_task(
        settings.POSITION_SYNC_INTERVAL_MINUTES * 60,
        sync_open_positions.s(),
        name='Sync open positions from exchange'
    )

@celery_app.task(name="tasks.manual_sync_positions")
def manual_sync_positions():
    """
    Manual trigger for position sync - useful for testing and immediate updates
    """
    logger.info("Manual position sync triggered")
    return sync_open_positions()

@celery_app.task(name="tasks.sync_open_positions")
def sync_open_positions():
    """
    Periodically sync open positions from the exchange for all users and bots.
    Uses exchange order IDs to check actual order status on the exchange.
    """
    db: Session = SessionLocal()
    try:
        # Get all exchange connections
        connections = db.query(ExchangeConnection).all()
        
        # Group positions by exchange connection
        for connection in connections:
            logger.info(f"Syncing positions for exchange connection: {connection.exchange_name} (ID: {connection.id})")
            
            # Get all open positions for this exchange connection
            db_positions = db.query(Position).filter(
                Position.exchange_connection_id == connection.id,
                Position.is_open == True
            ).all()
            
            if not db_positions:
                logger.info(f"No open positions found for exchange connection {connection.id}")
                continue
                
            logger.info(f"Found {len(db_positions)} open positions to sync for {connection.exchange_name}")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                positions_updated = 0
                positions_closed = 0
                
                # Check each position individually using its exchange order ID
                for db_position in db_positions:
                    if not db_position.exchange_order_id:
                        logger.warning(f"Position {db_position.id} ({db_position.symbol}) has no exchange order ID, skipping")
                        continue
                    
                    try:
                        # Fetch the order status from the exchange
                        order = loop.run_until_complete(
                            trading_service.get_order(connection.id, db_position.exchange_order_id, db_position.symbol)
                        )
                        
                        if order is None:
                            logger.warning(f"Order {db_position.exchange_order_id} for position {db_position.id} not found on exchange or in trade history. Skipping.")
                            continue
                        
                        logger.info(f"Order {db_position.exchange_order_id} status: {order.status}")
                        
                        # Update position based on order status
                        if order.status in ['closed', 'filled', 'canceled']:
                            # Order is closed, so position should be closed
                            db_position.is_open = False
                            db_position.closed_at = datetime.utcnow()
                            db_position.updated_at = datetime.utcnow()
                            positions_closed += 1
                            logger.info(f"Closed position {db_position.id} ({db_position.symbol}) - order status: {order.status}")
                        else:
                            # Order is still open, update position data
                            db_position.quantity = float(order.filled_amount) if order.filled_amount else db_position.quantity
                            db_position.current_price = float(order.price) if order.price else db_position.current_price
                            db_position.updated_at = datetime.utcnow()
                            positions_updated += 1
                            logger.info(f"Updated position {db_position.id} ({db_position.symbol}) - quantity: {db_position.quantity}, price: {db_position.current_price}")
                    
                    except Exception as e:
                        logger.error(f"Error checking order {db_position.exchange_order_id} for position {db_position.id}: {e}")
                        continue
                
                db.commit()
                logger.info(f"Position sync completed for {connection.exchange_name}: {positions_updated} updated, {positions_closed} closed")
                
            except Exception as e:
                logger.error(f"Error syncing positions for exchange {connection.exchange_name}: {e}", exc_info=True)
            finally:
                loop.close()
                
    except Exception as e:
        logger.error(f"Error in sync_open_positions task: {e}", exc_info=True)
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
                        # Determine timeframe from strategy_params or default to '1d' for Cassava
                        strategy_params = getattr(bot, 'strategy_params', {}) or {}
                        timeframe = strategy_params.get('timeframe', '1d')
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
                        market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
                        
                        # Calculate indicators for Cassava strategy
                        strategy_service._calculate_indicators(market_data)
                        
                        # Get the latest signal with stoploss info from Cassava strategy
                        latest_signal = strategy_service._check_signal(market_data, len(market_data) - 1)
                        current_ema25 = latest_signal.get('current_ema25')
                        
                        # Get current stop loss for this symbol
                        current_stoploss = bot._last_stoploss_levels.get(symbol)
                        
                        # Implement EMA25 trailing stop loss logic for long positions
                        if current_ema25 is not None:
                            # Check if we have an existing stop loss (meaning we're in a long position)
                            if current_stoploss is not None:
                                # We're in a long position - implement trailing stop loss logic
                                # Only update if new EMA25 is higher than current stop loss (trailing up only)
                                if current_ema25 > current_stoploss:
                                    # New EMA25 is higher - update stop loss
                                    new_stoploss = current_ema25
                                    log_stoploss_adjustment(db, bot, symbol, new_stoploss)
                                    bot._last_stoploss_levels[symbol] = new_stoploss
                                    logger.info(f"Cassava strategy LONG trailing stop loss for {symbol}: {current_stoploss} -> {new_stoploss} (EMA25: {current_ema25})")
                                else:
                                    # New EMA25 is not higher - keep current stop loss
                                    logger.info(f"Cassava strategy LONG stop loss for {symbol}: keeping current {current_stoploss} (EMA25: {current_ema25} <= current stop loss)")
                            else:
                                # No existing stop loss - this might be a new entry signal
                                # The stop loss will be set when the BUY signal is executed
                                logger.info(f"Cassava strategy for {symbol}: No current stop loss, EMA25: {current_ema25}")
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

            # Use appropriate sleep interval based on strategy timeframe
            if bot.strategy_name == 'cassava_trend_following':
                # For daily timeframe, check every 4 hours (14400 seconds)
                sleep_interval = 14400
            else:
                # Use bot's configured interval for other strategies
                sleep_interval = bot.trade_interval_seconds
                
            time.sleep(sleep_interval)

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
                    trade_type=bot.trade_type,  # CRITICAL FIX: Use bot's trade_type (spot/futures)
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
            logger.info(f"Executing {order_side.value} {bot.trade_type} trade for {amount_to_trade:.4f} {symbol.split('/')[0]} on bot {bot.id}")

            # CRITICAL FIX: Pass trade_type to ensure proper exchange client selection
            order_params = {"trade_type": bot.trade_type} if bot.trade_type == "futures" else None
            
            order_result = loop.run_until_complete(
                trading_service.create_order(
                    connection_id=bot.exchange_connection_id,
                    symbol=symbol,
                    order_type=OrderType.MARKET,
                    side=order_side,
                    amount=Decimal(str(amount_to_trade)),
                    price=None,  # Market order
                    params=order_params  # Pass trade_type for futures
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

                # Create position record for successful bot trade
                try:
                    # Check if position already exists for this order
                    existing_position = db.query(Position).filter(
                        Position.exchange_order_id == str(order_result.id),
                        Position.symbol == symbol,
                        Position.user_id == bot.user_id
                    ).first()
                    
                    if existing_position:
                        logger.warning(f"Position already exists for bot order {order_result.id} - skipping creation")
                    else:
                        # Validate required fields before creating position
                        if not amount_to_trade or amount_to_trade <= 0:
                            raise ValueError(f"Invalid trade amount: {amount_to_trade}")
                        
                        if not order_result.price and not current_price:
                            raise ValueError("No price available for position creation")
                        
                        entry_price = float(order_result.price) if order_result.price else current_price
                        
                        # CRITICAL FIX: Set leverage for futures bots before creating position
                        bot_leverage = bot.leverage or (1 if bot.trade_type == "spot" else 10)
                        
                        if bot.trade_type == "futures":
                            try:
                                # Set leverage on exchange for futures bot
                                exchange = loop.run_until_complete(trading_service.get_exchange_by_connection_id(bot.exchange_connection_id))
                                if exchange:
                                    leverage_set = loop.run_until_complete(exchange.set_leverage(symbol, bot_leverage))
                                    if leverage_set:
                                        logger.info(f"Bot {bot.id}: Leverage set to {bot_leverage}x for futures position on {symbol}")
                                    else:
                                        logger.warning(f"Bot {bot.id}: Failed to set leverage for {symbol}, using exchange default")
                            except Exception as leverage_error:
                                logger.error(f"Bot {bot.id}: Error setting leverage for {symbol}: {leverage_error}")
                                # Don't fail the trade if leverage setting fails
                        
                        position = Position(
                            user_id=bot.user_id,
                            bot_id=bot.id,
                            exchange_connection_id=bot.exchange_connection_id,
                            symbol=symbol,
                            trade_type=bot.trade_type,  # CRITICAL FIX: Use bot's trade_type
                            side=order_side.value,
                            quantity=amount_to_trade,
                            entry_price=entry_price,
                            current_price=entry_price,
                            leverage=bot_leverage,  # CRITICAL FIX: Use bot's leverage setting
                            exchange_order_id=str(order_result.id),  # Store the exchange order ID
                            unrealized_pnl=0.0,  # Will be calculated later
                            realized_pnl=0.0,
                            total_pnl=0.0,
                            is_open=True,
                            opened_at=datetime.utcnow()
                        )
                        
                        db.add(position)
                        db.commit()
                        logger.info(f"Position record created for bot trade: {position.id} with order ID {order_result.id}")

                        # Verify position was created successfully
                        created_position = db.query(Position).filter(
                            Position.id == position.id
                        ).first()
                        
                        if not created_position:
                            raise Exception("Position was not saved to database")
                        
                        # Set initial stop loss for Cassava strategy BUY trades
                        if bot.strategy_name == 'cassava_trend_following' and signal == Signal.BUY:
                            try:
                                # Get D-1 EMA25 value for initial stop loss (consistency with D-1 signal generation)
                                from app.trading.data_service import data_service
                                market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
                                
                                if not market_data.empty and len(market_data) >= 2:
                                    # Calculate indicators
                                    strategy_service._calculate_indicators(market_data)
                                    
                                    # Get D-1 EMA25 value (second to last row for D-1 data)
                                    ema_exit_period = strategy_service.params.get('ema_exit', 25)
                                    ema_exit_col = f"EMA_{ema_exit_period}"
                                    
                                    if ema_exit_col in market_data.columns:
                                        d1_ema25 = market_data[ema_exit_col].iloc[-2]  # D-1 EMA25
                                        if not pd.isna(d1_ema25):
                                            # Set initial stop loss at D-1 EMA25
                                            bot._last_stoploss_levels[symbol] = d1_ema25
                                            logger.info(f"Cassava strategy: Initial stop loss set for {symbol} at D-1 EMA25: {d1_ema25}")
                                            # Log the stop loss setting
                                            log_stoploss_adjustment(db, bot, symbol, d1_ema25)
                                            # Log activity for stop loss setting
                                            if user:
                                                activity = ActivityCreate(
                                                    type="STOP_LOSS_SET",
                                                    description=f"Bot '{bot.name}' set initial D-1 EMA25 stop loss for {symbol} at {d1_ema25}",
                                                    amount=d1_ema25
                                                )
                                                activity_service.log_activity(db, user, activity)
                                            # --- Place stop loss order on exchange using timeout handler ---
                                            # Use the trading_service's exchange instance
                                            exchange = loop.run_until_complete(trading_service.get_exchange_client(connection))
                                            # Define a get_position_func for this bot position
                                            def get_position_func(symbol):
                                                return {'quantity': float(amount_to_trade)}
                                            # Use the safe wrapper for dynamic stop loss update
                                            update_result = loop.run_until_complete(safe_dynamic_stoploss_update(
                                                exchange=exchange,
                                                session=db,
                                                symbol=symbol,
                                                current_stop=0,  # No previous stop for new position
                                                new_ema_stop=d1_ema25,
                                                user_id=bot.user_id,
                                                exchange_conn=connection,
                                                user=user,
                                                activity_service=activity_service,
                                                get_position_func=get_position_func
                                            ))
                                            if update_result.get('success'):
                                                logger.info(f"Cassava bot: Stop loss order created successfully using cancel-and-replace for {symbol}")
                                            else:
                                                logger.warning(f"Cassava bot: Stop loss creation failed for {symbol}: {update_result.get('reason')}")
                            except Exception as sl_error:
                                logger.error(f"Failed to set initial stop loss for Cassava strategy: {sl_error}")
                                # Don't fail the trade if stop loss setting fails
                        
                except Exception as pos_error:
                    logger.error(f"Failed to create position record for bot trade: {pos_error}")
                    logger.error(f"Position creation error details: {type(pos_error).__name__}: {str(pos_error)}")
                    logger.error(f"Bot trade details - Order ID: {order_result.id}, Symbol: {symbol}, Amount: {amount_to_trade}, Price: {order_result.price}")
                    # Don't fail the trade if position creation fails, but log the error for investigation

                # Log successful trade activity
                if user:
                    status_text = "closed" if order_result.status == "closed" else "open"
                    activity = ActivityCreate(
                        type="BOT_TRADE",
                        description=f"Bot '{bot.name}' successfully executed {bot.trade_type} {order_side.value} of {amount_to_trade:.4f} {symbol.split('/')[0]} at market price ({bot_leverage}x leverage). Status: {status_text} (trade id: {pending_trade.id}, order id: {order_result.id})",
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

@celery_app.task(name="tasks.retry_stop_loss_order")
def retry_stop_loss_order(trade_id: int):
    db: Session = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return
        if trade.stop_loss_failed:
            return
        if trade.trade_type != "STOP_LOSS":
            return
        # Allow retry for rejected, open, or pending stop losses
        if trade.status not in [OrderStatus.OPEN.value, OrderStatus.PENDING.value, OrderStatus.REJECTED.value]:
            return
        max_retries = 5
        now = datetime.utcnow()
        retry_count = trade.stop_loss_retry_count or 0
        if retry_count < 3:
            next_interval = timedelta(minutes=5) / 3
        else:
            next_interval = timedelta(minutes=5) / 2
        
        # Actual stop loss placement logic using robust timeout handler
        try:
            conn = db.query(ExchangeConnection).filter(ExchangeConnection.id == trade.exchange_connection_id).first()
            if not conn:
                raise Exception("Exchange connection not found")
            # Get the user
            user = db.query(User).filter(User.id == trade.user_id).first()
            if not user:
                raise Exception("User not found")
            # Find the original trade to get the user's intended stop loss price
            original_trade = db.query(Trade).filter(
                and_(
                    Trade.symbol == trade.symbol,
                    Trade.user_id == trade.user_id,
                    Trade.side == "buy",  # Original trade was a buy
                    Trade.trade_type.in_(["spot", "futures"]),
                    Trade.status == "filled",
                    Trade.created_at < trade.created_at  # Original trade was created before this stop loss
                )
            ).order_by(Trade.created_at.desc()).first()
            if not original_trade:
                logger.error(f"Original trade not found for stop loss trade {trade.id}")
                return
            # Use the user's stored stop loss price from the original trade
            stop_loss_price = original_trade.stop_loss if original_trade.stop_loss else trade.price
            logger.info(f"Using stop loss price: {stop_loss_price} from original trade {original_trade.id}")
            # Get exchange instance
            exchange = asyncio.run(trading_service.get_exchange(conn.exchange_name))
            # Define a get_position_func for this trade
            def get_position_func(symbol):
                return {'quantity': float(trade.quantity)}
            # Use the safe wrapper for dynamic stop loss update
            update_result = asyncio.run(safe_dynamic_stoploss_update(
                exchange=exchange,
                session=db,
                symbol=trade.symbol,
                current_stop=trade.stop_loss,
                new_ema_stop=stop_loss_price,
                user_id=trade.user_id,
                exchange_conn=conn,
                user=user,
                activity_service=activity_service,
                get_position_func=get_position_func
            ))
            if update_result.get('success'):
                trade.stop_loss_retry_count = 0
                trade.stop_loss_last_attempt = now
                trade.status = OrderStatus.OPEN.value
                # Optionally update exchange_order_id if available
                db.commit()
                logger.info(f"Stop loss order created successfully using cancel-and-replace for trade {trade.id}")
            else:
                retry_count += 1
                trade.stop_loss_retry_count = retry_count
                trade.stop_loss_last_attempt = now
                db.commit()
                if retry_count < max_retries:
                    retry_stop_loss_order.apply_async((trade_id,), eta=now + next_interval)
                else:
                    trade.stop_loss_failed = True
                    db.commit()
                    asyncio.run(_close_trade_after_failed_stop_loss(db, trade, user))
                logger.warning(f"Stop loss retry failed for trade {trade.id}: {update_result.get('reason')}")
                return

        except Exception as e:
            retry_count += 1
            trade.stop_loss_retry_count = retry_count
            trade.stop_loss_last_attempt = now
            db.commit()
            if retry_count < max_retries:
                retry_stop_loss_order.apply_async((trade_id,), eta=now + next_interval)
            else:
                trade.stop_loss_failed = True
                db.commit()
                asyncio.run(_close_trade_after_failed_stop_loss(db, trade, user))
    except Exception as outer_e:
        logger.error(f"Error in retry_stop_loss_order for trade {trade_id}: {outer_e}")
    finally:
        db.close()

async def _close_trade_after_failed_stop_loss(db: Session, trade: Trade, user: User):
    """Helper function to close a trade after stop loss retries fail"""
    try:
        conn = db.query(ExchangeConnection).filter(ExchangeConnection.id == trade.exchange_connection_id).first()
        if not conn:
            raise Exception("Exchange connection not found for closing trade")
        exchange_service = ExchangeService(db)
        exchange = asyncio.run(exchange_service.get_exchange_client_for_user(trade.user_id, conn.exchange_name))
        close_order = asyncio.run(exchange.create_order(
            symbol=trade.symbol,
            order_type="market",
            side="sell" if trade.side == "buy" else "buy",
            amount=trade.quantity
        ))
        trade.status = OrderStatus.FILLED.value
        trade.exchange_order_id = str(close_order.id)
        db.commit()
        if user:
            activity_data = ActivityCreate(
                type="STOP_LOSS_CLOSE_TRADE",
                description=f"Closed trade {trade.id} after stop loss failed 5 times (order id: {close_order.id})",
                amount=trade.quantity
            )
            activity_service.log_activity(db, user, activity_data)
    except Exception as close_e:
        logger.error(f"Failed to close trade {trade.id} after stop loss retries: {close_e}")

@celery_app.on_after_configure.connect
def setup_stop_loss_sweep(sender, **kwargs):
    # Add hourly sweep for failed stop loss trades
    sender.add_periodic_task(3600, sweep_and_close_failed_stop_loss_trades.s(), name='Sweep and close failed stop loss trades every hour')
    # Add periodic task to create missing stop losses (every 5 minutes)
    sender.add_periodic_task(300, create_missing_stop_losses.s(), name='Create missing stop losses every 5 minutes')
    # Add daily task to update Cassava trend data (once daily at 00:05 UTC)
    from app.tasks.cassava_data_tasks import update_cassava_trend_data
    sender.add_periodic_task(86400, update_cassava_trend_data.s(), name='Update Cassava trend data daily')

@celery_app.task(name="tasks.sweep_and_close_failed_stop_loss_trades")
def sweep_and_close_failed_stop_loss_trades():
    db: Session = SessionLocal()
    try:
        open_trades = db.query(Trade).filter(
            and_(
                Trade.trade_type == "STOP_LOSS",
                Trade.status.in_([OrderStatus.OPEN.value, OrderStatus.PENDING.value]),
                Trade.stop_loss_failed == True
            )
        ).all()
        for trade in open_trades:
            try:
                conn = db.query(ExchangeConnection).filter(ExchangeConnection.id == trade.exchange_connection_id).first()
                if not conn:
                    continue
                exchange_service = ExchangeService(db)
                exchange = asyncio.run(exchange_service.get_exchange_client_for_user(trade.user_id, conn.exchange_name))
                close_order = asyncio.run(exchange.create_order(
                    symbol=trade.symbol,
                    order_type="market",
                    side="sell" if trade.side == "buy" else "buy",
                    amount=trade.quantity
                ))
                trade.status = OrderStatus.FILLED.value
                trade.exchange_order_id = str(close_order.id)
                db.commit()
                user = db.query(User).filter(User.id == trade.user_id).first()
                if user:
                    activity_data = ActivityCreate(
                        type="STOP_LOSS_SWEEP_CLOSE_TRADE",
                        description=f"Hourly sweep closed trade {trade.id} (order id: {close_order.id})",
                        amount=trade.quantity
                    )
                    activity_service.log_activity(db, user, activity_data)
            except Exception as e:
                logger.error(f"Hourly sweep: Failed to close trade {trade.id}: {e}")
    except Exception as outer_e:
        logger.error(f"Error in sweep_and_close_failed_stop_loss_trades: {outer_e}")
    finally:
        db.close()

@celery_app.task(name="tasks.create_missing_stop_losses")
def create_missing_stop_losses():
    """Create stop loss orders for filled trades that don't have them"""
    import logging
    db: Session = SessionLocal()
    try:
        # Find filled buy trades from the last 24 hours that don't have corresponding stop losses
        yesterday = datetime.utcnow() - timedelta(days=1)
        filled_buy_trades = db.query(Trade).filter(
            and_(
                Trade.side == "buy",
                Trade.status == "filled",
                Trade.trade_type.in_(["spot", "futures"]),
                Trade.created_at > yesterday
            )
        ).all()
        
        logger.info(f"Found {len(filled_buy_trades)} filled buy trades to check for stop losses")
        
        for trade in filled_buy_trades:
            # Check if this trade already has a stop loss
            existing_stop_loss = db.query(Trade).filter(
                and_(
                    Trade.trade_type == "STOP_LOSS",
                    Trade.symbol == trade.symbol,
                    Trade.user_id == trade.user_id,
                    Trade.created_at > trade.created_at
                )
            ).first()
            
            if existing_stop_loss:
                logger.info(f"Trade {trade.id} already has stop loss {existing_stop_loss.id}")
                continue
                
            # Create stop loss order using robust timeout handler
            try:
                conn = db.query(ExchangeConnection).filter(ExchangeConnection.id == trade.exchange_connection_id).first()
                if not conn:
                    logger.error(f"Exchange connection {trade.exchange_connection_id} not found for trade {trade.id}")
                    continue
                
                # Get the user
                user = db.query(User).filter(User.id == trade.user_id).first()
                if not user:
                    logger.error(f"User {trade.user_id} not found for trade {trade.id}")
                    continue
                
                # Use the stop loss price from the user or calculated
                raw_stop_loss_price = getattr(trade, 'stop_loss', None) or trade.executed_price * 0.98
                
                # Create a mock trade order object for the stop loss
                class MockTradeOrder:
                    def __init__(self, symbol, side, amount, stop_loss):
                        self.symbol = symbol
                        self.side = side
                        self.amount = amount
                        self.stop_loss = stop_loss

                # For buy trades, stop loss is always sell
                trade_order = MockTradeOrder(
                    symbol=trade.symbol,
                    side="sell",
                    amount=trade.quantity,
                    stop_loss=raw_stop_loss_price
                )
                
                # Create exchange instance
                exchange = ExchangeFactory.create_exchange(
                    exchange_name=conn.exchange_name,
                    api_key=conn.api_key,
                    api_secret=conn.api_secret,
                    is_testnet=conn.is_testnet
                )
                
                # Use the robust timeout handler to create stop loss order
                stop_loss_order = asyncio.run(create_stop_loss_safe(
                    trade_order, 
                    trade.user_id, 
                    conn, 
                    user, 
                    activity_service, 
                    exchange, 
                    db
                ))
                
                if stop_loss_order:
                    # The timeout handler already created the Trade record
                    logger.info(f"Created stop loss for trade {trade.id} using timeout handler")
                else:
                    logger.error(f"Stop loss creation failed for trade {trade.id}")
                    continue
                
            except Exception as e:
                logger.error(f"Failed to create stop loss for trade {trade.id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error in create_missing_stop_losses: {e}")
    finally:
        db.close()