"""
LangGraph 그래프 구성
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.langgraph.state import StateContext
from src.langgraph.nodes import (
    init_node,
    case_classification_node,
    fact_collection_node,
    validation_node,
    re_question_node,
    summary_node,
    completed_node
)
from src.langgraph.edges.conditional_edges import route_after_validation
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_graph() -> StateGraph:
    """
    LangGraph 그래프 생성
    
    Returns:
        컴파일된 StateGraph 인스턴스
    """
    # 그래프 생성
    workflow = StateGraph(dict)  # StateContext는 TypedDict이므로 dict로 사용
    
    # Node 추가
    workflow.add_node("INIT", init_node)
    workflow.add_node("CASE_CLASSIFICATION", case_classification_node)
    workflow.add_node("FACT_COLLECTION", fact_collection_node)
    workflow.add_node("VALIDATION", validation_node)
    workflow.add_node("RE_QUESTION", re_question_node)
    workflow.add_node("SUMMARY", summary_node)
    workflow.add_node("COMPLETED", completed_node)
    
    # Edge 연결
    workflow.set_entry_point("INIT")
    workflow.add_edge("INIT", "CASE_CLASSIFICATION")
    workflow.add_edge("CASE_CLASSIFICATION", "FACT_COLLECTION")
    workflow.add_edge("FACT_COLLECTION", "VALIDATION")
    
    # Conditional Edge: VALIDATION → RE_QUESTION or SUMMARY
    workflow.add_conditional_edges(
        "VALIDATION",
        route_after_validation,
        {
            "RE_QUESTION": "RE_QUESTION",
            "SUMMARY": "SUMMARY"
        }
    )
    
    # Loop: RE_QUESTION → FACT_COLLECTION
    workflow.add_edge("RE_QUESTION", "FACT_COLLECTION")
    
    # SUMMARY → COMPLETED
    workflow.add_edge("SUMMARY", "COMPLETED")
    
    # COMPLETED → END
    workflow.add_edge("COMPLETED", END)
    
    # 그래프 컴파일
    app = workflow.compile()
    
    logger.info("LangGraph 그래프 생성 완료")
    return app


def run_graph_step(state: StateContext) -> StateContext:
    """
    LangGraph 1 step 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State Context
    """
    try:
        app = get_graph()
        
        # 현재 State에 따라 해당 Node만 실행
        current_state = state.get("current_state", "INIT")
        
        # 현재 State에 해당하는 Node 실행
        node_map = {
            "INIT": init_node,
            "CASE_CLASSIFICATION": case_classification_node,
            "FACT_COLLECTION": fact_collection_node,
            "VALIDATION": validation_node,
            "RE_QUESTION": re_question_node,
            "SUMMARY": summary_node,
            "COMPLETED": completed_node
        }
        
        node_func = node_map.get(current_state)
        if not node_func:
            logger.error(f"알 수 없는 State: {current_state}")
            return state
        
        # Node 실행
        result = node_func(state)
        
        # next_state 업데이트
        next_state = result.get("next_state")
        if next_state:
            result["current_state"] = next_state
        
        logger.info(f"Graph step 실행 완료: {current_state} → {next_state}")
        return result
    
    except Exception as e:
        logger.error(f"Graph step 실행 실패: {str(e)}")
        raise


# 전역 그래프 인스턴스 (캐싱)
_graph_instance = None


def get_graph() -> StateGraph:
    """
    그래프 인스턴스 획득 (싱글톤)
    
    Returns:
        컴파일된 StateGraph 인스턴스
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_graph()
    return _graph_instance

