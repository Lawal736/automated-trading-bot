from app.core.celery import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)

@celery_app.task
def example_task(x, y):
    logger.info(f"Running example task with args: {x}, {y}")
    return x + y 