# Config Fallback Keywords 검토 보고서

## 검토 대상
- 파일: `config/fallback_keywords.py`
- 검토 일자: 2024년
- 검토 범위: 폴백 키워드, 사건 유형 매핑

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-5)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 포함

### 2. 폴백 키워드 정의 (Lines 8-30)
- ✅ 사건 유형별 키워드 정의
- ✅ 각 사건 유형에 `keywords`, `sub_case_type`, `description` 포함
- ✅ 명확한 구조

### 3. 기본값 정의 (Lines 32-34)
- ✅ `DEFAULT_CASE_TYPE`, `DEFAULT_SUB_CASE_TYPE` 정의

### 4. 함수 구현 (Lines 37-70)
- ✅ `get_fallback_case_type()`: 키워드 기반 사건 유형 추정
- ✅ `get_keywords_by_case_type()`: 사건 유형별 키워드 조회
- ✅ 명확한 docstring과 타입 힌팅

---

## ⚠️ 발견된 문제점

### 1. 🔴 **치명적**: 타입 힌팅 오류 (`any` → `Any`)

**문제**: Line 9에서 `Dict[str, any]`를 사용하고 있습니다. Python 타입 힌팅에서는 `Any`를 사용해야 하며, `any`는 유효하지 않습니다.

**영향도**: 치명적 (타입 체커 오류)  
**수정 권장**: `any` → `Any`로 수정

**수정 예시**:
```python
from typing import Dict, List, Tuple, Any

# 사건 유형별 폴백 키워드
FALLBACK_KEYWORDS: Dict[str, Dict[str, Any]] = {
    # ...
}
```

---

### 2. 🟢 **낮음**: 키워드 매칭 로직 개선 가능

**문제**: `get_fallback_case_type()` 함수에서 키워드 매칭 시 부분 문자열 검색(`keyword in user_input_lower`)을 사용합니다. 이는 "사기"가 "사기꾼"에 매칭되는 등 의도하지 않은 매칭이 발생할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 단어 경계 매칭 또는 정규식 사용 (선택적)

**수정 예시**:
```python
import re

def get_fallback_case_type(user_input: str) -> Tuple[str, str]:
    """
    사용자 입력에서 키워드를 기반으로 사건 유형 추정
    
    Args:
        user_input: 사용자 입력 텍스트
    
    Returns:
        (main_case_type, sub_case_type) 튜플
    """
    user_input_lower = user_input.lower()
    
    # 각 사건 유형별로 키워드 매칭
    for case_type, config in FALLBACK_KEYWORDS.items():
        keywords = config.get("keywords", [])
        # 단어 경계를 고려한 매칭
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, user_input_lower):
                return case_type, config.get("sub_case_type", DEFAULT_SUB_CASE_TYPE)
    
    # 매칭 실패 시 기본값 반환
    return DEFAULT_CASE_TYPE, DEFAULT_SUB_CASE_TYPE
```

---

### 3. 🟢 **낮음**: 여러 키워드 매칭 시 우선순위

**문제**: 사용자 입력에 여러 사건 유형의 키워드가 포함되어 있을 때, 첫 번째로 매칭되는 사건 유형을 반환합니다. 우선순위나 가중치를 고려할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재 로직도 충분히 합리적)

---

### 4. 🟢 **낮음**: 빈 입력 처리

**문제**: `get_fallback_case_type()` 함수에서 빈 문자열이나 공백만 있는 입력에 대한 명시적 처리가 없습니다.

**영향도**: 낮음  
**수정 권장**: 빈 입력 처리 추가 (선택적)

**수정 예시**:
```python
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
    
    # ... 나머지 로직
```

---

### 5. 🟢 **낮음**: `get_keywords_by_case_type()` 대소문자 처리

**문제**: `get_keywords_by_case_type()` 함수에서 `case_type`을 그대로 사용하는데, 대소문자가 일치하지 않으면 매칭이 실패할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `case_type`을 대문자로 정규화

**수정 예시**:
```python
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
```

---

## 📊 검토 요약

### 발견된 문제
- 🔴 **치명적**: 1개 (타입 힌팅 오류)
- 🟢 **낮음**: 4개 (키워드 매칭 로직, 우선순위, 빈 입력 처리, 대소문자 처리)

### 우선순위별 수정 권장
1. 🔴 **치명적**: 타입 힌팅 오류 수정 (`any` → `Any`)
2. 🟢 **낮음**: `get_keywords_by_case_type()` 대소문자 정규화
3. 🟢 **낮음**: 빈 입력 처리 추가 (선택적)
4. 🟢 **낮음**: 키워드 매칭 로직 개선 (선택적)
5. 🟢 **낮음**: 여러 키워드 매칭 시 우선순위 (선택적)

---

## 🔧 수정 제안

### 수정 1: 타입 힌팅 오류 수정 및 개선

```python
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
```

---

## ✅ 결론

`config/fallback_keywords.py` 모듈은 전반적으로 잘 구현되어 있습니다. **타입 힌팅 오류 수정**이 필수이며, **대소문자 정규화**와 **빈 입력 처리**를 권장합니다.

**우선순위**:
1. 🔴 **치명적**: 타입 힌팅 오류 수정 (`any` → `Any`)
2. 🟢 **낮음**: `get_keywords_by_case_type()` 대소문자 정규화
3. 🟢 **낮음**: 빈 입력 처리 추가 (선택적)
4. 🟢 **낮음**: 키워드 매칭 로직 개선 (선택적)
5. 🟢 **낮음**: 여러 키워드 매칭 시 우선순위 (선택적)

