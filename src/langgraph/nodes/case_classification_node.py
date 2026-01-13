"""
CASE_CLASSIFICATION Node 구현
"""
import sys
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.keyword_extractor import keyword_extractor
from src.services.gpt_client import gpt_client
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import (
    CASE_TYPE_MAPPING,
    DEFAULT_CASE_TYPE,
    DEFAULT_SUB_CASE_TYPE,
    CaseStage,
    Limits,
    REQUIRED_FIELDS_BY_CASE_TYPE,
    REQUIRED_FIELDS
)
from src.utils.rag_helpers import extract_required_fields_from_rag
from src.utils.question_loader import get_question_message
from src.utils.helpers import get_kst_now
from src.langgraph.nodes.qa_helpers import _analyze_initial_description
from config.fallback_keywords import get_fallback_case_type
from src.db.connection import db_manager
from src.db.models.case_master import CaseMaster
from src.db.models.chat_session import ChatSession

logger = get_logger(__name__)


def post_classification_analysis(state: StateContext) -> StateContext:
    """
    CASE_CLASSIFICATION 이후 1차 서술 분석
    
    Args:
        state: 현재 State Context
    
    Returns:
        분석 결과를 포함한 state 업데이트
    """
    try:
        session_id = state.get("session_id", "unknown")
        initial_description = state.get("last_user_input", "")  # CASE_CLASSIFICATION에서 받은 입력
        case_type = state.get("case_type")
        
        logger.info(f"🔍 [1차 서술 분석] 시작: session_id={session_id}")
        logger.info(f"📝 initial_description: {initial_description[:100] if initial_description else '(없음)'}...")
        logger.info(f"🏷️  case_type: {case_type}")
        
        if not initial_description or not case_type:
            logger.warning(f"[{session_id}] 1차 서술 분석 스킵: initial_description 또는 case_type 없음")
            logger.info(f"⚠️  1차 서술 분석 스킵: initial_description={bool(initial_description)}, case_type={bool(case_type)}")
            # case_type이 없어도 기본 필수 필드로 missing_fields 설정
            if not case_type:
                logger.warning(f"[{session_id}] case_type이 없어 기본 필수 필드 사용")
                default_required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(DEFAULT_CASE_TYPE, REQUIRED_FIELDS)
            else:
                default_required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
            
            state["initial_description"] = initial_description
            state["initial_analysis"] = {
                "extracted_facts": {},
                "answered_fields": [],
                "missing_fields": default_required_fields
            }
            state["conversation_history"] = []
            state["skipped_fields"] = []
            state["missing_fields"] = default_required_fields  # 모든 필드를 질문 대상으로 설정
            logger.info(f"[{session_id}] 기본 missing_fields 설정: {default_required_fields}")
            return state
        
        # RAG에서 필수 필드 목록 가져오기
        try:
            rag_results = rag_searcher.search(
                query="필수 필드",
                knowledge_type="K2",
                main_case_type=case_type,
                top_k=1
            )
            required_fields = extract_required_fields_from_rag(rag_results)
        except Exception as e:
            logger.warning(f"[{session_id}] RAG 필수 필드 조회 실패: {str(e)}")
            required_fields = []
        
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
            logger.debug(f"[{session_id}] RAG 결과 없음, 기본 필수 필드 사용: {required_fields}")
        
        # 1차 서술 분석 (GPT)
        logger.info(f"🤖 GPT API 호출 시작: 1차 서술 분석...")
        analysis_result = _analyze_initial_description(
            initial_description,
            case_type,
            required_fields
        )
        logger.info(f"✅ GPT API 호출 완료")
        
        # State 업데이트
        state["initial_description"] = initial_description
        state["initial_analysis"] = analysis_result
        
        # 1차 서술에서 추출된 정보를 conversation_history에 추가
        extracted_facts = analysis_result.get("extracted_facts", {})
        answered_fields = analysis_result.get("answered_fields", [])
        
        conversation_history = []
        for field in answered_fields:
            if extracted_facts.get(field) is not None:
                # RAG에서 해당 필드의 질문 템플릿 가져오기 (로깅용)
                question = get_question_message(field, case_type)
                conversation_history.append({
                    "question": question,
                    "field": field,
                    "answer": str(extracted_facts[field]),
                    "source": "initial_description",
                    "timestamp": get_kst_now().isoformat()
                })
        
        state["conversation_history"] = conversation_history
        state["skipped_fields"] = answered_fields
        state["missing_fields"] = analysis_result.get("missing_fields", [])
        
        # 상세 로깅
        logger.info(f"[{session_id}] 1차 서술 분석 완료: answered_fields={answered_fields} ({len(answered_fields)}개), missing_fields={state['missing_fields']} ({len(state['missing_fields'])}개)")
        logger.debug(f"[{session_id}] conversation_history 추가: {len(conversation_history)}개 Q-A 쌍")
        logger.debug(f"[{session_id}] extracted_facts: {[(k, v) for k, v in extracted_facts.items() if v is not None]}")
        
        logger.info(f"✅ 1차 서술 분석 완료: answered_fields={len(answered_fields)}개, missing_fields={len(state['missing_fields'])}개")
        logger.info(f"📊 conversation_history: {len(conversation_history)}개 Q-A 쌍")
        
        return state
    
    except Exception as e:
        logger.error(f"1차 서술 분석 실패: {str(e)}", exc_info=True)
        # 폴백: 모든 필드를 질문 대상으로 설정
        case_type = state.get("case_type", DEFAULT_CASE_TYPE)
        default_required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
        if not default_required_fields:
            default_required_fields = REQUIRED_FIELDS
        
        state["initial_description"] = state.get("last_user_input", "")
        state["initial_analysis"] = {
            "extracted_facts": {},
            "answered_fields": [],
            "missing_fields": default_required_fields
        }
        state["conversation_history"] = []
        state["skipped_fields"] = []
        state["missing_fields"] = default_required_fields  # 모든 필드를 질문 대상으로 설정
        logger.warning(f"[{state.get('session_id', 'unknown')}] 1차 서술 분석 실패, 모든 필드를 질문 대상으로 설정: {default_required_fields}")
        return state


