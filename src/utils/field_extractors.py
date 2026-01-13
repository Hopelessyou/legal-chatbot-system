"""
필드 추출 공통 헬퍼 함수 (폴백 전용)
증거, 날짜, 금액, 당사자 등 필드 추출 로직을 공통화

주의: Q-A 매칭 방식으로 전환되었으며, 이 함수들은 GPT API 실패 시 폴백으로만 사용됩니다.
일반적인 엔티티 추출은 GPT를 통해 Q-A 쌍에서 추출됩니다.
"""
import re
from typing import Dict, Any, Optional, Tuple
from src.utils.constants import (
    EVIDENCE_KEYWORDS_POSITIVE,
    EVIDENCE_KEYWORDS_NEGATIVE,
    EVIDENCE_SIMPLE_POSITIVE_KEYWORDS,
    EVIDENCE_TYPE_KEYWORDS,
    Limits
)
from src.services.entity_extractor import entity_extractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


def extract_evidence_from_input(
    user_input: str,
    current_evidence: Optional[bool] = None,
    is_evidence_question: bool = False
) -> Tuple[Optional[bool], Optional[str]]:
    """
    사용자 입력에서 증거 정보 추출
    
    Args:
        user_input: 사용자 입력 텍스트
        current_evidence: 현재 증거 값 (None이면 추출 시도)
        is_evidence_question: 증거 질문에 대한 응답인지 여부
    
    Returns:
        (evidence: Optional[bool], evidence_type: Optional[str]) 튜플
    """
    if current_evidence is not None and not is_evidence_question:
        return current_evidence, None
    
    user_input_lower = user_input.lower().strip()
    
    # 증거 질문에 대한 응답인 경우, 단순 긍정/부정 응답을 먼저 확인
    if is_evidence_question:
        # "모름", "없음" 같은 부정 응답인 경우
        negative_keywords = ["모름", "없음", "없어", "없습니다", "모르겠", "알 수 없", "알수없"]
        if any(keyword in user_input_lower for keyword in negative_keywords):
            return False, None  # 명시적으로 False 반환
        
        # "네", "있어요", "있음", "있다고" 같은 단순 긍정 응답인 경우
        if any(keyword in user_input_lower for keyword in EVIDENCE_SIMPLE_POSITIVE_KEYWORDS):
            # 증거 타입이 포함되어 있는지 확인
            evidence_type = None
            for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, user_input_lower):
                    evidence_type = evidence_type_value
                    break
            
            return True, evidence_type
    
    # 긍정 키워드 확인 (단어 경계 확인으로 정확한 매칭)
    positive_match = False
    for keyword in EVIDENCE_KEYWORDS_POSITIVE:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, user_input_lower):
            positive_match = True
            break
    
    if positive_match:
        # 명시적 증거 키워드가 있으면 evidence_type도 함께 추출
        evidence_type = None
        for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, user_input_lower):
                evidence_type = evidence_type_value
                break
        
        return True, evidence_type
    elif any(keyword in user_input_lower for keyword in EVIDENCE_KEYWORDS_NEGATIVE):
        return False, None
    
    return None, None


def extract_evidence_type_from_input(
    user_input: str,
    current_evidence_type: Optional[str] = None
) -> Optional[str]:
    """
    사용자 입력에서 증거 타입 추출
    
    Args:
        user_input: 사용자 입력 텍스트
        current_evidence_type: 현재 증거 타입
    
    Returns:
        증거 타입 문자열 또는 None
    """
    if current_evidence_type:
        return current_evidence_type
    
    user_input_lower = user_input.lower()
    evidence_type = None
    
    for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, user_input_lower):
            evidence_type = evidence_type_value
            break
    
    if evidence_type:
        return evidence_type
    
    # 키워드가 없으면 사용자 입력을 그대로 저장 (길이 제한)
    if user_input.strip():
        return user_input.strip()[:Limits.EVIDENCE_TYPE_MAX_LENGTH]
    
    return None


def extract_date_from_input(
    user_input: str,
    current_date: Optional[str] = None
) -> Optional[str]:
    """
    사용자 입력에서 날짜 추출
    
    Args:
        user_input: 사용자 입력 텍스트
        current_date: 현재 날짜 값
    
    Returns:
        날짜 문자열 (YYYY-MM-DD 형식) 또는 None
    """
    if current_date:
        return current_date
    
    # entity_extractor 사용
    extracted_date = entity_extractor.extract_date(user_input)
    if extracted_date:
        return extracted_date
    
    return None


def extract_amount_from_input(
    user_input: str,
    current_amount: Optional[int] = None
) -> Optional[int]:
    """
    사용자 입력에서 금액 추출
    
    Args:
        user_input: 사용자 입력 텍스트
        current_amount: 현재 금액 값
    
    Returns:
        금액 정수 또는 None (모름/없음 같은 답변은 None 반환)
    """
    if current_amount is not None:
        return current_amount
    
    user_input_lower = user_input.lower().strip()
    
    # "모름", "없음", "없어" 같은 답변은 None 반환 (명시적으로 처리되지 않음으로 표시)
    negative_keywords = ["모름", "없음", "없어", "없습니다", "모르겠", "알 수 없", "알수없", "불명"]
    if any(keyword in user_input_lower for keyword in negative_keywords):
        return None  # 명시적으로 None 반환 (다음 필드로 넘어가도록)
    
    # 숫자 추출 (한글 숫자 단위 처리)
    numbers = re.findall(
        r'\d+',
        user_input.replace(',', '').replace('만', '0000').replace('천', '000')
    )
    
    if numbers:
        try:
            amount = int(numbers[0])
            # 금액은 일반적으로 최소 임계값 이상 (날짜의 일/월과 구분)
            if amount >= Limits.MIN_AMOUNT_THRESHOLD:
                return amount
        except ValueError:
            pass
    
    return None


def extract_counterparty_from_input(
    user_input: str,
    current_counterparty: Optional[str] = None
) -> Optional[str]:
    """
    사용자 입력에서 당사자 정보 추출
    
    Args:
        user_input: 사용자 입력 텍스트
        current_counterparty: 현재 당사자 값
    
    Returns:
        당사자 이름 문자열 또는 None
    """
    if current_counterparty:
        return current_counterparty
    
    # 빈 문자열이나 "없음" 같은 값은 제외
    if not user_input or not user_input.strip():
        return None
    
    user_input_stripped = user_input.strip()
    
    # 숫자만 있거나 너무 짧으면 제외
    if len(user_input_stripped) < 2 or user_input_stripped.isdigit():
        return None
    
    # "없음", "None" 같은 값 제외
    if user_input_stripped in ["없음", "None", ""]:
        return None
    
    return user_input_stripped


def has_date_pattern(user_input: str) -> bool:
    """
    사용자 입력에 날짜 패턴이 포함되어 있는지 확인
    
    Args:
        user_input: 사용자 입력 텍스트
    
    Returns:
        날짜 패턴 포함 여부
    """
    date_patterns = [
        r'\d+월', r'\d+일', r'\d+년',
        r'올해', r'작년', r'내년',
        r'올해\s*\d+월', r'작년\s*\d+월',
        r'인지', r'발생'
    ]
    
    return any(re.search(pattern, user_input) for pattern in date_patterns)

