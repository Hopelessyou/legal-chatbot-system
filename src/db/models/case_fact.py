"""
CaseFact 모델
"""
from sqlalchemy import Column, BigInteger, String, Date, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseFact(BaseModel):
    """핵심 사실관계 테이블"""
    __tablename__ = "case_fact"
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="check_confidence_score"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="check_amount"),
        Index('idx_case_fact_case', 'case_id'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    fact_type = Column(String(50))
    incident_date = Column(Date)
    location = Column(String(255))
    description = Column(Text)
    amount = Column(BigInteger)
    confidence_score = Column(Integer)
    source_text = Column(Text)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="facts")

