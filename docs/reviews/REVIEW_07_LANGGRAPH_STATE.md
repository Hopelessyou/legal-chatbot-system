# LangGraph State 검토 보고서

## 검토 대상
- 파일: `src/langgraph/state.py`
- 검토 일자: 2024년
- 검토 범위: StateContext 정의, 상태 검증, 초기 상태 생성

---

## ✅ 정상 동작 부분

### 1. TypedDict 정의 (Lines 8-20)
```python
class StateContext(TypedDict, total=False):
    """LangGraph State Context 타입 정의"""
    session_id: str
    current_state: str
    case_type: Optional[str]
    # ...
```
- ✅ TypedDict로 타입 힌트 제공
- ✅ `total=False`로 모든 필드 선택적

### 2. Pydantic 모델 검증 (Lines 23-55)
```python
class StateContextModel(BaseModel):
    """State Context Pydantic 모델 (검증용)"""
    session_id: str
    current_state: str = Field(default="INIT")
    # ...
```
- ✅ Pydantic v2 호환 (`field_validator` 사용)
- ✅ 필드 기본값 설정
- ✅ `completion_rate` 범위 검증 (0-100)

### 3. State 검증 (Lines 37-52)
```python
@field_validator('current_state')
@classmethod
def validate_state(cls, v: str) -> str:
    valid_states = [
        "INIT", "CASE_CLASSIFICATION", "FACT_COLLECTION",
        "VALIDATION", "RE_QUESTION", "SUMMARY", "COMPLETED"
    ]
    if v not in valid_states:
        raise ValueError(f"유효하지 않은 State: {v}")
    return v
```
- ✅ 유효한 State만 허용
- ✅ 명확한 에러 메시지

### 4. 초기 Context 생성 (Lines 58-86)
```python
def create_initial_context(session_id: str) -> StateContext:
    return {
        "session_id": session_id,
        "current_state": "INIT",
        "facts": {
            "incident_date": None,
            "location": None,
            # ...
        },
        # ...
    }
```
- ✅ 모든 필드 초기화
- ✅ facts 구조 명확

### 5. Context 검증 함수 (Lines 89-106)
- ✅ Pydantic 모델로 검증
- ✅ 예외 처리

---

## ⚠️ 발견된 문제점

### 1. TypedDict와 Pydantic 모델 불일치 (Lines 8-20, 23-35)
```python
# TypedDict
class StateContext(TypedDict, total=False):
    missing_fields: List[str]  # Line 18에 있음

# Pydantic Model
class StateContextModel(BaseModel):
    missing_fields: List[str] = Field(default_factory=list)  # Line 33에 있음
```
**영향도**: 낮음  
**현황**: 두 정의 모두 `missing_fields` 포함  
**주의사항**: 
- TypedDict와 Pydantic 모델을 동기화 유지 필요
- 필드 추가/제거 시 양쪽 모두 수정 필요

### 2. validate_context 에러 정보 손실 (Lines 99-106)
```python
def validate_context(context: StateContext) -> bool:
    try:
        StateContextModel(**context)
        return True
    except Exception as e:
        logger.error(f"Context 검증 실패: {str(e)}")
        return False  # 에러 정보 손실
```
**영향도**: 중간  
**문제**: 
- 에러 정보가 로그에만 기록되고 반환되지 않음
- 호출자가 어떤 필드가 문제인지 알 수 없음

**권장 수정**:
```python
def validate_context(context: StateContext) -> Tuple[bool, Optional[str]]:
    """
    Context 검증
    
    Returns:
        (검증 결과, 에러 메시지)
    """
    try:
        StateContextModel(**context)
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Context 검증 실패: {error_msg}")
        return False, error_msg
```

### 3. facts 구조 하드코딩 (Lines 73-79)
```python
"facts": {
    "incident_date": None,
    "location": None,
    "counterparty": None,
    "amount": None,
    "evidence": None
}
```
**영향도**: 낮음  
**문제**: 
- facts 필드가 하드코딩됨
- 사건 유형별로 다른 필드가 필요할 수 있음
- 확장성 제한

**권장 개선**:
```python
def create_initial_context(
    session_id: str,
    case_type: Optional[str] = None
) -> StateContext:
    """초기 Context 생성"""
    # 기본 facts 구조
    facts = {
        "incident_date": None,
        "location": None,
        "counterparty": None,
        "amount": None,
        "evidence": None
    }
    
    # 사건 유형별 추가 필드 (필요시)
    if case_type:
        # case_type에 따라 추가 필드 설정
        pass
    
    return {
        "session_id": session_id,
        "current_state": "INIT",
        "case_type": case_type,
        "facts": facts,
        # ...
    }
```

### 4. Config.extra = "allow" (Line 55)
```python
class Config:
    extra = "allow"
```
**영향도**: 낮음  
**문제**: 
- 예상치 못한 필드도 허용
- 오타나 잘못된 필드명이 검증되지 않음

**권장 수정**:
```python
class Config:
    extra = "forbid"  # 또는 "ignore"
```
또는:
```python
# LangGraph가 추가 필드를 사용할 수 있으므로 "allow" 유지
# 하지만 문서화 필요
```

### 5. State 상수 중복 정의 가능성
**영향도**: 낮음  
**현황**: `valid_states` 리스트가 하드코딩됨  
**권장사항**: 
- 상수로 분리하여 재사용
- 다른 모듈에서도 동일한 리스트 사용 시 일관성 유지

