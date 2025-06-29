from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.example_tasks",
        "app.tasks.trading_tasks",
        "app.tasks.cassava_data_tasks",
        "app.tasks.manual_stop_loss_tasks"
    ],
    beat_scheduler='redbeat.RedBeatScheduler'
)

celery_app.conf.update(
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
    beat_schedule={
        # Daily Cassava data update at 00:05 UTC
        'update-cassava-data-daily': {
            'task': 'tasks.update_cassava_trend_data',
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
    }
) 