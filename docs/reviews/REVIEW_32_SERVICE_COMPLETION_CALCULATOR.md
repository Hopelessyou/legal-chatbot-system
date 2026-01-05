# Service Completion Calculator 검토 보고서

## 검토 대상
- 파일: `src/services/completion_calculator.py`
- 검토 일자: 2024년
- 검토 범위: 완성도 계산, RAG 활용, 필드 체크

---

## ✅ 정상 동작 부분

### 1. 함수 구조 (Lines 16-104)
- ✅ `calculate_completion_rate()`: 완성도 계산 함수
- ✅ 타입 힌트 적절히 사용됨
- ✅ 반환 타입 명확 (0~100 정수)

### 2. RAG 통합 (Lines 31-85)
- ✅ RAG K2 문서에서 필수 필드 목록 조회 시도
- ✅ 폴백 메커니즘 (RAG 실패 시 기본값 사용)
- ✅ YAML 파싱 및 K2 문서 파싱 로직 구현

### 3. 완성도 계산 로직 (Lines 87-99)
- ✅ 채워진 필드 개수 계산
- ✅ 비율 계산 및 최대값 제한
- ✅ 빈 필수 필드 목록 처리

### 4. 에러 처리 (Lines 101-103)
- ✅ 예외 발생 시 0 반환으로 안전하게 처리

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중요한 문제**: `case_type` 변환 로직 누락 (Line 35)

**문제**: `rag_searcher.search()`에 `main_case_type=case_type`을 전달하지만, `case_type`이 한글("민사", "형사" 등)일 수 있습니다. RAG 검색은 영문 코드("CIVIL", "CRIMINAL" 등)를 기대합니다.

```python
rag_results = rag_searcher.search(
    query="필수 필드",
    knowledge_type="K2",
    main_case_type=case_type,  # ❌ 한글일 수 있음
    sub_case_type=sub_case_type,
    node_scope="VALIDATION",
    top_k=1
)
```

**영향도**: 중간  
**수정 필요**: `case_type`을 영문으로 변환

**수정 예시**:
```python
from src.utils.constants import CASE_TYPE_MAPPING

# case_type 변환 (한글 → 영문)
main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None

rag_results = rag_searcher.search(
    query="필수 필드",
    knowledge_type="K2",
    main_case_type=main_case_type_en,  # ✅ 영문 코드
    sub_case_type=sub_case_type,
    node_scope="VALIDATION",
    top_k=1
)
```

---

### 2. 🟡 **중요한 문제**: `case_type` 변환 누락 (Line 42)

**문제**: `REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, ...)`에서도 `case_type`이 한글일 수 있습니다. `REQUIRED_FIELDS_BY_CASE_TYPE`은 영문 키를 사용합니다.

```python
required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", []))
# ❌ case_type이 "민사"이면 None 반환
```

**영향도**: 중간  
**수정 필요**: `case_type`을 영문으로 변환

**수정 예시**:
```python
from src.utils.constants import CASE_TYPE_MAPPING, REQUIRED_FIELDS_BY_CASE_TYPE

# case_type 변환 (한글 → 영문)
main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None

required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(
    main_case_type_en, 
    REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", [])
)
```

---

### 3. 🟢 **낮음**: 빈 값 체크 로직 (Lines 91-92)

**문제**: `value is not None and value != ""`로 체크하지만, 빈 리스트(`[]`)나 빈 딕셔너리(`{}`)는 체크하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 더 포괄적인 빈 값 체크

**수정 예시**:
```python
def _is_filled_value(value: Any) -> bool:
    """값이 채워져 있는지 확인"""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True

# 사용
for field in required_fields:
    if _is_filled_value(facts.get(field)):
        filled_count += 1
```

---

### 4. 🟢 **낮음**: 중복된 RAG 파싱 로직 (Lines 44-85)

**문제**: RAG 파싱 로직이 복잡하고 중첩된 try-except가 많습니다. `missing_field_manager.py`와 동일한 로직이 중복됩니다.

**영향도**: 낮음  
**수정 권장**: 공통 함수로 분리

---

### 5. 🟢 **낮음**: `fact_collection_node.py`에 중복 함수 존재

**문제**: `fact_collection_node.py`에 `_calculate_completion_rate()` 함수가 별도로 정의되어 있습니다 (Lines 433-450). `completion_calculator.py`의 함수를 사용하도록 통일해야 합니다.

**영향도**: 낮음  
**수정 권장**: `fact_collection_node.py`에서 `completion_calculator.calculate_completion_rate()` 사용

---

### 6. 🟢 **낮음**: `node_scope` 파라미터 사용 (Line 37)

**문제**: `node_scope="VALIDATION"`을 전달하지만, `rag_searcher.search()`가 이 파라미터를 지원하는지 확인 필요.

**영향도**: 낮음  
**수정 권장**: `rag_searcher.search()` 시그니처 확인 및 필요시 제거

---

### 7. 🟢 **낮음**: 로깅 개선 (Line 81)

**문제**: `logger.debug()`를 사용하지만, 중요한 정보는 `logger.info()`로 변경하는 것이 좋습니다.

**영향도**: 낮음  
**수정 권장**: 중요 정보는 `info` 레벨로 변경

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중요한 문제**: 2개 (`case_type` 변환 누락)
- 🟢 **낮음**: 5개 (빈 값 체크, 중복 로직, 미사용 함수 등)

### 우선순위별 수정 권장
1. 🟡 **중요**: `case_type` 변환 로직 추가 (Lines 35, 42)
2. 🟢 **낮음**: 빈 값 체크 개선, 중복 로직 제거, 함수 통일

---

## 🔧 수정 제안

### 수정 1: `case_type` 변환 로직 추가

```python
from src.utils.constants import CASE_TYPE_MAPPING, REQUIRED_FIELDS_BY_CASE_TYPE

def calculate_completion_rate(state: StateContext) -> int:
    try:
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        facts = state.get("facts", {})
        
        # case_type 변환 (한글 → 영문)
        main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None
        
        # RAG K2에서 필수 필드 목록 조회
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=main_case_type_en,  # ✅ 영문 코드
            sub_case_type=sub_case_type,
            node_scope="VALIDATION",
            top_k=1
        )
        
        # 필수 필드 목록 추출 (RAG 결과에서 추출 시도, 실패 시 기본값 사용)
        required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(
            main_case_type_en,  # ✅ 영문 코드
            REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", [])
        )
        
        # ... (나머지 로직)
```

### 수정 2: 빈 값 체크 개선

```python
def _is_filled_value(value: Any) -> bool:
    """값이 채워져 있는지 확인"""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True

# 사용
filled_count = 0
for field in required_fields:
    if _is_filled_value(facts.get(field)):
        filled_count += 1
```

---

## ✅ 결론

`CompletionCalculator` 모듈은 전반적으로 잘 구현되어 있으나, **`case_type` 변환 로직 누락** 문제가 있습니다. `case_type`이 한글일 때 RAG 검색과 필수 필드 조회가 실패할 수 있으므로 수정이 필요합니다.

**우선순위**:
1. 🟡 **중요**: `case_type` 변환 로직 추가 (Lines 35, 42)
2. 🟢 **낮음**: 빈 값 체크 개선, 중복 로직 제거, 함수 통일

