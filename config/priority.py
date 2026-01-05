"""
필드 우선순위 설정
사건 유형별로 필드 질문 우선순위를 정의
"""
from typing import Dict, List, Optional


# 기본 필드 우선순위
DEFAULT_PRIORITY_ORDER: List[str] = [
    "incident_date",
    "amount",
    "counterparty",
    "evidence"
]

# 사건 유형별 필드 우선순위
PRIORITY_BY_CASE_TYPE: Dict[str, List[str]] = {
    "CIVIL": [
        "incident_date",  # 날짜가 가장 중요 (계약일, 이행일 등)
        "amount",         # 금액이 두 번째로 중요
        "counterparty",   # 상대방 정보
        "evidence"        # 증거 자료
    ],
    "CRIMINAL": [
        "incident_date",  # 사건 발생일이 가장 중요
        "counterparty",   # 가해자 정보가 금액보다 중요
        "amount",         # 피해 금액
        "evidence"        # 증거 자료
    ],
    "FAMILY": [
        "incident_date",  # 관련 사건 발생일
        "counterparty",   # 상대방 정보
        "amount",         # 관련 금액 (위자료, 재산분할 등)
        "evidence"        # 증거 자료
    ],
    "ADMIN": [
        "incident_date",  # 행정처분일
        "counterparty",   # 관련 기관/상대방
        "amount",         # 관련 금액 (과태료, 과징금 등)
        "evidence"        # 행정처분 문서
    ]
}


def get_priority_order(case_type: Optional[str] = None) -> List[str]:
    """
    사건 유형별 필드 우선순위 반환
    
    Args:
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        필드 우선순위 리스트 (복사본)
    """
    if case_type:
        case_type_upper = case_type.upper()
        if case_type_upper in PRIORITY_BY_CASE_TYPE:
            return PRIORITY_BY_CASE_TYPE[case_type_upper].copy()
    
    return DEFAULT_PRIORITY_ORDER.copy()


def get_next_priority_field(missing_fields: List[str], case_type: Optional[str] = None) -> Optional[str]:
    """
    누락 필드 중에서 우선순위가 가장 높은 필드 반환
    
    Args:
        missing_fields: 누락된 필드 리스트
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
    
    Returns:
        다음 질문할 필드 키 또는 None
    """
    if not missing_fields:
        return None
    
    priority_order = get_priority_order(case_type)
    
    # 우선순위 순서대로 확인
    for field in priority_order:
        if field in missing_fields:
            return field
    
    # 우선순위에 없으면 첫 번째 필드 반환
    return missing_fields[0]

