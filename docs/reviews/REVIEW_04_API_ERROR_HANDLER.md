# API 에러 핸들러 검토 보고서

## 검토 대상
- 파일: `src/api/error_handler.py`
- 검토 일자: 2024년
- 검토 범위: 예외 처리 전략, 에러 응답 형식, 로깅

---

## ✅ 정상 동작 부분

### 1. 에러 핸들러 구조 (7개 핸들러)
- ✅ `validation_exception_handler`: 요청 검증 에러 (422)
- ✅ `session_not_found_handler`: 세션 없음 (404)
- ✅ `invalid_input_handler`: 잘못된 입력 (400)
- ✅ `gpt_api_error_handler`: GPT API 에러 (500)
- ✅ `rag_search_error_handler`: RAG 검색 에러 (500)
- ✅ `database_error_handler`: DB 에러 (500)
- ✅ `general_exception_handler`: 일반 예외 (500)

### 2. HTTP 상태 코드 사용 (적절)
- ✅ 422: 검증 에러
- ✅ 404: 리소스 없음
- ✅ 400: 잘못된 요청
- ✅ 500: 서버 내부 오류

### 3. 에러 응답 형식 (Lines 14, 30-34)
```python
from src.utils.response import error_response

return JSONResponse(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    content=error_response(
        code="VALIDATION_ERROR",
        message="요청 데이터 검증 실패",
        details=error_details
    )
)
```
- ✅ 일관된 에러 응답 형식 사용
- ✅ 에러 코드, 메시지, 상세 정보 포함

### 4. 로깅 (Lines 63, 76, 88, 100)
- ✅ 에러 발생 시 로깅
- ✅ 일반 예외 핸들러에서 `exc_info=True` 사용 (스택 트레이스 포함)

### 5. 커스텀 예외 활용
- ✅ 커스텀 예외 클래스 사용
- ✅ 예외별 적절한 처리

---

## ⚠️ 발견된 문제점

### 1. 검증 에러 - 첫 번째 에러만 반환 (Lines 20-35)
```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_details = {
        "field": errors[0].get("loc")[-1] if errors else None,
        "message": errors[0].get("msg") if errors else "검증 오류"
    }
```
**영향도**: 중간  
**문제**: 
- 여러 필드에 에러가 있어도 첫 번째만 반환
- 클라이언트가 모든 에러를 한 번에 수정할 수 없음

