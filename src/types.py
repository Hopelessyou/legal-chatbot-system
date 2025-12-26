"""
공통 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


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


class FactDict(TypedDict, total=False):
    """사실 정보 딕셔너리 타입"""
    incident_date: Optional[str]
    location: Optional[str]
    counterparty: Optional[str]
    amount: Optional[int]
    evidence: Optional[bool]


class EmotionDict(TypedDict, total=False):
    """감정 정보 딕셔너리 타입"""
    emotion_type: str
    intensity: int
    source_text: str


class ExpectedInput(TypedDict, total=False):
    """예상 입력 타입"""
    type: str  # date, choice, text 등
    field: str
    options: Optional[List[str]]

