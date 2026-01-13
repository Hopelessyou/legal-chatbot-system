"""
VALIDATION Node 구현 (Q-A 매칭 방식)
"""
import sys
import logging
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import (
    REQUIRED_FIELDS_BY_CASE_TYPE,
    Limits,
    VALID_PARTY_TYPES,
    DEFAULT_PARTY_TYPE,
    PARTY_ROLES,
    EVIDENCE_TYPE_KEYWORDS
)
from src.utils.rag_helpers import extract_required_fields_from_rag
from src.utils.helpers import parse_date
from src.langgraph.nodes.qa_helpers import _extract_facts_from_conversation
from src.db.connection import db_manager
from src.db.models.case_missing_field import CaseMissingField
from src.db.models.case_master import CaseMaster
from src.db.models.case_fact import CaseFact
from src.db.models.case_party import CaseParty
from src.db.models.case_evidence import CaseEvidence

logger = get_logger(__name__)

# 콘솔 핸들러 추가 (터미널 출력용)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)


@log_execution_time(logger)
def validation_node(state: StateContext) -> Dict[str, Any]:
    """
    VALIDATION Node 실행 (Q-A 매칭 방식)
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        conversation_history = state.get("conversation_history", [])
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        
        # 단계 표시
        print("\n" + "="*70)
        print("📍 [STEP 4] VALIDATION 노드 실행")
        print("="*70)
        print(f"📌 세션 ID: {session_id}")
        print(f"🏷️  사건 유형: {case_type} ({sub_case_type})")
        print(f"💬 대화 기록: {len(conversation_history)}개 Q-A 쌍")
        print("="*70 + "\n")
        logger.info("="*70)
        logger.info("📍 [STEP 4] VALIDATION 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"🏷️  사건 유형: {case_type} ({sub_case_type})")
        logger.info(f"💬 대화 기록: {len(conversation_history)}개 Q-A 쌍")
        logger.info("="*70)
        
        # GPT로 Q-A 쌍에서 facts 추출 (1차 서술 포함)
        # conversation_history에는 이미 1차 서술에서 추출된 정보가 포함됨
        try:
            facts = _extract_facts_from_conversation(conversation_history, case_type)
            logger.info(f"[{session_id}] GPT로 facts 추출 성공: {list(facts.keys())}")
        except Exception as e:
            logger.error(f"[{session_id}] GPT facts 추출 실패: {str(e)}", exc_info=True)
            # 폴백: 빈 facts로 시작 (기존 엔티티 추출 방식은 _extract_facts_from_conversation 내부에서 처리)
            facts = {}
            logger.warning(f"[{session_id}] GPT 추출 실패, 빈 facts로 계속 진행")
        
        # 1차 서술 분석 결과도 병합 (더 정확한 정보 우선)
        initial_analysis = state.get("initial_analysis", {})
        if initial_analysis:
            initial_facts = initial_analysis.get("extracted_facts", {})
            # conversation_history의 최신 정보가 우선, 없으면 initial_facts 사용
            for key, value in initial_facts.items():
                if facts.get(key) is None and value is not None:
                    facts[key] = value
                    logger.debug(f"[{session_id}] 1차 서술 분석 결과 병합: {key}={value}")
        
        state["facts"] = facts
        
        # 상세 로깅 (GPT 추출 결과 상세 확인)
        extracted_count = sum(1 for v in facts.values() if v is not None)
        logger.info(f"[{session_id}] GPT로 facts 추출 완료: {extracted_count}개 필드 추출 성공")
        logger.info(f"[{session_id}] 추출된 facts 상세: {[(k, v) for k, v in facts.items() if v is not None]}")
        logger.info(f"[{session_id}] conversation_history: {len(conversation_history)}개 Q-A 쌍")
        logger.info(f"[{session_id}] conversation_history 상세: {[(qa.get('field'), qa.get('answer', '')[:30]) for qa in conversation_history]}")
        
        # RAG에서 필수 필드 조회
        try:
            rag_results = rag_searcher.search(
                query="필수 필드",
                knowledge_type="K2",
                main_case_type=case_type,
                sub_case_type=sub_case_type,
                top_k=1
            )
            required_fields = extract_required_fields_from_rag(rag_results)
        except Exception as e:
            logger.warning(f"[{session_id}] RAG 필수 필드 조회 실패: {str(e)}")
            required_fields = []
        
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", []))
            logger.debug(f"[{session_id}] RAG 결과 없음, 기본 필수 필드 사용: {required_fields}")
        
        # 질문한 필드 확인 (conversation_history에서)
        asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
        
        # 상세 로깅
        logger.info(f"[{session_id}] asked_fields (conversation_history 기반): {asked_fields}")
        
        # 누락 필드 확인
        # 중요: conversation_history에 명시적인 Q-A 쌍이 있는 필드만 수집 완료로 간주
        # GPT가 추출한 facts는 참고용이며, 실제 질문한 필드만 수집 완료로 판단
        collected_fields = set()
        for qa in conversation_history:
            field = qa.get("field")
            answer = qa.get("answer", "").strip()
            # 명시적인 Q-A 쌍이 있고 답변이 있는 경우만 수집 완료로 간주
            if field and answer:
                collected_fields.add(field)
                logger.debug(f"[{session_id}] 수집 완료 필드 확인: {field} (Q-A 쌍 존재)")
        
        # missing_fields 계산: required_fields 중 collected_fields에 없는 필드
        missing_fields = [f for f in required_fields if f not in collected_fields]
        
        # 로깅
        for field in required_fields:
            if field in collected_fields:
                logger.info(f"[{session_id}] 필드 수집 완료: {field} (Q-A 쌍 존재)")
            else:
                logger.debug(f"[{session_id}] 누락 필드: {field} (Q-A 쌍 없음)")
        
        logger.info(f"[{session_id}] 누락 필드 분석 완료: required_fields={required_fields}, asked_fields={asked_fields}, missing_fields={missing_fields}")
        logger.info(f"[{session_id}] facts 상태: {[(k, v) for k, v in facts.items() if k in required_fields]}")
        
        # evidence=True인데 evidence_type이 없으면 추가 질문 필요
        if facts.get("evidence") is True and not facts.get("evidence_type"):
            if "evidence_type" not in missing_fields:
                missing_fields.append("evidence_type")
            logger.info(f"[{session_id}] VALIDATION: evidence=True이지만 evidence_type 없음, 추가 질문 필요")
        
        state["missing_fields"] = missing_fields
        
        # 터미널 강제 출력
        import sys
        import os
        print(f"📋 누락 필드 분석 완료", flush=True)
        print(f"   required_fields: {required_fields}", flush=True)
        print(f"   asked_fields: {asked_fields}", flush=True)
        print(f"   missing_fields: {missing_fields}", flush=True)
        os.write(2, f"📋 누락 필드 분석 완료\n".encode('utf-8'))
        os.write(2, f"   required_fields: {required_fields}\n".encode('utf-8'))
        os.write(2, f"   asked_fields: {asked_fields}\n".encode('utf-8'))
        os.write(2, f"   missing_fields: {missing_fields}\n".encode('utf-8'))
        
        # DB 저장 (facts를 DB 테이블에 저장)
        try:
            with db_manager.get_db_session() as db_session:
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if case:
                    # CaseFact 저장 (날짜나 금액이 있는 경우)
                    if facts.get("incident_date") or facts.get("amount"):
                        incident_date = None
                        if facts.get("incident_date"):
                            try:
                                parsed_date = parse_date(facts["incident_date"])
                                if parsed_date:
                                    incident_date = parsed_date.date()
                            except (ValueError, TypeError) as e:
                                logger.warning(f"[{session_id}] 날짜 파싱 실패: {facts['incident_date']}, 오류: {str(e)}")
                        
                        fact = CaseFact(
                            case_id=case.case_id,
                            fact_type="사실",
                            incident_date=incident_date,
                            amount=facts.get("amount"),
                            description=None,  # conversation_history에서 추출된 정보는 description에 저장하지 않음
                            source_text=None
                        )
                        db_session.add(fact)
                    
                    # CaseParty 저장 (counterparty가 있는 경우)
                    if facts.get("counterparty"):
                        # 기존 상대방 파티 삭제 후 새로 추가
                        db_session.query(CaseParty).filter(
                            CaseParty.case_id == case.case_id,
                            CaseParty.party_role == PARTY_ROLES["COUNTERPARTY"]
                        ).delete()
                        
                        party_type = facts.get("counterparty_type", DEFAULT_PARTY_TYPE)
                        if party_type not in VALID_PARTY_TYPES:
                            party_type = DEFAULT_PARTY_TYPE
                        
                        party = CaseParty(
                            case_id=case.case_id,
                            party_role=PARTY_ROLES["COUNTERPARTY"],
                            party_type=party_type,
                            party_description=facts["counterparty"]
                        )
                        db_session.add(party)
                    
                    # CaseEvidence 저장 (evidence가 있는 경우)
                    if facts.get("evidence") is not None:
                        # 기존 증거 삭제 후 새로 추가
                        db_session.query(CaseEvidence).filter(
                            CaseEvidence.case_id == case.case_id
                        ).delete()
                        
                        evidence_type = facts.get("evidence_type")
                        if not evidence_type and facts.get("evidence"):
                            evidence_type = "기타"
                        
                        evidence = CaseEvidence(
                            case_id=case.case_id,
                            available=bool(facts["evidence"]),
                            evidence_type=evidence_type
                        )
                        db_session.add(evidence)
                    
                    # CaseMissingField 저장
                    db_session.query(CaseMissingField).filter(
                        CaseMissingField.case_id == case.case_id
                    ).delete()
                    
                    for field_key in missing_fields:
                        missing_field = CaseMissingField(
                            case_id=case.case_id,
                            field_key=field_key,
                            required=True,
                            resolved=False
                        )
                        db_session.add(missing_field)
                    
                    db_session.commit()
                    logger.info(f"[{session_id}] VALIDATION: DB 저장 완료")
        except Exception as db_error:
            logger.error(f"[{session_id}] DB 저장 실패: {str(db_error)}", exc_info=True)
            # DB 오류가 있어도 계속 진행
        
        # 조건부 분기
        import sys
        import os
        if missing_fields:
            msg = f"➡️  VALIDATION → RE_QUESTION 전이 (누락 필드 {len(missing_fields)}개)\n"
            os.write(2, msg.encode('utf-8'))
            sys.stderr.write(msg)
            sys.stderr.flush()
            logger.info(f"[{session_id}] VALIDATION 완료: 누락 필드 {len(missing_fields)}개, 다음 State=RE_QUESTION")
            # RE_QUESTION 노드가 bot_message를 생성하므로 여기서는 설정하지 않음
            # 하지만 빈 메시지 방지를 위해 기본 메시지 설정
            if not state.get("bot_message"):
                state["bot_message"] = "추가 정보가 필요합니다."
            # missing_fields를 반드시 포함
            return {
                **state,
                "next_state": "RE_QUESTION",
                "missing_fields": missing_fields  # 명시적으로 포함
            }
        else:
            msg = f"➡️  VALIDATION → SUMMARY 전이 (누락 필드 없음)\n"
            os.write(2, msg.encode('utf-8'))
            sys.stderr.write(msg)
            sys.stderr.flush()
            logger.info(f"[{session_id}] VALIDATION 완료: 누락 필드 없음, 다음 State=SUMMARY")
            state["bot_message"] = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
            return {
                **state,
                "next_state": "SUMMARY",
                "missing_fields": []  # 명시적으로 빈 리스트
            }
    
    except Exception as e:
        logger.error(f"VALIDATION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백: 기존 conversation_history 기반으로 처리
        missing_fields = state.get("missing_fields", [])
        
        if missing_fields:
            return {
                **state,
                "bot_message": "추가 정보가 필요합니다. 질문에 답변해주세요.",
                "next_state": "RE_QUESTION"
            }
        else:
            return {
                **state,
                "bot_message": "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다.",
                "next_state": "SUMMARY"
            }

