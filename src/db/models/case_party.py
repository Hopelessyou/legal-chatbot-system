"""
CaseParty 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseParty(BaseModel):
    """사건 당사자 정보 테이블"""
    __tablename__ = "case_party"
    __table_args__ = (
        CheckConstraint("party_role IN ('의뢰인', '상대방')", name="check_party_role"),
        CheckConstraint("party_type IN ('개인', '법인')", name="check_party_type"),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    party_role = Column(String(20), nullable=False)
    party_type = Column(String(20))
    party_description = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="parties")

