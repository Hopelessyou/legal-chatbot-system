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
from config.settings import settings

logger = get_logger(__name__)

# 최대 재귀 깊이 (무한 루프 방지)
DEFAULT_RECURSION_LIMIT = 50


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
    
    # 그래프 컴파일 (recursion_limit 설정으로 무한 루프 방지)
    recursion_limit = getattr(settings, 'graph_recursion_limit', DEFAULT_RECURSION_LIMIT)
    app = workflow.compile(checkpointer=None, interrupt_before=None, interrupt_after=None)
    
    logger.info(f"LangGraph 그래프 생성 완료 (recursion_limit: {recursion_limit})")
    return app


def run_graph_step(state: StateContext) -> StateContext:
    """
    LangGraph 1 step 실행 (현재 State에 해당하는 Node만 실행)
    
    현재 State에 해당하는 Node만 직접 실행하여 상태 전이를 처리합니다.
    무한 루프 방지를 위해 재귀 제한을 확인합니다.
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State Context
    
    Raises:
        RuntimeError: 재귀 제한 초과 시
    """
    try:
        session_id = state.get("session_id", "unknown")
        current_state = state.get("current_state", "INIT")
        
        # 재귀 제한 확인
        if _check_recursion_limit(session_id):
            logger.error(f"[{session_id}] 무한 루프 감지, 그래프 실행 중단")
            state["current_state"] = "COMPLETED"
            state["bot_message"] = "죄송합니다. 시스템 오류가 발생했습니다. 세션을 다시 시작해주세요."
            _reset_session_step_count(session_id)
            return state
        
        # 현재 State에 해당하는 Node 실행
        from src.langgraph.nodes import (
            init_node,
            case_classification_node,
            fact_collection_node,
            validation_node,
            re_question_node,
            summary_node,
            completed_node
        )
        
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
            logger.error(f"[{session_id}] 알 수 없는 State: {current_state}")
            return state
        
        # Node 실행
        logger.info(f"[{session_id}] Node 실행: {current_state}")
        result = node_func(state)
        
        # last_user_input 보존 (Node가 반환하지 않았을 수 있음)
        if "last_user_input" not in result and "last_user_input" in state:
            result["last_user_input"] = state["last_user_input"]
        
        # next_state 업데이트
        next_state = result.get("next_state")
        if next_state:
            # next_state가 있으면 current_state 업데이트
            result["current_state"] = next_state
            logger.info(f"[{session_id}] State 전이: {current_state} → {next_state}")
        elif "current_state" not in result:
            # current_state가 없으면 현재 상태 유지
            result["current_state"] = current_state
            logger.debug(f"[{session_id}] State 유지: {current_state}")
        
        # current_state가 명시적으로 설정된 경우 확인
        if "current_state" in result and result["current_state"] != current_state:
            logger.info(f"[{session_id}] State 변경: {current_state} → {result['current_state']}")
        
        # _check_recursion_limit에서 이미 카운트를 증가시키므로 여기서는 증가하지 않음
        return result
    
    except Exception as e:
        session_id = state.get("session_id", "unknown")
        logger.error(f"[{session_id}] Graph step 실행 실패: {str(e)}", exc_info=True)
        _reset_session_step_count(session_id)
        raise


# 전역 그래프 인스턴스 (캐싱)
_graph_instance = None

# 세션별 실행 횟수 추적 (무한 루프 방지)
_session_step_count = {}


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


def _check_recursion_limit(session_id: str) -> bool:
    """
    재귀 제한 확인
    
    Args:
        session_id: 세션 ID
    
    Returns:
        제한 초과 여부 (True: 초과, False: 정상)
    """
    global _session_step_count
    recursion_limit = getattr(settings, 'graph_recursion_limit', DEFAULT_RECURSION_LIMIT)
    
    if session_id not in _session_step_count:
        _session_step_count[session_id] = 0
    
    _session_step_count[session_id] += 1
    
    if _session_step_count[session_id] > recursion_limit:
        logger.error(
            f"[{session_id}] 재귀 제한 초과: {_session_step_count[session_id]} > {recursion_limit}. "
            "무한 루프 가능성이 있습니다."
        )
        return True
    
    return False


def _reset_session_step_count(session_id: str):
    """세션별 실행 횟수 초기화"""
    global _session_step_count
    if session_id in _session_step_count:
        del _session_step_count[session_id]

