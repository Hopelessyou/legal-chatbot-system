"""
LangGraph Node 통합 테스트
"""
import pytest
from src.langgraph.state import create_initial_context, StateContext
from src.langgraph.nodes import (
    init_node,
    case_classification_node,
    fact_collection_node,
    validation_node,
    re_question_node,
    summary_node,
    completed_node
)


def test_init_node():
    """INIT Node 테스트"""
    session_id = "sess_test_123"
    state = create_initial_context(session_id)
    
    result = init_node(state)
    
    assert result["current_state"] == "INIT"
    assert result["next_state"] == "CASE_CLASSIFICATION"
    assert "bot_message" in result


def test_case_classification_node():
    """CASE_CLASSIFICATION Node 테스트"""
    state = create_initial_context("sess_test_123")
    state["last_user_input"] = "계약 관련 문제입니다"
    
    # INIT 실행 후
    state = init_node(state)
    state["current_state"] = state["next_state"]
    
    # CASE_CLASSIFICATION 실행
    result = case_classification_node(state)
    
    assert result["next_state"] == "FACT_COLLECTION"
    assert result.get("case_type") is not None or result.get("sub_case_type") is not None


def test_validation_node_with_missing_fields():
    """VALIDATION Node 테스트 (누락 필드 있는 경우)"""
    state = create_initial_context("sess_test_123")
    state["facts"] = {
        "incident_date": "2023-10-15",
        "counterparty": None,  # 누락
        "amount": None,  # 누락
        "evidence": None
    }
    state["current_state"] = "VALIDATION"
    
    result = validation_node(state)
    
    assert len(result["missing_fields"]) > 0
    assert result["next_state"] == "RE_QUESTION"


def test_validation_node_complete():
    """VALIDATION Node 테스트 (모든 필드 충족)"""
    state = create_initial_context("sess_test_123")
    state["facts"] = {
        "incident_date": "2023-10-15",
        "counterparty": "개인",
        "amount": 50000000,
        "evidence": True
    }
    state["current_state"] = "VALIDATION"
    
    result = validation_node(state)
    
    assert len(result["missing_fields"]) == 0
    assert result["next_state"] == "SUMMARY"

