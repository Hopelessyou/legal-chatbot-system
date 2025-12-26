"""
완성도 계산 모듈
"""
from typing import List, Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_completion_rate(state: StateContext) -> int:
    """
    완성도 계산
    
    Args:
        state: StateContext
    
    Returns:
        완성도 (0~100)
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
        
        # 필수 필드 목록 추출 (간단화)
        # 실제로는 RAG 결과를 파싱하여 required_fields 추출
        required_fields = ["incident_date", "counterparty", "amount", "evidence"]
        
        # 채워진 필드 개수 계산
        filled_count = 0
        for field in required_fields:
            value = facts.get(field)
            if value is not None and value != "":
                filled_count += 1
        
        # 완성도 계산
        if not required_fields:
            return 0
        
        completion_rate = int((filled_count / len(required_fields)) * 100)
        return min(completion_rate, 100)
    
    except Exception as e:
        logger.error(f"완성도 계산 실패: {str(e)}")
        return 0

