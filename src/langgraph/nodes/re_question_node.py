"""
RE_QUESTION Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import FIELD_INPUT_TYPE_MAPPING
from src.utils.question_loader import get_question_message
from src.services.missing_field_manager import get_next_missing_field
from src.utils.rag_helpers import extract_question_template_from_rag

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
        
        # 1. 우선순위 기반으로 다음 질문할 필드 선택 (asked_fields 제외)
        asked_fields = state.get("asked_fields", [])
        
        # asked_fields에 포함되지 않은 missing_fields만 필터링
        unasked_missing_fields = [f for f in missing_fields if f not in asked_fields]
        
        if unasked_missing_fields:
            next_field = get_next_missing_field(unasked_missing_fields, case_type)
        else:
            # 모든 missing_fields를 이미 질문한 경우, 다시 질문하지 않고 SUMMARY로 이동
            logger.info(f"[{session_id}] 모든 누락 필드를 이미 질문했습니다. SUMMARY로 이동합니다.")
            return {
                **state,
                "next_state": "SUMMARY"
            }
        
        if not next_field:
            logger.warning(f"[{session_id}] 다음 질문할 필드를 찾을 수 없습니다.")
            return {
                **state,
                "next_state": "SUMMARY"
            }
        logger.info(f"[{session_id}] 다음 질문 필드: {next_field} (우선순위 기반, asked_fields: {asked_fields})")
        
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
        
        # 3. 질문 생성 (RAG 결과 우선 사용)
        question = extract_question_template_from_rag(rag_results, next_field)
        
        # RAG 결과에서 추출 실패 시 YAML 파일에서 로드
        if not question:
            question = get_question_message(next_field, case_type)
            logger.debug(f"[{session_id}] RAG 결과에서 질문 추출 실패, YAML 파일 사용")
        else:
            logger.info(f"[{session_id}] RAG 결과에서 질문 템플릿 추출 성공: {next_field}")
        
        # 4. asked_fields 업데이트 (중복 질문 방지)
        if next_field not in asked_fields:
            asked_fields.append(next_field)
            state["asked_fields"] = asked_fields
        
        # 5. State 업데이트
        state["bot_message"] = question
        state["expected_input"] = {
            "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
            "field": next_field
        }
        
        logger.info(f"[{session_id}] RE_QUESTION 완료: 필드={next_field}, asked_fields={asked_fields}")
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"  # Loop: FACT_COLLECTION으로 복귀
        }
    
    except Exception as e:
        logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기본 질문 메시지 반환
        missing_fields = state.get("missing_fields", [])
        if missing_fields:
            next_field = missing_fields[0]
            state["bot_message"] = get_question_message(next_field, state.get("case_type"))
            state["expected_input"] = {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            }
        else:
            state["bot_message"] = "추가 정보를 알려주세요."
            state["next_state"] = "SUMMARY"
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }

