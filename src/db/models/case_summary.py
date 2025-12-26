"""
CaseSummary 모델
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseSummary(BaseModel):
    """최종 요약 테이블"""
    __tablename__ = "case_summary"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    structured_json = Column(JSON)
    risk_level = Column(String(20))
    ai_version = Column(String(20))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="summary")