**권장 수정**:
```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_list = [
        {
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "검증 오류"),
            "type": error.get("type", "validation_error")
        }
        for error in errors
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

### 2. 에러 로깅에 요청 정보 없음 (Lines 63, 76, 88)
```python
logger.error(f"GPT API 오류: {str(exc)}")
```
**영향도**: 중간  
**문제**: 
- 어떤 요청에서 에러가 발생했는지 추적 어려움
- 디버깅 시 요청 경로, 메서드, 파라미터 정보 필요

**권장 수정**:
```python
logger.error(
    f"GPT API 오류: {request.method} {request.url.path} - {str(exc)}",
    exc_info=True
)
```

### 3. 프로덕션에서 상세 에러 정보 노출 (Lines 68, 81, 93, 105)
```python
message="GPT API 호출 중 오류가 발생했습니다."
```
**영향도**: 낮음  
**현황**: 적절한 수준의 일반적 메시지  
**주의사항**: 
- `details`에 민감한 정보가 포함되지 않도록 주의
- 스택 트레이스는 로그에만 기록 (응답에는 포함 안 됨)

### 4. 에러 코드 일관성
**영향도**: 낮음  
**현황**: 
- `VALIDATION_ERROR`, `SESSION_NOT_FOUND`, `INVALID_INPUT` 등 일관된 형식
- 모두 대문자와 언더스코어 사용

### 5. 일반 예외 핸들러의 스택 트레이스 (Line 100)
```python
logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
```
**영향도**: 낮음  
**현황**: 적절함 (스택 트레이스 포함)  
**권장사항**: 다른 핸들러에도 `exc_info=True` 추가 고려

### 6. 요청 정보 접근 (모든 핸들러)
**영향도**: 낮음  
**현황**: `request` 파라미터는 받지만 사용하지 않음  
**권장사항**: 로깅에 요청 정보 포함

---

## 🔍 추가 검토 사항

### 1. 에러 응답 형식 일관성
- `error_response` 유틸리티 사용으로 일관성 확보
- 모든 핸들러에서 동일한 형식 사용

### 2. 프로덕션 vs 개발 환경
- 현재: 환경 구분 없음
- 권장: 개발 환경에서는 더 상세한 에러 정보 제공

### 3. 에러 메트릭 수집
- 현재: 로깅만 수행
- 권장: 에러 메트릭 수집 시스템 연동

### 4. 재시도 가능한 에러 구분
- 현재: 모든 에러를 동일하게 처리
- 권장: 일시적 에러(재시도 가능)와 영구적 에러 구분

---

## 📊 종합 평가

### 강점
1. ✅ 7개 핸들러로 체계적 예외 처리
2. ✅ 적절한 HTTP 상태 코드 사용
3. ✅ 일관된 에러 응답 형식
4. ✅ 커스텀 예외 활용
5. ✅ 일반 예외 핸들러에서 스택 트레이스 포함

### 개선 필요
1. 🟡 **중간**: 검증 에러 - 모든 에러 반환
2. 🟡 **중간**: 에러 로깅에 요청 정보 추가
3. 🟢 **낮음**: 다른 핸들러에도 `exc_info=True` 추가

### 우선순위
- **중간**: 검증 에러 모든 필드 반환
- **중간**: 에러 로깅에 요청 정보 포함
- **낮음**: 스택 트레이스 로깅 일관성

---

## 📝 권장 수정 사항

### 수정 1: 검증 에러 - 모든 에러 반환
```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 에러 핸들러"""
    errors = exc.errors()
    
    # 모든 검증 에러를 리스트로 반환
    error_list = [
        {
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "검증 오류"),
            "type": error.get("type", "validation_error")
        }
        for error in errors
    ]
    
    logger.warning(
        f"요청 검증 실패: {request.method} {request.url.path} - "
        f"{len(error_list)}개 필드 오류"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            code="VALIDATION_ERROR",
            message="요청 데이터 검증 실패",
            details={"errors": error_list}
        )
    )
```

### 수정 2: 에러 로깅에 요청 정보 추가
```python
async def gpt_api_error_handler(request: Request, exc: GPTAPIError):
    """GPT API 에러 핸들러"""
    logger.error(
        f"GPT API 오류: {request.method} {request.url.path} - {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="GPT_API_ERROR",
            message="GPT API 호출 중 오류가 발생했습니다.",
            details={"status_code": exc.status_code} if exc.status_code else None
        )
    )

async def rag_search_error_handler(request: Request, exc: RAGSearchError):
    """RAG 검색 에러 핸들러"""
    logger.error(
        f"RAG 검색 오류: {request.method} {request.url.path} - {str(exc)}",
        exc_info=True
    )
    # ...

async def database_error_handler(request: Request, exc: DatabaseError):
    """데이터베이스 에러 핸들러"""
    logger.error(
        f"데이터베이스 오류: {request.method} {request.url.path} - {str(exc)}",
        exc_info=True
    )
    # ...
```

### 수정 3: 환경별 에러 정보 제공 (선택사항)
```python
from config.settings import settings

async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(
        f"예상치 못한 오류: {request.method} {request.url.path} - {str(exc)}",
        exc_info=True
    )
    
    # 개발 환경에서는 더 상세한 정보 제공
    details = None
    if settings.environment.lower() == "development":
        details = {
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다.",
            details=details
        )
    )
```

---

## ✅ 검토 완료

**검토 항목**: `review_04_api_error_handler`  
**상태**: 완료  
**다음 항목**: `review_05_api_chat_router`

