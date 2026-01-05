# Service Missing Field Manager 검토 보고서

## 검토 대상
- 파일: `src/services/missing_field_manager.py`
- 검토 일자: 2024년
- 검토 범위: 누락 필드 감지, RAG 활용, 우선순위 처리

---

## ✅ 정상 동작 부분

### 1. 함수 구조 (Lines 14-116)
- ✅ `detect_missing_fields()`: 누락 필드 감지 함수
- ✅ `get_next_missing_field()`: 다음 질문할 필드 선택 함수
- ✅ 타입 힌트 적절히 사용됨

### 2. RAG 통합 (Lines 29-83)
- ✅ RAG K2 문서에서 필수 필드 목록 조회 시도
- ✅ 폴백 메커니즘 (RAG 실패 시 기본값 사용)
- ✅ YAML 파싱 및 K2 문서 파싱 로직 구현

### 3. 우선순위 처리 (Lines 100-116)
- ✅ `config/priority.py`의 `get_next_priority_field` 함수 활용
- ✅ 사건 유형별 우선순위 지원

### 4. 에러 처리 (Lines 95-97)
- ✅ 예외 발생 시 빈 리스트 반환으로 안전하게 처리

---

## ⚠️ 발견된 문제점

### 1. 🟥 **치명적 버그**: Line 78 `else` 블록 누락

**문제**: Line 78의 `else` 블록이 비어있습니다. `k2_data.get("required_fields")`가 없을 때 `required_fields`가 업데이트되지 않습니다.

```python
if k2_data.get("required_fields"):
    # ... (처리 로직)
else:
    # ❌ 비어있음 - required_fields가 업데이트되지 않음
    required_fields = k2_doc.required_fields  # 이 줄이 빠져있음
```

**영향도**: 높음  
**수정 필요**: `else` 블록에 `required_fields = k2_doc.required_fields` 추가

**수정 예시**:
```python
if k2_data.get("required_fields"):
    raw_fields = k2_data.get("required_fields", [])
    if raw_fields and isinstance(raw_fields[0], dict):
        # 딕셔너리 리스트인 경우 required=True인 필드만 추출
        required_fields = [
            field.get("field") for field in raw_fields 
            if field.get("required", True)
        ]
    else:
        # 이미 문자열 리스트인 경우
        required_fields = k2_doc.required_fields
else:
    # required_fields가 없으면 k2_doc에서 가져오기
    required_fields = k2_doc.required_fields
```

---

### 2. 🟡 **중요한 문제**: `case_type` 변환 로직 누락 (Line 33)

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

### 3. 🟡 **중요한 문제**: `case_type` 변환 누락 (Line 40)

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

### 4. 🟢 **낮음**: 빈 값 체크 로직 (Lines 89-90)

**문제**: `value is None or value == ""`로 체크하지만, 빈 리스트(`[]`)나 빈 딕셔너리(`{}`)는 체크하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 더 포괄적인 빈 값 체크

**수정 예시**:
```python
def is_empty_value(value: Any) -> bool:
    """값이 비어있는지 확인"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False

# 사용
if is_empty_value(facts.get(field)):
    missing_fields.append(field)
```

---

### 5. 🟢 **낮음**: 중복된 RAG 파싱 로직 (Lines 44-83)

**문제**: RAG 파싱 로직이 복잡하고 중첩된 try-except가 많습니다. `validation_node.py`에서도 유사한 로직이 있습니다.

**영향도**: 낮음  
**수정 권장**: 공통 함수로 분리

---

### 6. 🟢 **낮음**: `detect_missing_fields` 함수 미사용

**문제**: `detect_missing_fields` 함수가 정의되어 있지만, 실제로는 `validation_node.py`에서 직접 구현되어 사용되지 않습니다.

**영향도**: 낮음  
**수정 권장**: `validation_node.py`에서 이 함수를 사용하도록 리팩토링

---

### 7. 🟢 **낮음**: `node_scope` 파라미터 사용 (Line 35)

**문제**: `node_scope="VALIDATION"`을 전달하지만, `rag_searcher.search()`가 이 파라미터를 지원하는지 확인 필요.

**영향도**: 낮음  
**수정 권장**: `rag_searcher.search()` 시그니처 확인 및 필요시 제거

---

### 8. 🟢 **낮음**: 로깅 개선 (Lines 79, 92)

**문제**: `logger.debug()`를 사용하지만, 중요한 정보는 `logger.info()`로 변경하는 것이 좋습니다.

**영향도**: 낮음  
**수정 권장**: 중요 정보는 `info` 레벨로 변경

---

## 📊 검토 요약

### 발견된 문제
- 🟥 **치명적 버그**: 1개 (Line 78 `else` 블록 누락)
- 🟡 **중요한 문제**: 2개 (`case_type` 변환 누락)
- 🟢 **낮음**: 5개 (빈 값 체크, 중복 로직, 미사용 함수 등)

### 우선순위별 수정 권장
1. 🟥 **즉시 수정**: Line 78 `else` 블록 수정
2. 🟡 **중요**: `case_type` 변환 로직 추가 (Lines 33, 40)
3. 🟢 **낮음**: 빈 값 체크 개선, 중복 로직 제거, 함수 사용

---

## 🔧 수정 제안

### 수정 1: Line 78 `else` 블록 수정

```python
if k2_data.get("required_fields"):
    raw_fields = k2_data.get("required_fields", [])
    if raw_fields and isinstance(raw_fields[0], dict):
        # 딕셔너리 리스트인 경우 required=True인 필드만 추출
        required_fields = [
            field.get("field") for field in raw_fields 
            if field.get("required", True)
        ]
    else:
        # 이미 문자열 리스트인 경우
        required_fields = k2_doc.required_fields
else:
    # required_fields가 없으면 k2_doc에서 가져오기
    required_fields = k2_doc.required_fields
```

### 수정 2: `case_type` 변환 로직 추가

```python
from src.utils.constants import CASE_TYPE_MAPPING, REQUIRED_FIELDS_BY_CASE_TYPE

def detect_missing_fields(state: StateContext) -> List[str]:
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
        
        # 필수 필드 목록 (RAG 결과에서 추출 시도, 실패 시 기본값 사용)
        required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(
            main_case_type_en,  # ✅ 영문 코드
            REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", [])
        )
        
        # ... (나머지 로직)
```

### 수정 3: 빈 값 체크 개선

```python
def _is_empty_value(value: Any) -> bool:
    """값이 비어있는지 확인"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False

# 사용
for field in required_fields:
    if _is_empty_value(facts.get(field)):
        missing_fields.append(field)
```

---

## ✅ 결론

`MissingFieldManager` 모듈은 전반적으로 잘 구현되어 있으나, **`else` 블록 누락**과 **`case_type` 변환 로직 누락** 문제가 있습니다. 특히 `case_type`이 한글일 때 RAG 검색과 필수 필드 조회가 실패할 수 있으므로 즉시 수정이 필요합니다.

**우선순위**:
1. 🟥 **즉시**: Line 78 `else` 블록 수정
2. 🟡 **중요**: `case_type` 변환 로직 추가 (Lines 33, 40)
3. 🟢 **낮음**: 빈 값 체크 개선, 중복 로직 제거

