"""
Conditional Edge 구현
"""
from typing import Literal
from src.langgraph.state import StateContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


def route_after_validation(state: StateContext) -> Literal["RE_QUESTION", "SUMMARY"]:
    """
    VALIDATION 후 분기 결정
    
    Args:
        state: 현재 State Context
    
    Returns:
        다음 State ("RE_QUESTION" 또는 "SUMMARY")
    """
    missing_fields = state.get("missing_fields", [])
    
    if len(missing_fields) > 0:
        logger.debug(f"누락 필드 존재: {missing_fields} → RE_QUESTION")
        return "RE_QUESTION"
    else:
        logger.debug("모든 필수 필드 충족 → SUMMARY")
        return "SUMMARY"


def should_continue_to_summary(state: StateContext) -> bool:
    """
    SUMMARY로 진행할지 여부 판단
    
    Args:
        state: 현재 State Context
    
    Returns:
        True: SUMMARY로 진행, False: RE_QUESTION으로 진행
    """
    missing_fields = state.get("missing_fields", [])
    return len(missing_fields) == 0

