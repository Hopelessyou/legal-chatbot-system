"""
VALIDATION Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.db.connection import db_manager
from src.db.models.case_missing_field import CaseMissingField
from src.db.models.case_master import CaseMaster
from src.db.models.case_fact import CaseFact
from src.db.models.case_party import CaseParty
from src.db.models.case_evidence import CaseEvidence
from datetime import datetime

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
            
            logger.info(f"[{session_id}] VALIDATION: 사용자 입력 처리 중 - expected_field={expected_field}, input={last_user_input[:50]}")
            
            # 날짜 패턴 확인 (날짜가 포함된 입력은 counterparty로 저장하지 않음)
            import re
            date_patterns = [r'\d+월', r'\d+일', r'\d+년', r'올해', r'작년', r'내년', r'올해\s*\d+월', r'작년\s*\d+월', r'인지', r'발생']
            has_date_pattern = any(re.search(pattern, last_user_input) for pattern in date_patterns)
            
            # 날짜 필드 처리 (우선순위 1: 날짜 패턴이 있거나 expected_field가 incident_date인 경우)
            if expected_field == "incident_date" or (not expected_field and (has_date_pattern or not facts.get("incident_date"))):
                # 날짜 필드: 간단한 날짜 추출 시도
                from src.services.entity_extractor import entity_extractor
                extracted_date = entity_extractor.extract_date(last_user_input)
                if extracted_date:
                    facts["incident_date"] = extracted_date
                    logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 날짜 추출: {extracted_date}")
                    # 날짜가 추출되면 counterparty로 저장하지 않음
                    has_date_pattern = True
            
            # 당사자 필드 처리 (날짜 패턴이 없고 expected_field가 counterparty인 경우만)
            if expected_field == "counterparty" or (not expected_field and not has_date_pattern and not facts.get("counterparty")):
                # 당사자 필드: 사용자 입력을 그대로 저장 (이름으로 추정)
                if last_user_input.strip() and last_user_input not in ["없음", "None", ""]:
                    # 숫자만 있거나 너무 짧으면 제외
                    if len(last_user_input.strip()) >= 2 and not last_user_input.strip().isdigit():
                        facts["counterparty"] = last_user_input.strip()
                        logger.info(f"[{session_id}] VALIDATION: 사용자 입력을 counterparty로 저장: {last_user_input.strip()}")
            
            if expected_field == "amount" or (not expected_field and not has_date_pattern and not facts.get("amount")):
                # 금액 필드: 숫자 추출 시도 (날짜 패턴 제외)
                # 날짜 패턴이 포함된 경우 금액 추출 건너뛰기
                if has_date_pattern:
                    logger.debug(f"[{session_id}] VALIDATION: 날짜 패턴 감지, 금액 추출 건너뛰기")
                else:
                    numbers = re.findall(r'\d+', last_user_input.replace(',', '').replace('만', '0000').replace('천', '000'))
                    if numbers:
                        try:
                            amount = int(numbers[0])
                            # 금액은 일반적으로 1000원 이상 (날짜의 일/월과 구분)
                            if amount >= 1000:  # 1000원 이상만 금액으로 간주
                                facts["amount"] = amount
                                logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 금액 추출: {amount}")
                        except ValueError:
                            pass
            
            if expected_field == "evidence" or (not expected_field and facts.get("evidence") is None):
                # 증거 필드: 키워드 확인
                evidence_keywords_positive = ["있음", "있어", "네", "그래", "예", "yes", "계약서", "카톡", "이체", "내역", "대화", "송금"]
                user_input_lower = last_user_input.lower()
                
                # 명시적 증거 키워드 확인 (단순 "네"와 구분)
                explicit_evidence_keywords = ["계약서", "카톡", "이체", "내역", "대화", "송금", "대화내역", "송금내역", "계좌이체", "문서", "사진", "영상", "녹음", "증빙", "자료", "증거"]
                has_explicit_keyword = any(keyword in user_input_lower for keyword in explicit_evidence_keywords)
                
                if has_explicit_keyword:
                    facts["evidence"] = True
                    logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 증거 추출: True (명시적 키워드)")
                elif any(keyword in user_input_lower for keyword in ["있음", "있어", "네", "그래", "예", "yes"]):
                    # 단순 긍정 응답인 경우
                    facts["evidence"] = True
                    # evidence_type이 없으면 추가 질문 필요
                    if not facts.get("evidence_type"):
                        logger.info(f"[{session_id}] VALIDATION: 증거는 있지만 타입 불명, 추가 질문 필요")
                else:
                    evidence_keywords_negative = ["없음", "없어", "아니", "no", "없다", "없습니다"]
                    if any(keyword in user_input_lower for keyword in evidence_keywords_negative):
                        facts["evidence"] = False
                        logger.info(f"[{session_id}] VALIDATION: 사용자 입력에서 증거 추출: False")
            
            # facts 업데이트
            state["facts"] = facts
            logger.info(f"[{session_id}] VALIDATION: 사용자 입력 처리 후 facts={list(facts.keys())}, values={[(k, v) for k, v in facts.items() if v is not None]}")
            
            # 사용자 입력으로 업데이트된 facts를 DB에 저장
            last_user_input = state.get("last_user_input", "")
            with db_manager.get_db_session() as db_session:
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if case:
                    # CaseFact 저장 (날짜나 금액이 업데이트된 경우)
                    if facts.get("incident_date") or facts.get("amount"):
                        fact = CaseFact(
                            case_id=case.case_id,
                            fact_type="사실",
                            incident_date=datetime.strptime(facts["incident_date"], "%Y-%m-%d").date() if facts.get("incident_date") else None,
                            amount=facts.get("amount"),
                            description=last_user_input[:500] if last_user_input else None,
                            source_text=last_user_input if last_user_input else None
                        )
                        db_session.add(fact)
                    
                    # CaseParty 저장 (counterparty가 업데이트된 경우)
                    if facts.get("counterparty"):
                        # 기존 상대방 파티 삭제 후 새로 추가
                        db_session.query(CaseParty).filter(
                            CaseParty.case_id == case.case_id,
                            CaseParty.party_role == "상대방"
                        ).delete()
                        
                        party_type = facts.get("counterparty_type", "개인")
                        if party_type not in ["개인", "법인"]:
                            party_type = "개인"
                        
                        party = CaseParty(
                            case_id=case.case_id,
                            party_role="상대방",
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
                        
                        evidence = CaseEvidence(
                            case_id=case.case_id,
                            available=facts["evidence"],
                            evidence_type="대화내역" if facts["evidence"] else None
                        )
                        db_session.add(evidence)
                        logger.info(f"[{session_id}] VALIDATION: CaseEvidence 저장 완료: available={facts['evidence']}")
                    
                    db_session.commit()
        
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
        
        # 2. 필수 필드 목록 추출 (간단화 - 실제로는 RAG 결과 파싱)
        required_fields = ["incident_date", "counterparty", "amount", "evidence"]
        
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
        
        # 4. DB에 누락 필드 저장
        with db_manager.get_db_session() as db_session:
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if case:
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
        
        # 5. 분기 조건 결정
        if missing_fields:
            next_state = "RE_QUESTION"
            # RE_QUESTION Node를 즉시 실행하여 질문 생성
            from src.langgraph.nodes.re_question_node import re_question_node
            re_question_result = re_question_node(state)
            logger.info(f"VALIDATION 완료: 누락 필드 {len(missing_fields)}개, 다음 State={next_state}")
            # RE_QUESTION 노드의 결과를 반환 (next_state는 FACT_COLLECTION으로 설정됨)
            return re_question_result
        else:
            next_state = "SUMMARY"
            # 모든 필드가 충족되었으므로 SUMMARY Node를 즉시 실행
            from src.langgraph.nodes.summary_node import summary_node
            logger.info(f"VALIDATION 완료: 누락 필드 없음, 다음 State={next_state}, SUMMARY Node 실행 시작")
            summary_result = summary_node(state)
            logger.info(f"VALIDATION 완료: SUMMARY Node 실행 완료")
            return summary_result
    
    except Exception as e:
        logger.error(f"VALIDATION Node 실행 실패: {str(e)}")
        raise

