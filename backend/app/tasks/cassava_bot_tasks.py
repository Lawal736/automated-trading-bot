"""
Celery tasks for Cassava BOT signal generation and stop loss management
Event-driven scheduling for Cassava strategy BOTs
"""

import asyncio
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd

from app.core.database import SessionLocal
from app.core.celery import celery_app
from app.models.bot import Bot
from app.models.trading import Trade, Position, OrderStatus
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.services.activity_service import ActivityService, ActivityCreate
from app.services.strategy_service import StrategyService, Signal
from app.services.exchange_service import ExchangeService
from app.trading.data_service import data_service
from app.trading.trading_service import trading_service
from app.core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task(name="tasks.process_cassava_bot_signals_and_trades")
def process_cassava_bot_signals_and_trades() -> Dict[str, Any]:
    """
    Daily task at 00:05 UTC to generate signals and execute trades for active Cassava BOTs
    This replaces the continuous while loop with event-driven scheduling
    """
    db = SessionLocal()
    try:
        logger.info("Starting Cassava BOT signal generation and trading task")
        
        # Get all active Cassava BOTs
        active_cassava_bots = db.query(Bot).filter(
            and_(
                Bot.is_active == True,
                Bot.strategy_name == 'cassava_trend_following'
            )
        ).all()
        
        results = {
            'total_bots': len(active_cassava_bots),
            'signals_generated': 0,
            'trades_executed': 0,
            'errors': 0,
            'bot_results': []
        }
        
        for bot in active_cassava_bots:
            try:
                bot_result = _process_single_cassava_bot(db, bot)
                results['bot_results'].append(bot_result)
                results['signals_generated'] += bot_result['signals_generated']
                results['trades_executed'] += bot_result['trades_executed']
                results['errors'] += bot_result['errors']
                
            except Exception as e:
                logger.error(f"Error processing Cassava BOT {bot.id}: {e}")
                results['errors'] += 1
                results['bot_results'].append({
                    'bot_id': bot.id,
                    'bot_name': bot.name,
                    'status': 'error',
                    'error': str(e),
                    'signals_generated': 0,
                    'trades_executed': 0,
                    'errors': 1
                })
        
        logger.info(f"Cassava BOT signal generation completed: {results['signals_generated']} signals, {results['trades_executed']} trades, {results['errors']} errors")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in Cassava BOT signal generation task: {e}")
        return {
            'total_bots': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'errors': 1,
            'bot_results': [{'status': 'error', 'error': str(e)}]
        }
    finally:
        db.close()

def _process_single_cassava_bot(db: Session, bot: Bot) -> Dict[str, Any]:
    """Process signal generation and trading for a single Cassava BOT"""
    bot_result = {
        'bot_id': bot.id,
        'bot_name': bot.name,
        'signals_generated': 0,
        'trades_executed': 0,
        'errors': 0,
        'symbol_results': []
    }
    
    try:
        # Initialize services
        exchange_service = ExchangeService(db)
        strategy_service = StrategyService(
            strategy_name=bot.strategy_name,
            exchange_service=exchange_service,
            strategy_params={
                'ema_fast': 10,
                'ema_slow_buy': 20,
                'ema_slow_sell': 15,
                'ema_exit': 25,
                'short_exit_ema': 5,
                'dmi_length': 14,
                'di_plus_buy': 25,
                'di_plus_short': 16,
            }
        )
        
        # Load exchange connection
        connection = db.query(ExchangeConnection).filter(
            ExchangeConnection.id == bot.exchange_connection_id
        ).first()
        
        if not connection:
            logger.error(f"Exchange connection {bot.exchange_connection_id} not found for bot {bot.id}")
            bot_result['errors'] += 1
            return bot_result
        
        # Process each trading pair
        for pair in bot.trading_pairs.split(','):
            symbol = pair.strip()
            
            try:
                symbol_result = _process_cassava_symbol(db, bot, symbol, strategy_service, connection)
                bot_result['symbol_results'].append(symbol_result)
                bot_result['signals_generated'] += symbol_result['signals_generated']
                bot_result['trades_executed'] += symbol_result['trades_executed']
                bot_result['errors'] += symbol_result['errors']
                
            except Exception as e:
                logger.error(f"Error processing symbol {symbol} for bot {bot.id}: {e}")
                bot_result['errors'] += 1
                bot_result['symbol_results'].append({
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e),
                    'signals_generated': 0,
                    'trades_executed': 0,
                    'errors': 1
                })
    
    except Exception as e:
        logger.error(f"Error in bot {bot.id} processing: {e}")
        bot_result['errors'] += 1
    
    return bot_result

