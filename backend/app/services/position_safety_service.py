import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import structlog

from app.core.database import get_db
from app.models.trading import Trade, Position
from app.models.exchange import ExchangeConnection
from app.models.user import User
from app.services.activity_service import activity_service
from app.schemas.activity import ActivityCreate
from app.trading.exchanges.factory import ExchangeFactory
from app.services.stop_loss_timeout_handler import create_stop_loss_safe

logger = structlog.get_logger()


class PositionSafetyService:
    """
    Comprehensive position safety service that implements:
    1. 15-minute retry system for failed stop losses
    2. 4-hour force closure safety net for unprotected positions
    3. Database session issue prevention
    """
    
    def __init__(self):
        self.max_retry_attempts = 20  # 20 attempts over 5 hours
        self.retry_interval_minutes = 15
        self.force_closure_hours = 4
        
    async def scan_and_protect_positions(self) -> dict:
        """
        Main safety scanner that checks for:
        1. Failed stop loss positions needing retry
        2. Unprotected positions approaching force closure
        3. Database session issues
        """
        db_gen = get_db()
        db = next(db_gen)
        
        results = {
            "retries_attempted": 0,
            "retries_successful": 0,
            "force_closures": 0,
            "database_fixes": 0,
            "errors": []
        }
        
        try:
            # Get all unprotected positions
            unprotected_positions = await self._get_unprotected_positions(db)
            logger.info(f"Found {len(unprotected_positions)} unprotected positions")
            
            for position_data in unprotected_positions:
                trade = position_data["trade"]
                position = position_data["position"]
                age_hours = position_data["age_hours"]
                
                logger.info(f"Processing unprotected position - Trade ID: {trade.id}, Age: {age_hours:.1f}h")
                
                # Check if position needs force closure (4+ hours unprotected)
                if age_hours >= self.force_closure_hours:
                    logger.warning(f"Force closing position after {age_hours:.1f} hours - Trade ID: {trade.id}")
                    closure_result = await self._force_close_position(trade, position, db)
                    if closure_result:
                        results["force_closures"] += 1
                    continue
                
                # Check if position needs retry (every 15 minutes)
                if await self._should_retry_stop_loss(trade):
                    logger.info(f"Attempting stop loss retry for Trade ID: {trade.id}")
                    results["retries_attempted"] += 1
                    
                    retry_result = await self._retry_stop_loss_creation(trade, db)
                    if retry_result:
                        results["retries_successful"] += 1
                        logger.info(f"✅ Stop loss retry successful for Trade ID: {trade.id}")
                    else:
                        logger.error(f"❌ Stop loss retry failed for Trade ID: {trade.id}")
                        
        except Exception as e:
            logger.error(f"Error in position safety scan: {e}")
            results["errors"].append(str(e))
        finally:
            db.close()
            
        return results
    
    async def _get_unprotected_positions(self, db: Session) -> List[dict]:
        """Get all positions that are open but don't have stop loss protection"""
        unprotected = []
        
        # Find open positions without stop loss
        open_positions = db.query(Position).filter(
            Position.is_open == True,
            or_(
                Position.stop_loss.is_(None),
                Position.stop_loss == 0
            )
        ).all()
        
        for position in open_positions:
            # Find the original trade that created this position
            original_trade = db.query(Trade).filter(
                and_(
                    Trade.user_id == position.user_id,
                    Trade.symbol == position.symbol,
                    Trade.side == position.side,
                    Trade.status == "filled",
                    Trade.trade_type == "spot",  # Original buy/sell trade
                    or_(
                        Trade.stop_loss.is_(None),
                        Trade.stop_loss_failed == True
                    )
                )
            ).order_by(Trade.created_at.desc()).first()
            
            if original_trade:
                # Calculate how long position has been unprotected
                age_hours = (datetime.utcnow() - original_trade.created_at.replace(tzinfo=None)).total_seconds() / 3600
                
                unprotected.append({
                    "trade": original_trade,
                    "position": position,
                    "age_hours": age_hours
                })
        
        return unprotected
    
    async def _should_retry_stop_loss(self, trade: Trade) -> bool:
        """Check if we should retry creating stop loss for this trade"""
        if not trade.stop_loss_failed:
            return False
            
        if trade.stop_loss_retry_count >= self.max_retry_attempts:
            return False
            
        # Check if enough time has passed since last attempt (15 minutes)
        if trade.stop_loss_last_attempt:
            minutes_since_last = (datetime.utcnow() - trade.stop_loss_last_attempt.replace(tzinfo=None)).total_seconds() / 60
            return minutes_since_last >= self.retry_interval_minutes
        
        return True
    
    async def _retry_stop_loss_creation(self, trade: Trade, db: Session) -> bool:
        """Retry creating stop loss for a failed trade"""
        try:
            # Get required objects
            conn = db.query(ExchangeConnection).filter(
                ExchangeConnection.id == trade.exchange_connection_id
            ).first()
            user = db.query(User).filter(User.id == trade.user_id).first()
            
            if not conn or not user:
                logger.error(f"Missing connection or user for Trade ID: {trade.id}")
                return False
            
            # Calculate stop loss price (2% below execution price)
            stop_loss_price = float(trade.executed_price) * 0.98
            
            # Create mock trade order for stop loss creation
            # CRITICAL FIX: trade_order.side should match the ORIGINAL trade side
            # The stop loss handler will invert it correctly
            class MockTradeOrder:
                def __init__(self, symbol, side, amount, stop_loss):
                    self.symbol = symbol
                    self.side = side  # Same side as original trade
                    self.amount = amount
                    self.stop_loss = stop_loss
            
            trade_order = MockTradeOrder(
                symbol=trade.symbol,
                side=trade.side,  # Same side as original trade (buy)
                amount=trade.quantity,
                stop_loss=stop_loss_price
            )
            
            # Create fresh database session to avoid session issues
            fresh_db_gen = get_db()
            fresh_db = next(fresh_db_gen)
            
            try:
                # Create exchange instance
                exchange = ExchangeFactory.create_exchange(
                    exchange_name=conn.exchange_name,
                    api_key=conn.api_key,
                    api_secret=conn.api_secret,
                    is_testnet=conn.is_testnet
                )
                
                # Attempt stop loss creation with fresh session
                stop_loss_order = await create_stop_loss_safe(
                    trade_order, 
                    trade.user_id, 
                    conn, 
                    user, 
                    activity_service, 
                    exchange, 
                    fresh_db
                )
                
                if stop_loss_order:
                    # Update original trade in main session
                    trade.stop_loss = stop_loss_price
                    trade.stop_loss_failed = False
                    trade.stop_loss_retry_count += 1
                    trade.stop_loss_last_attempt = datetime.utcnow()
                    
                    # Also update the position
                    position = db.query(Position).filter(
                        and_(
                            Position.user_id == trade.user_id,
                            Position.symbol == trade.symbol,
                            Position.is_open == True
                        )
                    ).first()
                    
                    if position:
                        position.stop_loss = stop_loss_price
                    
                    db.commit()
                    
                    # Log success activity
                    await activity_service.log_activity(
                        ActivityCreate(
                            user_id=trade.user_id,
                            action="stop_loss_retry_success",
                            details=f"Successfully created stop loss for Trade ID {trade.id} after {trade.stop_loss_retry_count} attempts",
                            bot_id=trade.bot_id
                        ),
                        fresh_db
                    )
                    
                    await exchange.close()
                    return True
                else:
                    # Update retry count even on failure
                    trade.stop_loss_retry_count += 1
                    trade.stop_loss_last_attempt = datetime.utcnow()
                    db.commit()
                    
                    await exchange.close()
                    return False
                    
            finally:
                fresh_db.close()
                
        except Exception as e:
            logger.error(f"Error retrying stop loss for Trade ID {trade.id}: {e}")
            # Update retry count even on error
            trade.stop_loss_retry_count += 1
            trade.stop_loss_last_attempt = datetime.utcnow()
            db.commit()
            return False
    
    async def _force_close_position(self, trade: Trade, position: Position, db: Session) -> bool:
        """Force close an unprotected position after 4 hours"""
        try:
            # Get exchange connection
            conn = db.query(ExchangeConnection).filter(
                ExchangeConnection.id == trade.exchange_connection_id
            ).first()
            
            if not conn:
                logger.error(f"No exchange connection for Trade ID: {trade.id}")
                return False
            
            # Create exchange instance
            exchange = ExchangeFactory.create_exchange(
                exchange_name=conn.exchange_name,
                api_key=conn.api_key,
                api_secret=conn.api_secret,
                is_testnet=conn.is_testnet
            )
            
            # Execute market order to close position
            close_side = "sell" if trade.side == "buy" else "buy"
            
            market_order = await exchange.create_market_order(
                symbol=trade.symbol,
                side=close_side,
                amount=trade.quantity
            )
            
            if market_order and market_order.get('id'):
                # Close the position
                position.is_open = False
                position.closed_at = datetime.utcnow()
                
                # Create closure trade record
                closure_trade = Trade(
                    user_id=trade.user_id,
                    bot_id=trade.bot_id,
                    strategy_id=trade.strategy_id,
                    exchange_connection_id=trade.exchange_connection_id,
                    symbol=trade.symbol,
                    trade_type="spot",
                    order_type="market",
                    side=close_side,
                    quantity=trade.quantity,
                    price=market_order.get('price', 0),
                    executed_price=market_order.get('price', 0),
                    status="filled",
                    exchange_order_id=market_order.get('id'),
                    executed_at=datetime.utcnow()
                )
                
                db.add(closure_trade)
                db.commit()
                
                # Log force closure activity
                await activity_service.log_activity(
                    ActivityCreate(
                        user_id=trade.user_id,
                        action="position_force_closed",
                        details=f"Force closed unprotected position after 4 hours - Original Trade ID: {trade.id}, Closure Trade ID: {closure_trade.id}",
                        bot_id=trade.bot_id
                    ),
                    db
                )
                
                logger.warning(f"🚨 FORCE CLOSED unprotected position - Trade ID: {trade.id}")
                
                await exchange.close()
                return True
            else:
                logger.error(f"Failed to execute force closure market order for Trade ID: {trade.id}")
                await exchange.close()
                return False
                
        except Exception as e:
            logger.error(f"Error force closing position for Trade ID {trade.id}: {e}")
            return False


# Global instance
position_safety_service = PositionSafetyService() 