"""
FACT_COLLECTION Node 구현 (핵심)
"""
import asyncio
from typing import Dict, Any, List, Optional
from src.langgraph.state import StateContext
from src.services.entity_extractor import entity_extractor
from src.services.fact_emotion_splitter import fact_emotion_splitter
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.db.connection import db_manager
from src.db.models.case_fact import CaseFact
from src.db.models.case_emotion import CaseEmotion
from src.db.models.case_master import CaseMaster
from src.db.models.case_party import CaseParty
from src.db.models.case_evidence import CaseEvidence
from src.db.models.chat_session import ChatSession
from datetime import datetime

logger = get_logger(__name__)


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
        
        if not user_input:
            logger.warning("사용자 입력이 없습니다.")
            return {
                **state,
                "next_state": "FACT_COLLECTION"
            }
        
        # 0. 조건부 엔티티 추출을 위한 필드 결정
        facts = state.get("facts", {})
        expected_input = state.get("expected_input")
        
        # expected_input이 있으면 해당 필드만 추출
        entity_fields = None
        if expected_input and isinstance(expected_input, dict):
            expected_field = expected_input.get("field")
            field_mapping = {
                "incident_date": ["date"],
                "counterparty": ["party"],
                "amount": ["amount"],
                "evidence": []  # evidence는 엔티티 추출 불필요
            }
            entity_fields = field_mapping.get(expected_field)
            if entity_fields:
                logger.info(f"[{session_id}] 조건부 엔티티 추출: field={expected_field}, 추출 필드={entity_fields}")
        
        # case_type 변환 (한글 → 영문)
        case_type_mapping = {
            "민사": "CIVIL",
            "형사": "CRIMINAL",
            "가사": "FAMILY",
            "행정": "ADMIN"
        }
        main_case_type_en = case_type_mapping.get(case_type, case_type) if case_type else None
        
        # 1. 병렬 처리: 엔티티 추출, 사실/감정 분리, RAG 검색
        import concurrent.futures
        
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
            
            # 결과 대기
            entities = entities_future.result()
            fact_emotion = fact_emotion_future.result()
            rag_results = rag_future.result()
        
        logger.info(f"[{session_id}] 병렬 처리 완료: entities={list(entities.keys())}, fact_emotion={len(fact_emotion.get('facts', []))}개 사실, rag={len(rag_results)}개 결과")
        
        # 2. Facts 업데이트
        
        # expected_input이 있으면 해당 필드에 집중하여 추출
        if expected_input and isinstance(expected_input, dict):
            expected_field = expected_input.get("field")
            
            if expected_field == "incident_date":
                # 날짜 필드에 집중
                extracted_date = entities.get("date")
                if extracted_date:
                    facts["incident_date"] = extracted_date
                    logger.info(f"[{session_id}] 날짜 추출 성공: {extracted_date}")
                else:
                    # 엔티티 추출에서 날짜를 못 찾았으면 사용자 입력에서 직접 추출 시도
                    extracted_date = entity_extractor.extract_date(user_input)
                    if extracted_date:
                        facts["incident_date"] = extracted_date
                        logger.info(f"[{session_id}] 사용자 입력에서 날짜 추출 성공: {extracted_date}")
                    else:
                        logger.debug(f"[{session_id}] 날짜 추출 실패: user_input={user_input[:50]}")
            
            elif expected_field == "counterparty":
                # 당사자 필드에 집중
                if entities.get("party"):
                    party = entities["party"]
                    party_name = party.get("name") or party.get("type")
                    if party_name and party_name not in ["없음", "None", ""]:
                        facts["counterparty"] = party_name
                        logger.info(f"[{session_id}] 당사자 추출 성공: {party_name}")
                else:
                    # 엔티티 추출 실패 시 사용자 입력을 그대로 저장 (이름으로 추정)
                    if user_input and user_input.strip() and user_input not in ["없음", "None", ""]:
                        facts["counterparty"] = user_input.strip()
                        logger.info(f"[{session_id}] 사용자 입력을 당사자로 저장: {user_input.strip()}")
            
            elif expected_field == "amount":
                # 금액 필드에 집중
                if entities.get("amount"):
                    facts["amount"] = entities["amount"]
                    logger.info(f"[{session_id}] 금액 추출 성공: {entities['amount']}")
                else:
                    # 엔티티 추출 실패 시 사용자 입력에서 숫자 추출 시도
                    import re
                    numbers = re.findall(r'\d+', user_input.replace(',', '').replace('만', '0000').replace('천', '000'))
                    if numbers:
                        try:
                            amount = int(numbers[0])
                            facts["amount"] = amount
                            logger.info(f"[{session_id}] 사용자 입력에서 금액 추출 성공: {amount}")
                        except ValueError:
                            logger.debug(f"[{session_id}] 금액 변환 실패: {numbers[0]}")
            
            elif expected_field == "evidence":
                # 증거 필드는 아래에서 처리
                pass
        else:
            # expected_input이 없으면 모든 필드 추출 시도
            # 날짜 업데이트
            extracted_date = entities.get("date")
            if extracted_date:
                facts["incident_date"] = extracted_date
                logger.info(f"[{session_id}] 날짜 추출 성공: {extracted_date}")
            else:
                # 엔티티 추출에서 날짜를 못 찾았으면 사용자 입력에서 직접 추출 시도
                extracted_date = entity_extractor.extract_date(user_input)
                if extracted_date:
                    facts["incident_date"] = extracted_date
                    logger.info(f"[{session_id}] 사용자 입력에서 날짜 추출 성공: {extracted_date}")
                else:
                    logger.debug(f"[{session_id}] 날짜 추출 실패: user_input={user_input[:50]}")
            
            # 금액 업데이트
            if entities.get("amount"):
                facts["amount"] = entities["amount"]
                logger.info(f"[{session_id}] 금액 추출 성공: {entities['amount']}")
            
            # 당사자 업데이트
            if entities.get("party"):
                party = entities["party"]
                party_name = party.get("name") or party.get("type")
                # "없음"이나 빈 문자열은 저장하지 않음
                if party_name and party_name not in ["없음", "None", ""]:
                    facts["counterparty"] = party_name
                    logger.info(f"[{session_id}] 당사자 추출 성공: {party_name}")
                
                # party_type을 DB 제약 조건에 맞게 매핑 ("개인" 또는 "법인"만 허용)
                party_type_raw = party.get("type", "")
                if party_type_raw and party_type_raw not in ["없음", "None", ""]:
                    # "기타", "개인/법인", "기타" 등을 "개인"으로 매핑
                    if party_type_raw in ["개인", "법인"]:
                        facts["counterparty_type"] = party_type_raw
                    else:
                        # 기본값은 "개인"
                        facts["counterparty_type"] = "개인"
                        logger.debug(f"[{session_id}] party_type '{party_type_raw}'를 '개인'으로 매핑")
        
        # 행위 업데이트
        if entities.get("action"):
            action = entities["action"]
            if action.get("action_description"):
                facts["action_description"] = action["action_description"]
        
        # 증거(evidence) 필드 추출
        # expected_input이 evidence 필드를 요구하는 경우 또는 증거 관련 키워드가 있는 경우 추출
        expected_input = state.get("expected_input")
        is_evidence_question = (
            expected_input and 
            isinstance(expected_input, dict) and 
            expected_input.get("field") == "evidence"
        )
        
        # evidence 필드가 아직 없거나, evidence 질문에 대한 응답인 경우 추출 시도
        if facts.get("evidence") is None or is_evidence_question:
            # 사용자 입력에서 증거 관련 키워드 확인 (명시적 키워드만 사용)
            import re
            evidence_keywords_positive = [
                "증거", "계약서", "카톡", "이체", "내역", "대화", "송금", "대화내역", 
                "송금내역", "계좌이체", "문서", "사진", "영상", "녹음", "증빙", "자료"
            ]
            evidence_keywords_negative = ["없음", "없어", "아니", "no", "없다", "없습니다", "증거 없"]
            
            user_input_lower = user_input.lower()
            
            # 긍정 키워드 확인 (단어 경계 확인으로 정확한 매칭)
            positive_match = False
            for keyword in evidence_keywords_positive:
                # 단어 경계를 확인하여 정확한 매칭만 허용
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, user_input_lower):
                    positive_match = True
                    break
            
            if positive_match:
                facts["evidence"] = True
                logger.info(f"[{session_id}] 증거 추출 성공: True (키워드 매칭)")
                
                # 명시적 증거 키워드가 있으면 evidence_type도 함께 추출
                evidence_type_keywords = {
                    "계약서": "계약서",
                    "카톡": "대화내역",
                    "대화": "대화내역",
                    "대화내역": "대화내역",
                    "이체": "이체내역",
                    "송금": "이체내역",
                    "송금내역": "이체내역",
                    "계좌이체": "이체내역",
                    "사진": "사진",
                    "영상": "영상",
                    "녹음": "녹음",
                    "문서": "문서",
                    "증빙": "증빙",
                    "자료": "기타"
                }
                
                # 증거 타입 추출 (여러 키워드가 있으면 우선순위 적용)
                evidence_type = None
                for keyword, evidence_type_value in evidence_type_keywords.items():
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, user_input_lower):
                        evidence_type = evidence_type_value
                        break
                
                if evidence_type:
                    facts["evidence_type"] = evidence_type
                    logger.info(f"[{session_id}] 증거 타입 추출 성공: {evidence_type}")
            # 부정 키워드 확인
            elif any(keyword in user_input_lower for keyword in evidence_keywords_negative):
                facts["evidence"] = False
                logger.info(f"[{session_id}] 증거 추출 성공: False (키워드 매칭)")
            # evidence 질문에 대한 명시적 응답인 경우만 처리
            elif is_evidence_question:
                # "네", "있어요" 같은 단순 긍정 응답인 경우
                simple_positive_keywords = ["네", "있어", "있어요", "예", "그래", "yes"]
                if any(keyword in user_input_lower for keyword in simple_positive_keywords):
                    facts["evidence"] = True
                    # evidence_type은 아직 모름, 추가 질문 필요
                    logger.info(f"[{session_id}] 증거 질문에 대한 단순 긍정 응답, evidence=True 설정, evidence_type 추가 질문 필요")
                else:
                    # evidence 질문에 대한 응답인데 명시적 키워드가 없으면 None 유지 (추측하지 않음)
                    logger.debug(f"[{session_id}] 증거 질문에 대한 응답이지만 명시적 키워드 없음, 추출 건너뛰기")
        
        # evidence_type 필드 추출 (expected_input이 evidence_type인 경우 또는 evidence=True이고 evidence_type이 없는 경우)
        expected_input = state.get("expected_input")
        is_evidence_type_question = (
            expected_input and 
            isinstance(expected_input, dict) and 
            expected_input.get("field") == "evidence_type"
        )
        
        # evidence_type 질문에 대한 응답이거나, evidence=True이고 evidence_type이 없고 사용자 입력에 증거 키워드가 있는 경우
        if (is_evidence_type_question or (facts.get("evidence") is True and not facts.get("evidence_type"))) and user_input:
            # 사용자 입력에서 증거 타입 추출
            evidence_type_keywords = {
                "계약서": "계약서",
                "카톡": "대화내역",
                "대화": "대화내역",
                "대화내역": "대화내역",
                "이체": "이체내역",
                "송금": "이체내역",
                "송금내역": "이체내역",
                "계좌이체": "이체내역",
                "사진": "사진",
                "영상": "영상",
                "녹음": "녹음",
                "문서": "문서",
                "증빙": "증빙",
                "자료": "기타"
            }
            
            user_input_lower = user_input.lower()
            evidence_type = None
            
            for keyword, evidence_type_value in evidence_type_keywords.items():
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, user_input_lower):
                    evidence_type = evidence_type_value
                    break
            
            if evidence_type:
                facts["evidence_type"] = evidence_type
                logger.info(f"[{session_id}] 증거 타입 추출 성공: {evidence_type}")
            elif is_evidence_type_question:
                # evidence_type 질문에 대한 응답인데 키워드가 없으면 사용자 입력을 그대로 저장
                facts["evidence_type"] = user_input.strip()[:50]  # 최대 50자
                logger.info(f"[{session_id}] 증거 타입을 사용자 입력으로 저장: {facts['evidence_type']}")
        
        # 사실 정보에서 추가 추출
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
        state["emotion"].extend(emotions)
        
        # 6. DB에 저장
        with db_manager.get_db_session() as db_session:
            # case_master 조회
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if case:
                # case_fact 저장 (날짜나 금액이 업데이트된 경우만)
                if facts.get("incident_date") or facts.get("amount"):
                    fact = CaseFact(
                        case_id=case.case_id,
                        fact_type="사실",
                        incident_date=datetime.strptime(facts["incident_date"], "%Y-%m-%d").date() if facts.get("incident_date") else None,
                        amount=facts.get("amount"),
                        description=user_input[:500],  # 원문 일부
                        source_text=user_input
                    )
                    db_session.add(fact)
                
                # case_party 저장 (counterparty가 업데이트된 경우만)
                if facts.get("counterparty"):
                    # 기존 상대방 파티 삭제 후 새로 추가
                    db_session.query(CaseParty).filter(
                        CaseParty.case_id == case.case_id,
                        CaseParty.party_role == "상대방"
                    ).delete()
                    
                    # party_type을 DB 제약 조건에 맞게 검증 ("개인" 또는 "법인"만 허용)
                    party_type = facts.get("counterparty_type", "개인")
                    if party_type not in ["개인", "법인"]:
                        party_type = "개인"  # 기본값
                        logger.warning(f"[{session_id}] 잘못된 party_type을 '개인'으로 변경: {facts.get('counterparty_type')}")
                    
                    party = CaseParty(
                        case_id=case.case_id,
                        party_role="상대방",
                        party_type=party_type,
                        party_description=facts["counterparty"]
                    )
                    db_session.add(party)
                    logger.info(f"[{session_id}] CaseParty 저장: counterparty={facts['counterparty']}, party_type={party_type}")
                
                # case_emotion 저장
                for emotion_item in emotions:
                    emotion = CaseEmotion(
                        case_id=case.case_id,
                        emotion_type=emotion_item.get("type", ""),
                        intensity=emotion_item.get("intensity", 3),
                        source_text=emotion_item.get("source_text", "")
                    )
                    db_session.add(emotion)
                
                # case_evidence 저장 (evidence 필드가 업데이트된 경우만)
                if facts.get("evidence") is not None:
                    # 기존 증거 정보 삭제 후 새로 추가
                    db_session.query(CaseEvidence).filter(
                        CaseEvidence.case_id == case.case_id
                    ).delete()
                    
                    # 증거 타입 추출 (facts에서 가져오거나 사용자 입력에서 추출)
                    evidence_type = facts.get("evidence_type")
                    
                    if not evidence_type:
                        # facts에 없으면 사용자 입력에서 추출
                        evidence_type_keywords = {
                            "계약서": "계약서",
                            "카톡": "대화내역",
                            "대화": "대화내역",
                            "대화내역": "대화내역",
                            "이체": "이체내역",
                            "송금": "이체내역",
                            "송금내역": "이체내역",
                            "계좌이체": "이체내역",
                            "사진": "사진",
                            "영상": "영상",
                            "녹음": "녹음",
                            "문서": "문서",
                            "증빙": "증빙"
                        }
                        
                        user_input_lower = user_input.lower()
                        for keyword, evidence_type_value in evidence_type_keywords.items():
                            if keyword in user_input_lower:
                                evidence_type = evidence_type_value
                                break
                        
                        if not evidence_type:
                            evidence_type = "기타"
                    
                    evidence = CaseEvidence(
                        case_id=case.case_id,
                        evidence_type=evidence_type,
                        description=user_input[:255] if user_input else None,
                        available=bool(facts["evidence"])
                    )
                    db_session.add(evidence)
                    logger.info(f"[{session_id}] CaseEvidence 저장: available={facts['evidence']}, type={evidence_type}")
                
                db_session.commit()
        
        # 7. Completion Rate 재계산
        completion_rate = _calculate_completion_rate(state, rag_results)
        state["completion_rate"] = completion_rate
        
        # 세션 completion_rate 업데이트
        with db_manager.get_db_session() as db_session:
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            if chat_session:
                chat_session.completion_rate = completion_rate
                db_session.commit()
        
        # 8. 다음 질문 생성 (RAG K2 질문 템플릿 활용)
        next_question = _generate_next_question(state, rag_results)
        
        state["bot_message"] = next_question["message"]
        state["expected_input"] = next_question["expected_input"]
        
        logger.info(f"FACT_COLLECTION 완료: completion_rate={completion_rate}%")
        
        return {
            **state,
            "next_state": "VALIDATION"
        }
    
    except Exception as e:
        logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}")
        raise


