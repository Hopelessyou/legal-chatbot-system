# Config Priority 검토 보고서

## 검토 대상
- 파일: `config/priority.py`
- 검토 일자: 2024년
- 검토 범위: 필드 우선순위, 질문 순서

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-5)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 포함

### 2. 우선순위 정의 (Lines 8-42)
- ✅ 기본 우선순위 정의
- ✅ 사건 유형별 우선순위 정의
- ✅ 명확한 주석

### 3. 함수 구현 (Lines 45-83)
- ✅ `get_priority_order()`: 사건 유형별 우선순위 반환
- ✅ `get_next_priority_field()`: 다음 질문할 필드 선택
- ✅ 명확한 로직

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: docstring 들여쓰기 오류

**문제**: Line 62의 `get_next_priority_field()` 함수에서 docstring이 함수 정의 바로 아래에 있지 않고 잘못 들여쓰기되어 있습니다.

**영향도**: 중간  
**수정 권장**: docstring 들여쓰기 수정

**수정 예시**:
```python
def get_next_priority_field(missing_fields: List[str], case_type: Optional[str] = None) -> Optional[str]:
    """
    누락 필드 중에서 우선순위가 가장 높은 필드 반환
    
    Args:
        missing_fields: 누락된 필드 리스트
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
    
    Returns:
        다음 질문할 필드 키 또는 None
    """
    # ...
```

---

### 2. 🟢 **낮음**: `case_type` 대소문자 처리

**문제**: `get_priority_order()` 함수에서 `case_type`을 그대로 사용하는데, 대소문자가 일치하지 않으면 매칭이 실패할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `case_type`을 대문자로 정규화

**수정 예시**:
```python
def get_priority_order(case_type: Optional[str] = None) -> List[str]:
    """
    사건 유형별 필드 우선순위 반환
    
    Args:
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        필드 우선순위 리스트
    """
    if case_type:
        case_type_upper = case_type.upper()
        if case_type_upper in PRIORITY_BY_CASE_TYPE:
            return PRIORITY_BY_CASE_TYPE[case_type_upper]
    
    return DEFAULT_PRIORITY_ORDER
```

---

### 3. 🟢 **낮음**: `get_next_priority_field()` 입력 검증

**문제**: `get_next_priority_field()` 함수에서 `missing_fields`가 빈 리스트인지 확인하지만, `None`이나 잘못된 타입에 대한 검증이 없습니다.

**영향도**: 낮음  
**수정 권장**: 입력 검증 추가 (선택적)

**수정 예시**:
```python
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
    
    if not isinstance(missing_fields, list):
        raise TypeError("missing_fields는 리스트여야 합니다.")
    
    priority_order = get_priority_order(case_type)
    
    # 우선순위 순서대로 확인
    for field in priority_order:
        if field in missing_fields:
            return field
    
    # 우선순위에 없으면 첫 번째 필드 반환
    return missing_fields[0]
```

---

### 4. 🟢 **낮음**: 우선순위 리스트 불변성

**문제**: `get_priority_order()` 함수가 리스트를 직접 반환하는데, 호출자가 이 리스트를 수정하면 원본 데이터가 변경될 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 리스트 복사본 반환 (선택적)

**수정 예시**:
```python
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
```

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 1개 (docstring 들여쓰기 오류)
- 🟢 **낮음**: 3개 (case_type 대소문자, 입력 검증, 리스트 불변성)

### 우선순위별 수정 권장
1. 🟡 **중간**: docstring 들여쓰기 수정
2. 🟢 **낮음**: `case_type` 대소문자 정규화
3. 🟢 **낮음**: 리스트 복사본 반환 (선택적)
4. 🟢 **낮음**: 입력 검증 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: docstring 수정 및 개선

```python
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
```

---

## ✅ 결론

`config/priority.py` 모듈은 전반적으로 잘 구현되어 있습니다. **docstring 들여쓰기 수정**과 **case_type 대소문자 정규화**를 권장합니다.

**우선순위**:
1. 🟡 **중간**: docstring 들여쓰기 수정
2. 🟢 **낮음**: `case_type` 대소문자 정규화
3. 🟢 **낮음**: 리스트 복사본 반환 (선택적)
4. 🟢 **낮음**: 입력 검증 추가 (선택적)