def _process_cassava_symbol(db: Session, bot: Bot, symbol: str, strategy_service: StrategyService, connection: ExchangeConnection) -> Dict[str, Any]:
    """Process signal generation and trading for a single symbol"""
    symbol_result = {
        'symbol': symbol,
        'signals_generated': 0,
        'trades_executed': 0,
        'errors': 0,
        'signal': 'HOLD',
        'action_taken': 'none'
    }
    
    try:
        # Check for new daily candle data (Cassava is hardcoded to daily)
        market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
        
        if market_data.empty or len(market_data) < 50:
            logger.warning(f"Insufficient market data for {symbol}")
            return symbol_result
        
        # Check if we have new candle data since last check
        latest_bar_time = market_data.index[-1] if hasattr(market_data, 'index') else None
        
        # For now, always process since this is daily scheduled task
        # In future, we could store last_processed_candle_time in bot config
        
        # Calculate indicators
        strategy_service._calculate_indicators(market_data)
        
        # Check current position and exit conditions first
        position = db.query(Position).filter_by(bot_id=bot.id, symbol=symbol, is_open=True).first()
        
        if position:
            latest_signal = strategy_service._check_signal(market_data, len(market_data) - 1)
            
            # Check exit conditions
            if position.side == 'buy' and latest_signal.get('exit_long'):
                logger.info(f"Cassava BOT {bot.id}: Exiting LONG position for {symbol} due to EMA25 exit condition")
                _execute_cassava_trade(db, bot, symbol, Signal.SELL, connection)
                symbol_result['signal'] = 'SELL'
                symbol_result['action_taken'] = 'exit_long'
                symbol_result['trades_executed'] += 1
                symbol_result['signals_generated'] += 1
                return symbol_result
                
            elif position.side == 'sell' and latest_signal.get('exit_short'):
                logger.info(f"Cassava BOT {bot.id}: Exiting SHORT position for {symbol} due to EMA8 exit condition")
                _execute_cassava_trade(db, bot, symbol, Signal.BUY, connection)
                symbol_result['signal'] = 'BUY'
                symbol_result['action_taken'] = 'exit_short'
                symbol_result['trades_executed'] += 1
                symbol_result['signals_generated'] += 1
                return symbol_result
        
        # Generate new entry signal
        signal = strategy_service.generate_signal(symbol)
        symbol_result['signal'] = signal.value
        symbol_result['signals_generated'] += 1
        
        # Log signal generation
        user = db.query(User).filter(User.id == bot.user_id).first()
        if user:
            activity_service = ActivityService()
            activity = ActivityCreate(
                type="signal_generated",
                description=f"Cassava BOT '{bot.name}' generated {signal.value} signal for {symbol}",
                amount=None
            )
            activity_service.log_activity(db, user, activity, bot_id=bot.id)
        
        # Execute trade if not HOLD
        if signal != Signal.HOLD:
            # Check position constraints
            if signal == Signal.BUY and position and position.side == 'buy':
                logger.info(f"BUY signal for {symbol}, but already in LONG position. Holding.")
                symbol_result['action_taken'] = 'already_in_position'
                return symbol_result
                
            if signal == Signal.SELL and position and position.side == 'sell':
                logger.info(f"SELL signal for {symbol}, but already in SHORT position. Holding.")
                symbol_result['action_taken'] = 'already_in_position'
                return symbol_result
            
            # Execute the trade
            _execute_cassava_trade(db, bot, symbol, signal, connection)
            symbol_result['trades_executed'] += 1
            symbol_result['action_taken'] = f'executed_{signal.value.lower()}'
        else:
            symbol_result['action_taken'] = 'hold'
    
    except Exception as e:
        logger.error(f"Error processing Cassava symbol {symbol}: {e}")
        symbol_result['errors'] += 1
    
    return symbol_result

