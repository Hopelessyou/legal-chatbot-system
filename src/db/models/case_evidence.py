"""
CaseEvidence 모델
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseEvidence(BaseModel):
    """증거 정보 테이블"""
    __tablename__ = "case_evidence"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50))
    description = Column(String(255))
    available = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="evidences")

