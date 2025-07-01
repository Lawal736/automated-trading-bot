"""
Trade Analytics Service
Enhanced trade counting, analytics, and real-time tracking
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from app.models.trading import Trade, OrderStatus, Position
from app.models.bot import Bot
from app.models.user import User
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = get_logger(__name__)

class TradeAnalyticsService:
    """Enhanced Trade Analytics Service"""

    def __init__(self, db: Session):
        self.db = db

    def get_enhanced_trade_counts(self, user_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive trade counts with multiple dimensions"""
        logger.info(f"🔢 Getting enhanced trade counts for user {user_id}, last {days} days")
        
        try:
            # Base query
            base_query = self.db.query(Trade)
            if user_id:
                base_query = base_query.filter(Trade.user_id == user_id)
            
            # Time filter
            if days > 0:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                base_query = base_query.filter(Trade.created_at >= cutoff_date)
            
            # Total trades
            total_trades = base_query.count()
            
            # Status breakdown
            status_counts = {}
            for status in OrderStatus:
                count = base_query.filter(Trade.status == status.value).count()
                status_counts[status.value] = count
            
            # Side breakdown
            buy_trades = base_query.filter(Trade.side == 'buy').count()
            sell_trades = base_query.filter(Trade.side == 'sell').count()
            
            # Type breakdown
            spot_trades = base_query.filter(Trade.trade_type == 'spot').count()
            futures_trades = base_query.filter(Trade.trade_type == 'futures').count()
            
            # Bot vs Manual trades
            manual_trades = base_query.filter(Trade.bot_id.is_(None)).count()
            bot_trades = base_query.filter(Trade.bot_id.isnot(None)).count()
            
            # Success metrics
            filled_trades = status_counts.get('filled', 0)
            success_rate = filled_trades / total_trades if total_trades > 0 else 0
            
            # Volume analysis
            volume_result = self.db.query(
                func.sum(Trade.executed_price * Trade.quantity)
            ).filter(
                Trade.status == 'filled',
                Trade.executed_price.isnot(None)
            )
            
            if user_id:
                volume_result = volume_result.filter(Trade.user_id == user_id)
            if days > 0:
                volume_result = volume_result.filter(Trade.created_at >= cutoff_date)
            
            total_volume = float(volume_result.scalar() or 0)
            avg_trade_size = total_volume / filled_trades if filled_trades > 0 else 0
            
            # Time distribution analysis
            time_distribution = self._get_time_distribution(base_query)
            
            # Symbol breakdown
            symbol_breakdown = self._get_symbol_breakdown(base_query)
            
            result = {
                "summary": {
                    "total_trades": total_trades,
                    "time_period_days": days,
                    "success_rate": success_rate,
                    "total_volume": total_volume,
                    "avg_trade_size": avg_trade_size
                },
                "status_breakdown": status_counts,
                "side_breakdown": {
                    "buy_trades": buy_trades,
                    "sell_trades": sell_trades,
                    "buy_percentage": buy_trades / total_trades * 100 if total_trades > 0 else 0,
                    "sell_percentage": sell_trades / total_trades * 100 if total_trades > 0 else 0
                },
                "type_breakdown": {
                    "spot_trades": spot_trades,
                    "futures_trades": futures_trades,
                    "spot_percentage": spot_trades / total_trades * 100 if total_trades > 0 else 0,
                    "futures_percentage": futures_trades / total_trades * 100 if total_trades > 0 else 0
                },
                "automation_breakdown": {
                    "manual_trades": manual_trades,
                    "bot_trades": bot_trades,
                    "automation_rate": bot_trades / total_trades * 100 if total_trades > 0 else 0
                },
                "time_distribution": time_distribution,
                "symbol_breakdown": symbol_breakdown
            }
            
            logger.info(f"✅ Enhanced trade counts complete: {total_trades} trades analyzed")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting enhanced trade counts: {e}")
            return {"error": str(e)}

    def get_real_time_trade_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get real-time trade metrics and live statistics"""
        logger.info(f"⚡ Getting real-time trade metrics for user {user_id}")
        
        try:
            now = datetime.utcnow()
            
            # Base query
            base_query = self.db.query(Trade)
            if user_id:
                base_query = base_query.filter(Trade.user_id == user_id)
            
            # Last 24 hours
            last_24h = now - timedelta(hours=24)
            trades_24h = base_query.filter(Trade.created_at >= last_24h).count()
            
            # Last hour
            last_hour = now - timedelta(hours=1)
            trades_last_hour = base_query.filter(Trade.created_at >= last_hour).count()
            
            # Last 5 minutes
            last_5min = now - timedelta(minutes=5)
            trades_last_5min = base_query.filter(Trade.created_at >= last_5min).count()
            
            # Current active positions
            active_positions_query = self.db.query(Position).filter(Position.is_open == True)
            if user_id:
                active_positions_query = active_positions_query.filter(Position.user_id == user_id)
            active_positions = active_positions_query.count()
            
            # Pending trades
            pending_trades = base_query.filter(Trade.status == 'pending').count()
            
            # Recent failures (last hour)
            recent_failures = base_query.filter(
                Trade.created_at >= last_hour,
                Trade.status.in_(['rejected', 'cancelled'])
            ).count()
            
            # Trading frequency analysis
            trading_frequency = self._calculate_trading_frequency(base_query)
            
            # Current trading activity level
            activity_level = self._assess_activity_level(trades_last_hour, trades_24h)
            
            return {
                "real_time_counts": {
                    "trades_last_5min": trades_last_5min,
                    "trades_last_hour": trades_last_hour,
                    "trades_last_24h": trades_24h,
                    "active_positions": active_positions,
                    "pending_trades": pending_trades,
                    "recent_failures": recent_failures
                },
                "trading_frequency": trading_frequency,
                "activity_level": activity_level,
                "last_updated": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting real-time metrics: {e}")
            return {"error": str(e)}

    def _get_time_distribution(self, base_query) -> Dict[str, int]:
        """Get hourly distribution of trades"""
        try:
            hourly_data = self.db.query(
                func.extract('hour', Trade.created_at).label('hour'),
                func.count(Trade.id).label('count')
            ).filter(
                Trade.id.in_(base_query.with_entities(Trade.id).subquery())
            ).group_by('hour').all()
            
            distribution = {str(i): 0 for i in range(24)}
            
            for hour, count in hourly_data:
                distribution[str(int(hour))] = count
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting time distribution: {e}")
            return {}

    def _get_symbol_breakdown(self, base_query, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top trading symbols"""
        try:
            symbol_data = self.db.query(
                Trade.symbol,
                func.count(Trade.id).label('count'),
                func.sum(Trade.executed_price * Trade.quantity).label('volume')
            ).filter(
                Trade.id.in_(base_query.with_entities(Trade.id).subquery()),
                Trade.status == 'filled',
                Trade.executed_price.isnot(None)
            ).group_by(Trade.symbol).order_by(desc('count')).limit(limit).all()
            
            return [
                {
                    "symbol": symbol,
                    "trade_count": count,
                    "volume": float(volume or 0)
                }
                for symbol, count, volume in symbol_data
            ]
            
        except Exception as e:
            logger.error(f"Error getting symbol breakdown: {e}")
            return []

    def _calculate_trading_frequency(self, base_query) -> Dict[str, float]:
        """Calculate trading frequency metrics"""
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_trades = base_query.filter(Trade.created_at >= thirty_days_ago).count()
            
            daily_avg = recent_trades / 30
            weekly_avg = recent_trades / 4.3
            hourly_avg = recent_trades / (30 * 24)
            
            return {
                "trades_per_day": daily_avg,
                "trades_per_week": weekly_avg,
                "trades_per_hour": hourly_avg
            }
            
        except Exception as e:
            logger.error(f"Error calculating trading frequency: {e}")
            return {}

    def _assess_activity_level(self, last_hour: int, last_24h: int) -> str:
        """Assess current trading activity level"""
        try:
            hourly_rate = last_hour
            daily_rate = last_24h / 24
            
            if hourly_rate >= 5:
                return "Very High"
            elif hourly_rate >= 2:
                return "High"
            elif hourly_rate >= 1:
                return "Medium"
            elif daily_rate >= 0.5:
                return "Low"
            else:
                return "Very Low"
                
        except Exception:
            return "Unknown"