def _execute_cassava_trade(db: Session, bot: Bot, symbol: str, signal: Signal, connection: ExchangeConnection):
    """Execute a Cassava trade with proper error handling and logging"""
    try:
        # Import here to avoid circular imports
        from app.tasks.trading_tasks import _execute_trade
        
        # Execute the trade using the existing trade execution logic
        _execute_trade(db, bot, symbol, signal)
        
        logger.info(f"Cassava BOT {bot.id}: Successfully executed {signal.value} trade for {symbol}")
        
    except Exception as e:
        logger.error(f"Error executing Cassava trade for {symbol}: {e}")
        # Log the error to user activity
        user = db.query(User).filter(User.id == bot.user_id).first()
        if user:
            activity_service = ActivityService()
            activity = ActivityCreate(
                type="error",
                description=f"Cassava BOT '{bot.name}': Error executing {signal.value} trade for {symbol}: {e}",
                amount=None
            )
            activity_service.log_activity(db, user, activity, bot_id=bot.id)

@celery_app.task(name="tasks.update_cassava_bot_stop_losses")
def update_cassava_bot_stop_losses() -> Dict[str, Any]:
    """
    Daily task at 00:20 UTC to update EMA25 trailing stop losses for active Cassava BOT trades
    """
    db = SessionLocal()
    try:
        logger.info("Starting Cassava BOT stop loss update task")
        
        # Get all active Cassava BOTs with open positions
        active_cassava_bots = db.query(Bot).filter(
            and_(
                Bot.is_active == True,
                Bot.strategy_name == 'cassava_trend_following'
            )
        ).all()
        
        results = {
            'total_bots': len(active_cassava_bots),
            'positions_checked': 0,
            'stop_losses_updated': 0,
            'errors': 0,
            'bot_results': []
        }
        
        for bot in active_cassava_bots:
            try:
                bot_result = _update_cassava_bot_stop_losses(db, bot)
                results['bot_results'].append(bot_result)
                results['positions_checked'] += bot_result['positions_checked']
                results['stop_losses_updated'] += bot_result['stop_losses_updated']
                results['errors'] += bot_result['errors']
                
            except Exception as e:
                logger.error(f"Error updating stop losses for Cassava BOT {bot.id}: {e}")
                results['errors'] += 1
        
        logger.info(f"Cassava BOT stop loss update completed: {results['positions_checked']} positions checked, {results['stop_losses_updated']} stop losses updated")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in Cassava BOT stop loss update task: {e}")
        return {
            'total_bots': 0,
            'positions_checked': 0,
            'stop_losses_updated': 0,
            'errors': 1,
            'bot_results': [{'status': 'error', 'error': str(e)}]
        }
    finally:
        db.close()

