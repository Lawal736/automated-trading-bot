from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base_class import Base

class BotConfig(Base):
    __tablename__ = "bot_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    
    config_key = Column(String(100), nullable=False)
    config_value = Column(Text, nullable=False)
    
    bot = relationship("Bot", back_populates="configs")


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange_connection_id = Column(Integer, ForeignKey("exchange_connections.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    strategy_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Core trading settings
    trade_type = Column(String(10), nullable=False) # spot, futures
    direction = Column(String(10), nullable=False) # long, short, both
    leverage = Column(Integer, default=1)
    
    # Financials
    initial_balance = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    
    # Advanced Stop Loss Configuration
    stop_loss_type = Column(String(50), default="fixed_percentage")  # fixed_percentage, trailing_max_price, ema_based, atr_based, support_level
    stop_loss_percentage = Column(Float, default=5.0)
    stop_loss_timeframe = Column(String(10), default="4h")  # For trailing stops
    stop_loss_ema_period = Column(Integer, default=7)  # For EMA-based stops
    stop_loss_atr_period = Column(Integer, default=14)  # For ATR-based stops
    stop_loss_atr_multiplier = Column(Float, default=2.0)  # For ATR-based stops
    stop_loss_support_lookback = Column(Integer, default=20)  # For support level stops
    
    # Risk Management
    # This field is now covered by the more specific stop_loss_percentage
    # stop_loss_percent = Column(Float, nullable=True) 
    
    # Trading Limits
    max_trades_per_day = Column(Integer, default=10)
    min_balance_threshold = Column(Float, default=100.0)
    max_daily_loss = Column(Float, default=50.0)
    max_position_size_percent = Column(Float, default=10.0)  # Max % of balance per trade
    trade_interval_seconds = Column(Integer, default=60)  # Seconds between trade checks
    
    # Status
    is_active = Column(Boolean, default=False)
    celery_task_id = Column(String(255), nullable=True)
    
    # Trading Pairs (could be a relationship or a simple string for now)
    trading_pairs = Column(Text) # e.g., "BTC/USDT,ETH/USDT"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Check constraints
    __table_args__ = (
        CheckConstraint(trade_type.in_(['spot', 'futures']), name='valid_bot_trade_type'),
        CheckConstraint(direction.in_(['long', 'short', 'both']), name='valid_bot_direction'),
        CheckConstraint(leverage >= 1, name='valid_leverage'),
    )

    # Relationships
    user = relationship("User", back_populates="bots")
    exchange_connection = relationship("ExchangeConnection", back_populates="bots")
    configs = relationship("BotConfig", back_populates="bot", cascade="all, delete-orphan")
    # A bot will also have trades and positions, similar to a strategy
    trades = relationship("Trade", back_populates="bot", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="bot", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="bot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bot(id={self.id}, name='{self.name}', user_id={self.user_id})>" 