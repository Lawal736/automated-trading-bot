import logging
import sys
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging():
    """Setup structured logging configuration"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format=settings.LOG_FORMAT,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        stream=sys.stdout,
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    
    # Create logger instance
    logger = structlog.get_logger()
    logger.info("Logging configured successfully")


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def log_trade_event(event_type: str, data: Dict[str, Any], user_id: int = None):
    """Log trading events with structured data"""
    logger = get_logger("trading")
    log_data = {
        "event_type": event_type,
        "data": data,
        "user_id": user_id,
        "timestamp": structlog.processors.TimeStamper(fmt="iso")
    }
    logger.info("trading_event", **log_data)


def log_strategy_event(event_type: str, strategy_id: int, data: Dict[str, Any]):
    """Log strategy events with structured data"""
    logger = get_logger("strategy")
    log_data = {
        "event_type": event_type,
        "strategy_id": strategy_id,
        "data": data,
        "timestamp": structlog.processors.TimeStamper(fmt="iso")
    }
    logger.info("strategy_event", **log_data)


def log_user_event(event_type: str, user_id: int, data: Dict[str, Any]):
    """Log user events with structured data"""
    logger = get_logger("user")
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "data": data,
        "timestamp": structlog.processors.TimeStamper(fmt="iso")
    }
    logger.info("user_event", **log_data) 