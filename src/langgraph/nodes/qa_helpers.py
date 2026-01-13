"""
Q-A 매칭 방식 헬퍼 함수
"""
import json
from typing import Dict, Any, List, Optional
from src.services.gpt_client import gpt_client
from src.utils.logger import get_logger
from src.utils.constants import REQUIRED_FIELDS_BY_CASE_TYPE
from src.utils.exceptions import GPTAPIError

logger = get_logger(__name__)


def _analyze_initial_description(
    initial_description: str,
    case_type: str,
    required_fields: List[str]
) -> Dict[str, Any]:
    """
    1차 서술(초기 사용자 입력)을 GPT로 분석하여 포함된 정보 추출
    
    Args:
        initial_description: 초기 사용자 입력 ("친구가 2024년 1월 2일에 300만원을 빌려갔는데...")
        case_type: 사건 유형 (CIVIL, CRIMINAL, etc.)
        required_fields: 필수 필드 목록 (RAG K2에서 가져온 것)
    
    Returns:
        {
            "extracted_facts": {...},  # 추출된 정보
            "answered_fields": ["incident_date", "amount", "counterparty"],  # 이미 답변된 필드
            "missing_fields": ["evidence", "evidence_type"]  # 질문해야 할 필드
        }
    """
    try:
        prompt = f"""다음은 법률 상담 챗봇에 처음 입력한 사용자의 사건 서술입니다.
사건 유형: {case_type}

사용자 서술:
{initial_description}

위 서술에서 다음 필드에 대한 정보가 포함되어 있는지 분석하고, 포함된 정보를 추출해주세요.

필수 필드 목록:
{', '.join(required_fields)}

각 필드별 설명:
- incident_date: 사건 발생 날짜
- amount: 금액 또는 손해액
- counterparty: 상대방 이름 또는 설명
- counterparty_type: 상대방 유형 (개인/법인/기관)
- evidence: 증거 유무
- evidence_type: 증거 종류

다음 JSON 형식으로 반환해주세요:
{{
    "extracted_facts": {{
        "incident_date": "날짜가 있으면 YYYY-MM-DD 형식으로, 없으면 null",
        "amount": "금액이 있으면 숫자만, 없으면 null",
        "counterparty": "상대방이 있으면 이름, 없으면 null",
        "counterparty_type": "상대방 유형이 있으면, 없으면 null",
        "evidence": "증거 언급이 있으면 true/false, 없으면 null",
        "evidence_type": "증거 종류가 있으면, 없으면 null"
    }},
    "answered_fields": ["이미 답변된 필드 목록"],
    "missing_fields": ["질문해야 할 필드 목록"]
}}

주의사항:
- 서술에 명시적으로 언급된 정보만 추출 (추측하지 않음)
- 날짜는 "2024년 1월 2일", "24년 1월 2일", "1월 2일", "어제", "지난달" 등 다양한 형식을 YYYY-MM-DD로 변환
- 금액은 "300만원", "3백만원", "3,000,000원" 등을 숫자만 추출
- "없음", "모름" 등은 해당 필드가 null로 처리
- 정보가 불확실하면 null로 처리
- answered_fields에는 extracted_facts에서 null이 아닌 필드만 포함
- missing_fields에는 required_fields 중 answered_fields에 없는 필드만 포함

JSON만 반환하세요 (설명 없이):
"""
        
        # session_id는 함수 인자에 없으므로 None으로 전달 (비용 추적은 선택적)
        response = gpt_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
            session_id=None,  # 1차 서술 분석은 세션 컨텍스트 없이 호출될 수 있음
            node_name="analyze_initial_description"
        )
        
        result = json.loads(response["content"])
        
        # 검증: answered_fields와 missing_fields가 올바르게 설정되었는지 확인
        extracted_facts = result.get("extracted_facts", {})
        answered_fields = result.get("answered_fields", [])
        missing_fields = result.get("missing_fields", [])
        
        # extracted_facts에서 null이 아닌 필드만 answered_fields에 포함되도록 보정
        actual_answered = [
            field for field in required_fields
            if extracted_facts.get(field) is not None
        ]
        
        # missing_fields는 required_fields 중 answered_fields에 없는 필드
        actual_missing = [
            field for field in required_fields
            if field not in actual_answered
        ]
        
        result["answered_fields"] = actual_answered
        result["missing_fields"] = actual_missing
        
        # 상세 로깅
        logger.info(f"[1차 서술 분석] 완료: answered_fields={actual_answered} ({len(actual_answered)}개), missing_fields={actual_missing} ({len(actual_missing)}개)")
        logger.debug(f"[1차 서술 분석] extracted_facts: {[(k, v) for k, v in extracted_facts.items() if v is not None]}")
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"1차 서술 분석 JSON 파싱 실패: {str(e)}")
        logger.warning("1차 서술 분석 실패, 모든 필드를 질문 대상으로 설정")
        # 폴백: 빈 결과 반환 (모든 필드를 질문해야 함)
        return {
            "extracted_facts": {},
            "answered_fields": [],
            "missing_fields": required_fields
        }
    except GPTAPIError as e:
        logger.error(f"1차 서술 분석 GPT API 실패: {str(e)}", exc_info=True)
        logger.warning("GPT API 실패, 모든 필드를 질문 대상으로 설정")
        # GPT API 실패 시 폴백: 빈 결과 반환
        return {
            "extracted_facts": {},
            "answered_fields": [],
            "missing_fields": required_fields
        }
    except Exception as e:
        logger.error(f"1차 서술 분석 실패: {str(e)}", exc_info=True)
        logger.warning("예상치 못한 오류 발생, 모든 필드를 질문 대상으로 설정")
        # 폴백: 빈 결과 반환
        return {
            "extracted_facts": {},
            "answered_fields": [],
            "missing_fields": required_fields
        }


