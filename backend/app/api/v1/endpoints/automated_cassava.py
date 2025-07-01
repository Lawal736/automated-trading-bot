"""
Automated Cassava Data Generation API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from .... import models
from ....api import deps
from ....services.automated_cassava_service import AutomatedCassavaService
from ....tasks.automated_cassava_tasks import (
    automated_cassava_data_generation,
    cassava_health_monitor,
    cassava_gap_scanner,
    cassava_data_validator,
    cassava_performance_optimizer,
    cassava_emergency_backfill,
    cassava_system_report
)
from ....core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/status")
def get_system_status(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get current automated Cassava system status
    """
    try:
        service = AutomatedCassavaService(db)
        status = service.get_system_status()
        
        return {
            'success': True,
            'data': status,
            'timestamp': status['timestamp']
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@router.post("/generate")
async def trigger_automated_generation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger automated Cassava data generation
    """
    try:
        # Only allow admin users to trigger generation
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Trigger the task
        task = automated_cassava_data_generation.delay()
        
        return {
            "success": True,
            "message": "Automated Cassava data generation triggered",
            "task_id": task.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering automated generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger generation")


@router.post("/health-check")
async def trigger_health_monitor(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger health monitoring
    """
    try:
        # Trigger the task
        task = cassava_health_monitor.delay()
        
        return {
            "success": True,
            "message": "Health monitor triggered",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error triggering health monitor: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger health monitor")


@router.post("/scan-gaps")
async def trigger_gap_scanner(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger gap scanning
    """
    try:
        # Trigger the task
        task = cassava_gap_scanner.delay()
        
        return {
            "success": True,
            "message": "Gap scanner triggered",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error triggering gap scanner: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger gap scanner")


@router.post("/validate")
async def trigger_data_validation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger comprehensive data validation
    """
    try:
        # Trigger the task
        task = cassava_data_validator.delay()
        
        return {
            "success": True,
            "message": "Data validation triggered",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error triggering data validation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger validation")


@router.post("/optimize")
async def trigger_performance_optimization(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Manually trigger performance optimization
    """
    try:
        # Only allow admin users to trigger optimization
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Trigger the task
        task = cassava_performance_optimizer.delay()
        
        return {
            "success": True,
            "message": "Performance optimization triggered",
            "task_id": task.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger optimization")


@router.post("/emergency-backfill")
async def trigger_emergency_backfill(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    days_back: int = 7,
) -> Dict[str, Any]:
    """
    Trigger emergency backfill for recent days
    """
    try:
        # Only allow admin users to trigger emergency backfill
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Validate days_back parameter
        if days_back < 1 or days_back > 30:
            raise HTTPException(status_code=400, detail="days_back must be between 1 and 30")
        
        # Trigger the task
        task = cassava_emergency_backfill.delay(days_back)
        
        return {
            "success": True,
            "message": f"Emergency backfill triggered for last {days_back} days",
            "task_id": task.id,
            "days_back": days_back
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering emergency backfill: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger emergency backfill")


@router.get("/report")
async def get_system_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Generate comprehensive system report
    """
    try:
        # Trigger the task
        task = cassava_system_report.delay()
        
        return {
            "success": True,
            "message": "System report generation triggered",
            "task_id": task.id,
            "note": "Report will be available after task completion"
        }
        
    except Exception as e:
        logger.error(f"Error triggering system report: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger system report")


@router.get("/gaps/analysis")
async def get_gap_analysis(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get real-time gap analysis
    """
    try:
        service = AutomatedCassavaService(db)
        
        # Run gap analysis in background
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        gap_analysis = loop.run_until_complete(service._analyze_all_gaps())
        
        loop.close()
        
        return {
            'success': True,
            'data': gap_analysis,
            'summary': gap_analysis['gap_summary'],
            'critical_gaps_count': len(gap_analysis['critical_gaps'])
        }
        
    except Exception as e:
        logger.error(f"Error getting gap analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get gap analysis")


@router.get("/health/detailed")
async def get_detailed_health_check(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get detailed health check results
    """
    try:
        service = AutomatedCassavaService(db)
        
        # Run health check in background
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        health_results = loop.run_until_complete(service._validate_data_health())
        
        loop.close()
        
        return {
            'success': True,
            'data': health_results,
            'status': health_results['status'],
            'issues_count': len(health_results['issues']),
            'recommendations': health_results['recommendations']
        }
        
    except Exception as e:
        logger.error(f"Error getting detailed health check: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health check")


@router.get("/monitoring/dashboard")
def get_monitoring_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get comprehensive monitoring dashboard data
    """
    try:
        service = AutomatedCassavaService(db)
        
        # Get basic status
        status = service.get_system_status()
        
        # Get record counts
        from app.services.cassava_data_service import CassavaDataService
        cassava_service = CassavaDataService(db)
        counts = cassava_service.get_records_count_per_symbol()
        
        # Calculate metrics
        total_records = sum(counts.values())
        expected_total = len(service.trading_pairs) * 50
        symbols_with_full_data = len([c for c in counts.values() if c == 50])
        
        dashboard = {
            'timestamp': status['timestamp'],
            'system_status': status['status'],
            'health_score': status['health_score'],
            'overview': {
                'total_symbols': len(service.trading_pairs),
                'symbols_with_data': len(counts),
                'symbols_with_full_data': symbols_with_full_data,
                'total_records': total_records,
                'expected_records': expected_total,
                'data_completeness_percent': (total_records / expected_total * 100) if expected_total > 0 else 0
            },
            'date_range': status['date_range'],
            'symbol_counts': counts,
            'alerts': []
        }
        
        # Generate alerts
        if dashboard['health_score'] < 90:
            dashboard['alerts'].append({
                'level': 'warning',
                'message': f"Health score is {dashboard['health_score']:.1f}% - below recommended threshold"
            })
        
        if symbols_with_full_data < len(service.trading_pairs):
            missing_symbols = len(service.trading_pairs) - symbols_with_full_data
            dashboard['alerts'].append({
                'level': 'info',
                'message': f"{missing_symbols} symbols have incomplete data (less than 50 records)"
            })
        
        if total_records < expected_total * 0.95:
            dashboard['alerts'].append({
                'level': 'warning',
                'message': "Total data completeness is below 95%"
            })
        
        return {
            'success': True,
            'data': dashboard
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


@router.get("/symbols/status")
def get_symbols_status(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get detailed status for each trading symbol
    """
    try:
        service = AutomatedCassavaService(db)
        
        # Get counts per symbol
        from app.services.cassava_data_service import CassavaDataService
        cassava_service = CassavaDataService(db)
        counts = cassava_service.get_records_count_per_symbol()
        
        # Get latest data per symbol
        from app.models.trading import CassavaTrendData
        from sqlalchemy import func, desc
        
        latest_data_query = db.query(
            CassavaTrendData.symbol,
            func.max(CassavaTrendData.date).label('latest_date')
        ).group_by(CassavaTrendData.symbol).all()
        
        latest_data_by_symbol = {symbol: latest_date for symbol, latest_date in latest_data_query}
        
        # Build status for each symbol
        symbols_status = []
        
        for symbol in service.trading_pairs:
            record_count = counts.get(symbol, 0)
            latest_date = latest_data_by_symbol.get(symbol)
            
            # Calculate status
            if record_count == 50:
                status = 'healthy'
            elif record_count > 40:
                status = 'needs_attention'
            elif record_count > 0:
                status = 'unhealthy'
            else:
                status = 'no_data'
            
            # Calculate days behind
            days_behind = 0
            if latest_date:
                from datetime import datetime, timedelta
                yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                if latest_date < yesterday:
                    days_behind = (yesterday - latest_date).days
            
            symbols_status.append({
                'symbol': symbol,
                'record_count': record_count,
                'expected_count': 50,
                'latest_date': latest_date,
                'days_behind': days_behind,
                'status': status,
                'completion_percent': (record_count / 50 * 100) if record_count <= 50 else 100
            })
        
        # Sort by status (unhealthy first)
        status_priority = {'no_data': 0, 'unhealthy': 1, 'needs_attention': 2, 'healthy': 3}
        symbols_status.sort(key=lambda x: status_priority[x['status']])
        
        return {
            'success': True,
            'data': symbols_status,
            'summary': {
                'total_symbols': len(symbols_status),
                'healthy': len([s for s in symbols_status if s['status'] == 'healthy']),
                'needs_attention': len([s for s in symbols_status if s['status'] == 'needs_attention']),
                'unhealthy': len([s for s in symbols_status if s['status'] == 'unhealthy']),
                'no_data': len([s for s in symbols_status if s['status'] == 'no_data'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get symbols status") 