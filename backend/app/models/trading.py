from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.models.base_class import Base


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Trade(Base):
    """Individual trade model"""
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    exchange_connection_id = Column(Integer, ForeignKey("exchange_connections.id"), nullable=False)
    
    # Trade details
    symbol = Column(String(20), nullable=False)  # BTC/USDT, ETH/USDT, etc.
    trade_type = Column(String(10), nullable=False)  # spot, futures
    order_type = Column(String(15), nullable=False)  # market, limit, stop, stop_limit
    side = Column(String(4), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_price = Column(Float)  # Actual execution price
    fee = Column(Float, default=0.0)
    fee_currency = Column(String(10), default="USDT")
    
    # Order status
    status = Column(String(20), default=OrderStatus.PENDING.value)
    exchange_order_id = Column(String(255))  # Exchange's order ID
    client_order_id = Column(String(255), nullable=True)  # Client-generated order ID for idempotency
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    executed_at = Column(DateTime(timezone=True))
    
    # Check constraints
    __table_args__ = (
        CheckConstraint(trade_type.in_(['spot', 'futures']), name='valid_trade_type'),
        CheckConstraint(order_type.in_(['market', 'limit', 'stop', 'stop_limit', 'stop-limit']), name='valid_order_type'),
        CheckConstraint(side.in_(['buy', 'sell']), name='valid_side'),
        CheckConstraint(status.in_(['pending', 'open', 'filled', 'partially_filled', 'cancelled', 'rejected']), name='valid_status'),
    )
    
    # Relationships
    user = relationship("User", back_populates="trades")
    bot = relationship("Bot", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    exchange_connection = relationship("ExchangeConnection", back_populates="trades")

    # Stop loss retry tracking
    stop_loss_retry_count = Column(Integer, default=0)
    stop_loss_last_attempt = Column(DateTime(timezone=True), nullable=True)
    stop_loss_failed = Column(Boolean, default=False)
    exchange_info = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # New column for stop loss
    stop_loss = Column(Float, nullable=True)  # User's intended stop loss price


class Position(Base):
    """Open positions model"""
    
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    exchange_connection_id = Column(Integer, ForeignKey("exchange_connections.id"), nullable=False)
    
    # Position details
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # spot, futures
    side = Column(String(4), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    leverage = Column(Integer, default=1)
    
    # Exchange order tracking
    exchange_order_id = Column(String(255))  # Exchange's order ID that created this position
    
    # P&L calculations
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    liquidation_price = Column(Float)  # For futures
    
    # Status
    is_open = Column(Boolean, default=True)
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Check constraints
    __table_args__ = (
        CheckConstraint(trade_type.in_(['spot', 'futures']), name='valid_position_trade_type'),
        CheckConstraint(side.in_(['buy', 'sell']), name='valid_position_side'),
    )
    
    # Relationships
    user = relationship("User")
    bot = relationship("Bot", back_populates="positions")
    strategy = relationship("Strategy", back_populates="positions")
    exchange_connection = relationship("ExchangeConnection")


class PerformanceRecord(Base):
    """Daily performance records for users"""
    
    __tablename__ = "performance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Daily metrics
    starting_balance = Column(Float, nullable=False)
    ending_balance = Column(Float, nullable=False)
    daily_return = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    
    # Trading activity
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    volatility = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="performance_records")


class BacktestResult(Base):
    """Backtesting results for strategies"""
    
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    
    # Backtest parameters
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_balance = Column(Float, nullable=False)
    symbols = Column(Text)  # JSON array of symbols tested
    
    # Results
    final_balance = Column(Float, nullable=False)
    total_return = Column(Float, default=0.0)
    annualized_return = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Trade statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    average_win = Column(Float, default=0.0)
    average_loss = Column(Float, default=0.0)
    
    # Detailed results (stored as JSON)
    equity_curve = Column(Text)  # JSON array of daily equity values
    trade_history = Column(Text)  # JSON array of all trades
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="backtest_results")


class CassavaTrendData(Base):
    """Daily Cassava strategy trend data for all trading pairs"""
    
    __tablename__ = "cassava_trend_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)  # Daily UTC+0
    symbol = Column(String(20), nullable=False, index=True)  # Trading pair
    
    # Technical Indicators
    ema_10 = Column(Float, nullable=False)
    ema_8 = Column(Float, nullable=False)
    ema_20 = Column(Float, nullable=False)
    ema_15 = Column(Float, nullable=False)
    ema_25 = Column(Float, nullable=False)
    ema_5 = Column(Float, nullable=False)
    di_plus = Column(Float, nullable=False)
    top_fractal = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    
    # Trading Condition
    trading_condition = Column(String(10), nullable=False)  # BUY, SHORT, HOLD
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Check constraints
    __table_args__ = (
        CheckConstraint(trading_condition.in_(['BUY', 'SHORT', 'HOLD']), name='valid_trading_condition'),
        # Unique constraint for date + symbol combination
        UniqueConstraint('date', 'symbol', name='unique_date_symbol'),
    ) 