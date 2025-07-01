from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

celery_app = Celery(
    "trading_bot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.trading_tasks",
        "app.tasks.cassava_data_tasks",
        "app.tasks.cassava_bot_tasks",
        "app.tasks.manual_stop_loss_tasks",
        "app.tasks.position_tasks",
        "app.tasks.advanced_stop_loss_tasks",
        "app.tasks.automated_cassava_tasks",
        "app.tasks.grid_trading_tasks",
        "app.tasks.trade_analytics_tasks",
        "app.tasks.example_tasks"
    ],
    beat_scheduler='redbeat.RedBeatScheduler'
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    broker_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
    },
    redis_retry_on_timeout=True,
    redis_socket_connect_timeout=30,
    redis_socket_timeout=30,
    redis_max_connections=20,
    worker_max_tasks_per_child=1000,
    task_routes={
        "tasks.update_all_position_prices": {"queue": "position_updates"},
        "tasks.update_user_position_prices": {"queue": "position_updates"},
        "tasks.calculate_daily_pnl_records": {"queue": "pnl_calculations"},
        "tasks.run_trading_bot_strategy": {"queue": "trading"},
        "tasks.process_cassava_bot_signals_and_trades": {"queue": "cassava_bots"},
        "tasks.update_cassava_trend_data": {"queue": "data_updates"},
        "tasks.update_manual_stop_losses": {"queue": "stop_loss_management"},
        "tasks.update_cassava_bot_stop_losses": {"queue": "stop_loss_management"},
        "tasks.update_advanced_stop_losses": {"queue": "advanced_stop_loss"},
        "tasks.analyze_stop_loss_performance": {"queue": "analytics"},
        "tasks.optimize_stop_loss_parameters": {"queue": "optimization"},
        "tasks.automated_cassava_data_generation": {"queue": "automated_cassava"},
        "tasks.cassava_health_monitor": {"queue": "monitoring"},
        "tasks.cassava_gap_scanner": {"queue": "monitoring"},
        "tasks.cassava_data_validator": {"queue": "validation"},
        "tasks.cassava_performance_optimizer": {"queue": "optimization"},
        "tasks.cassava_emergency_backfill": {"queue": "emergency"},
        "tasks.cassava_system_report": {"queue": "reporting"},
        "tasks.process_active_grids": {"queue": "grid_trading"},
        "tasks.initialize_new_grids": {"queue": "grid_trading"},
        "tasks.grid_rebalancing": {"queue": "grid_rebalancing"},
        "tasks.grid_performance_monitor": {"queue": "monitoring"},
        "tasks.emergency_grid_stop": {"queue": "emergency"},
        "tasks.cleanup_completed_grids": {"queue": "cleanup"},
        "tasks.position_safety_monitor": {"queue": "safety"},
        "tasks.emergency_position_scan": {"queue": "emergency"},
        "tasks.check_unprotected_position": {"queue": "safety"},
    },
    beat_schedule={
        # Position price updates every 2 minutes
        'update-all-position-prices': {
            'task': 'tasks.update_all_position_prices',
            'schedule': crontab(minute='*/2'),
        },
        # Daily P&L calculation at 00:01 UTC
        'calculate-daily-pnl-records': {
            'task': 'tasks.calculate_daily_pnl_records',
            'schedule': crontab(hour=0, minute=1),
        },
        # Cleanup old performance records weekly (Sunday at 02:00 UTC)
        'cleanup-old-performance-records': {
            'task': 'tasks.cleanup_old_performance_records',
            'schedule': crontab(hour=2, minute=0, day_of_week=0),
        },
        # Daily Cassava data update at 00:05 UTC
        'update-cassava-data-daily': {
            'task': 'tasks.update_cassava_trend_data',
            'schedule': crontab(hour=0, minute=5),
        },
        # Daily Cassava BOT signal generation and trading at 00:05 UTC (same time as data update)
        'cassava-bot-signals-and-trading': {
            'task': 'tasks.process_cassava_bot_signals_and_trades',
            'schedule': crontab(hour=0, minute=5),
        },
        # Daily Cassava data cleanup at 00:10 UTC
        'cleanup-old-cassava-data': {
            'task': 'tasks.cleanup_old_cassava_data',
            'schedule': crontab(hour=0, minute=10),
        },
        # Daily manual stop loss update at 00:15 UTC
        'update-manual-stop-losses': {
            'task': 'tasks.update_manual_stop_losses',
            'schedule': crontab(hour=0, minute=15),
        },
        # Daily Cassava BOT stop loss update at 00:20 UTC
        'update-cassava-bot-stop-losses': {
            'task': 'tasks.update_cassava_bot_stop_losses',
            'schedule': crontab(hour=0, minute=20),
        },
        # Position sync every 4 hours
        'sync-open-positions': {
            'task': 'tasks.sync_open_positions',
            'schedule': crontab(minute=0, hour='*/4'),
        },
        # Stop loss sweep every hour
        'sweep-failed-stop-losses': {
            'task': 'tasks.sweep_and_close_failed_stop_loss_trades',
            'schedule': crontab(minute=0),
        },
        # Advanced stop loss updates every 5 minutes
        'update-advanced-stop-losses': {
            'task': 'tasks.update_advanced_stop_losses',
            'schedule': crontab(minute='*/5'),
        },
        # Stop loss performance analysis daily at 01:00 UTC
        'analyze-stop-loss-performance': {
            'task': 'tasks.analyze_stop_loss_performance',
            'schedule': crontab(hour=1, minute=0),
        },
        # Automated Cassava data generation every 30 minutes
        'automated-cassava-generation': {
            'task': 'tasks.automated_cassava_data_generation',
            'schedule': crontab(minute='*/30'),
        },
        # Cassava health monitoring every 15 minutes
        'cassava-health-monitor': {
            'task': 'tasks.cassava_health_monitor',
            'schedule': crontab(minute='*/15'),
        },
        # Cassava gap scanning every 2 hours
        'cassava-gap-scanner': {
            'task': 'tasks.cassava_gap_scanner',
            'schedule': crontab(minute=0, hour='*/2'),
        },
        # Data validation daily at 02:00 UTC
        'cassava-data-validation': {
            'task': 'tasks.cassava_data_validator',
            'schedule': crontab(hour=2, minute=0),
        },
        # Performance optimization weekly (Sunday at 03:00 UTC)
        'cassava-performance-optimization': {
            'task': 'tasks.cassava_performance_optimizer',
            'schedule': crontab(hour=3, minute=0, day_of_week=0),
        },
        # System report daily at 06:00 UTC
        'cassava-system-report': {
            'task': 'tasks.cassava_system_report',
            'schedule': crontab(hour=6, minute=0),
        },
        # Grid Trading Tasks
        # Process active grids every 1 minute
        'process-active-grids': {
            'task': 'tasks.process_active_grids',
            'schedule': crontab(minute='*/1'),
        },
        # Initialize new grids every 5 minutes
        'initialize-new-grids': {
            'task': 'tasks.initialize_new_grids',
            'schedule': crontab(minute='*/5'),
        },
        # Grid rebalancing every 15 minutes
        'grid-rebalancing': {
            'task': 'tasks.grid_rebalancing',
            'schedule': crontab(minute='*/15'),
        },
        # Grid performance monitoring every hour
        'grid-performance-monitor': {
            'task': 'tasks.grid_performance_monitor',
            'schedule': crontab(minute=0),
        },
        # Grid cleanup daily at 04:00 UTC
        'cleanup-completed-grids': {
            'task': 'tasks.cleanup_completed_grids',
            'schedule': crontab(hour=4, minute=0),
        },
        
        # Trade Analytics Tasks
        # Real-time metrics update every 2 minutes
        'update-real-time-metrics': {
            'task': 'tasks.update_real_time_metrics',
            'schedule': crontab(minute='*/2'),
        },
        # Daily reports generation at 01:00 UTC
        'generate-daily-reports': {
            'task': 'tasks.generate_daily_reports',
            'schedule': crontab(hour=1, minute=0),
        },
        # Activity monitoring every 15 minutes
        'activity-monitor': {
            'task': 'tasks.activity_monitor',
            'schedule': crontab(minute='*/15'),
        },
        # System health check every hour at minute 30
        'trade-analytics-health-check': {
            'task': 'tasks.system_health_check',
            'schedule': crontab(minute=30),
        },
        # Cleanup old metrics daily at 03:00 UTC
        'cleanup-old-metrics': {
            'task': 'tasks.cleanup_old_metrics',
            'schedule': crontab(hour=3, minute=0),
        },
        
        # COMPREHENSIVE POSITION SAFETY SYSTEM
        # Position safety monitor every 15 minutes (15-minute retry + 4-hour force closure)
        'position-safety-monitor': {
            'task': 'tasks.position_safety_monitor',
            'schedule': crontab(minute='*/15'),
        },
    }
) 