@log_execution_time(logger)
def case_classification_node(state: StateContext) -> Dict[str, Any]:
    """
    CASE_CLASSIFICATION Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    import os
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "")
        
        # 단계 표시 (강제 출력 - os.write 사용)
        os.write(2, b"\n" + b"="*70 + b"\n")
        os.write(2, "[STEP 2] CASE_CLASSIFICATION 노드 실행!!!\n".encode('utf-8'))
        os.write(2, b"="*70 + b"\n")
        os.write(2, f"세션 ID: {session_id}\n".encode('utf-8'))
        os.write(2, f"사용자 입력: {user_input[:50] if user_input else '(없음)'}...\n".encode('utf-8'))
        os.write(2, b"="*70 + b"\n")
        logger.info("="*70)
        logger.info("📍 [STEP 2] CASE_CLASSIFICATION 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📝 사용자 입력: {user_input[:50] if user_input else '(없음)'}...")
        logger.info("="*70)
        logger.info("="*70)
        logger.info("📍 [STEP 2] CASE_CLASSIFICATION 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📝 사용자 입력: {user_input[:Limits.LOG_PREVIEW_LENGTH] if user_input else 'None'}...")
        logger.info("="*70)
        
        if not user_input:
            logger.warning("사용자 입력이 없습니다.")
            return {
                **state,
                "bot_message": "사건과 관련된 내용을 알려주세요.",
                "next_state": "CASE_CLASSIFICATION"
            }
        
        # 1. 키워드 및 의미 추출
        semantic_features = keyword_extractor.extract_semantic_features(user_input)
        keywords = semantic_features.get("keywords", [])
        
        # 2. RAG K1 조회 (사건 유형 분류 기준)
        query = " ".join(keywords) if keywords else user_input
        rag_results = rag_searcher.search_by_knowledge_type(
            query=query,
            knowledge_type="K1",
            top_k=3
        )
        
        # 3. 사건 유형 결정
        main_case_type = None
        sub_case_type = None
        
        if rag_results:
            # 가장 유사도 높은 결과 사용
            best_match = rag_results[0]
            metadata = best_match.get("metadata", {})
            main_case_type = metadata.get("main_case_type")
            sub_case_type = metadata.get("sub_case_type")
        
        # GPT API로 최종 분류 (RAG 결과를 참고)
        if not main_case_type:
            try:
                # 프롬프트 파일에서 로드 시도
                from src.services.prompt_loader import prompt_loader
                prompt_template = prompt_loader.load_prompt("case_classification", sub_dir="classification")
                if prompt_template:
                    classification_prompt = prompt_template.format(user_input=user_input)
                else:
                    # 기본 프롬프트 사용
                    classification_prompt = f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
가능한 분류:
- 민사: 계약, 불법행위, 대여금, 손해배상
- 형사: 사기, 성범죄, 폭행
- 가사: 이혼, 상속
- 행정: 행정처분, 세무

텍스트: {user_input}

JSON 형식으로 반환:
{{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}}"""
            except Exception as prompt_error:
                logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
                classification_prompt = f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
