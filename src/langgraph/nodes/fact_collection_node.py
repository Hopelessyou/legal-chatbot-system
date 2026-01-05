"""
FACT_COLLECTION Node 구현 (핵심)
"""
import concurrent.futures
import re
from typing import Dict, Any, List, Optional, Tuple
from src.langgraph.state import StateContext
from src.services.entity_extractor import entity_extractor
from src.services.fact_emotion_splitter import fact_emotion_splitter
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.helpers import parse_date
from src.utils.constants import (
    CASE_TYPE_MAPPING,
    FIELD_ENTITY_MAPPING,
    EVIDENCE_TYPE_KEYWORDS,
    VALID_PARTY_TYPES,
    DEFAULT_PARTY_TYPE,
    PARTY_ROLES,
    REQUIRED_FIELDS,
    FIELD_INPUT_TYPE_MAPPING,
    Limits
)
from src.utils.field_extractors import (
    extract_evidence_from_input,
    extract_evidence_type_from_input,
    extract_date_from_input,
    extract_amount_from_input
)
from src.utils.rag_helpers import (
    extract_required_fields_from_rag,
    extract_question_template_from_rag
)
from src.utils.question_loader import get_question_message
from src.db.connection import db_manager
from src.db.models.case_fact import CaseFact
from src.db.models.case_emotion import CaseEmotion
from src.db.models.case_master import CaseMaster
from src.db.models.case_party import CaseParty
from src.db.models.case_evidence import CaseEvidence
from src.db.models.chat_session import ChatSession

logger = get_logger(__name__)


