from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base_class import Base
import enum

class StrategyType(str, enum.Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    GRID_TRADING = "grid_trading"
    SCALPING = "scalping"
    CUSTOM = "custom"

class TradeType(str, enum.Enum):
    SPOT = "spot"
    FUTURES = "futures"

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(20), nullable=False)  # trend_following, mean_reversion, etc.
    trade_type = Column(String(10), default=TradeType.SPOT.value)  # spot, futures
    
    # Strategy parameters (stored as JSON)
    parameters = Column(JSONB)  # JSONB for storing strategy parameters
    risk_management = Column(JSONB)  # JSONB for storing risk management rules
    
    # Strategy status
    is_active = Column(Boolean, default=False)
    is_backtested = Column(Boolean, default=False)
    is_optimized = Column(Boolean, default=False)
    
    # Performance metrics
    total_return = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Check constraints
    __table_args__ = (
        CheckConstraint(strategy_type.in_(['trend_following', 'mean_reversion', 'arbitrage', 'grid_trading', 'scalping', 'custom']), name='valid_strategy_type'),
        CheckConstraint(trade_type.in_(['spot', 'futures']), name='valid_strategy_trade_type'),
    )

    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="strategy", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan") 