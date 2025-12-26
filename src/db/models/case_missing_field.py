"""
CaseMissingField 모델
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseMissingField(BaseModel):
    """누락 정보 관리 테이블"""
    __tablename__ = "case_missing_field"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False)
    field_key = Column(String(50), nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="missing_fields")