**권장 수정**:
```python
# constants.py 또는 state.py 상단
VALID_STATES = [
    "INIT",
    "CASE_CLASSIFICATION",
    "FACT_COLLECTION",
    "VALIDATION",
    "RE_QUESTION",
    "SUMMARY",
    "COMPLETED"
]

@field_validator('current_state')
@classmethod
def validate_state(cls, v: str) -> str:
    if v not in VALID_STATES:
        raise ValueError(f"유효하지 않은 State: {v}. 유효한 값: {VALID_STATES}")
    return v
```

### 6. validate_context에서 logger 동적 import (Lines 103-104)
```python
from src.utils.logger import get_logger
logger = get_logger(__name__)
```
**영향도**: 낮음  
**문제**: 함수 내부에서 매번 import  
**권장 수정**: 모듈 레벨에서 import
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

def validate_context(context: StateContext) -> bool:
    # ...
```

### 7. TypedDict와 dict 혼용 (graph.py Line 30)
```python
workflow = StateGraph(dict)  # StateContext는 TypedDict이므로 dict로 사용
```
**영향도**: 낮음  
**현황**: LangGraph가 dict를 요구하므로 적절  
**주의사항**: 타입 안정성을 위해 주석으로 명시

---

## 🔍 추가 검토 사항

### 1. State 전이 검증
- 현재: State 값만 검증
- 권장: State 전이 규칙 검증 (예: INIT → CASE_CLASSIFICATION만 허용)

### 2. 필드 타입 검증 강화
- 현재: 기본 타입 검증만
- 권장: facts 내부 구조 검증, emotion 구조 검증

### 3. 불변성 보장
- 현재: StateContext는 가변 딕셔너리
- 권장: State 변경 시 검증 강제

### 4. State 버전 관리
- 현재: 버전 정보 없음
- 권장: State 스키마 버전 추가 (마이그레이션 대비)

---

## 📊 종합 평가

### 강점
1. ✅ TypedDict와 Pydantic 모델로 타입 안정성 확보
2. ✅ State 값 검증 구현
3. ✅ 초기 Context 생성 함수 제공
4. ✅ Pydantic v2 호환
5. ✅ 필드 기본값 적절히 설정

### 개선 필요
1. 🟡 **중간**: validate_context 에러 정보 반환
2. 🟡 **중간**: facts 구조 동적 생성
3. 🟢 **낮음**: State 상수 분리
4. 🟢 **낮음**: logger import 위치
5. 🟢 **낮음**: Config.extra 정책 명확화

### 우선순위
- **중간**: validate_context 개선, facts 구조 개선
- **낮음**: State 상수 분리, import 정리

---

## 📝 권장 수정 사항

### 수정 1: validate_context 에러 정보 반환
```python
from typing import Tuple, Optional

def validate_context(context: StateContext) -> Tuple[bool, Optional[str]]:
    """
    Context 검증
    
    Args:
        context: StateContext 딕셔너리
    
    Returns:
        (검증 결과, 에러 메시지)
        - (True, None): 검증 성공
        - (False, str): 검증 실패, 에러 메시지 포함
    """
    try:
        StateContextModel(**context)
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Context 검증 실패: {error_msg}", exc_info=True)
        return False, error_msg
```

### 수정 2: State 상수 분리
```python
# 파일 상단에 상수 정의
VALID_STATES = [
    "INIT",
    "CASE_CLASSIFICATION",
    "FACT_COLLECTION",
    "VALIDATION",
    "RE_QUESTION",
    "SUMMARY",
    "COMPLETED"
]

@field_validator('current_state')
@classmethod
def validate_state(cls, v: str) -> str:
    """State 유효성 검증"""
    if v not in VALID_STATES:
        raise ValueError(
            f"유효하지 않은 State: {v}. "
            f"유효한 값: {VALID_STATES}"
        )
    return v
```

### 수정 3: logger 모듈 레벨 import
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

def validate_context(context: StateContext) -> Tuple[bool, Optional[str]]:
    # logger 사용
    # ...
```

### 수정 4: facts 구조 동적 생성 (선택사항)
```python
def _get_default_facts(case_type: Optional[str] = None) -> Dict[str, Any]:
    """기본 facts 구조 생성"""
    facts = {
        "incident_date": None,
        "location": None,
        "counterparty": None,
        "amount": None,
        "evidence": None
    }
    
    # 사건 유형별 추가 필드
    if case_type == "CRIMINAL":
        facts["crime_type"] = None
        facts["victim"] = None
    elif case_type == "LABOR":
        facts["employer"] = None
        facts["workplace"] = None
    
    return facts

def create_initial_context(
    session_id: str,
    case_type: Optional[str] = None
) -> StateContext:
    """초기 Context 생성"""
    return {
        "session_id": session_id,
        "current_state": "INIT",
        "case_type": case_type,
        "sub_case_type": None,
        "facts": _get_default_facts(case_type),
        "emotion": [],
        "completion_rate": 0,
        "last_user_input": "",
        "missing_fields": [],
        "bot_message": None,
        "expected_input": None
    }
```

### 수정 5: Config.extra 정책 명확화
```python
class Config:
    # LangGraph가 추가 필드를 사용할 수 있으므로 "allow" 유지
    # 하지만 문서화 필요
    extra = "allow"  # LangGraph 내부 필드 허용
    
    # 또는 엄격한 검증이 필요하면:
    # extra = "forbid"  # 예상치 못한 필드 거부
```

---

## ✅ 검토 완료

**검토 항목**: `review_07_langgraph_state`  
**상태**: 완료  
**다음 항목**: `review_08_langgraph_graph`