def _update_cassava_bot_stop_losses(db: Session, bot: Bot) -> Dict[str, Any]:
    """Update EMA25 trailing stop losses for a single Cassava BOT"""
    bot_result = {
        'bot_id': bot.id,
        'bot_name': bot.name,
        'positions_checked': 0,
        'stop_losses_updated': 0,
        'errors': 0,
        'position_results': []
    }
    
    try:
        # Get all open LONG positions for this bot (only LONG positions use EMA25 trailing)
        open_positions = db.query(Position).filter(
            and_(
                Position.bot_id == bot.id,
                Position.is_open == True,
                Position.side == 'buy'  # Only LONG positions
            )
        ).all()
        
        bot_result['positions_checked'] = len(open_positions)
        
        # Initialize strategy service for EMA calculation
        strategy_service = StrategyService(
            strategy_name=bot.strategy_name,
            exchange_service=None,
            strategy_params={
                'ema_fast': 10,
                'ema_slow_buy': 20,
                'ema_slow_sell': 15,
                'ema_exit': 25,
                'short_exit_ema': 5,
                'dmi_length': 14,
                'di_plus_buy': 25,
                'di_plus_short': 16,
            }
        )
        
        for position in open_positions:
            try:
                position_result = _update_position_stop_loss(db, bot, position, strategy_service)
                bot_result['position_results'].append(position_result)
                if position_result.get('updated'):
                    bot_result['stop_losses_updated'] += 1
                if position_result.get('error'):
                    bot_result['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Error updating stop loss for position {position.id}: {e}")
                bot_result['errors'] += 1
    
    except Exception as e:
        logger.error(f"Error in stop loss update for bot {bot.id}: {e}")
        bot_result['errors'] += 1
    
    return bot_result

def _update_position_stop_loss(db: Session, bot: Bot, position: Position, strategy_service: StrategyService) -> Dict[str, Any]:
    """Update EMA25 trailing stop loss for a single position"""
    position_result = {
        'position_id': position.id,
        'symbol': position.symbol,
        'updated': False,
        'error': False,
        'old_stop_loss': None,
        'new_stop_loss': None,
        'd1_ema25': None
    }
    
    try:
        symbol = position.symbol
        
        # Get current stop loss from associated trade
        trade = db.query(Trade).filter(
            and_(
                Trade.bot_id == bot.id,
                Trade.symbol == symbol,
                Trade.side == 'buy',
                Trade.status == OrderStatus.FILLED.value
            )
        ).order_by(Trade.created_at.desc()).first()
        
        if not trade or not trade.stop_loss:
            logger.warning(f"No trade with stop loss found for position {position.id}")
            return position_result
        
        current_stop_loss = trade.stop_loss
        position_result['old_stop_loss'] = current_stop_loss
        
        # Get D-1 EMA25 value (yesterday's EMA25)
        market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
        
        if market_data.empty or len(market_data) < 2:
            logger.warning(f"Insufficient market data for {symbol}")
            position_result['error'] = True
            return position_result
        
        # Calculate indicators
        strategy_service._calculate_indicators(market_data)
        
        # Get D-1 EMA25 value (second to last row)
        ema_exit_period = strategy_service.params.get('ema_exit', 25)
        ema_exit_col = f"EMA_{ema_exit_period}"
        
        if ema_exit_col not in market_data.columns:
            logger.warning(f"EMA column {ema_exit_col} not found for {symbol}")
            position_result['error'] = True
            return position_result
        
        d1_ema25 = market_data[ema_exit_col].iloc[-2]  # D-1 EMA25
        position_result['d1_ema25'] = float(d1_ema25)
        
        if pd.isna(d1_ema25):
            logger.warning(f"D-1 EMA25 is NaN for {symbol}")
            position_result['error'] = True
            return position_result
        
        # Implement EMA25 trailing logic: only update if D-1 EMA25 > current stop loss
        if d1_ema25 > current_stop_loss:
            new_stop_loss = d1_ema25
            
            # Update the trade's stop loss
            trade.stop_loss = new_stop_loss
            db.commit()
            
            position_result['new_stop_loss'] = float(new_stop_loss)
            position_result['updated'] = True
            
            # Log the stop loss update
            user = db.query(User).filter(User.id == bot.user_id).first()
            if user:
                activity_service = ActivityService()
                activity = ActivityCreate(
                    type="stop_loss_updated",
                    description=f"Cassava BOT '{bot.name}': EMA25 trailing stop loss updated for {symbol}: {current_stop_loss:.6f} → {new_stop_loss:.6f}",
                    amount=None
                )
                activity_service.log_activity(db, user, activity, bot_id=bot.id)
            
            logger.info(f"Cassava BOT {bot.id}: EMA25 trailing stop loss updated for {symbol}: {current_stop_loss} -> {new_stop_loss} (D-1 EMA25: {d1_ema25})")
        else:
            logger.info(f"Cassava BOT {bot.id}: Stop loss unchanged for {symbol}: {current_stop_loss} (D-1 EMA25: {d1_ema25} <= current stop loss)")
    
    except Exception as e:
        logger.error(f"Error updating stop loss for position {position.id}: {e}")
        position_result['error'] = True
    
    return position_result 