def _extract_facts_from_conversation(
    conversation_history: List[Dict[str, str]],
    case_type: str
) -> Dict[str, Any]:
    """
    Q-A 대화 기록에서 구조화된 facts 추출
    
    Args:
        conversation_history: 질문-답변 쌍 리스트
        case_type: 사건 유형
    
    Returns:
        구조화된 facts 딕셔너리
    """
    try:
        if not conversation_history:
            return {}
        
        # Q-A 쌍을 텍스트로 변환
        qa_text = "\n\n".join([
            f"Q: {qa.get('question', '')}\nA: {qa.get('answer', '')}"
            for qa in conversation_history
        ])
        
        # GPT 프롬프트 구성
        prompt = f"""다음은 법률 상담 챗봇과 사용자의 질문-답변 대화입니다.
사건 유형: {case_type}

대화 내용:
{qa_text}

위 대화 내용에서 다음 정보를 추출하여 JSON 형식으로 반환해주세요:
{{
    "incident_date": "사건 발생 날짜 (YYYY-MM-DD 형식, 없으면 null)",
    "amount": "금액 (숫자만, 없으면 null)",
    "counterparty": "상대방 이름 또는 설명 (없으면 null)",
    "counterparty_type": "상대방 유형 (개인/법인/기관, 없으면 null)",
    "evidence": "증거 유무 (true/false/null)",
    "evidence_type": "증거 종류 (없으면 null)",
    "action_description": "행위 설명 (간단히, 없으면 null)"
}}

주의사항:
- 날짜는 반드시 YYYY-MM-DD 형식으로 변환해야 합니다
  * "25년 1월 2일" → "2025-01-02"
  * "2024년 10월 15일" → "2024-10-15"
  * "어제" → 오늘 기준 전날 날짜 (예: "2025-01-08")
  * "지난주", "지난달" 등도 현재 날짜 기준으로 계산하여 YYYY-MM-DD 형식으로 변환
  * 날짜를 확정할 수 없으면 null
- 금액은 "300만원" → 3000000 형식으로 변환 (숫자만)
- 증거 질문에 "네", "있음", "있습니다" 등 긍정 답변은 evidence: true
- 증거 질문에 "없음", "모름" 등 부정 답변은 evidence: false
- 정보가 없으면 null로 반환
- 추측하지 말고 대화 내용에 있는 정보만 추출
- **중요**: "어제", "오늘", "지난주" 같은 상대적 날짜는 현재 날짜 기준으로 계산하여 정확한 YYYY-MM-DD 형식으로 변환

JSON만 반환하세요 (설명 없이):
"""
        
        # GPT API 호출
        # session_id는 함수 인자에 없으므로 None으로 전달 (비용 추적은 선택적)
        response = gpt_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 낮은 온도로 일관성 확보
            response_format={"type": "json_object"},  # JSON 형식 강제
            session_id=None,  # conversation_history에서 추출할 수 없음
            node_name="extract_facts_from_conversation"
        )
        
        # JSON 파싱
        facts = json.loads(response["content"])
        
        # null 문자열을 None으로 변환 및 타입 정리
        for key, value in facts.items():
            if value == "null" or value == "" or value is None:
                facts[key] = None
            # 날짜 필드는 문자열이어야 함
            elif key == "incident_date" and isinstance(value, str):
                # 빈 문자열이나 "null" 문자열 체크
                if value.strip() == "" or value.strip().lower() == "null":
                    facts[key] = None
                else:
                    # 날짜 형식 검증 (YYYY-MM-DD)
                    facts[key] = value.strip()
        
        # 상세 로깅 (GPT 추출 결과 상세 확인)
        extracted_count = sum(1 for v in facts.values() if v is not None)
        logger.info(f"[Q-A 대화 분석] 완료: {extracted_count}개 필드 추출 성공")
        logger.info(f"[Q-A 대화 분석] 추출된 facts 전체: {facts}")
        logger.info(f"[Q-A 대화 분석] 추출된 facts (값 있음): {[(k, v) for k, v in facts.items() if v is not None]}")
        logger.info(f"[Q-A 대화 분석] Q-A 쌍 수: {len(conversation_history)}개")
        logger.info(f"[Q-A 대화 분석] Q-A 쌍 상세: {[(qa.get('field'), qa.get('answer', '')[:50]) for qa in conversation_history]}")
        
        # incident_date가 추출되었는지 특별히 확인
        if facts.get("incident_date"):
            logger.info(f"[Q-A 대화 분석] ✅ incident_date 추출 성공: {facts.get('incident_date')}")
        else:
            logger.warning(f"[Q-A 대화 분석] ⚠️ incident_date 추출 실패 또는 null")
        
        return facts
    
    except json.JSONDecodeError as e:
        logger.error(f"Q-A 대화 분석 JSON 파싱 실패: {str(e)}")
        logger.warning("Q-A 대화 분석 실패, 빈 facts 반환")
        # 폴백: 빈 facts 반환 (기존 방식으로 폴백하지 않음 - Q-A 매칭 방식 유지)
        return {}
    except GPTAPIError as e:
        logger.error(f"Q-A 대화 분석 GPT API 실패: {str(e)}", exc_info=True)
        logger.warning("GPT API 실패, 빈 facts 반환 (기존 엔티티 추출 방식으로 폴백 가능)")
        # GPT API 실패 시 기존 엔티티 추출 방식으로 폴백 시도
        return _fallback_extract_facts_from_conversation(conversation_history)
    except Exception as e:
        logger.error(f"Q-A 대화 분석 실패: {str(e)}", exc_info=True)
        logger.warning("예상치 못한 오류 발생, 빈 facts 반환")
        return {}


