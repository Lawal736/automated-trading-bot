from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.models.base_class import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class User(Base):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(15), default=UserRole.USER.value)  # user, admin, moderator
    
    # Subscription and billing
    subscription_tier = Column(String(15), default=SubscriptionTier.FREE.value)  # free, basic, premium, enterprise
    subscription_start_date = Column(DateTime(timezone=True))
    subscription_end_date = Column(DateTime(timezone=True))
    is_subscription_active = Column(Boolean, default=False)
    
    # Profile information
    phone_number = Column(String(20))
    country = Column(String(100))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Trading preferences
    default_leverage = Column(Integer, default=1)
    risk_tolerance = Column(String(20), default="medium")  # low, medium, high
    preferred_exchanges = Column(Text)  # JSON string of preferred exchanges
    
    # Account balance and limits
    account_balance = Column(Float, default=0.0)
    daily_trading_limit = Column(Float, default=1000.0)
    monthly_trading_limit = Column(Float, default=10000.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Check constraints
    __table_args__ = (
        CheckConstraint(role.in_(['user', 'admin', 'moderator']), name='valid_user_role'),
        CheckConstraint(subscription_tier.in_(['free', 'basic', 'premium', 'enterprise']), name='valid_subscription_tier'),
        CheckConstraint(risk_tolerance.in_(['low', 'medium', 'high']), name='valid_risk_tolerance'),
    )
    
    # Relationships
    exchange_connections = relationship("ExchangeConnection", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    bots = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")
    performance_records = relationship("PerformanceRecord", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")


class Deposit(Base):
    """User deposit requests"""
    
    __tablename__ = "deposits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    payment_method = Column(String(50))  # bank_transfer, credit_card, crypto, etc.
    status = Column(String(20), default="pending")  # pending, completed, failed, cancelled
    transaction_id = Column(String(255))
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="deposits")


class Withdrawal(Base):
    """User withdrawal requests"""
    
    __tablename__ = "withdrawals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    withdrawal_method = Column(String(50))  # bank_transfer, crypto, etc.
    destination_address = Column(String(255))  # For crypto withdrawals
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, cancelled
    transaction_id = Column(String(255))
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="withdrawals") 