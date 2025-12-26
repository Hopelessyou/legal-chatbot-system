"""
LangGraph State Context 구조 정의
"""
from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class StateContext(TypedDict, total=False):
    """LangGraph State Context 타입 정의"""
    session_id: str
    current_state: str
    case_type: Optional[str]
    sub_case_type: Optional[str]
    facts: Dict[str, Any]
    emotion: List[Dict[str, Any]]
    completion_rate: int
    last_user_input: str
    missing_fields: List[str]
    bot_message: Optional[str]
    expected_input: Optional[Dict[str, Any]]


class StateContextModel(BaseModel):
    """State Context Pydantic 모델 (검증용)"""
    session_id: str
    current_state: str = Field(default="INIT")
    case_type: Optional[str] = None
    sub_case_type: Optional[str] = None
    facts: Dict[str, Any] = Field(default_factory=dict)
    emotion: List[Dict[str, Any]] = Field(default_factory=list)
    completion_rate: int = Field(default=0, ge=0, le=100)
    last_user_input: str = Field(default="")
    missing_fields: List[str] = Field(default_factory=list)
    bot_message: Optional[str] = None
    expected_input: Optional[Dict[str, Any]] = None
    
    @validator('current_state')
    def validate_state(cls, v):
        """State 유효성 검증"""
        valid_states = [
            "INIT",
            "CASE_CLASSIFICATION",
            "FACT_COLLECTION",
            "VALIDATION",
            "RE_QUESTION",
            "SUMMARY",
            "COMPLETED"
        ]
        if v not in valid_states:
            raise ValueError(f"유효하지 않은 State: {v}")
        return v
    
    class Config:
        extra = "allow"


def create_initial_context(session_id: str) -> StateContext:
    """
    초기 Context 생성
    
    Args:
        session_id: 세션 ID
    
    Returns:
        초기화된 StateContext
    """
    return {
        "session_id": session_id,
        "current_state": "INIT",
        "case_type": None,
        "sub_case_type": None,
        "facts": {
            "incident_date": None,
            "location": None,
            "counterparty": None,
            "amount": None,
            "evidence": None
        },
        "emotion": [],
        "completion_rate": 0,
        "last_user_input": "",
        "missing_fields": [],
        "bot_message": None,
        "expected_input": None
    }


def validate_context(context: StateContext) -> bool:
    """
    Context 검증
    
    Args:
        context: StateContext 딕셔너리
    
    Returns:
        검증 결과 (True: 유효, False: 무효)
    """
    try:
        StateContextModel(**context)
        return True
    except Exception as e:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Context 검증 실패: {str(e)}")
        return False

