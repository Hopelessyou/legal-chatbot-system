"""
CaseEvidence 모델
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseEvidence(BaseModel):
    """증거 정보 테이블"""
    __tablename__ = "case_evidence"
    __table_args__ = (
        Index('idx_case_evidence_case', 'case_id'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50))
    description = Column(String(255))
    available = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="evidences")

