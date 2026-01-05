# API 메인 레이어 검토 보고서

## 검토 대상
- 파일: `src/api/main.py`
- 검토 일자: 2024년
- 검토 범위: FastAPI 앱 설정, 미들웨어, 에러 핸들러, 라우터 등록, startup/shutdown 이벤트

---

## ✅ 정상 동작 부분

### 1. FastAPI 앱 초기화 (Lines 34-38)
```python
app = FastAPI(
    title="법률 상담문의 수집 챗봇 API",
    description="RAG + LangGraph 기반 법률 상담문의 수집 시스템",
    version="0.1.0"
)
```
- ✅ 앱 메타데이터 설정 정상
- ✅ 버전 관리 적절

### 2. CORS 설정 (Lines 41-47)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- ✅ CORS 미들웨어 등록 정상
- ✅ 설정값을 settings에서 관리
- ⚠️ `allow_methods=["*"]`, `allow_headers=["*"]`는 프로덕션에서 제한 고려 필요

### 3. 로깅 미들웨어 (Line 50)
```python
app.add_middleware(LoggingMiddleware)
```
- ✅ 커스텀 로깅 미들웨어 등록 정상

### 4. 에러 핸들러 등록 (Lines 53-59)
```python
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SessionNotFoundError, session_not_found_handler)
app.add_exception_handler(InvalidInputError, invalid_input_handler)
app.add_exception_handler(GPTAPIError, gpt_api_error_handler)
app.add_exception_handler(RAGSearchError, rag_search_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(Exception, general_exception_handler)
```
- ✅ 7개 에러 핸들러 모두 등록됨
- ✅ 커스텀 예외와 일반 예외 모두 처리
- ✅ 예외 처리 계층 구조 적절 (구체적 → 일반적)

### 5. Startup 이벤트 (Lines 62-106)
- ✅ 필수 환경변수 검증 추가됨 (Lines 72-78)
- ✅ DB 연결 실패 시 strict 모드 처리 추가됨 (Lines 80-94)
- ✅ Vector DB 연결 실패 시 strict 모드 처리 추가됨 (Lines 96-106)
- ✅ 프로덕션 환경 자동 감지 및 strict 모드 적용

### 6. 헬스체크 엔드포인트 (Lines 129-144)
```python
@app.get("/health")
async def health_check():
    db_healthy = db_manager.health_check()
    vector_db_healthy = vector_db_manager.health_check()
    # ...
```
- ✅ DB와 Vector DB 상태 모두 확인
- ✅ 상세한 상태 정보 반환

### 7. 정적 파일 서빙 (Lines 147-151)
- ✅ 조건부 마운트 (디렉토리 존재 시에만)
- ✅ 로깅 추가

### 8. 라우터 등록 (Lines 153-156)
- ✅ chat, rag 라우터 등록 정상

---

## ⚠️ 발견된 문제점

### 1. 사용되지 않는 import (Line 4)
```python
from fastapi import FastAPI, Request  # Request는 사용되지 않음
```
**영향도**: 낮음  
**문제**: `Request`가 import되었지만 사용되지 않음  
**수정 필요**: 
```python
from fastapi import FastAPI  # Request 제거
```

### 2. 중복 import (Lines 10, 67)
```python
# Line 10
from config.settings import settings

# Line 67 (startup_event 내부)
from config.settings import settings
```
**영향도**: 낮음  
**문제**: `settings`가 두 번 import됨 (전역과 함수 내부)  
**수정 필요**: 함수 내부의 중복 import 제거 (이미 전역에서 import됨)

