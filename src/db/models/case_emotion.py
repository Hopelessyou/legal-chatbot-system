"""
CaseEmotion 모델
"""
from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseEmotion(BaseModel):
    """감정 정보 테이블"""
    __tablename__ = "case_emotion"
    __table_args__ = (
        CheckConstraint("intensity >= 1 AND intensity <= 5", name="check_intensity"),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    emotion_type = Column(String(50))
    intensity = Column(Integer, nullable=False)
    source_text = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="emotions")

