"""
Advanced Stop Loss Celery Tasks
Automated tasks for advanced dynamic stop loss management
"""

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any
from datetime import datetime, timedelta
import asyncio

from app.core.database import SessionLocal
from app.core.celery import celery_app
from app.models.trading import Position, Trade, OrderStatus
from app.models.bot import Bot
from app.services.advanced_stop_loss_service import AdvancedStopLossService
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="tasks.update_advanced_stop_losses")
def update_advanced_stop_losses() -> Dict[str, Any]:
    """
    Scheduled task to update advanced stop losses for all positions
    """
    db = SessionLocal()
    try:
        logger.info("Starting advanced stop loss update task")
        
        service = AdvancedStopLossService(db)
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(service.update_advanced_stop_losses())
        
        loop.close()
        
        logger.info(f"Advanced stop loss update completed: {results['updated_positions']} positions updated, {results['errors']} errors")
        
        return {
            'success': True,
            'timestamp': datetime.utcnow(),
            'total_positions': results['total_positions'],
            'updated_positions': results['updated_positions'],
            'errors': results['errors'],
            'details': results['position_results']
        }
        
    except Exception as e:
        logger.error(f"Error in advanced stop loss update task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow(),
            'total_positions': 0,
            'updated_positions': 0,
            'errors': 1
        }
    finally:
        db.close()