### 3. Shutdown 이벤트 - Vector DB 정리 누락 (Lines 109-116)
```python
@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info("애플리케이션 종료")
    
    # 리소스 정리
    from src.db.connection import db_manager
    db_manager.close()
    # Vector DB 정리는 없음
```
**영향도**: 중간  
**문제**: Vector DB (ChromaDB) 리소스 정리가 없음  
**현황**: ChromaDB는 파일 기반이므로 명시적 close가 필요 없을 수 있으나, 확인 필요  
**수정 필요**: 
- Vector DB에 close/cleanup 메서드가 있는지 확인
- 있다면 shutdown 이벤트에 추가
- 없다면 문서화 또는 주석 추가

### 4. CORS 설정 - 프로덕션 보안 (Lines 41-47)
```python
allow_methods=["*"],
allow_headers=["*"],
```
**영향도**: 중간  
**문제**: 모든 메서드와 헤더 허용은 보안 위험  
**권장사항**: 
- 프로덕션에서는 필요한 메서드와 헤더만 명시
- settings에 환경별 CORS 설정 추가 고려

### 5. 라우터 import 위치 (Lines 154-156)
```python
# 라우터 등록
from src.api.routers import chat, rag
app.include_router(chat.router)
app.include_router(rag.router)
```
**영향도**: 낮음  
**현황**: 파일 하단에 위치. 순환 참조는 없음  
**권장사항**: 
- import를 상단으로 이동하거나
- 현재 위치 유지해도 무방 (순환 참조 방지)

---

## 🔍 추가 검토 사항

### 1. FastAPI 버전 호환성
- `@app.on_event("startup")` / `@app.on_event("shutdown")`는 FastAPI 0.92+에서 deprecated
- 권장: `lifespan` 컨텍스트 매니저 사용
- 현재 코드는 동작하지만 향후 업데이트 필요

### 2. 에러 핸들러 순서
- 현재 순서는 적절함 (구체적 → 일반적)
- `Exception` 핸들러가 마지막에 위치하여 모든 예외를 포괄

### 3. 로깅 초기화
- `setup_logging()`이 앱 생성 전에 호출됨 (Line 31)
- 적절한 위치

### 4. 정적 파일 보안
- 정적 파일 디렉토리 존재 여부만 확인
- 파일 접근 권한 검증은 없음 (운영체제 레벨에서 처리)

---

## 📊 종합 평가

### 강점
1. ✅ 에러 핸들러 체계적 구성
2. ✅ Startup 이벤트에서 환경변수 및 DB 연결 검증 강화
3. ✅ Strict 모드로 프로덕션 안정성 확보
4. ✅ 헬스체크 엔드포인트 상세 정보 제공

### 개선 필요
1. ⚠️ 사용되지 않는 import 제거
2. ⚠️ 중복 import 정리
3. ⚠️ Vector DB shutdown 처리 확인/추가
4. ⚠️ CORS 설정 프로덕션 보안 강화

### 우선순위
- **높음**: 없음
- **중간**: Vector DB shutdown 처리, CORS 보안
- **낮음**: import 정리

---

## 📝 권장 수정 사항

### 수정 1: 사용되지 않는 import 제거
```python
# 수정 전
from fastapi import FastAPI, Request

# 수정 후
from fastapi import FastAPI
```

### 수정 2: 중복 import 제거
```python
# startup_event 내부의 중복 import 제거
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("애플리케이션 시작")
    
    # from config.settings import settings  # 제거 (이미 전역에서 import됨)
    from src.db.connection import db_manager
    # ...
```

### 수정 3: Vector DB shutdown 처리 확인 및 추가
```python
@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info("애플리케이션 종료")
    
    # 리소스 정리
    from src.db.connection import db_manager
    from src.rag.vector_db import vector_db_manager
    
    db_manager.close()
    
    # Vector DB 정리 (메서드 존재 시)
    if hasattr(vector_db_manager, 'close'):
        vector_db_manager.close()
    elif hasattr(vector_db_manager, 'cleanup'):
        vector_db_manager.cleanup()
```

---

## ✅ 검토 완료

**검토 항목**: `review_01_api_main`  
**상태**: 완료  
**다음 항목**: `review_02_api_auth`

