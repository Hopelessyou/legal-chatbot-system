"""
RAG 문서 메타데이터 스키마 정의
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime
from src.utils.helpers import get_kst_now


class RAGDocumentMetadata(BaseModel):
    """RAG 문서 메타데이터 스키마"""
    doc_id: str = Field(..., description="문서 고유 ID")
    knowledge_type: Literal["K0", "K1", "K2", "K3", "K4", "FACT"] = Field(..., description="지식 타입")
    main_case_type: Optional[str] = Field(None, description="주 사건 유형 (민사/형사/가사/행정)")
    sub_case_type: Optional[str] = Field(None, description="세부 사건 유형 (계약/사기 등)")
    node_scope: List[str] = Field(default_factory=list, description="사용 가능한 LangGraph Node 목록")
    version: str = Field(default="v1.0", description="문서 버전")
    last_updated: datetime = Field(default_factory=get_kst_now, description="마지막 업데이트 시간")
    
    @field_validator('doc_id')
    @classmethod
    def validate_doc_id(cls, v: str, info) -> str:
        """doc_id 형식 검증"""
        # Pydantic v2에서는 info.data로 다른 필드 값에 접근
        if hasattr(info, 'data') and 'knowledge_type' in info.data:
            kt = info.data['knowledge_type']
            if not v.startswith(kt):
                raise ValueError(f"doc_id는 {kt}로 시작해야 합니다")
        return v
    
    @field_validator('node_scope')
    @classmethod
    def validate_node_scope(cls, v: List[str]) -> List[str]:
        """node_scope 유효성 검증"""
        valid_nodes = [
            "INIT",
            "CASE_CLASSIFICATION",
            "FACT_COLLECTION",
            "VALIDATION",
            "RE_QUESTION",
            "SUMMARY",
            "COMPLETED"
        ]
        for node in v:
            if node not in valid_nodes:
                raise ValueError(f"유효하지 않은 Node: {node}")
        return v


class K1Document(BaseModel):
    """K1 문서 구조 (사건 유형 기준)"""
    metadata: RAGDocumentMetadata
    level1: Optional[str] = Field(None, description="LEVEL1 분류")
    level2_code: Optional[str] = Field(None, description="LEVEL2 코드")
    level2_name: Optional[str] = Field(None, description="LEVEL2 이름")
    scenarios: List[dict] = Field(..., description="시나리오 목록")
    typical_keywords: Optional[List[str]] = Field(None, description="전체 대표 키워드")
    typical_expressions: Optional[List[str]] = Field(None, description="전체 대표 표현")


class K2Document(BaseModel):
    """K2 문서 구조 (필수 정보·질문 기준)"""
    metadata: RAGDocumentMetadata
    required_fields: List[str] = Field(..., description="필수 필드 목록 (필드명 리스트)")
    questions: List[dict] = Field(..., description="질문 목록")
    level1: Optional[str] = Field(None, description="LEVEL1 분류")
    level2: Optional[str] = Field(None, description="LEVEL2 분류")
    scenario: Optional[str] = Field(None, description="시나리오 코드")


class K3Document(BaseModel):
    """K3 문서 구조 (법률 판단 보조 기준)"""
    metadata: RAGDocumentMetadata
    level1: Optional[str] = Field(None, description="LEVEL1 분류")
    level2: Optional[str] = Field(None, description="LEVEL2 분류")
    scenario: Optional[str] = Field(None, description="시나리오 코드")
    rules: List[dict] = Field(..., description="리스크 규칙 목록")


class K4Document(BaseModel):
    """K4 문서 구조 (출력·요약 포맷 기준)"""
    metadata: RAGDocumentMetadata
    target: Optional[str] = Field(None, description="대상 사용자 (COUNSELOR, LAWYER, CRM, INTERNAL)")
    sections: List[dict] = Field(..., description="섹션 목록")


class FACTDocument(BaseModel):
    """FACT 문서 구조 (사실 패턴 기준)"""
    metadata: RAGDocumentMetadata
    level1: Optional[str] = Field(None, description="LEVEL1 분류")
    level2: Optional[str] = Field(None, description="LEVEL2 분류")
    scenario: Optional[str] = Field(None, description="시나리오 코드")
    facts: List[dict] = Field(..., description="사실 패턴 목록")

