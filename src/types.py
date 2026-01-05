"""
공통 타입 정의

주의: StateContext는 src/langgraph/state.py에서 정의됩니다.
이 파일에는 StateContext를 제외한 공통 타입만 정의합니다.
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


# 타입 별칭 (선택적)
JsonDict = Dict[str, Any]
JsonList = List[JsonDict]
EmotionList = List[Dict[str, Any]]


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

