"""
AIProcessLog 모델
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class AIProcessLog(BaseModel):
    """GPT / RAG 호출 로그 테이블"""
    __tablename__ = "ai_process_log"
    __table_args__ = (
        CheckConstraint("token_input IS NULL OR token_input >= 0", name="check_token_input"),
        CheckConstraint("token_output IS NULL OR token_output >= 0", name="check_token_output"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="check_latency_ms"),
        Index('idx_ai_log_session', 'session_id'),
        Index('idx_ai_log_created', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    node_name = Column(String(50))
    model = Column(String(50))
    token_input = Column(Integer)
    token_output = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    session = relationship("ChatSession", back_populates="ai_logs")

