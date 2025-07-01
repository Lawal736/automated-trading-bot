"""
Advanced Position Management Service
Enhanced position management with advanced analytics, automation, and monitoring
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from app.models.trading import Position, Trade, OrderStatus
from app.models.bot import Bot
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.trading.exchanges.factory import ExchangeFactory
from app.services.position_service import PositionService
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics

logger = get_logger(__name__)

class PositionHealthStatus(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

class PositionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class AdvancedPositionManagementService:
    """Advanced Position Management Service"""

    def __init__(self, db: Session):
        self.db = db
        self.position_service = PositionService()

    async def get_advanced_position_overview(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive advanced position overview"""
        logger.info(f"🔍 Getting advanced position overview for user {user_id}")
        
        try:
            # Get basic position data
            positions = self.position_service.get_detailed_positions(self.db, user_id)
            
            # Calculate advanced metrics
            advanced_metrics = await self._calculate_advanced_position_metrics(user_id, positions)
            
            # Get position health scores
            health_scores = await self._calculate_position_health_scores(positions)
            
            # Get risk assessment
            risk_assessment = await self._perform_risk_assessment(user_id, positions)
            
            # Get performance metrics
            performance_metrics = await self._calculate_performance_metrics(positions)
            
            # Generate recommendations
            recommendations = await self._generate_position_recommendations(user_id, positions, advanced_metrics)
            
            return {
                "overview": {
                    "total_positions": len(positions),
                    "open_positions": len([p for p in positions if p["is_open"]]),
                    "total_value": sum(p["current_value"] for p in positions if p["is_open"]),
                    "total_pnl": sum(p["total_pnl"] for p in positions),
                    "avg_position_age": advanced_metrics["avg_position_age"],
                    "portfolio_health_score": advanced_metrics["portfolio_health_score"]
                },
                "positions": positions,
                "advanced_metrics": advanced_metrics,
                "health_scores": health_scores,
                "risk_assessment": risk_assessment,
                "performance_metrics": performance_metrics,
                "recommendations": recommendations,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting advanced position overview: {e}")
            return {"error": str(e)}

    async def get_position_monitoring_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get real-time position monitoring dashboard"""
        logger.info(f"📊 Getting position monitoring dashboard for user {user_id}")
        
        try:
            # Update all position prices first
            await self.position_service.update_position_prices(self.db, user_id)
            
            # Get active positions
            active_positions = self.position_service.get_detailed_positions(self.db, user_id, include_closed=False)
            
            # Real-time alerts
            alerts = await self._generate_real_time_alerts(user_id, active_positions)
            
            # Position status summary
            status_summary = await self._get_position_status_summary(active_positions)
            
            # Recent changes
            recent_changes = await self._get_recent_position_changes(user_id)
            
            # Market exposure analysis
            exposure_analysis = await self._analyze_market_exposure(active_positions)
            
            # Performance today
            daily_performance = await self._calculate_daily_performance(user_id)
            
            return {
                "dashboard": {
                    "active_positions": len(active_positions),
                    "total_exposure": sum(p["current_value"] for p in active_positions),
                    "unrealized_pnl": sum(p["unrealized_pnl"] for p in active_positions),
                    "daily_change": daily_performance["daily_change"],
                    "alerts_count": len(alerts)
                },
                "positions": active_positions,
                "alerts": alerts,
                "status_summary": status_summary,
                "recent_changes": recent_changes,
                "exposure_analysis": exposure_analysis,
                "daily_performance": daily_performance,
                "refresh_interval": 60,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting position monitoring dashboard: {e}")
            return {"error": str(e)}

    # Helper methods for calculations
    async def _calculate_advanced_position_metrics(self, user_id: int, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate advanced position metrics"""
        try:
            if not positions:
                return {"avg_position_age": 0, "portfolio_health_score": 0}
            
            # Average position age
            open_positions = [p for p in positions if p["is_open"]]
            if open_positions:
                ages = [p["duration_hours"] for p in open_positions]
                avg_age = statistics.mean(ages)
            else:
                avg_age = 0
            
            # Portfolio health score (0-100)
            total_pnl = sum(p["total_pnl"] for p in positions)
            winning_positions = len([p for p in positions if p["total_pnl"] > 0])
            total_positions = len(positions) if positions else 1
            
            win_rate = winning_positions / total_positions
            health_score = min(100, max(0, 50 + (total_pnl / 100) + (win_rate * 30)))
            
            return {
                "avg_position_age": avg_age,
                "portfolio_health_score": health_score,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "position_count": total_positions
            }
            
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {e}")
            return {"avg_position_age": 0, "portfolio_health_score": 0}

    async def _calculate_position_health_scores(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate health scores for individual positions"""
        try:
            health_scores = []
            
            for position in positions:
                if not position["is_open"]:
                    continue
                
                # Base score from P&L percentage
                pnl_pct = position.get("pnl_percentage", 0)
                base_score = 50 + min(30, max(-30, pnl_pct))
                
                # Age factor
                age_hours = position.get("duration_hours", 0)
                age_factor = max(0.8, 1 - (age_hours / (24 * 30)))
                
                # Stop loss factor
                stop_loss_factor = 1.1 if position.get("stop_loss") else 0.9
                
                # Calculate final score
                final_score = base_score * age_factor * stop_loss_factor
                final_score = min(100, max(0, final_score))
                
                # Determine status
                if final_score >= 80:
                    status = PositionHealthStatus.EXCELLENT
                elif final_score >= 65:
                    status = PositionHealthStatus.GOOD
                elif final_score >= 50:
                    status = PositionHealthStatus.FAIR
                elif final_score >= 30:
                    status = PositionHealthStatus.POOR
                else:
                    status = PositionHealthStatus.CRITICAL
                
                health_scores.append({
                    "position_id": position["id"],
                    "symbol": position["symbol"],
                    "health_score": final_score,
                    "health_status": status,
                    "factors": {
                        "pnl_impact": pnl_pct,
                        "age_factor": age_factor,
                        "stop_loss_factor": stop_loss_factor
                    }
                })
            
            return health_scores
            
        except Exception as e:
            logger.error(f"Error calculating health scores: {e}")
            return []

    async def _perform_risk_assessment(self, user_id: int, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive risk assessment"""
        try:
            open_positions = [p for p in positions if p["is_open"]]
            
            if not open_positions:
                return {"overall_risk": "low", "risk_factors": []}
            
            # Calculate risk factors
            total_exposure = sum(p["current_value"] for p in open_positions)
            positions_without_stop_loss = len([p for p in open_positions if not p.get("stop_loss")])
            concentrated_positions = len([p for p in open_positions if p["current_value"] > total_exposure * 0.2])
            
            # Risk scoring
            risk_score = 0
            risk_factors = []
            
            # Concentration risk
            if concentrated_positions > 0:
                risk_score += 20
                risk_factors.append(f"{concentrated_positions} concentrated positions (>20% of portfolio)")
            
            # Stop loss risk
            if positions_without_stop_loss > 0:
                risk_score += 15
                risk_factors.append(f"{positions_without_stop_loss} positions without stop loss")
            
            # Exposure risk
            if len(open_positions) > 10:
                risk_score += 10
                risk_factors.append("High number of open positions")
            
            # Determine risk level
            if risk_score >= 40:
                risk_level = PositionRiskLevel.EXTREME
            elif risk_score >= 25:
                risk_level = PositionRiskLevel.HIGH
            elif risk_score >= 15:
                risk_level = PositionRiskLevel.MEDIUM
            else:
                risk_level = PositionRiskLevel.LOW
            
            return {
                "overall_risk": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "total_exposure": total_exposure,
                "positions_count": len(open_positions),
                "recommendations": self._generate_risk_recommendations(risk_level, risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Error performing risk assessment: {e}")
            return {"overall_risk": "unknown", "risk_factors": []}

    async def _calculate_performance_metrics(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed performance metrics"""
        try:
            if not positions:
                return {"total_return": 0, "win_rate": 0, "avg_return": 0}
            
            # Calculate returns
            total_pnl = sum(p["total_pnl"] for p in positions)
            winning_positions = len([p for p in positions if p["total_pnl"] > 0])
            
            win_rate = winning_positions / len(positions) if positions else 0
            avg_return = total_pnl / len(positions) if positions else 0
            
            return {
                "total_return": total_pnl,
                "win_rate": win_rate,
                "avg_return": avg_return,
                "winning_positions": winning_positions,
                "total_positions": len(positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {"total_return": 0, "win_rate": 0, "avg_return": 0}

    async def _generate_position_recommendations(self, user_id: int, positions: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable position recommendations"""
        try:
            recommendations = []
            
            # Health-based recommendations
            if metrics.get("portfolio_health_score", 0) < 50:
                recommendations.append({
                    "type": "health_improvement",
                    "priority": "high",
                    "title": "Portfolio Health Alert",
                    "description": "Portfolio health score is below 50. Consider reviewing losing positions.",
                    "action": "Review and consider closing underperforming positions"
                })
            
            # Win rate recommendations
            if metrics.get("win_rate", 0) < 0.4:
                recommendations.append({
                    "type": "strategy_review",
                    "priority": "medium",
                    "title": "Low Win Rate",
                    "description": f"Win rate is {metrics.get('win_rate', 0):.1%}. Consider reviewing entry strategy.",
                    "action": "Analyze entry criteria and market timing"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    # Additional helper methods
    async def _generate_real_time_alerts(self, user_id: int, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate real-time alerts for position monitoring"""
        try:
            alerts = []
            
            for position in positions:
                # Stop loss alerts
                if not position.get("stop_loss"):
                    alerts.append({
                        "type": "warning",
                        "position_id": position["id"],
                        "symbol": position["symbol"],
                        "message": "Position without stop loss protection",
                        "severity": "medium",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Large loss alerts
                if position.get("pnl_percentage", 0) < -10:
                    alerts.append({
                        "type": "critical",
                        "position_id": position["id"],
                        "symbol": position["symbol"],
                        "message": f"Position down {abs(position['pnl_percentage']):.1f}%",
                        "severity": "high",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
            return []

    async def _get_position_status_summary(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get position status summary"""
        try:
            total_positions = len(positions)
            profitable = len([p for p in positions if p.get("total_pnl", 0) > 0])
            losing = len([p for p in positions if p.get("total_pnl", 0) < 0])
            
            return {
                "total": total_positions,
                "profitable": profitable,
                "losing": losing,
                "profitability_rate": profitable / total_positions if total_positions > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting status summary: {e}")
            return {"total": 0, "profitable": 0, "losing": 0}

    async def _get_recent_position_changes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get recent position changes"""
        try:
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_positions = self.db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.updated_at >= yesterday
                )
            ).order_by(desc(Position.updated_at)).limit(10).all()
            
            changes = []
            for position in recent_positions:
                changes.append({
                    "position_id": position.id,
                    "symbol": position.symbol,
                    "change_type": "price_update",
                    "timestamp": position.updated_at.isoformat(),
                    "current_pnl": position.total_pnl
                })
            
            return changes
            
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []

    async def _analyze_market_exposure(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze market exposure across positions"""
        try:
            if not positions:
                return {"total_exposure": 0, "symbol_distribution": {}}
            
            total_exposure = sum(p["current_value"] for p in positions)
            
            # Symbol distribution
            symbol_exposure = {}
            for position in positions:
                symbol = position["symbol"]
                if symbol not in symbol_exposure:
                    symbol_exposure[symbol] = 0
                symbol_exposure[symbol] += position["current_value"]
            
            return {
                "total_exposure": total_exposure,
                "symbol_distribution": symbol_exposure,
                "diversification_index": len(symbol_exposure)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing exposure: {e}")
            return {"total_exposure": 0, "symbol_distribution": {}}

    async def _calculate_daily_performance(self, user_id: int) -> Dict[str, Any]:
        """Calculate daily performance"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            daily_pnl = self.db.query(func.sum(Position.unrealized_pnl)).filter(
                and_(
                    Position.user_id == user_id,
                    Position.updated_at >= today_start,
                    Position.is_open == True
                )
            ).scalar() or 0.0
            
            return {
                "daily_change": daily_pnl,
                "period": "today",
                "last_calculated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily performance: {e}")
            return {"daily_change": 0}

    def _generate_risk_recommendations(self, risk_level: PositionRiskLevel, risk_factors: List[str]) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if risk_level in [PositionRiskLevel.HIGH, PositionRiskLevel.EXTREME]:
            recommendations.append("Reduce overall position size")
            recommendations.append("Implement stop losses on all positions")
            
        if "concentrated positions" in str(risk_factors):
            recommendations.append("Diversify portfolio across more symbols")
            
        if "without stop loss" in str(risk_factors):
            recommendations.append("Set stop losses for risk management")
            
        return recommendations
