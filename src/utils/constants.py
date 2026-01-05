"""
상수 정의 모듈
하드코딩된 값들을 한 곳에 모아 관리
"""
from enum import Enum
from typing import Dict, List


# ============================================================================
# 사건 유형 매핑
# ============================================================================

CASE_TYPE_MAPPING: Dict[str, str] = {
    "민사": "CIVIL",
    "형사": "CRIMINAL",
    "가사": "FAMILY",
    "행정": "ADMIN"
}

# 역매핑 (영문 → 한글)
CASE_TYPE_REVERSE_MAPPING: Dict[str, str] = {
    "CIVIL": "민사",
    "CRIMINAL": "형사",
    "FAMILY": "가사",
    "ADMIN": "행정"
}


# ============================================================================
# 필수 필드 목록
# ============================================================================

# 기본 필수 필드 (모든 사건 유형 공통)
REQUIRED_FIELDS: List[str] = [
    "incident_date",
    "counterparty",
    "amount",
    "evidence"
]

# 사건 유형별 필수 필드 (향후 확장 가능)
REQUIRED_FIELDS_BY_CASE_TYPE: Dict[str, List[str]] = {
    "CIVIL": REQUIRED_FIELDS,
    "CRIMINAL": REQUIRED_FIELDS,
    "FAMILY": REQUIRED_FIELDS,
    "ADMIN": REQUIRED_FIELDS
}


# ============================================================================
# 증거 관련 상수
# ============================================================================

