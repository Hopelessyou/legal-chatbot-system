"""
RE_QUESTION Node 구현
"""
import sys
import logging
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import FIELD_INPUT_TYPE_MAPPING
from src.utils.question_loader import get_question_message
from src.services.missing_field_manager import get_next_missing_field
from src.utils.rag_helpers import extract_question_template_from_rag

logger = get_logger(__name__)

# 콘솔 핸들러 추가 (터미널 출력용)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)


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
        
        # 단계 표시 및 디버깅 (터미널 강제 출력)
        import sys
        import os
        msg = f"\n{'='*70}\n📍 [STEP 5] RE_QUESTION 노드 실행\n{'='*70}\n📌 세션 ID: {session_id}\n🏷️  사건 유형: {case_type} ({sub_case_type})\n❓ 누락 필드: {missing_fields}\n📋 state.keys(): {list(state.keys())}\n{'='*70}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        logger.info("="*70)
        logger.info("📍 [STEP 5] RE_QUESTION 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"🏷️  사건 유형: {case_type} ({sub_case_type})")
        logger.info(f"❓ 누락 필드: {missing_fields}")
        logger.info(f"📋 state.keys(): {list(state.keys())}")
        logger.info(f"📋 state 전체: {state}")
        logger.info("="*70)
        
        # missing_fields가 없으면 경고하고 SUMMARY로 전이
        if not missing_fields:
            logger.warning(f"[{session_id}] ⚠️  누락 필드가 없습니다. 이것은 비정상적일 수 있습니다.")
            logger.warning(f"[{session_id}] VALIDATION 노드가 missing_fields를 설정하지 않았을 수 있습니다.")
            logger.warning(f"[{session_id}] state 내용: {state}")
            state["bot_message"] = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
            return {
                **state,
                "next_state": "SUMMARY"
            }
        
        # 1. 우선순위 기반으로 다음 질문할 필드 선택 (asked_fields 및 skipped_fields 제외)
        conversation_history = state.get("conversation_history", [])
        asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
        skipped_fields = state.get("skipped_fields", [])  # 1차 서술에서 이미 답변된 필드
        
        # 상세 로깅 (강제 출력)
        print("\n" + "="*70)
        print(f"🔍 [RE_QUESTION] 필드 분석")
        print("="*70)
        print(f"📌 세션 ID: {session_id}")
        print(f"📋 missing_fields: {missing_fields}")
        print(f"💬 conversation_history: {len(conversation_history)}개")
        print(f"📝 asked_fields: {asked_fields}")
        print(f"⏭️  skipped_fields: {skipped_fields}")
        print("="*70 + "\n")
        logger.info("="*70)
        logger.info(f"🔍 [RE_QUESTION] 필드 분석")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📋 missing_fields: {missing_fields}")
        logger.info(f"💬 conversation_history: {len(conversation_history)}개")
        logger.info(f"📝 asked_fields: {asked_fields}")
        logger.info(f"⏭️  skipped_fields: {skipped_fields}")
        logger.debug(f"[{session_id}] RE_QUESTION: conversation_history 상세={[(qa.get('field'), qa.get('answer', '')[:30]) for qa in conversation_history]}")
        logger.info("="*70)
        
        # asked_fields와 skipped_fields를 모두 제외
        excluded_fields = set(asked_fields) | set(skipped_fields)
        
        # excluded_fields에 포함되지 않은 missing_fields만 필터링
        unasked_missing_fields = [f for f in missing_fields if f not in excluded_fields]
        
        import sys
        import os
        msg = f"🚫 excluded_fields: {excluded_fields}\n❓ unasked_missing_fields: {unasked_missing_fields}\n{'='*70}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        logger.info(f"[{session_id}] RE_QUESTION: missing_fields={missing_fields}, excluded_fields={excluded_fields}, unasked_missing_fields={unasked_missing_fields}")
        
        # 핵심 수정: missing_fields가 있으면 무조건 질문하도록 변경
        # unasked_missing_fields가 비어있어도 missing_fields가 있으면 질문해야 함
        if missing_fields:
            # unasked_missing_fields가 있으면 우선 사용
            if unasked_missing_fields:
                next_field = get_next_missing_field(unasked_missing_fields, case_type)
                logger.info(f"[{session_id}] unasked_missing_fields에서 필드 선택: {next_field}")
            else:
                # unasked_missing_fields가 비어있어도 missing_fields가 있으면 강제로 질문
                # 이것은 asked_fields나 skipped_fields에 포함되어 있지만 facts에 값이 없어서 다시 질문해야 하는 경우
                logger.warning(f"[{session_id}] ⚠️  unasked_missing_fields가 비어있지만 missing_fields가 있음. 강제로 첫 번째 필드 질문.")
                logger.warning(f"[{session_id}] missing_fields={missing_fields}, asked_fields={asked_fields}, skipped_fields={skipped_fields}")
                next_field = missing_fields[0]  # 첫 번째 누락 필드 강제 선택
                logger.info(f"[{session_id}] 강제 질문 필드 선택: {next_field}")
        else:
            # missing_fields가 정말 비어있으면 SUMMARY로 이동
            logger.info(f"[{session_id}] missing_fields가 비어있습니다. SUMMARY로 이동합니다.")
            state["bot_message"] = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
            return {
                **state,
                "next_state": "SUMMARY"
            }
        
        # next_field가 None이면 강제로 설정
        if not next_field:
            if missing_fields:
                logger.warning(f"[{session_id}] ⚠️  next_field가 None이지만 missing_fields가 있음. 첫 번째 필드 강제 선택: {missing_fields[0]}")
                next_field = missing_fields[0]
            else:
                logger.error(f"[{session_id}] ❌ next_field가 None이고 missing_fields도 비어있음. 이것은 버그입니다!")
                state["bot_message"] = "죄송합니다. 시스템 오류가 발생했습니다. 다시 시도해주세요."
                return {
                    **state,
                    "next_state": "FACT_COLLECTION"  # 에러 시에도 FACT_COLLECTION으로 전이하여 재시도 가능하게
                }
        
        # next_field가 여전히 None이면 에러
        if not next_field:
            logger.error(f"[{session_id}] ❌ next_field가 여전히 None입니다. 기본 필드 사용.")
            next_field = "incident_date"  # 최후의 수단
        
        import sys
        import os
        msg = f"✅ 선택된 질문 필드: {next_field}\n{'='*70}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        logger.info(f"[{session_id}] ✅ 다음 질문 필드: {next_field} (missing_fields={missing_fields}, asked_fields={asked_fields})")
        
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
        if not question or not question.strip():
            question = get_question_message(next_field, case_type)
            logger.debug(f"[{session_id}] RAG 결과에서 질문 추출 실패, YAML 파일 사용")
        else:
            logger.info(f"[{session_id}] RAG 결과에서 질문 템플릿 추출 성공: {next_field}")
        
        # 질문이 여전히 없으면 기본 질문 생성
        if not question or not question.strip():
            logger.warning(f"[{session_id}] ⚠️  질문 템플릿을 찾을 수 없습니다. 기본 질문 생성: {next_field}")
            # 기본 질문 템플릿
            default_questions = {
                "incident_date": "사건이 발생한 날짜를 알려주세요.",
                "amount": "금액은 얼마인가요?",
                "counterparty": "상대방은 누구인가요?",
                "evidence": "증거 자료가 있나요?",
                "evidence_type": "어떤 증거 자료가 있나요?",
                "location": "사건이 발생한 장소를 알려주세요."
            }
            question = default_questions.get(next_field, f"{next_field}에 대한 정보를 알려주세요.")
            logger.info(f"[{session_id}] 기본 질문 사용: {question}")
        
        # 질문이 여전히 없으면 최후의 수단
        if not question or not question.strip():
            logger.error(f"[{session_id}] ❌ 질문 생성 실패. 최후의 수단 사용.")
            question = f"{next_field}에 대한 정보를 알려주세요."
        
        # 4. current_question 업데이트 (Q-A 매칭 방식)
        # bot_message는 반드시 설정되어야 함
        state["bot_message"] = question
        import sys
        import os
        print(f"✅ bot_message 설정: {question[:100]}...", flush=True)
        os.write(2, f"✅ bot_message 설정: {question[:100]}...\n".encode('utf-8'))
        logger.info(f"[{session_id}] ✅ bot_message 설정 완료: {question[:100]}...")
        state["current_question"] = {
            "question": question,
            "field": next_field
        }
        state["expected_input"] = {
            "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
            "field": next_field
        }
        
        logger.info(f"[{session_id}] RE_QUESTION 완료: 필드={next_field}, question={question[:50]}..., excluded_fields={excluded_fields}")
        
        # 반환값에 bot_message가 반드시 포함되도록 보장
        result = {
            **state,
            "bot_message": question,  # 명시적으로 bot_message 설정
            "current_question": {
                "question": question,
                "field": next_field
            },
            "expected_input": {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            },
            "next_state": "FACT_COLLECTION"  # Loop: FACT_COLLECTION으로 복귀
        }
        
        # 최종 검증: bot_message가 반드시 있어야 함
        if not result.get("bot_message"):
            logger.error(f"[{session_id}] ❌ CRITICAL: bot_message가 없습니다! 강제 설정.")
            result["bot_message"] = f"{next_field}에 대한 정보를 알려주세요."
            import sys
            import os
            os.write(2, f"❌ CRITICAL: bot_message 없음! 강제 설정: {result['bot_message']}\n".encode('utf-8'))
            sys.stderr.write(f"❌ CRITICAL: bot_message 없음! 강제 설정: {result['bot_message']}\n")
            sys.stderr.flush()
        
        final_bot_msg = result.get('bot_message', '(없음)')
        final_next_state = result.get('next_state')
        import sys
        import os
        msg = f"\n{'='*70}\n✅ RE_QUESTION 노드 완료\n💬 반환 bot_message: {final_bot_msg[:100] if isinstance(final_bot_msg, str) else final_bot_msg}\n➡️  반환 next_state: {final_next_state}\n{'='*70}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        logger.info(f"[{session_id}] ✅ RE_QUESTION 반환값: bot_message={final_bot_msg[:100] if isinstance(final_bot_msg, str) else final_bot_msg}..., next_state={final_next_state}")
        return result
    
    except Exception as e:
        logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기본 질문 메시지 반환
        missing_fields = state.get("missing_fields", [])
        if missing_fields:
            next_field = missing_fields[0]
            question = get_question_message(next_field, state.get("case_type"))
            # 질문이 없으면 기본 질문 사용
            if not question or not question.strip():
                default_questions = {
                    "incident_date": "사건이 발생한 날짜를 알려주세요.",
                    "amount": "금액은 얼마인가요?",
                    "counterparty": "상대방은 누구인가요?",
                    "evidence": "증거 자료가 있나요?",
                    "evidence_type": "어떤 증거 자료가 있나요?"
                }
                question = default_questions.get(next_field, f"{next_field}에 대한 정보를 알려주세요.")
            
            state["bot_message"] = question
            state["current_question"] = {
                "question": question,
                "field": next_field
            }
            state["expected_input"] = {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            }
            logger.info(f"[{state.get('session_id', 'unknown')}] 폴백 처리: field={next_field}, question={question[:50]}...")
        else:
            state["bot_message"] = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
            state["next_state"] = "SUMMARY"
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }

