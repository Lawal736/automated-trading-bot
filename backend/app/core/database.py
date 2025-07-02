from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.models.base_class import Base

logger = get_logger(__name__)

# Use DATABASE_URL environment variable directly if available, otherwise fall back to settings
database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URI

# Create a synchronous engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

# Create a session maker for synchronous sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

def get_db() -> Generator[Session, None, None]:
    """Provides a synchronous database session to a decorated function."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.info({"event": "Database connection closed"})

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        logger.info({"event": "Initializing database"})
        Base.metadata.create_all(bind=engine)
        logger.info({"event": "Database initialized successfully"})
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True) 