"""
폴백 키워드 설정
GPT API 실패 시 사용할 키워드 기반 분류 규칙
"""
from typing import Dict, List, Tuple, Any


# 사건 유형별 폴백 키워드
FALLBACK_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "CIVIL": {
        "keywords": ["돈", "빌려", "대여금", "계약", "미지급", "채무", "채권", "계약서", "약속어음"],
        "sub_case_type": "CIVIL_CONTRACT",
        "description": "민사 사건 관련 키워드"
    },
    "CRIMINAL": {
        "keywords": ["사기", "절도", "폭행", "성범죄", "협박", "강도", "살인", "상해"],
        "sub_case_type": "CRIMINAL_FRAUD",
        "description": "형사 사건 관련 키워드"
    },
    "FAMILY": {
        "keywords": ["이혼", "상속", "양육권", "재산분할", "위자료", "친권"],
        "sub_case_type": "FAMILY_DIVORCE",
        "description": "가족법 사건 관련 키워드"
    },
    "ADMIN": {
        "keywords": ["행정처분", "세무", "과태료", "과징금", "허가", "인허가"],
        "sub_case_type": "ADMIN_TAX",
        "description": "행정 사건 관련 키워드"
    }
}

# 기본 사건 유형 (폴백 실패 시)
DEFAULT_CASE_TYPE: str = "CIVIL"
DEFAULT_SUB_CASE_TYPE: str = "CIVIL_CONTRACT"


def get_fallback_case_type(user_input: str) -> Tuple[str, str]:
    """
    사용자 입력에서 키워드를 기반으로 사건 유형 추정
    
    Args:
        user_input: 사용자 입력 텍스트
    
    Returns:
        (main_case_type, sub_case_type) 튜플
    """
    if not user_input or not user_input.strip():
        return DEFAULT_CASE_TYPE, DEFAULT_SUB_CASE_TYPE
    
    user_input_lower = user_input.lower()
    
    # 각 사건 유형별로 키워드 매칭
    for case_type, config in FALLBACK_KEYWORDS.items():
        keywords = config.get("keywords", [])
        if any(keyword in user_input_lower for keyword in keywords):
            return case_type, config.get("sub_case_type", DEFAULT_SUB_CASE_TYPE)
    
    # 매칭 실패 시 기본값 반환
    return DEFAULT_CASE_TYPE, DEFAULT_SUB_CASE_TYPE


def get_keywords_by_case_type(case_type: str) -> List[str]:
    """
    사건 유형별 키워드 리스트 반환
    
    Args:
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
    
    Returns:
        키워드 리스트
    """
    case_type_upper = case_type.upper()
    config = FALLBACK_KEYWORDS.get(case_type_upper, {})
    return config.get("keywords", [])

