from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.models.base_class import Base

logger = get_logger(__name__)

# Global variables for engine and session
engine = None
SessionLocal = None

def get_engine():
    """Get or create the database engine with the correct URL"""
    global engine
    if engine is None:
        # Use DATABASE_URL environment variable directly if available, otherwise fall back to settings
        database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URI
        
        logger.info(f"Creating database engine with URL: {database_url}")
        
        # Create a synchronous engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=settings.DB_ECHO,
        )
        
        # Log the actual engine URL for verification
        logger.info(f"Engine created with URL components - User: {engine.url.username}, Host: {engine.url.host}, DB: {engine.url.database}")
    
    return engine

def get_session_maker():
    """Get or create the session maker"""
    global SessionLocal
    if SessionLocal is None:
        # Create a session maker for synchronous sessions
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return SessionLocal

def get_db() -> Generator[Session, None, None]:
    """Provides a synchronous database session to a decorated function."""
    session_maker = get_session_maker()
    db = session_maker()
    try:
        yield db
    finally:
        db.close()
        logger.info({"event": "Database connection closed"})

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        logger.info({"event": "Initializing database"})
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info({"event": "Database initialized successfully"})
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True) 