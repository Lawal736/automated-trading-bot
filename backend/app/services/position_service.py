from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.trading import Position, Trade, OrderStatus
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.trading.exchanges.factory import ExchangeFactory
from app.core.logging import get_logger
from app.services.base import ServiceBase
from app.schemas.position import Position as PositionSchema

logger = get_logger(__name__)

class PositionService(ServiceBase[Position, None, None]):
    """Enhanced Position Service with real-time P&L calculations"""
    
    def __init__(self):
        super().__init__(Position)
    
    async def update_position_prices(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Update current prices for all open positions and calculate P&L"""
        try:
            # Get all open positions for user
            positions = db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.is_open == True
                )
            ).all()
            
            updated_count = 0
            total_unrealized_pnl = 0.0
            position_updates = []
            
            for position in positions:
                try:
                    # Get exchange connection
                    exchange_conn = db.query(ExchangeConnection).filter(
                        ExchangeConnection.id == position.exchange_connection_id
                    ).first()
                    
                    if not exchange_conn:
                        logger.warning(f"Exchange connection not found for position {position.id}")
                        continue
                    
                    # Get current market price
                    exchange = await ExchangeFactory.create_exchange(exchange_conn)
                    ticker = await exchange.fetch_ticker(position.symbol)
                    current_price = float(ticker['last'])
                    
                    # Calculate unrealized P&L
                    if position.side == 'buy':
                        # Long position: profit when current > entry
                        unrealized_pnl = (current_price - position.entry_price) * position.quantity
                    else:
                        # Short position: profit when current < entry  
                        unrealized_pnl = (position.entry_price - current_price) * position.quantity
                    
                    # Apply leverage if applicable
                    if position.leverage > 1:
                        unrealized_pnl *= position.leverage
                    
                    # Update position
                    position.current_price = current_price
                    position.unrealized_pnl = unrealized_pnl
                    position.total_pnl = position.realized_pnl + unrealized_pnl
                    position.updated_at = datetime.utcnow()
                    
                    total_unrealized_pnl += unrealized_pnl
                    updated_count += 1
                    
                    position_updates.append({
                        'position_id': position.id,
                        'symbol': position.symbol,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'total_pnl': position.total_pnl
                    })
                    
                    logger.info(f"Updated position {position.id} - {position.symbol}: "
                              f"Price: {current_price}, P&L: {unrealized_pnl:.2f}")
                    
                except Exception as e:
                    logger.error(f"Error updating position {position.id}: {e}")
                    continue
            
            # Commit all updates
            db.commit()
            
            return {
                'updated_positions': updated_count,
                'total_unrealized_pnl': total_unrealized_pnl,
                'position_updates': position_updates,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error updating position prices for user {user_id}: {e}")
            db.rollback()
            return {
                'updated_positions': 0,
                'total_unrealized_pnl': 0.0,
                'position_updates': [],
                'error': str(e)
            }
    
    def get_portfolio_pnl_summary(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive P&L summary for a user's portfolio"""
        try:
            # Get all positions (open and closed)
            all_positions = db.query(Position).filter(Position.user_id == user_id).all()
            
            # Calculate totals
            total_unrealized_pnl = sum(p.unrealized_pnl for p in all_positions if p.is_open)
            total_realized_pnl = sum(p.realized_pnl for p in all_positions)
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            # Get daily P&L (positions updated today)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_pnl = db.query(func.sum(Position.unrealized_pnl)).filter(
                and_(
                    Position.user_id == user_id,
                    Position.updated_at >= today_start,
                    Position.is_open == True
                )
            ).scalar() or 0.0
            
            # Count active positions
            active_positions_count = db.query(Position).filter(
                and_(Position.user_id == user_id, Position.is_open == True)
            ).count()
            
            # Get best and worst performing positions
            best_position = db.query(Position).filter(
                Position.user_id == user_id
            ).order_by(desc(Position.total_pnl)).first()
            
            worst_position = db.query(Position).filter(
                Position.user_id == user_id
            ).order_by(Position.total_pnl).first()
            
            return {
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl, 
                'total_pnl': total_pnl,
                'daily_pnl': daily_pnl,
                'active_positions_count': active_positions_count,
                'best_position': {
                    'symbol': best_position.symbol if best_position else None,
                    'pnl': best_position.total_pnl if best_position else 0
                },
                'worst_position': {
                    'symbol': worst_position.symbol if worst_position else None,
                    'pnl': worst_position.total_pnl if worst_position else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio P&L summary for user {user_id}: {e}")
            return {
                'total_unrealized_pnl': 0.0,
                'total_realized_pnl': 0.0,
                'total_pnl': 0.0,
                'daily_pnl': 0.0,
                'active_positions_count': 0,
                'best_position': {'symbol': None, 'pnl': 0},
                'worst_position': {'symbol': None, 'pnl': 0},
                'error': str(e)
            }
    
    def get_detailed_positions(self, db: Session, user_id: int, include_closed: bool = False) -> List[Dict[str, Any]]:
        """Get detailed position information with P&L breakdown"""
        try:
            query = db.query(Position).filter(Position.user_id == user_id)
            
            if not include_closed:
                query = query.filter(Position.is_open == True)
            
            positions = query.order_by(desc(Position.opened_at)).all()
            
            detailed_positions = []
            
            for position in positions:
                # Calculate additional metrics
                duration = datetime.utcnow() - position.opened_at if position.is_open else position.closed_at - position.opened_at
                
                # Calculate percentage P&L
                pnl_percentage = 0.0
                if position.entry_price and position.entry_price > 0:
                    if position.side == 'buy':
                        pnl_percentage = ((position.current_price or position.entry_price) - position.entry_price) / position.entry_price * 100
                    else:
                        pnl_percentage = (position.entry_price - (position.current_price or position.entry_price)) / position.entry_price * 100
                
                # Calculate position value
                current_value = (position.current_price or position.entry_price) * position.quantity
                
                detailed_positions.append({
                    'id': position.id,
                    'symbol': position.symbol,
                    'side': position.side,
                    'quantity': position.quantity,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'leverage': position.leverage,
                    'unrealized_pnl': position.unrealized_pnl,
                    'realized_pnl': position.realized_pnl,
                    'total_pnl': position.total_pnl,
                    'pnl_percentage': pnl_percentage,
                    'current_value': current_value,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'is_open': position.is_open,
                    'opened_at': position.opened_at,
                    'closed_at': position.closed_at,
                    'duration_hours': duration.total_seconds() / 3600,
                    'trade_type': position.trade_type
                })
            
            return detailed_positions
            
        except Exception as e:
            logger.error(f"Error getting detailed positions for user {user_id}: {e}")
            return []
    
    def close_position(self, db: Session, position_id: int, closing_price: float, closing_trade_id: Optional[int] = None) -> bool:
        """Close a position and finalize P&L calculations"""
        try:
            position = db.query(Position).filter(Position.id == position_id).first()
            
            if not position:
                logger.error(f"Position {position_id} not found")
                return False
            
            if not position.is_open:
                logger.warning(f"Position {position_id} is already closed")
                return True
            
            # Calculate final P&L
            if position.side == 'buy':
                final_pnl = (closing_price - position.entry_price) * position.quantity
            else:
                final_pnl = (position.entry_price - closing_price) * position.quantity
            
            # Apply leverage
            if position.leverage > 1:
                final_pnl *= position.leverage
            
            # Update position
            position.current_price = closing_price
            position.realized_pnl = final_pnl
            position.unrealized_pnl = 0.0
            position.total_pnl = final_pnl
            position.is_open = False
            position.closed_at = datetime.utcnow()
            position.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Closed position {position_id} - {position.symbol}: "
                       f"Final P&L: {final_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            db.rollback()
            return False
    
    def get_position_risk_metrics(self, db: Session, position_id: int) -> Dict[str, Any]:
        """Calculate risk metrics for a specific position"""
        try:
            position = db.query(Position).filter(Position.id == position_id).first()
            
            if not position:
                return {'error': 'Position not found'}
            
            if not position.is_open:
                return {'error': 'Position is closed'}
            
            current_price = position.current_price or position.entry_price
            
            # Calculate distance to stop loss
            stop_loss_distance = None
            stop_loss_percentage = None
            
            if position.stop_loss:
                if position.side == 'buy':
                    stop_loss_distance = current_price - position.stop_loss
                    stop_loss_percentage = (stop_loss_distance / current_price) * 100
                else:
                    stop_loss_distance = position.stop_loss - current_price
                    stop_loss_percentage = (stop_loss_distance / current_price) * 100
            
            # Calculate position health score (0-100)
            health_score = 50  # Default neutral
            
            if position.unrealized_pnl > 0:
                health_score += min(40, position.unrealized_pnl / 100)  # Cap at 90
            elif position.unrealized_pnl < 0:
                health_score += max(-40, position.unrealized_pnl / 100)  # Floor at 10
            
            return {
                'position_id': position.id,
                'symbol': position.symbol,
                'current_price': current_price,
                'stop_loss_distance': stop_loss_distance,
                'stop_loss_percentage': stop_loss_percentage,
                'health_score': max(0, min(100, health_score)),
                'risk_level': 'High' if health_score < 30 else 'Medium' if health_score < 70 else 'Low'
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics for position {position_id}: {e}")
            return {'error': str(e)} 