def _extract_entities_parallel(
    user_input: str,
    entity_fields: Optional[List[str]],
    main_case_type_en: Optional[str],
    sub_case_type: Optional[str]
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    병렬 처리로 엔티티 추출, 사실/감정 분리, RAG 검색 수행
    
    Args:
        user_input: 사용자 입력
        entity_fields: 추출할 엔티티 필드 목록
        main_case_type_en: 사건 유형 (영문)
        sub_case_type: 세부 사건 유형
    
    Returns:
        (entities, fact_emotion, rag_results) 튜플
    """
    entities = {}
    fact_emotion = {"facts": [], "emotions": []}
    rag_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 엔티티 추출 (조건부)
        entities_future = executor.submit(
            entity_extractor.extract_all_entities,
            user_input,
            entity_fields
        )
        
        # 사실/감정 분리
        fact_emotion_future = executor.submit(
            fact_emotion_splitter.split_fact_emotion,
            user_input
        )
        
        # RAG K2 조회
        rag_future = executor.submit(
            rag_searcher.search,
            user_input,
            1,  # top_k
            "K2",  # knowledge_type
            main_case_type_en,  # main_case_type
            sub_case_type,  # sub_case_type
            None,  # node_scope
            0.0  # min_score
        )
        
        # 결과 대기 (예외 처리)
        try:
            entities = entities_future.result(timeout=30)
        except Exception as e:
            logger.error(f"엔티티 추출 실패: {str(e)}")
        
        try:
            fact_emotion = fact_emotion_future.result(timeout=30)
        except Exception as e:
            logger.error(f"사실/감정 분리 실패: {str(e)}")
        
        try:
            rag_results = rag_future.result(timeout=30)
        except Exception as e:
            logger.error(f"RAG 검색 실패: {str(e)}")
    
    return entities, fact_emotion, rag_results


def _update_facts_from_entities(
    facts: Dict[str, Any],
    entities: Dict[str, Any],
    user_input: str,
    expected_field: Optional[str],
    session_id: str
) -> Dict[str, Any]:
    """
    엔티티 추출 결과로부터 facts 업데이트
    
    Args:
        facts: 현재 facts 딕셔너리
        entities: 추출된 엔티티
        user_input: 사용자 입력
        expected_field: 기대하는 필드
        session_id: 세션 ID
    
    Returns:
        업데이트된 facts 딕셔너리
    """
    # expected_input이 있으면 해당 필드에 집중하여 추출
    if expected_field:
        if expected_field == "incident_date":
            extracted_date = entities.get("date") or extract_date_from_input(user_input, facts.get("incident_date"))
            if extracted_date:
                facts["incident_date"] = extracted_date
                logger.info(f"[{session_id}] 날짜 추출 성공: {extracted_date}")
        
        elif expected_field == "counterparty":
            if entities.get("party"):
                party = entities["party"]
                party_name = party.get("name") or party.get("type")
                if party_name and party_name not in ["없음", "None", ""]:
                    facts["counterparty"] = party_name
                    logger.info(f"[{session_id}] 당사자 추출 성공: {party_name}")
            else:
                if user_input and user_input.strip() and user_input not in ["없음", "None", ""]:
                    facts["counterparty"] = user_input.strip()
                    logger.info(f"[{session_id}] 사용자 입력을 당사자로 저장: {user_input.strip()}")
        
        elif expected_field == "amount":
            extracted_amount = entities.get("amount") or extract_amount_from_input(user_input, facts.get("amount"))
            if extracted_amount is not None:
                facts["amount"] = extracted_amount
                logger.info(f"[{session_id}] 금액 추출 성공: {extracted_amount}")
    else:
        # expected_input이 없으면 모든 필드 추출 시도
        # 날짜 업데이트
        extracted_date = entities.get("date") or extract_date_from_input(user_input, facts.get("incident_date"))
        if extracted_date:
            facts["incident_date"] = extracted_date
            logger.info(f"[{session_id}] 날짜 추출 성공: {extracted_date}")
        
        # 금액 업데이트
        extracted_amount = entities.get("amount") or extract_amount_from_input(user_input, facts.get("amount"))
        if extracted_amount is not None:
            facts["amount"] = extracted_amount
            logger.info(f"[{session_id}] 금액 추출 성공: {extracted_amount}")
        
        # 당사자 업데이트
        if entities.get("party"):
            party = entities["party"]
            party_name = party.get("name") or party.get("type")
            if party_name and party_name not in ["없음", "None", ""]:
                facts["counterparty"] = party_name
                logger.info(f"[{session_id}] 당사자 추출 성공: {party_name}")
            
            # party_type 매핑
            party_type_raw = party.get("type", "")
            if party_type_raw and party_type_raw not in ["없음", "None", ""]:
                if party_type_raw in VALID_PARTY_TYPES:
                    facts["counterparty_type"] = party_type_raw
                else:
                    facts["counterparty_type"] = DEFAULT_PARTY_TYPE
                    logger.debug(f"[{session_id}] party_type '{party_type_raw}'를 '{DEFAULT_PARTY_TYPE}'으로 매핑")
    
    # 행위 업데이트
    if entities.get("action"):
        action = entities["action"]
        if action.get("action_description"):
            facts["action_description"] = action["action_description"]
    
    return facts


def _update_facts_from_evidence(
    facts: Dict[str, Any],
    user_input: str,
    expected_input: Optional[Dict[str, Any]],
    session_id: str
) -> Dict[str, Any]:
    """
    증거 관련 facts 업데이트
    
    Args:
        facts: 현재 facts 딕셔너리
        user_input: 사용자 입력
        expected_input: 기대하는 입력
        session_id: 세션 ID
    
    Returns:
        업데이트된 facts 딕셔너리
    """
    is_evidence_question = (
        expected_input and 
        isinstance(expected_input, dict) and 
        expected_input.get("field") == "evidence"
    )
    
    # evidence 필드가 아직 없거나, evidence 질문에 대한 응답인 경우 추출 시도
    if facts.get("evidence") is None or is_evidence_question:
        evidence, evidence_type = extract_evidence_from_input(
            user_input,
            facts.get("evidence"),
            is_evidence_question
        )
        
        if evidence is not None:
            facts["evidence"] = evidence
            logger.info(f"[{session_id}] 증거 추출 성공: {evidence} (키워드 매칭)")
            
            if evidence_type:
                facts["evidence_type"] = evidence_type
                logger.info(f"[{session_id}] 증거 타입 추출 성공: {evidence_type}")
            elif evidence:
                logger.info(f"[{session_id}] 증거 질문에 대한 단순 긍정 응답, evidence=True 설정")
    
    # evidence_type 필드 추출
    is_evidence_type_question = (
        expected_input and 
        isinstance(expected_input, dict) and 
        expected_input.get("field") == "evidence_type"
    )
    
    if (is_evidence_type_question or (facts.get("evidence") is True and not facts.get("evidence_type"))) and user_input:
        extracted_evidence_type = extract_evidence_type_from_input(
            user_input,
            facts.get("evidence_type")
        )
        
        if extracted_evidence_type:
            facts["evidence_type"] = extracted_evidence_type
            logger.info(f"[{session_id}] 증거 타입 추출 성공: {extracted_evidence_type}")
    
    return facts


def _save_facts_to_database(
    session_id: str,
    facts: Dict[str, Any],
    emotions: List[Dict[str, Any]],
    user_input: str,
    completion_rate: int
) -> None:
    """
    Facts를 데이터베이스에 저장
    
    Args:
        session_id: 세션 ID
        facts: Facts 딕셔너리
        emotions: 감정 리스트
        user_input: 사용자 입력
        completion_rate: 완성도
    """
    with db_manager.get_db_session() as db_session:
        try:
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if not case:
                logger.warning(f"[{session_id}] CaseMaster를 찾을 수 없습니다.")
                return
            
            # CaseFact 저장 (날짜나 금액이 업데이트된 경우만)
            if facts.get("incident_date") or facts.get("amount"):
                # 날짜 파싱 에러 처리
                incident_date = None
                if facts.get("incident_date"):
                    try:
                        parsed_date = parse_date(facts["incident_date"])
                        if parsed_date:
                            incident_date = parsed_date.date()
                        else:
                            logger.warning(f"[{session_id}] 날짜 파싱 실패: {facts['incident_date']}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[{session_id}] 날짜 파싱 실패: {facts['incident_date']}, 오류: {str(e)}")
                
                fact = CaseFact(
                    case_id=case.case_id,
                    fact_type="사실",
                    incident_date=incident_date,
                    amount=facts.get("amount"),
                    description=user_input[:Limits.DESCRIPTION_MAX_LENGTH],
                    source_text=user_input
                )
                db_session.add(fact)
            
            # CaseParty 저장 (counterparty가 업데이트된 경우만)
            if facts.get("counterparty"):
                # 기존 상대방 파티 삭제 후 새로 추가
                db_session.query(CaseParty).filter(
                    CaseParty.case_id == case.case_id,
                    CaseParty.party_role == PARTY_ROLES["COUNTERPARTY"]
                ).delete()
                
                party_type = facts.get("counterparty_type", DEFAULT_PARTY_TYPE)
                if party_type not in VALID_PARTY_TYPES:
                    party_type = DEFAULT_PARTY_TYPE
                    logger.warning(f"[{session_id}] 잘못된 party_type을 '{DEFAULT_PARTY_TYPE}'으로 변경: {facts.get('counterparty_type')}")
                
                party = CaseParty(
                    case_id=case.case_id,
                    party_role=PARTY_ROLES["COUNTERPARTY"],
                    party_type=party_type,
                    party_description=facts["counterparty"]
                )
                db_session.add(party)
                logger.info(f"[{session_id}] CaseParty 저장: counterparty={facts['counterparty']}, party_type={party_type}")
            
            # CaseEmotion 저장
            for emotion_item in emotions:
                emotion = CaseEmotion(
                    case_id=case.case_id,
                    emotion_type=emotion_item.get("type", ""),
                    intensity=emotion_item.get("intensity", 3),
                    source_text=emotion_item.get("source_text", "")
                )
                db_session.add(emotion)
            
            # CaseEvidence 저장 (evidence 필드가 업데이트된 경우만)
            if facts.get("evidence") is not None:
                # 기존 증거 정보 삭제 후 새로 추가
                db_session.query(CaseEvidence).filter(
                    CaseEvidence.case_id == case.case_id
                ).delete()
                
                evidence_type = facts.get("evidence_type")
                if not evidence_type:
                    user_input_lower = user_input.lower()
                    for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
                        if keyword in user_input_lower:
                            evidence_type = evidence_type_value
                            break
                    if not evidence_type:
                        evidence_type = "기타"
                
                evidence = CaseEvidence(
                    case_id=case.case_id,
                    evidence_type=evidence_type,
                    description=user_input[:Limits.FILE_NAME_MAX_LENGTH] if user_input else None,
                    available=bool(facts["evidence"])
                )
                db_session.add(evidence)
                logger.info(f"[{session_id}] CaseEvidence 저장: available={facts['evidence']}, type={evidence_type}")
            
            # 세션 completion_rate 업데이트
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            if chat_session:
                chat_session.completion_rate = completion_rate
            
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            logger.error(f"[{session_id}] DB 저장 실패: {str(e)}", exc_info=True)
            raise


@log_execution_time(logger)
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    """
    FACT_COLLECTION Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "")
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        expected_input = state.get("expected_input")
        
        # 사용자 입력이 없으면 이전 질문 유지하고 FACT_COLLECTION 상태 유지
        if not user_input or not user_input.strip():
            logger.warning(f"[{session_id}] 사용자 입력이 없습니다. 이전 질문 유지")
            # 이전 bot_message가 있으면 유지, 없으면 새 질문 생성
            if not state.get("bot_message"):
                next_question = _generate_next_question(state, [])
                state["bot_message"] = next_question.get("message", "정보를 입력해주세요.")
                state["expected_input"] = next_question.get("expected_input")
            return {
                **state,
                "next_state": "FACT_COLLECTION"
            }
        
        # 사용자 입력이 의미 없는 경우 체크 (너무 짧거나 특정 패턴)
        user_input_stripped = user_input.strip()
        if len(user_input_stripped) < 2:
            logger.warning(f"[{session_id}] 사용자 입력이 너무 짧습니다: {user_input_stripped}")
            # 이전 질문 유지
            if state.get("bot_message"):
                return {
                    **state,
                    "next_state": "FACT_COLLECTION"
                }
        
        # 0. 사용자 입력 처리 전 facts 상태 저장 (처리 여부 확인용)
        import copy
        facts_before_update = copy.deepcopy(facts) if facts else {}
        expected_input = state.get("expected_input")
        expected_field = expected_input.get("field") if (expected_input and isinstance(expected_input, dict)) else None
        
        # 0-1. 조건부 엔티티 추출을 위한 필드 결정
        entity_fields = None
        if expected_input and isinstance(expected_input, dict):
            expected_field = expected_input.get("field")
            entity_fields = FIELD_ENTITY_MAPPING.get(expected_field)
            if entity_fields:
                logger.info(f"[{session_id}] 조건부 엔티티 추출: field={expected_field}, 추출 필드={entity_fields}")
        
        # case_type 변환 (한글 → 영문)
        main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None
        
        # 1. 병렬 처리: 엔티티 추출, 사실/감정 분리, RAG 검색
        entities, fact_emotion, rag_results = _extract_entities_parallel(
            user_input,
            entity_fields,
            main_case_type_en,
            sub_case_type
        )
        
        logger.info(f"[{session_id}] 병렬 처리 완료: entities={list(entities.keys())}, fact_emotion={len(fact_emotion.get('facts', []))}개 사실, rag={len(rag_results)}개 결과")
        
        # 2. Facts 업데이트 (엔티티에서)
        facts = _update_facts_from_entities(
            facts,
            entities,
            user_input,
            expected_field,
            session_id
        )
        
        # 3. Facts 업데이트 (증거 관련)
        facts_before_evidence = facts.copy()
        facts = _update_facts_from_evidence(
            facts,
            user_input,
            expected_input,
            session_id
        )
        
        # 증거 필드 업데이트 확인 로깅
        if expected_field == "evidence":
            evidence_before = facts_before_evidence.get("evidence")
            evidence_after = facts.get("evidence")
            if evidence_after != evidence_before:
                logger.info(f"[{session_id}] 증거 필드 업데이트: {evidence_before} → {evidence_after} (user_input: '{user_input[:50]}')")
            else:
                logger.warning(f"[{session_id}] 증거 필드 업데이트 실패: {evidence_before} (user_input: '{user_input[:50]}')")
        
        # 4. 사실 정보에서 추가 추출
        for fact_item in fact_emotion.get("facts", []):
            fact_content = fact_item.get("content", "")
            fact_type = fact_item.get("type", "")
            
            # 날짜가 없으면 사실 내용에서 재추출 시도
            if not facts.get("incident_date") and "날짜" in fact_type:
                date = entity_extractor.extract_date(fact_content)
                if date:
                    facts["incident_date"] = date
                    logger.info(f"[{session_id}] 사실 내용에서 날짜 추출 성공: {date}")
        
        # 5. Facts를 state에 명시적으로 저장
        state["facts"] = facts
        logger.info(f"[{session_id}] Facts 업데이트 완료: {list(facts.keys())}")
        
        # 6. 감정 정보 저장
        emotions = fact_emotion.get("emotions", [])
        if "emotion" not in state or not isinstance(state.get("emotion"), list):
            state["emotion"] = []
        state["emotion"].extend(emotions)
        
        # 7. Completion Rate 재계산
        completion_rate = _calculate_completion_rate(state, rag_results)
        state["completion_rate"] = completion_rate
        
        # 8. DB에 저장 (단일 세션으로 통합)
        _save_facts_to_database(
            session_id,
            facts,
            emotions,
            user_input,
            completion_rate
        )
        
        # 9. 사용자 입력 처리 여부 확인 (중복 질문 방지)
        # expected_field에 해당하는 값이 업데이트되었는지 확인
        field_updated = False
        any_field_updated = False
        
        if expected_field:
            # 이전 facts와 현재 facts 비교
            before_value = facts_before_update.get(expected_field)
            after_value = facts.get(expected_field)
            
            if after_value is not None and after_value != before_value:
                field_updated = True
                any_field_updated = True
                logger.info(f"[{session_id}] 필드 업데이트 확인: {expected_field}={after_value} (이전: {before_value})")
            elif after_value is not None and before_value is None:
                # None에서 값으로 변경된 경우
                field_updated = True
                any_field_updated = True
                logger.info(f"[{session_id}] 필드 업데이트 확인: {expected_field}={after_value} (새로 설정됨)")
        else:
            # expected_field가 없어도 facts가 변경되었는지 확인
            if facts != facts_before_update:
                any_field_updated = True
                logger.info(f"[{session_id}] Facts 변경 확인 (expected_field 없음): {list(facts.keys())}")
        
        # 10. 다음 질문 생성 (RAG K2 질문 템플릿 활용)
        next_question = _generate_next_question(state, rag_results)
        next_field = next_question.get("expected_input", {}).get("field") if next_question.get("expected_input") else None
        
        # 같은 필드를 반복해서 질문하지 않도록 확인
        asked_fields = state.get("asked_fields", [])
        
        # 사용자 입력이 처리되지 않았고, 같은 필드를 반복 질문하려는 경우
        if next_field == expected_field and not field_updated and expected_field:
            # asked_fields에 추가 (중복 질문 방지)
            if expected_field not in asked_fields:
                asked_fields.append(expected_field)
                state["asked_fields"] = asked_fields
                logger.warning(f"[{session_id}] 필드 '{expected_field}'를 asked_fields에 추가 (추출 실패: user_input='{user_input[:50]}')")
            
            # 다음 필드로 강제 이동 (asked_fields를 고려하여)
            next_question = _generate_next_question(state, rag_results)
            next_field = next_question.get("expected_input", {}).get("field") if next_question.get("expected_input") else None
            
            # 여전히 같은 필드인 경우, 최대 5번 시도
            retry_count = 0
            while next_field == expected_field and retry_count < 5:
                asked_fields = state.get("asked_fields", [])
                if expected_field not in asked_fields:
                    asked_fields.append(expected_field)
                    state["asked_fields"] = asked_fields
                next_question = _generate_next_question(state, rag_results)
                next_field = next_question.get("expected_input", {}).get("field") if next_question.get("expected_input") else None
                retry_count += 1
                logger.debug(f"[{session_id}] 다음 필드 찾기 시도 {retry_count}: next_field={next_field}, expected_field={expected_field}")
            
            if next_field == expected_field:
                # 모든 필드를 질문했거나, 더 이상 질문할 필드가 없는 경우
                logger.warning(f"[{session_id}] 필드 '{expected_field}' 추출 실패, 모든 필드 질문 완료 또는 요약으로 이동")
                # 요약으로 이동하도록 빈 메시지 설정
                state["bot_message"] = "추가 정보를 알려주세요." if next_question.get("message") else "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
            else:
                state["bot_message"] = next_question.get("message", "추가 정보를 알려주세요.")
        else:
            state["bot_message"] = next_question.get("message", "추가 정보를 알려주세요.")
        
        state["expected_input"] = next_question.get("expected_input")
        
        logger.info(f"[{session_id}] FACT_COLLECTION 완료: completion_rate={completion_rate}%, field_updated={field_updated}, any_field_updated={any_field_updated}, expected_field={expected_field}, next_field={next_field}")
        
        return {
            **state,
            "next_state": "VALIDATION"
        }
    
    except Exception as e:
        logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기존 facts 유지하고 다음 질문 생성
        facts = state.get("facts", {})
        next_question = _generate_next_question(state, [])
        
        return {
            **state,
            "bot_message": next_question.get("message", "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."),
            "expected_input": next_question.get("expected_input"),
            "next_state": "VALIDATION"
        }


