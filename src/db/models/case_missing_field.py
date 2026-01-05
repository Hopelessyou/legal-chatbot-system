"""
CaseMissingField 모델
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseMissingField(BaseModel):
    """누락 정보 관리 테이블"""
    __tablename__ = "case_missing_field"
    __table_args__ = (
        CheckConstraint("(resolved = 1 AND resolved_at IS NOT NULL) OR (resolved = 0 AND resolved_at IS NULL)", name="check_resolved_consistency"),
        Index('idx_missing_unresolved', 'case_id', 'resolved'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    field_key = Column(String(50), nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="missing_fields")

