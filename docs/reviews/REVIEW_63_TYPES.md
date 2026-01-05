# Types 검토 보고서

## 검토 대상
- 파일: `src/types.py`
- 검토 일자: 2024년
- 검토 범위: 타입 정의, TypedDict, 타입 별칭

---

## ✅ 정상 동작 부분

### 1. TypedDict 사용
- ✅ `StateContext`, `FactDict`, `EmotionDict`, `ExpectedInput` 모두 `TypedDict`로 정의됨
- ✅ `total=False` 옵션 사용으로 모든 필드가 선택적임

### 2. 타입 정의 구조
- ✅ 각 TypedDict에 명확한 docstring 제공
- ✅ 필드 타입이 명확히 정의됨 (`Optional`, `List`, `Dict` 등)

---

## ⚠️ 발견된 문제점

### 1. 🔴 **높음**: StateContext 중복 정의

**문제**: `StateContext`가 `src/types.py`와 `src/langgraph/state.py` 두 곳에 중복 정의되어 있습니다.

**영향도**: 높음  
**위험성**: 
- 두 정의가 동기화되지 않으면 타입 불일치 발생 가능
- IDE나 타입 체커가 혼란스러울 수 있음
- 실제로는 `src/langgraph/state.py`의 정의만 사용됨

**현재 사용 현황**:
- `src/langgraph/state.py`의 `StateContext`가 실제로 사용됨 (`from src.langgraph.state import StateContext`)
- `src/types.py`의 `StateContext`는 사용되지 않음

**수정 권장**: `src/types.py`에서 `StateContext` 제거하고, `src/langgraph/state.py`에서만 정의

---

### 2. 🟡 **중간**: 사용되지 않는 타입 정의

**문제**: `FactDict`, `EmotionDict`, `ExpectedInput`가 `src/types.py`에 정의되어 있지만 실제로 사용되지 않습니다.

**영향도**: 중간  
**위험성**: 
- 코드베이스에 불필요한 코드 존재
- 유지보수 시 혼란 가능
- 타입 정의가 실제 사용과 불일치할 수 있음

**검증 결과**:
- `FactDict`: 사용되지 않음 (코드베이스에서 import되지 않음)
- `EmotionDict`: 사용되지 않음 (코드베이스에서 import되지 않음)
- `ExpectedInput`: 사용되지 않음 (코드베이스에서 import되지 않음)

**수정 권장**: 
1. 실제로 사용할 계획이 있다면 사용하도록 수정
2. 사용할 계획이 없다면 제거

---

### 3. 🟢 **낮음**: 타입 별칭 부재

**문제**: 자주 사용되는 타입 조합에 대한 별칭이 없습니다. 예를 들어, `Dict[str, Any]`, `List[Dict[str, Any]]` 등이 반복적으로 사용됩니다.

**영향도**: 낮음  
**수정 권장**: 타입 별칭 추가 (선택적)

**예시**:
```python
from typing import Dict, List, Any, TypedDict

# 타입 별칭
JsonDict = Dict[str, Any]
JsonList = List[JsonDict]
EmotionList = List[Dict[str, Any]]
```

---

### 4. 🟢 **낮음**: 타입 정의 문서화 부족

**문제**: 각 타입 정의에 대한 상세한 설명이나 사용 예시가 없습니다.

**영향도**: 낮음  
**수정 권장**: 각 타입에 대한 상세한 docstring 추가 (선택적)

---

### 5. 🟢 **낮음**: 타입 검증 부재

**문제**: `FactDict`, `EmotionDict`, `ExpectedInput`에 대한 검증 로직이 없습니다. `StateContext`는 `StateContextModel`로 검증되지만, 다른 타입들은 검증되지 않습니다.

**영향도**: 낮음  
**수정 권장**: 필요시 Pydantic 모델 추가 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🔴 **높음**: 1개 (StateContext 중복 정의)
- 🟡 **중간**: 1개 (사용되지 않는 타입 정의)
- 🟢 **낮음**: 3개 (타입 별칭, 문서화, 검증)

### 우선순위별 수정 권장
1. 🔴 **높음**: `src/types.py`에서 `StateContext` 제거
2. 🟡 **중간**: 사용되지 않는 타입 정의 제거 또는 실제 사용
3. 🟢 **낮음**: 타입 별칭 추가 (선택적)
4. 🟢 **낮음**: 타입 정의 문서화 보완 (선택적)
5. 🟢 **낮음**: 타입 검증 로직 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: StateContext 중복 정의 제거

#### `src/types.py` 수정
```python
"""
공통 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime

# StateContext는 src/langgraph/state.py에서 정의됨
# 중복 정의 제거

class FactDict(TypedDict, total=False):
    """사실 정보 딕셔너리 타입"""
    incident_date: Optional[str]
    location: Optional[str]
    counterparty: Optional[str]
    amount: Optional[int]
    evidence: Optional[bool]


class EmotionDict(TypedDict, total=False):
    """감정 정보 딕셔너리 타입"""
    emotion_type: str
    intensity: int
    source_text: str


class ExpectedInput(TypedDict, total=False):
    """예상 입력 타입"""
    type: str  # date, choice, text 등
    field: str
    options: Optional[List[str]]
```

---

### 수정 2: 사용되지 않는 타입 정의 처리

#### 옵션 A: 제거 (권장)
사용되지 않는 타입 정의를 제거합니다.

#### 옵션 B: 실제 사용
타입 정의를 실제로 사용하도록 코드 수정:

```python
# 예시: fact_collection_node.py에서 FactDict 사용
from src.types import FactDict

def extract_facts(...) -> FactDict:
    ...
```

---

### 수정 3: 타입 별칭 추가 (선택적)

#### `src/types.py`에 추가
```python
from typing import Dict, List, Any, TypedDict, Optional

# 타입 별칭
JsonDict = Dict[str, Any]
JsonList = List[JsonDict]
EmotionList = List[Dict[str, Any]]
OptionalStr = Optional[str]
OptionalInt = Optional[int]
```

---

## ✅ 결론

`src/types.py` 파일은 전반적으로 잘 구성되어 있지만, **중복 정의**와 **사용되지 않는 타입** 문제가 있습니다.

**우선순위**:
1. 🔴 **높음**: `src/types.py`에서 `StateContext` 제거 (필수)
2. 🟡 **중간**: 사용되지 않는 타입 정의 제거 또는 실제 사용 (권장)
3. 🟢 **낮음**: 타입 별칭 추가 (선택적)
4. 🟢 **낮음**: 타입 정의 문서화 보완 (선택적)
5. 🟢 **낮음**: 타입 검증 로직 추가 (선택적)

**참고**: `StateContext`는 `src/langgraph/state.py`에서 정의하고 사용하므로, `src/types.py`의 중복 정의는 제거해야 합니다.

