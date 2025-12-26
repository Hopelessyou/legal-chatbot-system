"""
누락 필드 관리 모듈
"""
from typing import List, Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger

logger = get_logger(__name__)


def detect_missing_fields(state: StateContext) -> List[str]:
    """
    누락 필드 감지
    
    Args:
        state: StateContext
    
    Returns:
        누락된 필드 키 리스트
    """
    try:
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        facts = state.get("facts", {})
        
        # RAG K2에서 필수 필드 목록 조회
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=case_type,
            sub_case_type=sub_case_type,
            node_scope="VALIDATION",
            top_k=1
        )
        
        # 필수 필드 목록 (간단화)
        required_fields = ["incident_date", "counterparty", "amount", "evidence"]
        
        # 누락 필드 찾기
        missing_fields = []
        for field in required_fields:
            value = facts.get(field)
            if value is None or value == "":
                missing_fields.append(field)
        
        logger.debug(f"누락 필드 감지: {missing_fields}")
        return missing_fields
    
    except Exception as e:
        logger.error(f"누락 필드 감지 실패: {str(e)}")
        return []


def get_next_missing_field(missing_fields: List[str]) -> Optional[str]:
    """
    다음 질문할 누락 필드 선택 (우선순위 기반)
    
    Args:
        missing_fields: 누락 필드 리스트
    
    Returns:
        다음 질문할 필드 키 또는 None
    """
    if not missing_fields:
        return None
    
    # 우선순위: incident_date > amount > counterparty > evidence
    priority_order = ["incident_date", "amount", "counterparty", "evidence"]
    
    for field in priority_order:
        if field in missing_fields:
            return field
    
    # 우선순위에 없으면 첫 번째 필드 반환
    return missing_fields[0]