# 증거 타입 키워드 매핑
EVIDENCE_TYPE_KEYWORDS: Dict[str, str] = {
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

# 증거 긍정 키워드
EVIDENCE_KEYWORDS_POSITIVE: List[str] = [
    "증거", "계약서", "카톡", "이체", "내역", "대화", "송금",
    "대화내역", "송금내역", "계좌이체", "문서", "사진", "영상",
    "녹음", "증빙", "자료"
]

# 증거 부정 키워드
EVIDENCE_KEYWORDS_NEGATIVE: List[str] = [
    "없음", "없어", "아니", "no", "없다", "없습니다", "증거 없"
]

# 단순 긍정 응답 키워드
EVIDENCE_SIMPLE_POSITIVE_KEYWORDS: List[str] = [
    "네", "있어", "있어요", "예", "그래", "yes", "있음", "있습니다", "있다고", "있다", "있어"
]

# 명시적 증거 키워드 (evidence_type 추출용)
EVIDENCE_EXPLICIT_KEYWORDS: List[str] = [
    "계약서", "카톡", "이체", "내역", "대화", "송금",
    "대화내역", "송금내역", "계좌이체", "문서", "사진",
    "영상", "녹음", "증빙", "자료", "증거"
]


# ============================================================================
# 당사자 관련 상수
# ============================================================================

# 유효한 당사자 타입
VALID_PARTY_TYPES: List[str] = ["개인", "법인"]

# 기본 당사자 타입
DEFAULT_PARTY_TYPE: str = "개인"

# 당사자 역할
PARTY_ROLES: Dict[str, str] = {
    "CLIENT": "의뢰인",
    "COUNTERPARTY": "상대방"
}


# ============================================================================
# 세션 상태
# ============================================================================

class SessionStatus(str, Enum):
    """세션 상태 Enum"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


# ============================================================================
# 사건 단계
# ============================================================================

class CaseStage(str, Enum):
    """사건 단계 Enum"""
    BEFORE_CONSULTATION = "상담전"
    IN_CONSULTATION = "상담중"
    CONSULTATION_COMPLETED = "상담완료"
    ACCEPTED = "수임"
    REJECTED = "거절"


# ============================================================================
# 필드 매핑
# ============================================================================

# 필드 → 엔티티 타입 매핑
FIELD_ENTITY_MAPPING: Dict[str, List[str]] = {
    "incident_date": ["date"],
    "counterparty": ["party"],
    "amount": ["amount"],
    "evidence": []  # evidence는 엔티티 추출 불필요
}

# 필드 → 입력 타입 매핑
FIELD_INPUT_TYPE_MAPPING: Dict[str, str] = {
    "incident_date": "date",
    "counterparty": "text",
    "amount": "number",
    "evidence": "boolean",
    "evidence_type": "text"
}


# ============================================================================
# 우선순위
# ============================================================================

# 주의: 필드 우선순위는 config/priority.py에서 관리하는 것을 권장합니다.
# priority.get_priority_order() 또는 priority.get_next_priority_field() 함수를 사용하세요.

# 하위 호환성을 위한 기본 우선순위 (deprecated)
FIELD_PRIORITY_ORDER: List[str] = [
    "incident_date",
    "amount",
    "counterparty",
    "evidence"
]

# 하위 호환성을 위한 사건 유형별 우선순위 (deprecated)
FIELD_PRIORITY_BY_CASE_TYPE: Dict[str, List[str]] = {
    "CIVIL": FIELD_PRIORITY_ORDER,
    "CRIMINAL": ["incident_date", "counterparty", "amount", "evidence"],
    "FAMILY": FIELD_PRIORITY_ORDER,
    "ADMIN": FIELD_PRIORITY_ORDER
}


# ============================================================================
# 폴백 키워드 (GPT API 실패 시 사용)
# ============================================================================

# 주의: 폴백 키워드는 config/fallback_keywords.py에서 관리하는 것을 권장합니다.
# fallback_keywords.get_fallback_case_type() 함수를 사용하세요.

# 기본 사건 유형 (폴백)
DEFAULT_CASE_TYPE: str = "CIVIL"
DEFAULT_SUB_CASE_TYPE: str = "CIVIL_CONTRACT"


# ============================================================================
# 질문 텍스트
# ============================================================================

# 기본 질문 메시지 (YAML 파일이 없을 때 사용)
QUESTION_MESSAGES: Dict[str, str] = {
    "incident_date": "사건이 발생한 날짜를 알려주세요.",
    "counterparty": "계약 상대방은 누구인가요?",
    "amount": "문제가 된 금액은 얼마인가요?",
    "evidence": "계약서나 관련 증거를 가지고 계신가요?",
    "evidence_type": "어떤 증거를 가지고 계신가요? (예: 계약서, 카톡 대화내역, 송금내역, 사진, 영상 등)",
    "additional_info": "추가로 알려주실 내용이 있으신가요?"
}

# 주의: 질문 텍스트는 config/questions.yaml에서 관리하는 것을 권장합니다.
# question_loader.get_question_message() 함수를 사용하세요.


# ============================================================================
# 제한값 (Limits)
# ============================================================================

class Limits:
    """제한값 상수 클래스"""
    
    # 문자열 길이
    LOG_PREVIEW_LENGTH = 50
    DESCRIPTION_MAX_LENGTH = 500
    EVIDENCE_TYPE_MAX_LENGTH = 50
    SUMMARY_PREVIEW_LENGTH = 200
    FILE_NAME_MAX_LENGTH = 255
    
    # 금액
    MIN_AMOUNT_THRESHOLD = 1000  # 원 (날짜와 구분하기 위한 최소 금액)
    
    # GPT API 토큰 제한
    MAX_TOKENS_DATE_EXTRACTION = 50
    MAX_TOKENS_CLASSIFICATION = 100
    MAX_TOKENS_ENTITY_EXTRACTION = 200
    MAX_TOKENS_SUMMARY = 500
    MAX_TOKENS_FACT_EMOTION_SPLIT = 500
    
    # 완성도
    COMPLETION_RATE_MIN = 0
    COMPLETION_RATE_MAX = 100
    
    # 기타
    DEFAULT_ORDER_VALUE = 999  # 정렬 시 기본값


# ============================================================================
# 한글 숫자 매핑
# ============================================================================

KOREAN_NUMBER_MAPPING: Dict[str, int] = {
    '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
    '육': 6, '칠': 7, '팔': 8, '구': 9,
    '십': 10, '백': 100, '천': 1000, '만': 10000,
    '억': 100000000, '조': 1000000000000
}

