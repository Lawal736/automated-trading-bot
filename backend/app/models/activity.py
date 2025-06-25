from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_class import Base
from datetime import datetime

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String, index=True)
    description = Column(String)
    pnl = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)

    user = relationship("User", back_populates="activities")
    bot = relationship("Bot", back_populates="activities") 