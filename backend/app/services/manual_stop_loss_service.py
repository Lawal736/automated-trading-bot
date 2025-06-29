"""
Manual Trade Stop Loss Management Service
Manages EMA25 trailing stop losses for manual trades using the same logic as Cassava BOT
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import logging
import asyncio

from app.models.trading import Trade, Position, OrderStatus
from app.models.user import User
from app.models.activity import Activity
from app.models.exchange import ExchangeConnection
from app.services.activity_service import ActivityService, ActivityCreate
from app.services.strategy_service import StrategyService
from app.trading.data_service import data_service
from app.trading.trading_service import trading_service
from app.services.stop_loss_timeout_handler import create_stop_loss_safe, safe_dynamic_stoploss_update
from app.core.logging import get_logger

logger = get_logger(__name__)

class ManualStopLossService:
    """Service for managing EMA25 trailing stop losses for manual trades"""
    
    def __init__(self, db: Session):
        self.db = db
        self.activity_service = ActivityService(Activity)
        
    def get_manual_trades_with_stop_loss_management(self) -> List[Dict[str, Any]]:
        """Get all manual trades that should have EMA25 trailing stop loss management"""
        try:
            manual_trades = self.db.query(Trade).filter(
                and_(
                    Trade.bot_id.is_(None),  # Manual trades only
                    Trade.stop_loss.isnot(None),  # Has stop loss
                    Trade.status == OrderStatus.FILLED.value  # Successfully executed
                )
            ).all()
            
            # Filter for trades that should have EMA25 trailing (this would be stored in metadata)
            # For now, we'll assume all manual trades with stop losses should be managed
            managed_trades = []
            
            for trade in manual_trades:
                # Check if position is still open
                position = self.db.query(Position).filter(
                    and_(
                        Position.exchange_order_id == trade.exchange_order_id,
                        Position.is_open == True
                    )
                ).first()
                
                if position:
                    managed_trades.append({
                        'trade_id': trade.id,
                        'user_id': trade.user_id,
                        'symbol': trade.symbol,
                        'side': trade.side,
                        'entry_price': trade.executed_price,
                        'quantity': trade.quantity,
                        'current_stop_loss': trade.stop_loss,
                        'position_id': position.id,
                        'created_at': trade.created_at
                    })
            
            return managed_trades
            
        except Exception as e:
            logger.error(f"Error getting manual trades with stop loss management: {e}")
            return []
    
    async def update_manual_trade_stop_losses(self) -> Dict[str, Any]:
        """Update stop losses for all manual trades using EMA25 trailing logic with exchange orders"""
        try:
            managed_trades = self.get_manual_trades_with_stop_loss_management()
            results = {
                'total_trades': len(managed_trades),
                'updated_trades': 0,
                'errors': 0,
                'details': []
            }
            
            for trade_info in managed_trades:
                try:
                    symbol = trade_info['symbol']
                    current_stop_loss = trade_info['current_stop_loss']
                    user_id = trade_info['user_id']
                    trade_id = trade_info['trade_id']
                    
                    # Only manage LONG positions (buy side) with EMA25 trailing
                    if trade_info['side'] != 'buy':
                        continue
                    
                    # Get D-1 EMA25 value for comparison
                    market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
                    
                    if market_data.empty or len(market_data) < 2:
                        logger.warning(f"Insufficient market data for {symbol}")
                        continue
                    
                    # Calculate indicators
                    strategy_service = StrategyService('cassava_trend_following', None, {})
                    strategy_service._calculate_indicators(market_data)
                    
                    # Get D-1 EMA25 value (second to last row)
                    ema_exit_period = strategy_service.params.get('ema_exit', 25)
                    ema_exit_col = f"EMA_{ema_exit_period}"
                    
                    if ema_exit_col not in market_data.columns:
                        continue
                    
                    d1_ema25 = market_data[ema_exit_col].iloc[-2]  # D-1 EMA25
                    
                    if pd.isna(d1_ema25):
                        continue
                    
                    # Implement EMA25 trailing logic: only update if D-1 EMA25 > current stop loss
                    if d1_ema25 > current_stop_loss:
                        new_stop_loss = d1_ema25
                        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
                        if trade:
                            old_stop_loss = trade.stop_loss
                            trade.stop_loss = new_stop_loss
                            self.db.commit()
                            # Get the exchange connection
                            connection = self.db.query(ExchangeConnection).filter(
                                ExchangeConnection.user_id == user_id,
                                ExchangeConnection.exchange_name == 'binance'
                            ).first()
                            if not connection:
                                logger.error(f"No exchange connection found for user {user_id}")
                                continue
                            # Get the user
                            user = self.db.query(User).filter(User.id == user_id).first()
                            if not user:
                                logger.error(f"User {user_id} not found")
                                continue
                            # Get exchange instance
                            exchange = await trading_service.get_exchange(connection.exchange_name)
                            if not exchange:
                                logger.error("Failed to get exchange instance")
                                continue
                            # Define a get_position_func for this trade
                            def get_position_func(symbol):
                                return {'quantity': float(trade.quantity)}
                            # Use the safe wrapper for dynamic stop loss update
                            update_result = await safe_dynamic_stoploss_update(
                                exchange=exchange,
                                session=self.db,
                                symbol=symbol,
                                current_stop=current_stop_loss,
                                new_ema_stop=new_stop_loss,
                                user_id=user_id,
                                exchange_conn=connection,
                                user=user,
                                activity_service=self.activity_service,
                                get_position_func=get_position_func
                            )
                            if update_result.get('success'):
                                self._log_stop_loss_update(trade, old_stop_loss, new_stop_loss, d1_ema25)
                                results['updated_trades'] += 1
                                results['details'].append({
                                    'trade_id': trade_id,
                                    'symbol': symbol,
                                    'old_stop_loss': old_stop_loss,
                                    'new_stop_loss': new_stop_loss,
                                    'd1_ema25': d1_ema25,
                                    'status': 'updated_with_exchange_order'
                                })
                                logger.info(f"Manual trade {trade_id} stop loss updated with exchange order: {old_stop_loss} -> {new_stop_loss} (D-1 EMA25: {d1_ema25})")
                            else:
                                results['details'].append({
                                    'trade_id': trade_id,
                                    'symbol': symbol,
                                    'old_stop_loss': old_stop_loss,
                                    'new_stop_loss': new_stop_loss,
                                    'd1_ema25': d1_ema25,
                                    'status': 'exchange_update_failed',
                                    'reason': update_result.get('reason')
                                })
                                logger.warning(f"Manual trade {trade_id} stop loss update failed on exchange: {update_result.get('reason')}")
                        else:
                            results['errors'] += 1
                            logger.error(f"Trade {trade_id} not found for stop loss update")
                    else:
                        results['details'].append({
                            'trade_id': trade_id,
                            'symbol': symbol,
                            'current_stop_loss': current_stop_loss,
                            'd1_ema25': d1_ema25,
                            'status': 'unchanged'
                        })
                        
                        logger.info(f"Manual trade {trade_id} stop loss unchanged: {current_stop_loss} (D-1 EMA25: {d1_ema25} <= current stop loss)")
                
                except Exception as e:
                    results['errors'] += 1
                    logger.error(f"Error updating stop loss for trade {trade_info.get('trade_id')}: {e}")
                    results['details'].append({
                        'trade_id': trade_info.get('trade_id'),
                        'symbol': trade_info.get('symbol'),
                        'status': 'error',
                        'error': str(e)
                    })
            
            logger.info(f"Manual stop loss update completed: {results['updated_trades']} updated, {results['errors']} errors")
            return results
            
        except Exception as e:
            logger.error(f"Error in update_manual_trade_stop_losses: {e}")
            return {
                'total_trades': 0,
                'updated_trades': 0,
                'errors': 1,
                'details': [{'status': 'error', 'error': str(e)}]
            }
    
    async def _place_exchange_stop_loss_order(self, trade: Trade, new_stop_loss: float, user_id: int) -> bool:
        """Place a new stop loss order on the exchange using the timeout handler"""
        try:
            # Get the exchange connection
            connection = self.db.query(ExchangeConnection).filter(
                ExchangeConnection.user_id == user_id,
                ExchangeConnection.exchange_name == 'binance'  # Assuming Binance for now
            ).first()
            
            if not connection:
                logger.error(f"No exchange connection found for user {user_id}")
                return False
            
            # Get the user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Add exchange connection to trading service
            success = await trading_service.add_exchange_connection(connection)
            if not success:
                logger.error(f"Failed to add exchange connection {connection.exchange_name} to trading service")
                return False
            
            # Create a mock trade order object for the stop loss
            class MockTradeOrder:
                def __init__(self, symbol, side, amount, stop_loss):
                    self.symbol = symbol
                    self.side = side
                    self.amount = amount
                    self.stop_loss = stop_loss
            
            # For manual trades, we need to sell the position to create stop loss
            trade_order = MockTradeOrder(
                symbol=trade.symbol,
                side="sell",  # Sell to create stop loss for long position
                amount=trade.quantity,
                stop_loss=new_stop_loss
            )
            
            # Get exchange instance
            exchange = await trading_service.get_exchange(connection.exchange_name)
            if not exchange:
                logger.error("Failed to get exchange instance")
                return False
            
            # Use the robust timeout handler to create stop loss order
            stop_loss_order = await create_stop_loss_safe(
                trade_order, 
                user_id, 
                connection, 
                user, 
                self.activity_service, 
                exchange, 
                self.db
            )
            
            if stop_loss_order:
                logger.info(f"Manual trade stop loss order created successfully: {stop_loss_order.id}")
                return True
            else:
                logger.warning(f"Manual trade stop loss order creation failed")
                return False
                
        except Exception as e:
            logger.error(f"Error placing exchange stop loss order for trade {trade.id}: {e}")
            return False
    
    def _log_stop_loss_update(self, trade: Trade, old_stop_loss: float, new_stop_loss: float, d1_ema25: float):
        """Log stop loss update activity"""
        try:
            user = self.db.query(User).filter(User.id == trade.user_id).first()
            if user:
                activity = ActivityCreate(
                    type="MANUAL_STOP_LOSS_UPDATE",
                    description=f"Manual trade stop loss updated for {trade.symbol}: {old_stop_loss} -> {new_stop_loss} (D-1 EMA25: {d1_ema25})",
                    amount=new_stop_loss
                )
                self.activity_service.log_activity(self.db, user, activity)
        except Exception as e:
            logger.error(f"Error logging stop loss update: {e}")
    
    def setup_ema25_trailing_for_trade(self, trade_id: int, user_id: int) -> bool:
        """Set up EMA25 trailing stop loss management for a specific trade"""
        try:
            trade = self.db.query(Trade).filter(
                and_(
                    Trade.id == trade_id,
                    Trade.user_id == user_id,
                    Trade.bot_id.is_(None)  # Manual trade only
                )
            ).first()
            
            if not trade:
                logger.error(f"Trade {trade_id} not found or not a manual trade")
                return False
            
            if not trade.stop_loss:
                logger.error(f"Trade {trade_id} has no stop loss set")
                return False
            
            # For now, we'll use the existing stop_loss field
            # In a production system, you might want to add a separate field for EMA25 management
            logger.info(f"EMA25 trailing stop loss management set up for manual trade {trade_id}")
            
            # Log the setup
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                activity = ActivityCreate(
                    type="MANUAL_EMA25_SETUP",
                    description=f"EMA25 trailing stop loss management enabled for manual trade {trade_id} on {trade.symbol}",
                    amount=trade.stop_loss
                )
                self.activity_service.log_activity(self.db, user, activity)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up EMA25 trailing for trade {trade_id}: {e}")
            return False 