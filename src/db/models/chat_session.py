"""
ChatSession 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class ChatSession(BaseModel):
    """상담 세션 마스터 테이블"""
    __tablename__ = "chat_session"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'ABORTED')", name="check_status"),
        CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="check_completion_rate"),
    )
    
    session_id = Column(String(50), primary_key=True)
    channel = Column(String(20), nullable=False)
    user_hash = Column(String(64))
    current_state = Column(String(30), nullable=False, default="INIT")
    status = Column(String(20), nullable=False, default="ACTIVE")
    completion_rate = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    state_logs = relationship("ChatSessionStateLog", back_populates="session", cascade="all, delete-orphan")
    case = relationship("CaseMaster", back_populates="session", uselist=False, cascade="all, delete-orphan")
    ai_logs = relationship("AIProcessLog", back_populates="session", cascade="all, delete-orphan")
    files = relationship("ChatFile", back_populates="session", cascade="all, delete-orphan")