@celery_app.task(name="tasks.update_bot_advanced_stop_losses")
def update_bot_advanced_stop_losses(bot_id: int) -> Dict[str, Any]:
    """
    Update advanced stop losses for a specific bot
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting advanced stop loss update for bot {bot_id}")
        
        # Get bot
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return {
                'success': False,
                'error': f'Bot {bot_id} not found',
                'bot_id': bot_id
            }
        
        # Get open positions for this bot with advanced stop loss types
        advanced_stop_types = [
            'adaptive_atr', 'volatility_based', 'fibonacci_retracement',
            'supertrend', 'parabolic_sar', 'bollinger_band',
            'risk_reward_ratio', 'time_decay', 'momentum_divergence'
        ]
        
        if bot.stop_loss_type not in advanced_stop_types:
            return {
                'success': False,
                'error': f'Bot {bot_id} does not use advanced stop loss type',
                'bot_id': bot_id,
                'stop_loss_type': bot.stop_loss_type
            }
        
        positions = db.query(Position).join(Trade).filter(
            and_(
                Trade.bot_id == bot_id,
                Position.is_open == True
            )
        ).all()
        
        service = AdvancedStopLossService(db)
        
        results = {
            'bot_id': bot_id,
            'bot_name': bot.name,
            'stop_loss_type': bot.stop_loss_type,
            'total_positions': len(positions),
            'updated_positions': 0,
            'errors': 0,
            'position_results': []
        }
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for position in positions:
            try:
                position_result = loop.run_until_complete(
                    service._update_position_advanced_stop_loss(position)
                )
                results['position_results'].append(position_result)
                
                if position_result.get('updated'):
                    results['updated_positions'] += 1
                if position_result.get('error'):
                    results['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Error updating position {position.id}: {e}")
                results['errors'] += 1
                results['position_results'].append({
                    'position_id': position.id,
                    'error': True,
                    'reason': str(e)
                })
        
        loop.close()
        
        logger.info(f"Advanced stop loss update completed for bot {bot_id}: {results['updated_positions']} updated, {results['errors']} errors")
        
        return {
            'success': True,
            'timestamp': datetime.utcnow(),
            **results
        }
        
    except Exception as e:
        logger.error(f"Error updating advanced stop losses for bot {bot_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'bot_id': bot_id,
            'timestamp': datetime.utcnow()
        }
    finally:
        db.close()


@celery_app.task(name="tasks.analyze_stop_loss_performance")
def analyze_stop_loss_performance() -> Dict[str, Any]:
    """
    Analyze performance of different stop loss algorithms
    """
    db = SessionLocal()
    try:
        logger.info("Starting stop loss performance analysis")
        
        # Get closed positions from the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        closed_positions = db.query(Position).join(Trade).join(Bot).filter(
            and_(
                Position.is_open == False,
                Position.closed_at >= thirty_days_ago
            )
        ).all()
        
        # Group by stop loss type
        performance_by_type = {}
        
        for position in closed_positions:
            trade = db.query(Trade).filter(
                Trade.exchange_order_id == position.exchange_order_id
            ).first()
            
            if not trade or not trade.bot_id:
                continue
                
            bot = db.query(Bot).filter(Bot.id == trade.bot_id).first()
            if not bot:
                continue
                
            stop_loss_type = bot.stop_loss_type or 'fixed_percentage'
            
            if stop_loss_type not in performance_by_type:
                performance_by_type[stop_loss_type] = {
                    'total_trades': 0,
                    'profitable_trades': 0,
                    'total_pnl': 0.0,
                    'avg_hold_time_hours': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0
                }
            
            stats = performance_by_type[stop_loss_type]
            stats['total_trades'] += 1
            stats['total_pnl'] += position.total_pnl or 0.0
            
            if (position.total_pnl or 0.0) > 0:
                stats['profitable_trades'] += 1
            
            # Calculate hold time
            if position.closed_at and position.opened_at:
                hold_time = (position.closed_at - position.opened_at).total_seconds() / 3600
                stats['avg_hold_time_hours'] = (stats['avg_hold_time_hours'] * (stats['total_trades'] - 1) + hold_time) / stats['total_trades']
        
        # Calculate final metrics
        for stop_loss_type, stats in performance_by_type.items():
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['profitable_trades'] / stats['total_trades']) * 100
                stats['avg_pnl_per_trade'] = stats['total_pnl'] / stats['total_trades']
        
        logger.info(f"Stop loss performance analysis completed for {len(performance_by_type)} types")
        
        return {
            'success': True,
            'timestamp': datetime.utcnow(),
            'analysis_period_days': 30,
            'total_positions_analyzed': len(closed_positions),
            'performance_by_type': performance_by_type
        }
        
    except Exception as e:
        logger.error(f"Error in stop loss performance analysis: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow()
        }
    finally:
        db.close()


@celery_app.task(name="tasks.optimize_stop_loss_parameters")
def optimize_stop_loss_parameters(bot_id: int) -> Dict[str, Any]:
    """
    Optimize stop loss parameters for a specific bot based on historical performance
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting stop loss parameter optimization for bot {bot_id}")
        
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return {
                'success': False,
                'error': f'Bot {bot_id} not found',
                'bot_id': bot_id
            }
        
        # Get historical trades for this bot
        trades = db.query(Trade).filter(
            and_(
                Trade.bot_id == bot_id,
                Trade.status == OrderStatus.FILLED.value
            )
        ).all()
        
        if len(trades) < 10:
            return {
                'success': False,
                'error': 'Insufficient historical data for optimization (minimum 10 trades required)',
                'bot_id': bot_id,
                'trades_count': len(trades)
            }
        
        # Analyze current parameters performance
        current_performance = {
            'total_trades': len(trades),
            'profitable_trades': 0,
            'total_pnl': 0.0,
            'avg_hold_time': 0.0,
            'max_drawdown': 0.0
        }
        
        for trade in trades:
            position = db.query(Position).filter(
                Position.exchange_order_id == trade.exchange_order_id
            ).first()
            
            if position:
                current_performance['total_pnl'] += position.total_pnl or 0.0
                if (position.total_pnl or 0.0) > 0:
                    current_performance['profitable_trades'] += 1
        
        current_performance['win_rate'] = (current_performance['profitable_trades'] / current_performance['total_trades']) * 100
        
        # Suggest optimizations based on performance
        suggestions = []
        
        if current_performance['win_rate'] < 40:
            suggestions.append({
                'parameter': 'stop_loss_percentage',
                'current_value': bot.stop_loss_percentage,
                'suggested_value': max(bot.stop_loss_percentage * 0.8, 2.0),
                'reason': 'Low win rate suggests tighter stop losses might be needed'
            })
        
        if current_performance['win_rate'] > 80:
            suggestions.append({
                'parameter': 'stop_loss_percentage', 
                'current_value': bot.stop_loss_percentage,
                'suggested_value': min(bot.stop_loss_percentage * 1.2, 15.0),
                'reason': 'High win rate suggests looser stop losses might capture more profit'
            })
        
        # ATR-based suggestions
        if bot.stop_loss_type in ['atr_based', 'adaptive_atr']:
            if current_performance['total_pnl'] < 0:
                suggestions.append({
                    'parameter': 'stop_loss_atr_multiplier',
                    'current_value': bot.stop_loss_atr_multiplier,
                    'suggested_value': bot.stop_loss_atr_multiplier * 0.9,
                    'reason': 'Negative total P&L suggests reducing ATR multiplier'
                })
        
        logger.info(f"Stop loss optimization completed for bot {bot_id}: {len(suggestions)} suggestions")
        
        return {
            'success': True,
            'timestamp': datetime.utcnow(),
            'bot_id': bot_id,
            'bot_name': bot.name,
            'current_stop_loss_type': bot.stop_loss_type,
            'current_performance': current_performance,
            'optimization_suggestions': suggestions,
            'trades_analyzed': len(trades)
        }
        
    except Exception as e:
        logger.error(f"Error optimizing stop loss parameters for bot {bot_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'bot_id': bot_id,
            'timestamp': datetime.utcnow()
        }
    finally:
        db.close() 