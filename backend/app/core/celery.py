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
    }
) 