def _calculate_completion_rate(state: StateContext, rag_results: list) -> int:
    """
    완성도 계산 (RAG 결과 활용)
    
    Args:
        state: State Context
        rag_results: RAG 검색 결과
    
    Returns:
        완성도 (0-100)
    """
    # RAG 결과에서 필수 필드 목록 추출
    required_fields = extract_required_fields_from_rag(rag_results)
    
    # RAG 결과에서 추출 실패 시 기본 필수 필드 사용
    if not required_fields:
        required_fields = REQUIRED_FIELDS
        logger.debug("RAG 결과에서 필수 필드 추출 실패, 기본 필수 필드 사용")
    
    facts = state.get("facts", {})
    filled_count = sum(1 for field in required_fields if facts.get(field) is not None)
    
    if not required_fields:
        return 0
    
    completion_rate = int((filled_count / len(required_fields)) * 100)
    return min(completion_rate, 100)


def _generate_next_question(state: StateContext, rag_results: list) -> Dict[str, Any]:
    """
    다음 질문 생성 (RAG 결과 활용, 중복 질문 방지)
    
    Args:
        state: State Context
        rag_results: RAG 검색 결과
    
    Returns:
        질문 딕셔너리 (message, expected_input)
    """
    from config.priority import get_priority_order
    
    facts = state.get("facts", {})
    case_type = state.get("case_type")
    asked_fields = state.get("asked_fields", [])  # 이미 질문한 필드 목록
    
    # RAG 결과에서 필수 필드 목록 추출
    required_fields = extract_required_fields_from_rag(rag_results)
    if not required_fields:
        required_fields = REQUIRED_FIELDS
    
    # 우선순위 순서 가져오기
    priority_order = get_priority_order(case_type)
    
    # 우선순위에 따라 누락된 필드 찾기 (asked_fields 제외)
    next_field = None
    
    # 1. 우선순위 순서대로 확인
    for field in priority_order:
        if field in required_fields and facts.get(field) is None and field not in asked_fields:
            next_field = field
            break
    
    # 2. 우선순위에 없는 필수 필드 확인
    if not next_field:
        for field in required_fields:
            if facts.get(field) is None and field not in asked_fields:
                next_field = field
                break
    
    # 3. evidence 필드가 없고 아직 질문하지 않았으면 추가
    if not next_field and facts.get("evidence") is None and "evidence" not in asked_fields:
        next_field = "evidence"
    
    # 4. evidence_type 필드가 없고 evidence가 True인 경우
    if not next_field and facts.get("evidence") is True and not facts.get("evidence_type") and "evidence_type" not in asked_fields:
        next_field = "evidence_type"
    
    # 다음 질문 생성
    if next_field:
        # asked_fields에 추가 (중복 질문 방지)
        if next_field not in asked_fields:
            asked_fields.append(next_field)
            state["asked_fields"] = asked_fields
        
        # RAG 결과에서 질문 템플릿 추출 시도
        question_message = extract_question_template_from_rag(rag_results, next_field)
        if not question_message:
            # RAG 결과에서 추출 실패 시 YAML 파일에서 가져오기
            question_message = get_question_message(next_field, case_type)
        
        logger.info(f"[{state.get('session_id', 'unknown')}] 다음 질문 생성: {next_field} (asked_fields: {asked_fields})")
        
        return {
            "message": question_message,
            "expected_input": {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            }
        }
    else:
        # 모든 필수 필드가 채워졌거나 이미 질문한 경우
        # asked_fields를 확인하여 모든 필드를 질문했는지 확인
        all_fields_asked = all(
            field in asked_fields or facts.get(field) is not None
            for field in required_fields
        )
        
        if all_fields_asked:
            # 모든 필드를 질문했고, 추가 정보를 요청
            return {
                "message": get_question_message("additional_info", case_type),
                "expected_input": {"type": "text", "field": "additional_info"}
            }
        else:
            # 질문할 필드가 없지만 아직 채워지지 않은 필드가 있는 경우
            # 이미 질문한 필드 중에서 다시 질문 (사용자가 답변하지 않은 경우)
            for field in required_fields:
                if facts.get(field) is None and field in asked_fields:
                    # 이미 질문했지만 답변이 없는 경우, 다른 방식으로 질문
                    question_message = get_question_message(field, case_type)
                    return {
                        "message": f"{question_message} (이전에 답변해주시지 않으셨습니다.)",
                        "expected_input": {
                            "type": FIELD_INPUT_TYPE_MAPPING.get(field, "text"),
                            "field": field
                        }
                    }
            
            # 모든 경우를 처리했지만 질문할 필드가 없는 경우
            return {
                "message": get_question_message("additional_info", case_type),
                "expected_input": {"type": "text", "field": "additional_info"}
            }