가능한 분류:
- 민사: 계약, 불법행위, 대여금, 손해배상
- 형사: 사기, 성범죄, 폭행
- 가사: 이혼, 상속
- 행정: 행정처분, 세무

텍스트: {user_input}

JSON 형식으로 반환:
{{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}}"""
            
            try:
                response = gpt_client.chat_completion(
                    messages=[{"role": "user", "content": classification_prompt}],
                    temperature=0.3,
                    max_tokens=Limits.MAX_TOKENS_CLASSIFICATION,
                    session_id=session_id,
                    node_name="case_classification"
                )
                
                import json
                import re
                
                # 응답에서 JSON 추출 (마크다운 코드 블록 제거)
                content = response["content"].strip()
                
                # ```json ... ``` 또는 ``` ... ``` 제거
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                else:
                    # JSON 객체만 추출
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(0)
                
                classification = json.loads(content)
                main_case_type = classification.get("main_case_type")
                sub_case_type = classification.get("sub_case_type")
            except Exception as e:
                logger.error(f"GPT 분류 실패: {str(e)}")
                # 폴백: 키워드 기반 간단한 분류
                main_case_type, sub_case_type = get_fallback_case_type(user_input)
        
        # 4. case_type 변환 (한글 → 영문)
        main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type) if main_case_type else None
        
        # 5. State 업데이트
        state["case_type"] = main_case_type_en
        state["sub_case_type"] = sub_case_type
        
        # 5. DB에 case_master 생성/업데이트
        with db_manager.get_db_session() as db_session:
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                # case_master 생성 또는 업데이트
                from src.db.models.case_master import CaseMaster
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if not case:
                    case = CaseMaster(
                        session_id=session_id,
                        main_case_type=main_case_type_en,
                        sub_case_type=sub_case_type,
                        case_stage=CaseStage.BEFORE_CONSULTATION.value
                    )
                    db_session.add(case)
                else:
                    case.main_case_type = main_case_type_en
                    case.sub_case_type = sub_case_type
                
                # 세션 상태 업데이트
                chat_session.current_state = "CASE_CLASSIFICATION"
                db_session.commit()
        
        # 6. State 전이 로깅
        from src.langgraph.state_logger import log_state_transition
        log_state_transition(
            session_id=session_id,
            from_state="INIT",
            to_state="CASE_CLASSIFICATION",
            condition_key="user_input_received"
        )
        
        # 7. 1차 서술 분석 수행 (Q-A 매칭 방식)
        import os
        os.write(2, "[1차 서술 분석] 시작!!!\n".encode('utf-8'))
        logger.info(f"🔍 1차 서술 분석 시작...")
        try:
            state = post_classification_analysis(state)
            skipped_fields = state.get("skipped_fields", [])
            missing_fields = state.get("missing_fields", [])
            if skipped_fields:
                os.write(2, f"[1차 서술 분석] 성공!!! skipped_fields={skipped_fields}, missing_fields={missing_fields}\n".encode('utf-8'))
                logger.info(f"[{session_id}] 1차 서술 분석 성공: skipped_fields={skipped_fields}")
                logger.info(f"✅ 1차 서술 분석 성공: skipped_fields={skipped_fields}")
            else:
                os.write(2, f"[1차 서술 분석] 결과: skipped_fields 없음, missing_fields={missing_fields}\n".encode('utf-8'))
                logger.info(f"⚠️  1차 서술 분석 결과: skipped_fields 없음")
        except Exception as e:
            os.write(2, f"[1차 서술 분석] 실패!!! {str(e)}\n".encode('utf-8'))
            logger.error(f"[{session_id}] 1차 서술 분석 실패: {str(e)}", exc_info=True)
            logger.error(f"❌ 1차 서술 분석 실패: {str(e)}")
            # 폴백: 1차 서술 분석 실패해도 계속 진행
            # 모든 필드를 질문 대상으로 설정
            case_type = state.get("case_type", DEFAULT_CASE_TYPE)
            default_required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
            if not default_required_fields:
                default_required_fields = REQUIRED_FIELDS
            
            state["initial_description"] = state.get("last_user_input", "")
            state["initial_analysis"] = {
                "extracted_facts": {},
                "answered_fields": [],
                "missing_fields": default_required_fields
            }
            state["conversation_history"] = []
            state["skipped_fields"] = []
            state["missing_fields"] = default_required_fields  # 모든 필드를 질문 대상으로 설정
            os.write(2, f"[에러] 1차 서술 분석 실패!!! 모든 필드를 질문 대상으로 설정: {default_required_fields}\n".encode('utf-8'))
            logger.warning(f"[{session_id}] 1차 서술 분석 실패, 모든 필드를 질문 대상으로 설정: {default_required_fields}")
        
        # 8. 1차 서술 분석 결과 반영하여 다음 질문 생성
        skipped_fields = state.get("skipped_fields", [])
        missing_fields = state.get("missing_fields", [])
        conversation_history = state.get("conversation_history", [])
        
        logger.info(f"[{session_id}] 1차 서술 분석 결과 확인: skipped_fields={skipped_fields} ({len(skipped_fields) if skipped_fields else 0}개), missing_fields={missing_fields} ({len(missing_fields) if missing_fields else 0}개), conversation_history={len(conversation_history)}개")
        logger.info(f"✅ 1차 서술 분석 결과: skipped_fields={len(skipped_fields) if skipped_fields else 0}개, missing_fields={len(missing_fields) if missing_fields else 0}개")
        
        if skipped_fields:
            logger.info(f"[{session_id}] 1차 서술에서 이미 답변된 필드: {skipped_fields} ({len(skipped_fields)}개)")
            logger.info(f"✅ 1차 서술 분석 결과: {len(skipped_fields)}개 필드 이미 답변됨")
        
        if missing_fields:
            logger.info(f"[{session_id}] 1차 서술에서 누락된 필드: {missing_fields} ({len(missing_fields)}개)")
            logger.info(f"❓ 질문 필요한 필드: {len(missing_fields)}개")
        
        # 1차 서술 분석 결과 반영하여 다음 질문 생성
        import os
        os.write(2, f"[확인] missing_fields: {missing_fields} (개수: {len(missing_fields) if missing_fields else 0})\n".encode('utf-8'))
        os.write(2, f"[확인] skipped_fields: {skipped_fields} (개수: {len(skipped_fields) if skipped_fields else 0})\n".encode('utf-8'))
        
        # missing_fields가 있으면 다음 질문 생성 (질문해야 할 필드가 있음)
        if missing_fields and len(missing_fields) > 0:
            # FACT_COLLECTION의 _generate_next_question을 사용하여 다음 질문 생성
            from src.langgraph.nodes.fact_collection_node import _generate_next_question
            try:
                os.write(2, f"[다음 질문 생성] 호출 시작!!! missing_fields={missing_fields}\n".encode('utf-8'))
                logger.info(f"[{session_id}] _generate_next_question 호출 시작... (missing_fields={missing_fields})")
                next_question = _generate_next_question(state)
                os.write(2, f"[다음 질문 생성] 성공!!! field={next_question.get('field')}, question={next_question.get('question', '')[:50]}...\n".encode('utf-8'))
                logger.info(f"[{session_id}] _generate_next_question 결과: field={next_question.get('field')}, question={next_question.get('question', '')[:100]}...")
                logger.info(f"📝 다음 질문 생성 성공: field={next_question.get('field')}, question={next_question.get('question', '')[:50]}...")
                
                state["bot_message"] = next_question["question"]
                state["current_question"] = next_question
                state["expected_input"] = {
                    "type": "text",
                    "field": next_question.get("field", "fact_description")
                }
                logger.info(f"[{session_id}] 1차 서술 분석 기반 다음 질문 설정 완료: {next_question.get('field')}")
            except Exception as e:
                os.write(2, f"[다음 질문 생성] 실패!!! {str(e)}\n".encode('utf-8'))
                logger.error(f"[{session_id}] _generate_next_question 실패: {str(e)}", exc_info=True)
                logger.warning(f"[{session_id}] 다음 질문 생성 실패, 기본 메시지 사용: {str(e)}")
                logger.error(f"❌ 다음 질문 생성 실패: {str(e)}")
                state["bot_message"] = "추가 정보를 알려주세요."
                state["expected_input"] = {
                    "type": "text",
                    "field": "fact_description"
                }
        elif skipped_fields and len(skipped_fields) > 0:
            # skipped_fields만 있고 missing_fields가 없으면 모든 필드가 이미 답변됨
            # 하지만 아직 추가 정보가 필요할 수 있으므로 기본 메시지
            os.write(2, f"[경고] 모든 필수 필드가 이미 답변됨!!! skipped_fields={skipped_fields}\n".encode('utf-8'))
            logger.info(f"[{session_id}] 모든 필수 필드가 이미 답변됨 (skipped_fields={skipped_fields}), 추가 정보 요청")
            state["bot_message"] = "추가로 알려주실 정보가 있으신가요?"
            state["expected_input"] = {
                "type": "text",
                "field": "additional_info"
            }
        else:
            # 1차 서술 분석 결과가 없거나 모든 필드가 비어있으면 기본 메시지
            os.write(2, f"[에러] 1차 서술 분석 결과 없음!!! 기본 메시지 사용!!! skipped_fields={skipped_fields}, missing_fields={missing_fields}\n".encode('utf-8'))
            logger.warning(f"[{session_id}] 1차 서술 분석 결과가 없음 (skipped_fields={skipped_fields}, missing_fields={missing_fields}), 기본 메시지 사용")
            logger.warning(f"⚠️ 1차 서술 분석 결과 없음, 기본 메시지 사용")
            state["bot_message"] = "사건과 관련된 구체적인 내용을 알려주세요."
            state["expected_input"] = {
                "type": "text",
                "field": "fact_description"
            }
        
        final_bot_message = state.get("bot_message", "")
        os.write(2, f"[완료] CASE_CLASSIFICATION!!! bot_message='{final_bot_message[:50]}...'\n".encode('utf-8'))
        logger.info(f"[{session_id}] CASE_CLASSIFICATION 완료: {main_case_type_en} / {sub_case_type}, bot_message='{final_bot_message[:100]}...', skipped_fields={skipped_fields}, missing_fields={missing_fields}")
        logger.info(f"✅ CASE_CLASSIFICATION 완료: bot_message='{final_bot_message[:50]}...'")
        
        # bot_message가 없으면 기본 메시지 설정
        if not final_bot_message:
            state["bot_message"] = "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다."
            logger.warning(f"[{session_id}] ⚠️  bot_message가 없어 기본 메시지 설정")
        
        return {
            **state,
            "bot_message": state.get("bot_message", "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다."),  # 명시적으로 포함
            "next_state": "FACT_COLLECTION"
        }
    
    except Exception as e:
        logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기본 사건 유형으로 설정하고 계속 진행
        state["case_type"] = DEFAULT_CASE_TYPE
        state["sub_case_type"] = DEFAULT_SUB_CASE_TYPE
        state["bot_message"] = "사건과 관련된 구체적인 내용을 알려주세요."
        state["expected_input"] = {
            "type": "text",
            "field": "fact_description"
        }
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }

