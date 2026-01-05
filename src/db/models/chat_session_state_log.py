"""
ChatSessionStateLog 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class ChatSessionStateLog(BaseModel):
    """LangGraph 상태 전이 로그 테이블"""
    __tablename__ = "chat_session_state_log"
    __table_args__ = (
        CheckConstraint("from_state IS NULL OR from_state IN ('INIT', 'CASE_CLASSIFICATION', 'FACT_COLLECTION', 'VALIDATION', 'RE_QUESTION', 'SUMMARY', 'COMPLETED')", name="check_from_state"),
        CheckConstraint("to_state IN ('INIT', 'CASE_CLASSIFICATION', 'FACT_COLLECTION', 'VALIDATION', 'RE_QUESTION', 'SUMMARY', 'COMPLETED')", name="check_to_state"),
        Index('idx_state_log_session', 'session_id'),
        Index('idx_state_log_created', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    from_state = Column(String(30))
    to_state = Column(String(30), nullable=False)
    condition_key = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    session = relationship("ChatSession", back_populates="state_logs")

