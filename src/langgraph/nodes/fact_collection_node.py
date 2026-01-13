"""
FACT_COLLECTION Node 구현 (Q-A 매칭 방식)
"""
from typing import Dict, Any, List, Optional
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import (
    REQUIRED_FIELDS,
    FIELD_INPUT_TYPE_MAPPING,
    Limits,
    REQUIRED_FIELDS_BY_CASE_TYPE
)
from src.utils.rag_helpers import (
    extract_required_fields_from_rag,
    extract_question_template_from_rag
)
from src.utils.question_loader import get_question_message
from src.utils.helpers import get_kst_now

logger = get_logger(__name__)


def _generate_next_question(state: StateContext) -> Dict[str, Any]:
    """
    다음 질문 생성 (Q-A 매칭 방식, 1차 서술 분석 반영)
    
    Args:
        state: State Context
    
    Returns:
        질문 딕셔너리 (question, field)
    """
    conversation_history = state.get("conversation_history", [])
    asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
    skipped_fields = state.get("skipped_fields", [])  # 1차 서술에서 이미 답변된 필드
    missing_fields = state.get("missing_fields", [])  # 1차 서술 분석 결과
    case_type = state.get("case_type")
    
    # 아직 질문하지 않은 필수 필드 찾기
    # 1차 서술에서 이미 답변된 필드(skipped_fields)와 이미 질문한 필드(asked_fields)는 제외
    next_field = None
    excluded_fields = set(asked_fields) | set(skipped_fields)
    
    # missing_fields에서 찾기
    for field in missing_fields:
        if field not in excluded_fields:
            next_field = field
            break
    
    # missing_fields가 없거나 모두 제외된 경우, 전체 필수 필드에서 다시 확인
    if not next_field:
        try:
            rag_results = rag_searcher.search(
                query="필수 필드",
                knowledge_type="K2",
                main_case_type=case_type,
                top_k=1
            )
            required_fields = extract_required_fields_from_rag(rag_results)
        except Exception as e:
            logger.warning(f"RAG 필수 필드 조회 실패: {str(e)}")
            required_fields = []
        
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, REQUIRED_FIELDS)
        
        for field in required_fields:
            if field not in excluded_fields:
                next_field = field
                break
    
    if not next_field:
        # 모든 필수 필드 질문 완료
        return {
            "question": "추가로 알려주실 정보가 있으신가요?",
            "field": "additional_info"
        }
    
    # RAG에서 질문 템플릿 조회
    try:
        rag_results = rag_searcher.search(
            query=f"{next_field} 질문",
            knowledge_type="K2",
            main_case_type=case_type,
            top_k=1
        )
        question = extract_question_template_from_rag(rag_results, next_field)
    except Exception as e:
        logger.debug(f"RAG 질문 템플릿 조회 실패: {str(e)}")
        question = None
    
    if not question:
        question = get_question_message(next_field, case_type)
    
    logger.info(f"[{state.get('session_id', 'unknown')}] 다음 질문 생성: {next_field} (제외된 필드: {excluded_fields})")
    
    return {
        "question": question,
        "field": next_field
    }


