"""
VALIDATION Node 구현
"""
import re
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.helpers import parse_date
from src.utils.constants import (
    REQUIRED_FIELDS_BY_CASE_TYPE,
    EVIDENCE_TYPE_KEYWORDS,
    VALID_PARTY_TYPES,
    DEFAULT_PARTY_TYPE,
    PARTY_ROLES,
    Limits
)
from src.utils.field_extractors import (
    extract_evidence_from_input,
    extract_evidence_type_from_input,
    extract_date_from_input,
    extract_amount_from_input,
    extract_counterparty_from_input,
    has_date_pattern
)
from src.utils.rag_helpers import extract_required_fields_from_rag
from src.db.connection import db_manager
from src.db.models.case_missing_field import CaseMissingField
from src.db.models.case_master import CaseMaster
from src.db.models.case_fact import CaseFact
from src.db.models.case_party import CaseParty
from src.db.models.case_evidence import CaseEvidence

logger = get_logger(__name__)


@log_execution_time(logger)
def validation_node(state: StateContext) -> Dict[str, Any]:
    """
    VALIDATION Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        facts = state.get("facts", {})
        last_user_input = state.get("last_user_input", "")
        
        # 사용자 입력이 있으면 먼저 처리 (expected_input이 있으면 해당 필드에 집중, 없으면 모든 필드 시도)
        expected_input = state.get("expected_input")
        if last_user_input:
            expected_field = None
            if expected_input and isinstance(expected_input, dict):
                expected_field = expected_input.get("field")
            
            logger.info(f"[{session_id}] VALIDATION: 사용자 입력 처리 중 - expected_field={expected_field}, input={last_user_input[:Limits.LOG_PREVIEW_LENGTH]}")
            
            # 날짜 패턴 확인 (날짜가 포함된 입력은 counterparty로 저장하지 않음)
            has_date_pattern_flag = has_date_pattern(last_user_input)
            
            # 날짜 필드 처리 (우선순위 1: 날짜 패턴이 있거나 expected_field가 incident_date인 경우)
            if expected_field == "incident_date" or (not expected_field and (has_date_pattern_flag or not facts.get("incident_date"))):
                extracted_date = extract_date_from_input(last_user_input, facts.get("incident_date"))
                if extracted_date:
                    facts["incident_date"] = extracted_date
                    logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 날짜 추출: {extracted_date}")
                    has_date_pattern_flag = True
            
            # 당사자 필드 처리 (날짜 패턴이 없고 expected_field가 counterparty인 경우만)
            if expected_field == "counterparty" or (not expected_field and not has_date_pattern_flag and not facts.get("counterparty")):
                extracted_counterparty = extract_counterparty_from_input(last_user_input, facts.get("counterparty"))
                if extracted_counterparty:
                    facts["counterparty"] = extracted_counterparty
                    logger.info(f"[{session_id}] VALIDATION: 사용자 입력을 counterparty로 저장: {extracted_counterparty}")
            
            # 금액 필드 처리 (날짜 패턴 제외)
            if expected_field == "amount" or (not expected_field and not has_date_pattern_flag and not facts.get("amount")):
                if has_date_pattern_flag:
                    logger.debug(f"[{session_id}] VALIDATION: 날짜 패턴 감지, 금액 추출 건너뛰기")
                else:
                    extracted_amount = extract_amount_from_input(last_user_input, facts.get("amount"))
                    if extracted_amount is not None:
                        facts["amount"] = extracted_amount
                        logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 금액 추출: {extracted_amount}")
            
            # 증거 필드 처리
            if expected_field == "evidence" or (not expected_field and facts.get("evidence") is None):
                is_evidence_question = (expected_field == "evidence")
                evidence, evidence_type = extract_evidence_from_input(
                    last_user_input,
                    facts.get("evidence"),
                    is_evidence_question
                )
                if evidence is not None:
                    facts["evidence"] = evidence
                    if evidence_type:
                        facts["evidence_type"] = evidence_type
                    logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 증거 추출: {evidence}, type={evidence_type}")
                    if evidence and not evidence_type:
                        logger.info(f"[{session_id}] VALIDATION: 증거는 있지만 타입 불명, 추가 질문 필요")
            
            # facts 업데이트
            state["facts"] = facts
            logger.info(f"[{session_id}] VALIDATION: 사용자 입력 처리 후 facts={list(facts.keys())}, values={[(k, v) for k, v in facts.items() if v is not None]}")
            
            # 사용자 입력으로 업데이트된 facts를 DB에 저장
            last_user_input = state.get("last_user_input", "")
        
        logger.info(f"[{session_id}] VALIDATION Node 실행: facts={list(facts.keys())}, values={[(k, v) for k, v in facts.items() if v is not None]}")
        
        # 1. RAG K2에서 필수 필드 조회
        # case_type이 이미 영문이어야 함 (CIVIL, CRIMINAL, etc.)
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=case_type,
            sub_case_type=sub_case_type,
            # node_scope는 일단 제외 (ChromaDB 필터 제약)
            top_k=1
        )
        
        # 2. 필수 필드 목록 추출 (RAG 결과 우선, 없으면 상수 사용)
        required_fields = extract_required_fields_from_rag(rag_results)
        if not required_fields:
            # RAG 결과에서 추출 실패 시 상수 사용
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", []))
            logger.debug(f"[{session_id}] RAG 결과에서 필수 필드 추출 실패, 상수 사용: {required_fields}")
        else:
            logger.info(f"[{session_id}] RAG 결과에서 필수 필드 추출 성공: {required_fields}")
        
        # 3. 누락 필드 확인
        missing_fields = []
        for field in required_fields:
            if facts.get(field) is None:
                missing_fields.append(field)
        
        # 4. evidence=True이고 evidence_type이 없으면 추가 질문 필요
        if facts.get("evidence") is True and not facts.get("evidence_type"):
            # evidence_type을 누락 필드로 추가 (단, evidence는 이미 있으므로 missing_fields에 추가하지 않음)
            # 별도 플래그로 관리하거나 evidence_type을 missing_fields에 추가
            if "evidence_type" not in missing_fields:
                missing_fields.append("evidence_type")
            logger.info(f"[{session_id}] VALIDATION: evidence=True이지만 evidence_type 없음, 추가 질문 필요")
        
        state["missing_fields"] = missing_fields
        
        # 4. DB에 사용자 입력 처리 결과 및 누락 필드 저장 (단일 세션으로 통합)
        with db_manager.get_db_session() as db_session:
            try:
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if case:
                    # CaseFact 저장 (날짜나 금액이 업데이트된 경우)
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
                            description=last_user_input[:Limits.DESCRIPTION_MAX_LENGTH] if last_user_input else None,
                            source_text=last_user_input if last_user_input else None
                        )
                        db_session.add(fact)
                    
                    # CaseParty 저장 (counterparty가 업데이트된 경우)
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
                        logger.info(f"[{session_id}] VALIDATION: CaseParty 저장 완료: counterparty={facts['counterparty']}, party_type={party_type}")
                    
                    # CaseEvidence 저장 (evidence가 업데이트된 경우)
                    if facts.get("evidence") is not None:
                        # 기존 증거 삭제 후 새로 추가
                        db_session.query(CaseEvidence).filter(
                            CaseEvidence.case_id == case.case_id
                        ).delete()
                        
                        # 기본 증거 타입 (명시적 타입이 없을 때)
                        default_evidence_type = EVIDENCE_TYPE_KEYWORDS.get("대화내역", "대화내역") if facts["evidence"] else None
                        evidence_type = facts.get("evidence_type") or default_evidence_type
                        
                        evidence = CaseEvidence(
                            case_id=case.case_id,
                            available=facts["evidence"],
                            evidence_type=evidence_type
                        )
                        db_session.add(evidence)
                        logger.info(f"[{session_id}] VALIDATION: CaseEvidence 저장 완료: available={facts['evidence']}")
                    
                    # 기존 누락 필드 삭제
                    db_session.query(CaseMissingField).filter(
                        CaseMissingField.case_id == case.case_id
                    ).delete()
                    
                    # 새 누락 필드 저장
                    for field_key in missing_fields:
                        missing_field = CaseMissingField(
                            case_id=case.case_id,
                            field_key=field_key,
                            required=True,
                            resolved=False
                        )
                        db_session.add(missing_field)
                    
                    db_session.commit()
            except Exception as db_error:
                db_session.rollback()
                logger.error(f"[{session_id}] DB 저장 실패: {str(db_error)}", exc_info=True)
                raise
        
        # 5. 분기 조건 결정 (next_state만 반환하여 LangGraph가 자동으로 라우팅하도록 함)
        if missing_fields:
            next_state = "RE_QUESTION"
            logger.info(f"[{session_id}] VALIDATION 완료: 누락 필드 {len(missing_fields)}개, 다음 State={next_state}")
            return {
                **state,
                "next_state": next_state
            }
        else:
            next_state = "SUMMARY"
            logger.info(f"[{session_id}] VALIDATION 완료: 누락 필드 없음, 다음 State={next_state}")
            return {
                **state,
                "bot_message": "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다.",
                "next_state": next_state
            }
    
    except Exception as e:
        logger.error(f"VALIDATION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기존 missing_fields 유지하고 다음 상태로 전이
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

