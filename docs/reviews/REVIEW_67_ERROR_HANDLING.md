# 에러 처리 검토 보고서

## 검토 대상
- 전체 시스템 에러 처리
- 검토 일자: 2024년
- 검토 범위: 예외 처리 일관성, 에러 로깅, 복구 전략, 사용자 친화적 에러 메시지

---

## ✅ 정상 동작 부분

### 1. 커스텀 예외 클래스
- ✅ 명확한 예외 계층 구조: `LegalChatbotError` 기반
- ✅ 에러 코드 표준화: 각 예외에 `ERROR_CODE` 정의
- ✅ 적절한 예외 타입: `SessionNotFoundError`, `InvalidInputError`, `GPTAPIError` 등

### 2. API 에러 핸들러
- ✅ 7개의 전용 에러 핸들러 정의
- ✅ HTTP 상태 코드 적절히 사용 (404, 400, 422, 500)
- ✅ 일관된 에러 응답 형식: `error_response()` 사용

### 3. 에러 로깅
- ✅ 에러 발생 시 로깅 수행
- ✅ 일반 예외 핸들러에서 `exc_info=True` 사용 (스택 트레이스 포함)
- ✅ 노드별 에러 로깅: `logger.error()` 사용

### 4. 에러 처리 전략 문서화
- ✅ `ERROR_HANDLING.md` 파일 존재
- ✅ 노드별 에러 처리 전략 명시

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 검증 에러 - 첫 번째 에러만 반환

**문제**: `validation_exception_handler`에서 여러 필드에 에러가 있어도 첫 번째만 반환합니다.

**영향도**: 중간  
**위험성**: 
- 사용자가 여러 필드를 한 번에 수정할 수 없음
- 반복적인 요청 필요

**현재 상황**:
```python
errors = exc.errors()
error_details = {
    "field": errors[0].get("loc")[-1] if errors else None,
    "message": errors[0].get("msg") if errors else "검증 오류"
}
```

**수정 권장**: 
```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 에러 핸들러 (모든 에러 반환)"""
    errors = exc.errors()
    error_list = [
        {
            "field": ".".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "검증 오류")
        }
        for err in errors
    ]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            code="VALIDATION_ERROR",
            message="요청 데이터 검증 실패",
            details={"errors": error_list}
        )
    )
```

---

### 2. 🟡 **중간**: 사용자 친화적 에러 메시지 부족

**문제**: 에러 메시지가 기술적이고 사용자에게 친화적이지 않습니다.

**영향도**: 중간  
**위험성**: 
- 사용자가 에러를 이해하기 어려움
- 기술적 메시지가 노출되어 보안 위험 가능

**현재 상황**:
- "서버 내부 오류가 발생했습니다." (일반적)
- "GPT API 호출 중 오류가 발생했습니다." (기술적)
- 예외 메시지가 그대로 노출되는 경우 있음

**수정 권장**: 
```python
# src/utils/error_messages.py
USER_FRIENDLY_MESSAGES = {
    "SESSION_NOT_FOUND": "세션을 찾을 수 없습니다. 새로 시작해주세요.",
    "INVALID_INPUT": "입력값을 확인해주세요.",
    "GPT_API_ERROR": "AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "RAG_SEARCH_ERROR": "정보 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "DATABASE_ERROR": "데이터 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "VALIDATION_ERROR": "입력 데이터에 오류가 있습니다. 입력값을 확인해주세요.",
    "INTERNAL_SERVER_ERROR": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
}

def get_user_friendly_message(error_code: str, default: str = None) -> str:
    """사용자 친화적 에러 메시지 반환"""
    return USER_FRIENDLY_MESSAGES.get(error_code, default or "오류가 발생했습니다.")
```

---

### 3. 🟡 **중간**: 노드별 에러 처리 일관성 부족

**문제**: 노드마다 에러 처리 방식이 다릅니다. 일부는 예외를 그대로 전파하고, 일부는 로깅 후 계속 진행합니다.

**영향도**: 중간  
**위험성**: 
- 에러 처리 일관성 부족으로 디버깅 어려움
- 사용자 경험 불일치

**현재 상황**:
- `init_node`: 예외 발생 시 로깅 후 빈 상태 반환 (복구 가능)
- `case_classification_node`: 예외 발생 시 폴백 처리 후 계속 진행
- `fact_collection_node`: 예외 발생 시 로깅 후 `raise` (치명적)
- `completed_node`: 예외 발생 시 로깅 후 `raise` (치명적)

**수정 권장**: 
- `ERROR_HANDLING.md`의 전략을 일관되게 적용
- 공통 에러 처리 유틸리티 함수 생성

---

### 4. 🟢 **낮음**: 에러 복구 전략 부족

**문제**: 일시적 에러(예: GPT API Rate Limit, DB 연결 실패)에 대한 자동 복구 메커니즘이 제한적입니다.

