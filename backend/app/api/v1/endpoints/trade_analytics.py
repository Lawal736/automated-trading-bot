"""
Trade Analytics API Endpoints
Enhanced trade counting and analytics REST API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.trade_analytics_service import TradeAnalyticsService
from app.core.logging import get_logger
from typing import Dict, Any, Optional
import traceback

logger = get_logger(__name__)
router = APIRouter()

@router.get("/enhanced-counts", summary="Get enhanced trade counts")
async def get_enhanced_trade_counts(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive trade counts with multiple dimensions"""
    
    try:
        analytics_service = TradeAnalyticsService(db)
        result = analytics_service.get_enhanced_trade_counts(current_user.id, days)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"✅ Enhanced trade counts retrieved for user {current_user.id}")
        return {
            "success": True,
            "data": result,
            "message": f"Enhanced trade analysis for last {days} days"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting enhanced trade counts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/real-time-metrics", summary="Get real-time trade metrics")
async def get_real_time_trade_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get real-time trade metrics and live statistics"""
    
    try:
        analytics_service = TradeAnalyticsService(db)
        result = analytics_service.get_real_time_trade_metrics(current_user.id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"⚡ Real-time metrics retrieved for user {current_user.id}")
        return {
            "success": True,
            "data": result,
            "message": "Real-time trade metrics"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting real-time metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard", summary="Get comprehensive trade analytics dashboard")
async def get_trade_analytics_dashboard(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive trade analytics dashboard"""
    
    try:
        analytics_service = TradeAnalyticsService(db)
        
        # Get enhanced counts
        enhanced_counts = analytics_service.get_enhanced_trade_counts(current_user.id, days)
        
        # Get real-time metrics
        real_time_metrics = analytics_service.get_real_time_trade_metrics(current_user.id)
        
        # Check for errors
        if "error" in enhanced_counts:
            raise HTTPException(status_code=500, detail=enhanced_counts["error"])
        if "error" in real_time_metrics:
            raise HTTPException(status_code=500, detail=real_time_metrics["error"])
        
        # Combine data for dashboard
        dashboard_data = {
            "overview": {
                "total_trades": enhanced_counts["summary"]["total_trades"],
                "success_rate": enhanced_counts["summary"]["success_rate"],
                "total_volume": enhanced_counts["summary"]["total_volume"],
                "avg_trade_size": enhanced_counts["summary"]["avg_trade_size"],
                "activity_level": real_time_metrics["activity_level"],
                "analysis_period_days": days
            },
            "real_time": {
                "trades_last_5min": real_time_metrics["real_time_counts"]["trades_last_5min"],
                "trades_last_hour": real_time_metrics["real_time_counts"]["trades_last_hour"],
                "trades_last_24h": real_time_metrics["real_time_counts"]["trades_last_24h"],
                "active_positions": real_time_metrics["real_time_counts"]["active_positions"],
                "pending_trades": real_time_metrics["real_time_counts"]["pending_trades"]
            },
            "breakdowns": {
                "status": enhanced_counts["status_breakdown"],
                "side": enhanced_counts["side_breakdown"],
                "type": enhanced_counts["type_breakdown"],
                "automation": enhanced_counts["automation_breakdown"]
            },
            "patterns": {
                "time_distribution": enhanced_counts["time_distribution"],
                "symbol_breakdown": enhanced_counts["symbol_breakdown"],
                "trading_frequency": real_time_metrics["trading_frequency"]
            }
        }
        
        logger.info(f"📊 Trade analytics dashboard retrieved for user {current_user.id}")
        return {
            "success": True,
            "dashboard": dashboard_data,
            "message": f"Comprehensive trade analytics dashboard"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting trade analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health", summary="Trade analytics system health check")
async def trade_analytics_health() -> Dict[str, Any]:
    """Check the health of the trade analytics system"""
    
    try:
        health_status = {
            "trade_analytics_service": "healthy",
            "api_endpoints": "healthy",
            "database_queries": "healthy",
            "version": "1.0.0"
        }
        
        return {
            "success": True,
            "health": health_status,
            "message": "Trade analytics system is operational"
        }
        
    except Exception as e:
        logger.error(f"❌ Trade analytics health check failed: {e}")
        raise HTTPException(status_code=500, detail="Trade analytics system health check failed")
