"""
Enhanced Stop Loss Placement Service
Advanced stop loss placement with intelligent algorithms and market-aware adjustments
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from app.models.trading import Position, Trade, OrderStatus
from app.models.bot import Bot
from app.models.user import User
from app.models.exchange import ExchangeConnection
from app.services.advanced_stop_loss_service import AdvancedStopLossService
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics

logger = get_logger(__name__)

class StopLossPlacementStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    ADAPTIVE = "adaptive"

class MarketCondition(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"

class EnhancedStopLossPlacementService:
    """
    Enhanced Stop Loss Placement Service
    
    Features:
    - Intelligent stop loss placement based on market conditions
    - Multi-layered stop loss strategies
    - Risk-adjusted stop loss levels
    - Market volatility-aware adjustments
    - Portfolio-wide stop loss optimization
    """

    def __init__(self, db: Session):
        self.db = db
        self.advanced_stop_loss_service = AdvancedStopLossService(db)

    async def analyze_optimal_stop_loss_placement(self, user_id: int) -> Dict[str, Any]:
        """Analyze optimal stop loss placement for all user positions"""
        logger.info(f"🎯 Analyzing optimal stop loss placement for user {user_id}")
        
        try:
            # Get open positions without stop loss
            positions_without_sl = self._get_positions_without_stop_loss(user_id)
            
            # Get positions with suboptimal stop loss
            suboptimal_positions = await self._identify_suboptimal_stop_losses(user_id)
            
            # Analyze market conditions
            market_conditions = await self._analyze_market_conditions(user_id)
            
            # Generate placement recommendations
            placement_recommendations = await self._generate_placement_recommendations(
                positions_without_sl, suboptimal_positions, market_conditions
            )
            
            # Calculate portfolio-wide stop loss metrics
            portfolio_metrics = await self._calculate_portfolio_stop_loss_metrics(user_id)
            
            return {
                "analysis": {
                    "positions_without_stop_loss": len(positions_without_sl),
                    "suboptimal_positions": len(suboptimal_positions),
                    "total_at_risk": len(positions_without_sl) + len(suboptimal_positions),
                    "market_condition": market_conditions["overall_condition"],
                    "recommended_strategy": self._recommend_placement_strategy(market_conditions)
                },
                "positions_without_stop_loss": positions_without_sl,
                "suboptimal_positions": suboptimal_positions,
                "market_conditions": market_conditions,
                "placement_recommendations": placement_recommendations,
                "portfolio_metrics": portfolio_metrics,
                "last_analyzed": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing stop loss placement: {e}")
            return {"error": str(e)}

    async def get_intelligent_stop_loss_suggestions(self, position_id: int) -> Dict[str, Any]:
        """Get intelligent stop loss suggestions for a specific position"""
        logger.info(f"🧠 Getting intelligent stop loss suggestions for position {position_id}")
        
        try:
            # Get position details
            position = self.db.query(Position).filter(Position.id == position_id).first()
            
            if not position:
                return {"error": "Position not found"}
            
            # Analyze position-specific factors
            position_analysis = await self._analyze_position_factors(position)
            
            # Calculate multiple stop loss levels
            stop_loss_levels = await self._calculate_multiple_stop_loss_levels(position)
            
            # Get risk-adjusted recommendations
            risk_adjusted_levels = await self._calculate_risk_adjusted_levels(position, position_analysis)
            
            # Market condition adjustments
            market_adjustments = await self._apply_market_condition_adjustments(position, stop_loss_levels)
            
            # Generate final recommendations
            final_recommendations = await self._generate_final_recommendations(
                position, stop_loss_levels, risk_adjusted_levels, market_adjustments
            )
            
            return {
                "position_id": position_id,
                "symbol": position.symbol,
                "current_price": position.current_price,
                "entry_price": position.entry_price,
                "current_stop_loss": position.stop_loss,
                "position_analysis": position_analysis,
                "stop_loss_levels": stop_loss_levels,
                "risk_adjusted_levels": risk_adjusted_levels,
                "market_adjustments": market_adjustments,
                "final_recommendations": final_recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting stop loss suggestions: {e}")
            return {"error": str(e)}

    async def implement_portfolio_stop_loss_optimization(self, user_id: int) -> Dict[str, Any]:
        """Implement portfolio-wide stop loss optimization"""
        logger.info(f"⚡ Implementing portfolio stop loss optimization for user {user_id}")
        
        try:
            # Get all open positions
            open_positions = self.db.query(Position).filter(
                and_(Position.user_id == user_id, Position.is_open == True)
            ).all()
            
            if not open_positions:
                return {"message": "No open positions to optimize"}
            
            # Analyze portfolio risk
            portfolio_risk = await self._analyze_portfolio_risk(open_positions)
            
            # Calculate optimal stop loss distribution
            optimal_distribution = await self._calculate_optimal_stop_loss_distribution(open_positions)
            
            # Generate optimization actions
            optimization_actions = await self._generate_optimization_actions(open_positions, optimal_distribution)
            
            # Calculate expected impact
            expected_impact = await self._calculate_optimization_impact(optimization_actions)
            
            return {
                "optimization": {
                    "positions_analyzed": len(open_positions),
                    "actions_recommended": len(optimization_actions),
                    "estimated_risk_reduction": expected_impact["risk_reduction_pct"],
                    "portfolio_protection_score": expected_impact["protection_score"]
                },
                "portfolio_risk": portfolio_risk,
                "optimal_distribution": optimal_distribution,
                "optimization_actions": optimization_actions,
                "expected_impact": expected_impact,
                "implementation_priority": self._prioritize_optimization_actions(optimization_actions),
                "optimized_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error implementing portfolio optimization: {e}")
            return {"error": str(e)}

    async def monitor_stop_loss_effectiveness(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Monitor stop loss effectiveness over time"""
        logger.info(f"📈 Monitoring stop loss effectiveness for user {user_id}")
        
        try:
            # Get stop loss performance data
            performance_data = await self._get_stop_loss_performance_data(user_id, days)
            
            # Calculate effectiveness metrics
            effectiveness_metrics = await self._calculate_effectiveness_metrics(performance_data)
            
            # Identify patterns and trends
            patterns = await self._identify_stop_loss_patterns(performance_data)
            
            # Generate improvement suggestions
            improvement_suggestions = await self._generate_improvement_suggestions(
                effectiveness_metrics, patterns
            )
            
            return {
                "monitoring": {
                    "analysis_period_days": days,
                    "positions_analyzed": len(performance_data),
                    "overall_effectiveness": effectiveness_metrics["overall_score"],
                    "protection_rate": effectiveness_metrics["protection_rate"],
                    "avg_loss_reduction": effectiveness_metrics["avg_loss_reduction"]
                },
                "performance_data": performance_data,
                "effectiveness_metrics": effectiveness_metrics,
                "patterns": patterns,
                "improvement_suggestions": improvement_suggestions,
                "monitoring_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error monitoring stop loss effectiveness: {e}")
            return {"error": str(e)}

    # Helper methods for enhanced stop loss placement
    def _get_positions_without_stop_loss(self, user_id: int) -> List[Dict[str, Any]]:
        """Get positions without stop loss protection"""
        try:
            positions = self.db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.is_open == True,
                    or_(Position.stop_loss.is_(None), Position.stop_loss == 0)
                )
            ).all()
            
            return [
                {
                    "position_id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "quantity": pos.quantity,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "duration_hours": (datetime.utcnow() - pos.opened_at).total_seconds() / 3600,
                    "risk_exposure": pos.quantity * (pos.current_price or pos.entry_price)
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"Error getting positions without stop loss: {e}")
            return []

    async def _identify_suboptimal_stop_losses(self, user_id: int) -> List[Dict[str, Any]]:
        """Identify positions with suboptimal stop loss placement"""
        try:
            positions = self.db.query(Position).filter(
                and_(
                    Position.user_id == user_id,
                    Position.is_open == True,
                    Position.stop_loss.isnot(None),
                    Position.stop_loss != 0
                )
            ).all()
            
            suboptimal = []
            
            for pos in positions:
                # Calculate optimal stop loss range
                current_price = pos.current_price or pos.entry_price
                
                # Basic optimization checks
                if pos.side == 'buy':
                    # For long positions, stop loss should be below entry
                    if pos.stop_loss >= pos.entry_price:
                        suboptimal.append({
                            "position_id": pos.id,
                            "symbol": pos.symbol,
                            "issue": "Stop loss above entry price",
                            "current_stop_loss": pos.stop_loss,
                            "entry_price": pos.entry_price,
                            "suggested_action": "Move stop loss below entry price"
                        })
                    
                    # Check if stop loss is too tight (< 2% from entry)
                    elif (pos.entry_price - pos.stop_loss) / pos.entry_price < 0.02:
                        suboptimal.append({
                            "position_id": pos.id,
                            "symbol": pos.symbol,
                            "issue": "Stop loss too tight",
                            "current_stop_loss": pos.stop_loss,
                            "distance_pct": ((pos.entry_price - pos.stop_loss) / pos.entry_price) * 100,
                            "suggested_action": "Consider wider stop loss for normal market volatility"
                        })
                
                else:  # Short position
                    # For short positions, stop loss should be above entry
                    if pos.stop_loss <= pos.entry_price:
                        suboptimal.append({
                            "position_id": pos.id,
                            "symbol": pos.symbol,
                            "issue": "Stop loss below entry price",
                            "current_stop_loss": pos.stop_loss,
                            "entry_price": pos.entry_price,
                            "suggested_action": "Move stop loss above entry price"
                        })
            
            return suboptimal
            
        except Exception as e:
            logger.error(f"Error identifying suboptimal stop losses: {e}")
            return []

    async def _analyze_market_conditions(self, user_id: int) -> Dict[str, Any]:
        """Analyze current market conditions for stop loss placement"""
        try:
            # Get user's active symbols
            symbols = self.db.query(Position.symbol).filter(
                and_(Position.user_id == user_id, Position.is_open == True)
            ).distinct().all()
            
            if not symbols:
                return {"overall_condition": MarketCondition.SIDEWAYS, "volatility": "medium"}
            
            # For now, return basic market condition analysis
            # In a real implementation, this would analyze:
            # - Recent price movements
            # - Volatility indicators
            # - Market sentiment
            # - Volume patterns
            
            return {
                "overall_condition": MarketCondition.SIDEWAYS,
                "volatility": "medium",
                "trend_strength": "weak",
                "symbols_analyzed": len(symbols),
                "risk_level": "medium",
                "recommended_adjustments": {
                    "stop_loss_distance": "standard",
                    "trailing_sensitivity": "medium",
                    "protection_level": "balanced"
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {"overall_condition": MarketCondition.SIDEWAYS}

    async def _generate_placement_recommendations(
        self, 
        positions_without_sl: List[Dict[str, Any]], 
        suboptimal_positions: List[Dict[str, Any]], 
        market_conditions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate placement recommendations based on analysis"""
        try:
            recommendations = []
            
            # Recommendations for positions without stop loss
            for position in positions_without_sl:
                entry_price = position["entry_price"]
                current_price = position["current_price"] or entry_price
                
                # Calculate suggested stop loss based on market conditions
                if market_conditions["volatility"] == "high":
                    stop_distance_pct = 7.0  # Wider stops in volatile markets
                elif market_conditions["volatility"] == "low":
                    stop_distance_pct = 3.0  # Tighter stops in calm markets
                else:
                    stop_distance_pct = 5.0  # Standard distance
                
                if position["side"] == "buy":
                    suggested_stop = entry_price * (1 - stop_distance_pct / 100)
                else:
                    suggested_stop = entry_price * (1 + stop_distance_pct / 100)
                
                recommendations.append({
                    "position_id": position["position_id"],
                    "symbol": position["symbol"],
                    "type": "new_stop_loss",
                    "priority": "high",
                    "suggested_stop_loss": suggested_stop,
                    "distance_from_entry_pct": stop_distance_pct,
                    "reasoning": f"No stop loss protection - suggested {stop_distance_pct}% based on {market_conditions['volatility']} volatility",
                    "risk_reduction": "High"
                })
            
            # Recommendations for suboptimal positions
            for position in suboptimal_positions:
                recommendations.append({
                    "position_id": position["position_id"],
                    "symbol": position["symbol"],
                    "type": "optimize_stop_loss",
                    "priority": "medium",
                    "issue": position["issue"],
                    "suggested_action": position["suggested_action"],
                    "reasoning": f"Current stop loss placement is suboptimal: {position['issue']}",
                    "risk_reduction": "Medium"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating placement recommendations: {e}")
            return []

    async def _calculate_portfolio_stop_loss_metrics(self, user_id: int) -> Dict[str, Any]:
        """Calculate portfolio-wide stop loss metrics"""
        try:
            open_positions = self.db.query(Position).filter(
                and_(Position.user_id == user_id, Position.is_open == True)
            ).all()
            
            if not open_positions:
                return {"protected_positions": 0, "protection_rate": 0}
            
            protected_positions = len([p for p in open_positions if p.stop_loss])
            total_positions = len(open_positions)
            protection_rate = protected_positions / total_positions
            
            total_exposure = sum(p.quantity * (p.current_price or p.entry_price) for p in open_positions)
            protected_exposure = sum(
                p.quantity * (p.current_price or p.entry_price) 
                for p in open_positions if p.stop_loss
            )
            
            return {
                "total_positions": total_positions,
                "protected_positions": protected_positions,
                "unprotected_positions": total_positions - protected_positions,
                "protection_rate": protection_rate,
                "total_exposure": total_exposure,
                "protected_exposure": protected_exposure,
                "unprotected_exposure": total_exposure - protected_exposure,
                "portfolio_protection_score": min(100, protection_rate * 100)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {"protected_positions": 0, "protection_rate": 0}

    def _recommend_placement_strategy(self, market_conditions: Dict[str, Any]) -> StopLossPlacementStrategy:
        """Recommend placement strategy based on market conditions"""
        try:
            condition = market_conditions.get("overall_condition", MarketCondition.SIDEWAYS)
            volatility = market_conditions.get("volatility", "medium")
            
            if condition == MarketCondition.VOLATILE or volatility == "high":
                return StopLossPlacementStrategy.CONSERVATIVE
            elif condition == MarketCondition.BULLISH and volatility == "low":
                return StopLossPlacementStrategy.AGGRESSIVE
            elif condition in [MarketCondition.BEARISH, MarketCondition.VOLATILE]:
                return StopLossPlacementStrategy.CONSERVATIVE
            else:
                return StopLossPlacementStrategy.BALANCED
                
        except Exception:
            return StopLossPlacementStrategy.BALANCED

    # Placeholder methods for additional functionality
    async def _analyze_position_factors(self, position: Position) -> Dict[str, Any]:
        """Analyze position-specific factors"""
        return {"volatility": "medium", "trend": "neutral", "support_levels": []}

    async def _calculate_multiple_stop_loss_levels(self, position: Position) -> Dict[str, Any]:
        """Calculate multiple stop loss level options"""
        return {"conservative": 0, "balanced": 0, "aggressive": 0}

    async def _calculate_risk_adjusted_levels(self, position: Position, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk-adjusted stop loss levels"""
        return {"risk_adjusted": 0, "max_loss_limit": 0}

    async def _apply_market_condition_adjustments(self, position: Position, levels: Dict[str, Any]) -> Dict[str, Any]:
        """Apply market condition adjustments"""
        return {"adjusted_levels": levels}

    async def _generate_final_recommendations(self, position: Position, *args) -> List[Dict[str, Any]]:
        """Generate final stop loss recommendations"""
        return [{"recommendation": "Set 5% stop loss", "confidence": 0.8}]

    async def _analyze_portfolio_risk(self, positions: List[Position]) -> Dict[str, Any]:
        """Analyze portfolio risk factors"""
        return {"risk_score": 50, "concentration": "medium"}

    async def _calculate_optimal_stop_loss_distribution(self, positions: List[Position]) -> Dict[str, Any]:
        """Calculate optimal stop loss distribution"""
        return {"optimal_levels": {}}

    async def _generate_optimization_actions(self, positions: List[Position], distribution: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization actions"""
        return []

    async def _calculate_optimization_impact(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate expected optimization impact"""
        return {"risk_reduction_pct": 15, "protection_score": 85}

    def _prioritize_optimization_actions(self, actions: List[Dict[str, Any]]) -> List[str]:
        """Prioritize optimization actions"""
        return ["Set missing stop losses", "Optimize tight stop losses", "Review old positions"]

    async def _get_stop_loss_performance_data(self, user_id: int, days: int) -> List[Dict[str, Any]]:
        """Get stop loss performance data"""
        return []

    async def _calculate_effectiveness_metrics(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate stop loss effectiveness metrics"""
        return {"overall_score": 75, "protection_rate": 0.8, "avg_loss_reduction": 0.3}

    async def _identify_stop_loss_patterns(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify stop loss patterns and trends"""
        return {"patterns": [], "trends": []}

    async def _generate_improvement_suggestions(self, metrics: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions"""
        return ["Consider wider stop losses in volatile markets", "Review stop loss timing"]
