"""
Automated Cassava Data Generation Tasks
Comprehensive task system for eliminating manual backfill
"""

from celery import shared_task
from app.core.database import SessionLocal
from app.services.automated_cassava_service import AutomatedCassavaService
from app.core.celery import celery_app
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.automated_cassava_data_generation")
def automated_cassava_data_generation() -> Dict[str, Any]:
    """
    Main automated Cassava data generation task
    Runs comprehensive gap detection and intelligent backfill
    """
    db = SessionLocal()
    try:
        logger.info("🤖 Starting automated Cassava data generation")
        
        service = AutomatedCassavaService(db)
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(service.run_automated_data_generation())
        
        loop.close()
        
        # Log results
        if results['status'] == 'completed':
            logger.info(f"✅ Automated generation completed: {results['gaps_filled']} gaps filled, {results['total_records_created']} records created")
        else:
            logger.error(f"❌ Automated generation failed: {results.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in automated Cassava data generation: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow(),
            'gaps_filled': 0,
            'total_records_created': 0
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_health_monitor")
def cassava_health_monitor() -> Dict[str, Any]:
    """
    Continuous health monitoring for Cassava data
    Detects issues and triggers automatic fixes
    """
    db = SessionLocal()
    try:
        logger.info("🔍 Running Cassava health monitor")
        
        service = AutomatedCassavaService(db)
        status = service.get_system_status()
        
        # Check if intervention needed
        health_score = status.get('health_score', 0)
        
        results = {
            'timestamp': datetime.utcnow(),
            'health_score': health_score,
            'status': status['status'],
            'intervention_needed': False,
            'action_taken': 'none'
        }
        
        # Trigger automated fix if health score is low
        if health_score < 90:
            logger.warning(f"⚠️ Health score below threshold: {health_score}%. Triggering automated fix.")
            
            # Trigger automated data generation
            automated_task = automated_cassava_data_generation.delay()
            
            results['intervention_needed'] = True
            results['action_taken'] = 'triggered_automated_generation'
            results['task_id'] = automated_task.id
            
        elif health_score < 95:
            logger.info(f"🔶 Health score slightly low: {health_score}%. Monitoring closely.")
            results['action_taken'] = 'monitoring'
        else:
            logger.info(f"✅ System healthy: {health_score}%")
            results['action_taken'] = 'none_needed'
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in health monitor: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'status': 'error',
            'error': str(e),
            'health_score': 0,
            'intervention_needed': False
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_gap_scanner")
def cassava_gap_scanner() -> Dict[str, Any]:
    """
    Proactive gap scanner - detects gaps before they become critical
    """
    db = SessionLocal()
    try:
        logger.info("🔍 Scanning for Cassava data gaps")
        
        service = AutomatedCassavaService(db)
        
        # Run async gap analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        gap_analysis = loop.run_until_complete(service._analyze_all_gaps())
        
        loop.close()
        
        results = {
            'timestamp': datetime.utcnow(),
            'total_gaps': len(gap_analysis['critical_gaps']),
            'critical_gaps': len([g for g in gap_analysis['critical_gaps'] if g['priority'] == 'high']),
            'data_completeness': gap_analysis['gap_summary']['data_completeness_percent'],
            'action_needed': False,
            'recommendations': []
        }
        
        # Determine if action needed
        if results['critical_gaps'] > 0:
            results['action_needed'] = True
            results['recommendations'].append('Run immediate gap filling for critical gaps')
            
            # Auto-trigger if critical gaps are manageable
            if results['critical_gaps'] <= 10:
                logger.info(f"🔧 Auto-triggering gap fill for {results['critical_gaps']} critical gaps")
                automated_task = automated_cassava_data_generation.delay()
                results['auto_triggered'] = True
                results['task_id'] = automated_task.id
        
        if results['data_completeness'] < 95:
            results['recommendations'].append('Consider running full data validation')
        
        logger.info(f"📊 Gap scan complete: {results['total_gaps']} gaps found, {results['critical_gaps']} critical")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in gap scanner: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'status': 'error',
            'error': str(e),
            'total_gaps': 0,
            'critical_gaps': 0
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_data_validator")
def cassava_data_validator() -> Dict[str, Any]:
    """
    Comprehensive data validation task
    """
    db = SessionLocal()
    try:
        logger.info("✅ Running comprehensive data validation")
        
        service = AutomatedCassavaService(db)
        
        # Run async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        validation_results = loop.run_until_complete(service._validate_data_health())
        
        loop.close()
        
        results = {
            'timestamp': datetime.utcnow(),
            'status': validation_results['status'],
            'issues_found': len(validation_results['issues']),
            'recommendations': validation_results['recommendations'],
            'metrics': validation_results['metrics'],
            'needs_attention': validation_results['status'] != 'healthy'
        }
        
        if validation_results['issues']:
            logger.warning(f"⚠️ Validation found {len(validation_results['issues'])} issues")
            for issue in validation_results['issues']:
                logger.warning(f"  - {issue['type']}: {issue}")
        else:
            logger.info("✅ Data validation passed - no issues found")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in data validation: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'status': 'error',
            'error': str(e),
            'issues_found': 0,
            'needs_attention': True
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_performance_optimizer")
def cassava_performance_optimizer() -> Dict[str, Any]:
    """
    Performance optimization task for Cassava data storage
    """
    db = SessionLocal()
    try:
        logger.info("🚀 Running performance optimization")
        
        service = AutomatedCassavaService(db)
        
        # Run async optimization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        optimization_results = loop.run_until_complete(service._optimize_data_storage())
        
        loop.close()
        
        results = {
            'timestamp': datetime.utcnow(),
            'cleaned_records': optimization_results['cleaned_records'],
            'optimized_indexes': optimization_results['optimized_indexes'],
            'actions': optimization_results['actions'],
            'success': 'error' not in optimization_results
        }
        
        logger.info(f"🚀 Optimization complete: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in performance optimization: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'success': False,
            'error': str(e),
            'cleaned_records': 0
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_emergency_backfill")
def cassava_emergency_backfill(days_back: int = 7) -> Dict[str, Any]:
    """
    Emergency backfill task for critical data recovery
    """
    db = SessionLocal()
    try:
        logger.info(f"🚨 Running emergency backfill for last {days_back} days")
        
        service = AutomatedCassavaService(db)
        
        # Calculate date range
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        start_date = end_date - timedelta(days=days_back-1)
        
        # Run async backfill
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(service._fill_date_range(start_date, end_date))
        
        loop.close()
        
        results = {
            'timestamp': datetime.utcnow(),
            'start_date': start_date,
            'end_date': end_date,
            'days_processed': days_back,
            'status': 'completed'
        }
        
        logger.info(f"🚨 Emergency backfill completed for {days_back} days")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in emergency backfill: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'status': 'failed',
            'error': str(e),
            'days_processed': 0
        }
    finally:
        db.close()


@celery_app.task(name="tasks.cassava_system_report")
def cassava_system_report() -> Dict[str, Any]:
    """
    Generate comprehensive system report
    """
    db = SessionLocal()
    try:
        logger.info("📊 Generating Cassava system report")
        
        service = AutomatedCassavaService(db)
        
        # Get system status
        status = service.get_system_status()
        
        # Run comprehensive analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        gap_analysis = loop.run_until_complete(service._analyze_all_gaps())
        health_check = loop.run_until_complete(service._validate_data_health())
        
        loop.close()
        
        report = {
            'timestamp': datetime.utcnow(),
            'system_status': status,
            'gap_analysis': gap_analysis['gap_summary'],
            'health_check': {
                'status': health_check['status'],
                'issues_count': len(health_check['issues']),
                'metrics': health_check['metrics']
            },
            'recommendations': [],
            'overall_health': 'unknown'
        }
        
        # Generate recommendations
        if status['health_score'] < 90:
            report['recommendations'].append('Immediate gap filling required')
        if gap_analysis['gap_summary']['critical_gaps_count'] > 0:
            report['recommendations'].append('Address critical data gaps')
        if health_check['status'] != 'healthy':
            report['recommendations'].extend(health_check['recommendations'])
        
        # Determine overall health
        if status['health_score'] >= 95 and health_check['status'] == 'healthy':
            report['overall_health'] = 'excellent'
        elif status['health_score'] >= 85 and health_check['status'] in ['healthy', 'needs_attention']:
            report['overall_health'] = 'good'
        elif status['health_score'] >= 70:
            report['overall_health'] = 'fair'
        else:
            report['overall_health'] = 'poor'
        
        logger.info(f"📊 System report generated: {report['overall_health']} health")
        return report
        
    except Exception as e:
        logger.error(f"❌ Error generating system report: {e}")
        return {
            'timestamp': datetime.utcnow(),
            'status': 'error',
            'error': str(e),
            'overall_health': 'unknown'
        }
    finally:
        db.close() 