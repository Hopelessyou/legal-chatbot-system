"""
ChatSession 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class ChatSession(BaseModel):
    """상담 세션 마스터 테이블"""
    __tablename__ = "chat_session"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'ABORTED')", name="check_status"),
        CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="check_completion_rate"),
        CheckConstraint("channel IN ('web', 'mobile', 'kakao')", name="check_channel"),
        CheckConstraint("current_state IN ('INIT', 'CASE_CLASSIFICATION', 'FACT_COLLECTION', 'VALIDATION', 'RE_QUESTION', 'SUMMARY', 'COMPLETED')", name="check_current_state"),
        Index('idx_chat_session_status', 'status'),
        Index('idx_chat_session_current_state', 'current_state'),
        Index('idx_chat_session_updated_at', 'updated_at'),
        Index('idx_chat_session_user_hash', 'user_hash'),
    )
    
    session_id = Column(String(50), primary_key=True)
    channel = Column(String(20), nullable=False)
    user_hash = Column(String(64))
    current_state = Column(String(30), nullable=False, default="INIT")
    status = Column(String(20), nullable=False, default="ACTIVE")
    completion_rate = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False, default=get_kst_now)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    updated_at = Column(DateTime, nullable=False, default=get_kst_now, onupdate=get_kst_now)
    
    # Relationships
    state_logs = relationship("ChatSessionStateLog", back_populates="session", cascade="all, delete-orphan")
    case = relationship("CaseMaster", back_populates="session", uselist=False, cascade="all, delete-orphan")
    ai_logs = relationship("AIProcessLog", back_populates="session", cascade="all, delete-orphan")
    files = relationship("ChatFile", back_populates="session", cascade="all, delete-orphan")

