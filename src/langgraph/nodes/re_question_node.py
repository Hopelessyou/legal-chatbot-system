"""
RE_QUESTION Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time

logger = get_logger(__name__)


@log_execution_time(logger)
def re_question_node(state: StateContext) -> Dict[str, Any]:
    """
    RE_QUESTION Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state.get("session_id", "unknown")
        missing_fields = state.get("missing_fields", [])
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        
        logger.info(f"[{session_id}] RE_QUESTION Node 실행: missing_fields={missing_fields}, case_type={case_type}, sub_case_type={sub_case_type}")
        
        if not missing_fields:
            logger.warning(f"[{session_id}] 누락 필드가 없습니다.")
            return {
                **state,
                "next_state": "SUMMARY"
            }
        
        # 1. 첫 번째 누락 필드 선택 (우선순위 기반)
        next_field = missing_fields[0]
        logger.info(f"[{session_id}] 다음 질문 필드: {next_field}")
        
        # 2. RAG K2에서 질문 템플릿 조회
        # case_type이 이미 영문이어야 함 (CIVIL, CRIMINAL, etc.)
        try:
            rag_results = rag_searcher.search(
                query=f"{next_field} 질문",
                knowledge_type="K2",
                main_case_type=case_type,
                sub_case_type=sub_case_type,
                # node_scope는 일단 제외 (ChromaDB 필터 제약)
                top_k=1
            )
            logger.debug(f"[{session_id}] RAG 검색 완료: {len(rag_results)}개 결과")
        except Exception as e:
            logger.warning(f"[{session_id}] RAG 검색 실패 (계속 진행): {str(e)}")
            rag_results = []
        
        # 3. 질문 생성
        question_templates = {
            "incident_date": "사건이 발생한 날짜를 알려주세요.",
            "counterparty": "계약 상대방은 누구인가요?",
            "amount": "문제가 된 금액은 얼마인가요?",
            "evidence": "계약서나 관련 증거를 가지고 계신가요?",
            "evidence_type": "어떤 증거를 가지고 계신가요? (예: 계약서, 카톡 대화내역, 송금내역, 사진, 영상 등)"
        }
        
        question = question_templates.get(next_field, f"{next_field}에 대한 정보를 알려주세요.")
        
        # RAG 결과에서 질문 템플릿 사용 (있는 경우)
        if rag_results:
            # 질문 템플릿 추출 로직 (간단화)
            pass
        
        # 4. State 업데이트
        state["bot_message"] = question
        
        field_types = {
            "incident_date": "date",
            "counterparty": "text",
            "amount": "number",
            "evidence": "boolean",
            "evidence_type": "text"
        }
        
        state["expected_input"] = {
            "type": field_types.get(next_field, "text"),
            "field": next_field
        }
        
        logger.info(f"RE_QUESTION 완료: 필드={next_field}")
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"  # Loop: FACT_COLLECTION으로 복귀
        }
    
    except Exception as e:
        logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}")
        raise