**영향도**: 낮음  
**위험성**: 
- 일시적 에러로 인한 불필요한 실패
- 사용자 재시도 필요

**현재 상황**:
- GPT API 재시도: `GPTClient`에서 지수 백오프 재시도 구현됨 (✅)
- DB 연결 재시도: 없음
- RAG 검색 재시도: 없음

**수정 권장**: 
```python
# 공통 재시도 데코레이터
from functools import wraps
import time

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))
                    else:
                        raise
            raise last_exception
        return wrapper
    return decorator
```

---

### 5. 🟢 **낮음**: 에러 메시지에 기술적 정보 노출

**문제**: 프로덕션 환경에서도 기술적 에러 메시지가 노출될 수 있습니다.

**영향도**: 낮음  
**위험성**: 
- 내부 시스템 정보 노출
- 보안 취약점 가능

**현재 상황**:
```python
# error_handler.py
message="서버 내부 오류가 발생했습니다."  # ✅ 안전
detail=f"서버 내부 오류: {str(e)}"  # ⚠️ 예외 메시지 노출
```

**수정 권장**: 
```python
# 프로덕션 환경에서는 상세 정보 제거
from config.settings import settings

async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    # 프로덕션 환경에서는 상세 정보 제거
    if settings.environment == "production":
        detail_message = "서버 내부 오류가 발생했습니다."
    else:
        detail_message = f"서버 내부 오류: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message=detail_message
        )
    )
```

---

### 6. 🟢 **낮음**: 에러 메트릭 수집 부재

**문제**: 에러 발생 빈도, 에러 타입별 통계 등이 수집되지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
- 에러 발생 시 메트릭 수집 (선택적)
- 예: Prometheus, StatsD 등 사용

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 3개 (검증 에러 첫 번째만 반환, 사용자 친화적 메시지 부족, 노드별 에러 처리 일관성)
- 🟢 **낮음**: 3개 (에러 복구 전략, 기술적 정보 노출, 에러 메트릭)

### 우선순위별 수정 권장
1. 🟡 **중간**: 검증 에러 - 모든 에러 반환 (권장)
2. 🟡 **중간**: 사용자 친화적 에러 메시지 추가 (권장)
3. 🟡 **중간**: 노드별 에러 처리 일관성 개선 (권장)
4. 🟢 **낮음**: 에러 복구 전략 강화 (선택적)
5. 🟢 **낮음**: 프로덕션 환경에서 기술적 정보 숨김 (선택적)
6. 🟢 **낮음**: 에러 메트릭 수집 (선택적)

---

## 🔧 수정 제안

### 수정 1: 검증 에러 - 모든 에러 반환

#### `src/api/error_handler.py` 수정
```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 에러 핸들러 (모든 에러 반환)"""
    errors = exc.errors()
    
    # 모든 에러를 리스트로 반환
    error_list = [
        {
            "field": ".".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "검증 오류"),
            "type": err.get("type", "value_error")
        }
        for err in errors
    ]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            code="VALIDATION_ERROR",
            message="요청 데이터 검증 실패",
            details={"errors": error_list}
        )
    )
```

---

### 수정 2: 사용자 친화적 에러 메시지 추가

#### `src/utils/error_messages.py` 생성
```python
"""
사용자 친화적 에러 메시지 정의
"""
USER_FRIENDLY_MESSAGES = {
    "SESSION_NOT_FOUND": "세션을 찾을 수 없습니다. 새로 시작해주세요.",
    "INVALID_INPUT": "입력값을 확인해주세요.",
    "GPT_API_ERROR": "AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "RAG_SEARCH_ERROR": "정보 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "DATABASE_ERROR": "데이터 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "VALIDATION_ERROR": "입력 데이터에 오류가 있습니다. 입력값을 확인해주세요.",
    "INTERNAL_SERVER_ERROR": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
}

def get_user_friendly_message(error_code: str, default: str = None) -> str:
    """
    사용자 친화적 에러 메시지 반환
    
    Args:
        error_code: 에러 코드
        default: 기본 메시지 (없으면 "오류가 발생했습니다.")
    
    Returns:
        사용자 친화적 메시지
    """
    return USER_FRIENDLY_MESSAGES.get(error_code, default or "오류가 발생했습니다.")
```

#### `src/api/error_handler.py` 수정
```python
from src.utils.error_messages import get_user_friendly_message

async def gpt_api_error_handler(request: Request, exc: GPTAPIError):
    """GPT API 에러 핸들러"""
    logger.error(f"GPT API 오류: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="GPT_API_ERROR",
            message=get_user_friendly_message("GPT_API_ERROR"),
            details={"status_code": exc.status_code} if exc.status_code else None
        )
    )
```

---

### 수정 3: 노드별 에러 처리 일관성 개선

