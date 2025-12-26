"""
ChatSessionStateLog 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class ChatSessionStateLog(BaseModel):
    """LangGraph 상태 전이 로그 테이블"""
    __tablename__ = "chat_session_state_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    from_state = Column(String(30))
    to_state = Column(String(30), nullable=False)
    condition_key = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="state_logs")

