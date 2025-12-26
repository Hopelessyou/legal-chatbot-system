"""
AIProcessLog 모델
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class AIProcessLog(BaseModel):
    """GPT / RAG 호출 로그 테이블"""
    __tablename__ = "ai_process_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    node_name = Column(String(50))
    model = Column(String(50))
    token_input = Column(Integer)
    token_output = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="ai_logs")

