"""
ChatFile 모델 - 채팅 세션에 첨부된 파일 정보
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class ChatFile(BaseModel):
    """채팅 세션 파일 첨부 테이블"""
    __tablename__ = "chat_file"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    file_type = Column(String(50))  # MIME type
    file_extension = Column(String(10))  # .pdf, .jpg, etc.
    description = Column(Text)  # 사용자가 입력한 설명
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="files")

