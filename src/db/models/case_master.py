"""
CaseMaster 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseMaster(BaseModel):
    """법률 사건 마스터 테이블"""
    __tablename__ = "case_master"
    __table_args__ = (
        CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
        CheckConstraint("case_stage IN ('상담전', '상담중', '상담완료', '수임', '거절')", name="check_case_stage"),
        CheckConstraint("estimated_value IS NULL OR estimated_value >= 0", name="check_estimated_value"),
        Index('idx_case_type', 'main_case_type', 'sub_case_type'),
        Index('idx_case_value', 'estimated_value'),
        Index('idx_case_session', 'session_id'),
    )
    
    case_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False, unique=True)
    main_case_type = Column(String(50))
    sub_case_type = Column(String(50))
    case_stage = Column(String(30), default="상담전")
    urgency_level = Column(String(20))
    estimated_value = Column(BigInteger)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    updated_at = Column(DateTime, nullable=False, default=get_kst_now, onupdate=get_kst_now)
    
    # Relationships
    session = relationship("ChatSession", back_populates="case")
    parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    facts = relationship("CaseFact", back_populates="case", cascade="all, delete-orphan")
    evidences = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")
    emotions = relationship("CaseEmotion", back_populates="case", cascade="all, delete-orphan")
    missing_fields = relationship("CaseMissingField", back_populates="case", cascade="all, delete-orphan")
    summary = relationship("CaseSummary", back_populates="case", uselist=False, cascade="all, delete-orphan")