@log_execution_time(logger)
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    """
    FACT_COLLECTION Node 실행 (Q-A 매칭 방식)
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "")
        
        # 단계 표시
        print("\n" + "="*70)
        print("📍 [STEP 3] FACT_COLLECTION 노드 실행")
        print("="*70)
        print(f"📌 세션 ID: {session_id}")
        print(f"📝 사용자 입력: {user_input[:50] if user_input else '(없음)'}...")
        current_question = state.get("current_question", {})
        expected_field = current_question.get("field") if current_question else None
        print(f"❓ 예상 필드: {expected_field or '(없음)'}")
        print("="*70 + "\n")
        logger.info("="*70)
        logger.info("📍 [STEP 3] FACT_COLLECTION 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📝 사용자 입력: {user_input[:50] if user_input else '(없음)'}...")
        logger.info(f"❓ 예상 필드: {expected_field or '(없음)'}")
        logger.info("="*70)
        current_question = state.get("current_question")
        
        # 사용자 입력이 없으면 이전 질문 유지
        if not user_input:
            if not state.get("bot_message"):
                # 다음 질문 생성
                next_question = _generate_next_question(state)
                state["bot_message"] = next_question["question"]
                state["current_question"] = next_question
            return {
                **state,
                "next_state": "FACT_COLLECTION"
            }
        
        # 사용자 입력이 의미 없는 경우 체크 (너무 짧거나 특정 패턴)
        if len(user_input) < 2:
            logger.warning(f"[{session_id}] 사용자 입력이 너무 짧습니다: {user_input}")
            # 이전 질문 유지
            if state.get("bot_message"):
                return {
                    **state,
                    "next_state": "FACT_COLLECTION"
                }
        
        # Q-A 쌍 저장
        if current_question and user_input:
            qa_pair = {
                "question": current_question.get("question", ""),
                "field": current_question.get("field", ""),
                "answer": user_input,
                "timestamp": get_kst_now().isoformat()
            }
            conversation_history = state.get("conversation_history", [])
            conversation_history.append(qa_pair)
            state["conversation_history"] = conversation_history
            
            # 상세 로깅
            logger.info(f"[{session_id}] Q-A 쌍 저장: field={current_question.get('field')}, answer={user_input[:50]}")
            logger.debug(f"[{session_id}] conversation_history 업데이트: 총 {len(conversation_history)}개 Q-A 쌍")
            logger.debug(f"[{session_id}] 현재 Q-A 쌍: Q={current_question.get('question', '')[:50]}, A={user_input[:50]}")
        elif user_input and not current_question:
            # current_question이 없지만 사용자 입력이 있는 경우
            # expected_input, missing_fields, bot_message를 기반으로 Q-A 쌍 저장
            previous_bot_message = state.get("bot_message", "")
            expected_input = state.get("expected_input")
            missing_fields = state.get("missing_fields", [])
            conversation_history = state.get("conversation_history", [])
            asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
            
            # 1순위: expected_input에서 field 추출 (None 체크)
            target_field = None
            if expected_input and isinstance(expected_input, dict):
                target_field = expected_input.get("field")
            
            # 2순위: missing_fields에서 아직 질문하지 않은 첫 번째 필드
            if not target_field:
                for field in missing_fields:
                    if field not in asked_fields:
                        target_field = field
                        break
            
            if target_field:
                # target_field를 찾았으면 Q-A 쌍 저장 (bot_message가 없어도 질문 텍스트 생성)
                question_text = previous_bot_message
                if not question_text:
                    # bot_message가 없으면 질문 텍스트 생성
                    question_text = get_question_message(target_field, state.get("case_type"))
                    if not question_text:
                        question_text = f"{target_field}에 대한 정보를 알려주세요."
                
                qa_pair = {
                    "question": question_text,
                    "field": target_field,
                    "answer": user_input,
                    "timestamp": get_kst_now().isoformat()
                }
                conversation_history.append(qa_pair)
                state["conversation_history"] = conversation_history
                logger.info(f"[{session_id}] Q-A 쌍 저장 (current_question 없음, missing_fields 기반): field={target_field}, answer={user_input[:50]}")
            elif previous_bot_message:
                # 필드를 찾지 못한 경우, bot_message를 기반으로 추론
                if "구체적인 내용" in previous_bot_message or "상황" in previous_bot_message:
                    qa_pair = {
                        "question": previous_bot_message,
                        "field": "fact_description",  # 일반적인 사실 설명 필드
                        "answer": user_input,
                        "timestamp": get_kst_now().isoformat()
                    }
                    conversation_history.append(qa_pair)
                    state["conversation_history"] = conversation_history
                    logger.info(f"[{session_id}] Q-A 쌍 저장 (current_question 없음): field=fact_description, answer={user_input[:50]}")
                else:
                    logger.warning(f"[{session_id}] current_question 없음, 필드 추론 실패: bot_message={previous_bot_message[:50]}, missing_fields={missing_fields}")
            else:
                logger.warning(f"[{session_id}] current_question 없음, bot_message도 없음, missing_fields도 없음: {user_input[:50]}")
            # 이 입력은 다음 VALIDATION 노드에서 _extract_facts_from_conversation으로 처리됨
        
        # 다음 질문 생성
        next_question = _generate_next_question(state)
        state["bot_message"] = next_question["question"]
        state["current_question"] = next_question
        
        # completion_rate 계산 (conversation_history 기반)
        conversation_history = state.get("conversation_history", [])
        asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
        
        try:
            rag_results = rag_searcher.search(
                query="필수 필드",
                knowledge_type="K2",
                main_case_type=state.get("case_type"),
                top_k=1
            )
            required_fields = extract_required_fields_from_rag(rag_results)
        except:
            required_fields = []
        
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(state.get("case_type"), REQUIRED_FIELDS)
        
        # 1차 서술에서 답변된 필드도 포함하여 계산
        skipped_fields = state.get("skipped_fields", [])
        total_answered = len(set(asked_fields) | set(skipped_fields))
        completion_rate = int((total_answered / len(required_fields)) * 100) if required_fields else 0
        completion_rate = min(completion_rate, 100)
        state["completion_rate"] = completion_rate
        
        # 상세 로깅
        logger.info(f"[{session_id}] FACT_COLLECTION 완료: completion_rate={completion_rate}%, next_field={next_question.get('field')}")
        logger.debug(f"[{session_id}] conversation_history 상태: 총 {len(conversation_history)}개 Q-A 쌍")
        logger.debug(f"[{session_id}] asked_fields: {asked_fields}, skipped_fields: {skipped_fields}")
        logger.debug(f"[{session_id}] total_answered: {total_answered}/{len(required_fields)}")
        
        return {
            **state,
            "next_state": "VALIDATION"
        }
    
    except Exception as e:
        logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 다음 질문 생성 시도
        try:
            next_question = _generate_next_question(state)
            return {
                **state,
                "bot_message": next_question.get("question", "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."),
                "current_question": next_question,
                "next_state": "VALIDATION"
            }
        except:
            return {
                **state,
                "bot_message": "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.",
                "next_state": "VALIDATION"
            }
