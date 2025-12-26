"""
CaseMaster 모델
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import BaseModel


class CaseMaster(BaseModel):
    """법률 사건 마스터 테이블"""
    __tablename__ = "case_master"
    __table_args__ = (
        CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
    )
    
    case_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False, unique=True)
    main_case_type = Column(String(50))
    sub_case_type = Column(String(50))
    case_stage = Column(String(30), default="상담전")
    urgency_level = Column(String(20))
    estimated_value = Column(BigInteger)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="case")
    parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    facts = relationship("CaseFact", back_populates="case", cascade="all, delete-orphan")
    evidences = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")
    emotions = relationship("CaseEmotion", back_populates="case", cascade="all, delete-orphan")
    missing_fields = relationship("CaseMissingField", back_populates="case", cascade="all, delete-orphan")
    summary = relationship("CaseSummary", back_populates="case", uselist=False, cascade="all, delete-orphan")

