from typing import List, Optional
from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Project settings
    PROJECT_NAME: str = "Automated Trading Bot Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["http://localhost"]  # Only allow localhost for CORS
    
    # Trusted host settings (for TrustedHostMiddleware)
    TRUSTED_HOSTS: List[str] = ["*"]  # Allow all hosts in development
    
    # Database settings
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_USER: str = "trading_user"
    POSTGRES_PASSWORD: str = "your_strong_password"
    POSTGRES_DB: str = "trading_bot"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str = "postgresql://trading_user:your_strong_password@postgres:5432/trading_bot"
    DATABASE_URI: str = "postgresql://trading_user:your_strong_password@postgres:5432/trading_bot"
    ASYNC_DATABASE_URI: str = "postgresql+asyncpg://trading_user:your_strong_password@postgres:5432/trading_bot"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Redis settings
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # RabbitMQ settings
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    
    # Exchange API settings
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    BINANCE_TESTNET: bool = True
    
    GATEIO_API_KEY: Optional[str] = None
    GATEIO_SECRET_KEY: Optional[str] = None
    
    KUCOIN_API_KEY: Optional[str] = None
    KUCOIN_SECRET_KEY: Optional[str] = None
    KUCOIN_PASSPHRASE: Optional[str] = None
    
    BINGX_API_KEY: Optional[str] = None
    BINGX_SECRET_KEY: Optional[str] = None
    
    BITGET_API_KEY: Optional[str] = None
    BITGET_SECRET_KEY: Optional[str] = None
    BITGET_PASSPHRASE: Optional[str] = None
    
    # Email settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Trading settings
    DEFAULT_LEVERAGE: int = 1
    MAX_LEVERAGE: int = 100
    MIN_ORDER_SIZE: float = 0.001
    MAX_ORDER_SIZE: float = 1000000
    
    # Backtesting settings
    BACKTEST_DATA_DIR: str = "data/backtest"
    MAX_BACKTEST_DAYS: int = 365
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # WebSocket settings
    WEBSOCKET_PING_INTERVAL: int = 20
    WEBSOCKET_PING_TIMEOUT: int = 20
    
    DB_ECHO: bool = False
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # New setting
    POSITION_SYNC_INTERVAL_MINUTES: int = int(os.getenv("POSITION_SYNC_INTERVAL_MINUTES", 5))
    
    @field_validator("ALLOWED_HOSTS", mode='before')
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings() 