from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base_class import Base

class ExchangeConnection(Base):
    """User's exchange API connections"""
    
    __tablename__ = "exchange_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange_name = Column(String(50), nullable=False)
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)
    password = Column(String(255))  # Formerly passphrase
    is_active = Column(Boolean, default=True)
    is_testnet = Column(Boolean, default=True)
    
    can_trade = Column(Boolean, default=True)
    can_withdraw = Column(Boolean, default=False)
    can_read = Column(Boolean, default=True)
    
    last_verified = Column(DateTime(timezone=True))
    connection_status = Column(String(20), default="pending")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="exchange_connections")
    bots = relationship("Bot", back_populates="exchange_connection", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="exchange_connection", cascade="all, delete-orphan") 