#### `src/utils/node_error_handler.py` 생성
```python
"""
노드 에러 처리 유틸리티
"""
from typing import Dict, Any, Optional, Callable
from src.utils.logger import get_logger
from src.langgraph.state import StateContext

logger = get_logger(__name__)


def handle_node_error(
    node_name: str,
    state: StateContext,
    error: Exception,
    strategy: str = "raise",
    fallback_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    노드 에러 처리 공통 함수
    
    Args:
        node_name: 노드 이름
        state: 현재 상태
        error: 발생한 예외
        strategy: 처리 전략 ("raise", "fallback", "continue")
        fallback_state: 폴백 상태 (strategy="fallback"일 때 사용)
    
    Returns:
        업데이트된 상태 (strategy="fallback" 또는 "continue"일 때)
    
    Raises:
        Exception: strategy="raise"일 때
    """
    session_id = state.get("session_id", "unknown")
    logger.error(
        f"[{session_id}] {node_name} Node 실행 실패: {str(error)}",
        exc_info=True
    )
    
    if strategy == "raise":
        raise error
    elif strategy == "fallback":
        if fallback_state:
            return {
                **state,
                **fallback_state,
                "error": str(error)
            }
        return {
            **state,
            "error": str(error)
        }
    elif strategy == "continue":
        # 기본 상태 유지
        return {
            **state,
            "error": str(error)
        }
    else:
        raise ValueError(f"알 수 없는 전략: {strategy}")


def with_error_handling(
    node_name: str,
    strategy: str = "raise",
    fallback_state: Optional[Dict[str, Any]] = None
):
    """
    노드 함수에 에러 처리 데코레이터 적용
    
    Args:
        node_name: 노드 이름
        strategy: 처리 전략
        fallback_state: 폴백 상태
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(state: StateContext) -> Dict[str, Any]:
            try:
                return func(state)
            except Exception as e:
                return handle_node_error(
                    node_name,
                    state,
                    e,
                    strategy,
                    fallback_state
                )
        return wrapper
    return decorator
```

---

### 수정 4: 프로덕션 환경에서 기술적 정보 숨김

#### `src/api/error_handler.py` 수정
```python
from config.settings import settings

async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    # 프로덕션 환경에서는 상세 정보 제거
    if settings.environment == "production":
        detail_message = get_user_friendly_message("INTERNAL_SERVER_ERROR")
    else:
        detail_message = f"서버 내부 오류: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message=detail_message
        )
    )
```

---

## 📋 에러 처리 흐름 다이어그램

### 에러 전파 흐름
```
1. 노드/서비스에서 예외 발생
   ↓
2. 예외 타입 확인
   ├─ 커스텀 예외 → 해당 핸들러로 전달
   ├─ HTTPException → 그대로 반환
   └─ 일반 Exception → general_exception_handler
   ↓
3. 에러 핸들러에서 처리
   ├─ 로깅 (exc_info=True)
   ├─ 사용자 친화적 메시지 생성
   └─ HTTP 응답 반환
   ↓
4. 클라이언트에 에러 응답 전달
```

### 노드별 에러 처리 전략
```
INIT Node
  ├─ 에러 발생 → 로깅 → 기본 메시지 반환 (복구 가능)

CASE_CLASSIFICATION Node
  ├─ GPT API 실패 → 폴백 키워드 분류
  └─ 기타 에러 → raise (치명적)

FACT_COLLECTION Node
  └─ 에러 발생 → 로깅 → raise (치명적)

VALIDATION Node
  └─ 에러 발생 → 로깅 → raise (치명적)

RE_QUESTION Node
  └─ 에러 발생 → 로깅 → raise (치명적)

SUMMARY Node
  └─ 에러 발생 → 로깅 → raise (치명적)

COMPLETED Node
  └─ 에러 발생 → 로깅 → raise (치명적)
```

---

## ✅ 결론

전체 시스템 에러 처리는 전반적으로 잘 구성되어 있지만, **사용자 친화적 메시지**와 **에러 처리 일관성** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: 검증 에러 - 모든 에러 반환 (권장)
2. 🟡 **중간**: 사용자 친화적 에러 메시지 추가 (권장)
3. 🟡 **중간**: 노드별 에러 처리 일관성 개선 (권장)
4. 🟢 **낮음**: 에러 복구 전략 강화 (선택적)
5. 🟢 **낮음**: 프로덕션 환경에서 기술적 정보 숨김 (선택적)
6. 🟢 **낮음**: 에러 메트릭 수집 (선택적)

**참고**: 
- 커스텀 예외 클래스와 에러 핸들러가 잘 구성되어 있음
- 에러 로깅은 적절히 수행됨
- `ERROR_HANDLING.md` 문서가 존재하여 전략이 문서화됨
- GPT API 재시도 메커니즘이 구현되어 있음