def _fallback_extract_facts_from_conversation(
    conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    GPT API 실패 시 기존 엔티티 추출 방식으로 폴백
    
    Args:
        conversation_history: 질문-답변 쌍 리스트
    
    Returns:
        구조화된 facts 딕셔너리
    """
    try:
        from src.services.entity_extractor import entity_extractor
        from src.utils.field_extractors import (
            extract_date_from_input,
            extract_amount_from_input,
            extract_evidence_from_input
        )
        
        facts = {}
        
        # conversation_history에서 각 답변을 분석
        for qa in conversation_history:
            field = qa.get("field", "")
            answer = qa.get("answer", "")
            
            if not answer or not field:
                continue
            
            # 필드별로 기존 추출 함수 사용
            if field == "incident_date":
                date = extract_date_from_input(answer, facts.get("incident_date"))
                if date:
                    facts["incident_date"] = date
            
            elif field == "amount":
                amount = extract_amount_from_input(answer, facts.get("amount"))
                if amount is not None:
                    facts["amount"] = amount
            
            elif field == "evidence":
                is_evidence_question = True
                evidence, evidence_type = extract_evidence_from_input(
                    answer,
                    facts.get("evidence"),
                    is_evidence_question
                )
                if evidence is not None:
                    facts["evidence"] = evidence
                    if evidence_type:
                        facts["evidence_type"] = evidence_type
            
            elif field == "counterparty":
                # 간단한 추출: 답변을 그대로 저장
                if answer and answer.strip():
                    facts["counterparty"] = answer.strip()
        
        extracted_count = sum(1 for v in facts.values() if v is not None)
        logger.info(f"[폴백 엔티티 추출] 완료: {extracted_count}개 필드 추출 성공")
        logger.debug(f"[폴백 엔티티 추출] 추출된 facts: {[(k, v) for k, v in facts.items() if v is not None]}")
        return facts
    
    except Exception as e:
        logger.error(f"폴백 엔티티 추출 실패: {str(e)}", exc_info=True)
        return {}