def _calculate_completion_rate(state: StateContext, rag_results: list) -> int:
    """완성도 계산"""
    if not rag_results:
        return 0
    
    # RAG 결과에서 필수 필드 목록 추출
    required_fields = []
    if rag_results:
        # K2 문서에서 required_fields 추출 (간단화)
        # 실제로는 RAG 결과를 파싱하여 필수 필드 추출
        required_fields = ["incident_date", "counterparty", "amount", "evidence"]
    
    facts = state.get("facts", {})
    filled_count = sum(1 for field in required_fields if facts.get(field) is not None)
    
    if not required_fields:
        return 0
    
    completion_rate = int((filled_count / len(required_fields)) * 100)
    return min(completion_rate, 100)


def _generate_next_question(state: StateContext, rag_results: list) -> Dict[str, Any]:
    """다음 질문 생성"""
    facts = state.get("facts", {})
    
    # 아직 채워지지 않은 필드 확인
    if not facts.get("incident_date"):
        return {
            "message": "사건이 발생한 날짜를 알려주세요.",
            "expected_input": {"type": "date", "field": "incident_date"}
        }
    elif not facts.get("counterparty"):
        return {
            "message": "계약 상대방은 누구인가요?",
            "expected_input": {"type": "text", "field": "counterparty"}
        }
    elif not facts.get("amount"):
        return {
            "message": "문제가 된 금액은 얼마인가요?",
            "expected_input": {"type": "number", "field": "amount"}
        }
    elif facts.get("evidence") is None:
        return {
            "message": "계약서나 관련 증거를 가지고 계신가요?",
            "expected_input": {"type": "boolean", "field": "evidence"}
        }
    else:
        return {
            "message": "추가로 알려주실 내용이 있으신가요?",
            "expected_input": {"type": "text", "field": "additional_info"}
        }

