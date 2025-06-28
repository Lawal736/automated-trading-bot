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
        "app.tasks.cassava_data_tasks"
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
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'daily-cassava-data-update': {
        'task': 'tasks.update_cassava_trend_data',
        'schedule': crontab(hour=1, minute=0),  # Run at 1:00 AM UTC daily
    },
    'daily-cassava-data-cleanup': {
        'task': 'tasks.cleanup_old_cassava_data',
        'schedule': crontab(hour=2, minute=0),  # Run at 2:00 AM UTC daily (after update)
    },
} 