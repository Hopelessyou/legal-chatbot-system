# API 미들웨어 검토 보고서

## 검토 대상
- 파일: `src/api/middleware.py`
- 검토 일자: 2024년
- 검토 범위: 로깅 미들웨어, 요청/응답 처리, 성능 측정, 요청 바디 재사용

---

## ✅ 정상 동작 부분

### 1. BaseHTTPMiddleware 상속 (Lines 13-14)
```python
class LoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어"""
```
- ✅ Starlette의 표준 미들웨어 패턴 사용
- ✅ 비동기 처리 지원

### 2. 요청 정보 로깅 (Lines 20-27)
```python
client_ip = request.client.host if request.client else "unknown"
method = request.method
path = request.url.path

logger.info(f"요청 수신: {method} {path} - IP: {client_ip}")
```
- ✅ 요청 메서드, 경로, IP 주소 로깅
- ✅ IP 주소 없을 때 기본값 처리

### 3. 개인정보 마스킹 (Lines 29-49)
```python
masked_body = mask_personal_info(body_str)
logger.debug(f"요청 바디: {masked_body}")
```
- ✅ 개인정보 마스킹 적용
- ✅ DEBUG 레벨로 로깅 (프로덕션에서 노출 최소화)

### 4. 요청 바디 재사용 (Lines 38-47)
```python
request.state.body = body
request.state.body_str = body_str

async def receive():
    return {"type": "http.request", "body": body}
request._receive = receive
```
- ✅ 요청 바디를 request.state에 저장
- ✅ `_receive` 재정의로 후속 핸들러에서 재사용 가능
- ✅ 이전 버그 수정됨

### 5. 성능 측정 (Lines 55-66)
```python
process_time = time.time() - start_time
logger.info(f"응답 완료: {method} {path} - 상태: {response.status_code} - 소요 시간: {process_time:.3f}초")
response.headers["X-Process-Time"] = str(process_time)
```
- ✅ 요청 처리 시간 측정
- ✅ 응답 헤더에 처리 시간 포함
- ✅ 로그에 상세 정보 기록

### 6. 에러 처리 (Lines 70-77)
```python
except Exception as e:
    process_time = time.time() - start_time
    logger.error(f"요청 처리 실패: {method} {path} - 오류: {str(e)} - 소요 시간: {process_time:.3f}초")
    raise
```
- ✅ 예외 발생 시에도 처리 시간 기록
- ✅ 예외를 다시 raise하여 에러 핸들러로 전달

---

## ⚠️ 발견된 문제점

### 1. 사용되지 않는 import (Line 5)
```python
from fastapi import Request, Response  # Response는 사용되지 않음
```
**영향도**: 낮음  
**문제**: `Response`가 import되었지만 사용되지 않음  
**수정 필요**: 
```python
from fastapi import Request
```

### 2. 요청 바디 재사용 로직 복잡성 (Lines 42-47)
```python
async def receive():
    return {"type": "http.request", "body": body}
request._receive = receive
```
**영향도**: 중간  
**문제**: 
- Starlette의 내부 구현(`_receive`)에 의존
- Starlette 버전 업데이트 시 호환성 문제 가능
- 바디가 메모리에 완전히 로드됨 (큰 파일 처리 시 문제)

**권장 개선**:
- Starlette의 공식 API 사용 검토
- 큰 파일의 경우 스트리밍 처리 고려
- 또는 바디를 한 번만 읽고 캐싱하는 표준 패턴 사용

### 3. 바디 디코딩 실패 처리 (Line 34)
```python
body_str = body.decode("utf-8")
```
**영향도**: 중간  
**문제**: 
- UTF-8 디코딩 실패 시 예외 발생
- 바이너리 파일 업로드 시 문제 가능
- 에러 핸들러에서 처리되지만, 더 명확한 에러 메시지 필요

**권장 개선**:
```python
try:
    body_str = body.decode("utf-8")
except UnicodeDecodeError:
    body_str = f"<binary data: {len(body)} bytes>"
    logger.debug(f"요청 바디는 UTF-8로 디코딩할 수 없습니다 (바이너리 데이터로 추정)")
```

### 4. 큰 요청 바디 메모리 문제 (Lines 33-47)
```python
body = await request.body()  # 전체 바디를 메모리에 로드
```
**영향도**: 중간  
**문제**: 
- 큰 파일 업로드 시 메모리 사용량 증가
- 동시 요청이 많을 때 메모리 부족 가능

**권장 개선**:
- 파일 업로드 엔드포인트는 미들웨어에서 바디 로깅 제외
- 바디 크기 제한 설정
- 스트리밍 처리 고려

### 5. 에러 로깅에 스택 트레이스 없음 (Line 72)
```python
logger.error(f"요청 처리 실패: {method} {path} - 오류: {str(e)} - 소요 시간: {process_time:.3f}초")
```
**영향도**: 낮음  
**문제**: 스택 트레이스가 없어 디버깅 어려움  
**권장 개선**:
```python
logger.error(
    f"요청 처리 실패: {method} {path} - 오류: {str(e)} - 소요 시간: {process_time:.3f}초",
    exc_info=True  # 스택 트레이스 포함
)
```

### 6. 요청 바디 로깅 실패 시 경고만 (Line 49)
```python
except Exception as e:
    logger.warning(f"요청 바디 로깅 실패: {str(e)}")
```
**영향도**: 낮음  
**현황**: 적절한 처리 (로깅 실패가 요청 처리 실패로 이어지지 않음)  
**권장사항**: 현재 상태 유지

### 7. GET 요청 바디 처리 없음
**영향도**: 낮음  
**현황**: GET 요청은 일반적으로 바디가 없으므로 적절함  
**참고**: 일부 클라이언트가 GET 요청에 바디를 포함할 수 있으나, HTTP 스펙상 권장되지 않음

---

## 🔍 추가 검토 사항

### 1. 미들웨어 실행 순서
- 현재: CORS → Logging
- 권장: 로깅이 가장 먼저 실행되어 모든 요청 기록

### 2. 요청 ID 추적
- 현재: 요청 ID 없음
- 권장: 각 요청에 고유 ID 부여하여 로그 추적 용이

### 3. 성능 메트릭 수집
- 현재: 처리 시간만 로깅
- 권장: 메트릭 수집 시스템 연동 (Prometheus 등)

### 4. 바디 크기 제한
- 현재: 제한 없음
- 권장: 설정 가능한 최대 바디 크기

---

## 📊 종합 평가

### 강점
1. ✅ 요청/응답 로깅 체계적
2. ✅ 개인정보 마스킹 적용
3. ✅ 성능 측정 및 헤더 추가
4. ✅ 요청 바디 재사용 로직 구현 (이전 버그 수정)
5. ✅ 에러 처리 적절

### 개선 필요
1. 🟡 **중간**: 요청 바디 재사용 로직 개선 (표준 패턴 사용)
2. 🟡 **중간**: 바디 디코딩 실패 처리 강화
3. 🟡 **중간**: 큰 바디 메모리 문제 해결
4. 🟢 **낮음**: 사용되지 않는 import 제거
5. 🟢 **낮음**: 에러 로깅에 스택 트레이스 추가

### 우선순위
- **중간**: 바디 재사용 로직 표준화
- **중간**: 바디 디코딩 실패 처리
- **중간**: 큰 바디 처리 개선
- **낮음**: import 정리, 스택 트레이스 추가

---

## 📝 권장 수정 사항

### 수정 1: 사용되지 않는 import 제거
```python
# 수정 전
from fastapi import Request, Response

# 수정 후
from fastapi import Request
```

### 수정 2: 바디 디코딩 실패 처리 강화
```python
if request.method in ["POST", "PUT", "PATCH"]:
    try:
        body = await request.body()
        
        # UTF-8 디코딩 시도
        try:
            body_str = body.decode("utf-8")
        except UnicodeDecodeError:
            # 바이너리 데이터로 추정
            body_str = f"<binary data: {len(body)} bytes>"
            logger.debug(f"요청 바디는 UTF-8로 디코딩할 수 없습니다")
        
        masked_body = mask_personal_info(body_str)
        logger.debug(f"요청 바디: {masked_body}")
        
        # 바디 재사용 설정
        request.state.body = body
        request.state.body_str = body_str
        
        # Starlette Request의 _body를 복원
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
    except Exception as e:
        logger.warning(f"요청 바디 로깅 실패: {str(e)}")
```

### 수정 3: 에러 로깅에 스택 트레이스 추가
```python
except Exception as e:
    process_time = time.time() - start_time
    logger.error(
        f"요청 처리 실패: {method} {path} - "
        f"오류: {str(e)} - "
        f"소요 시간: {process_time:.3f}초",
        exc_info=True  # 스택 트레이스 포함
    )
    raise
```

### 수정 4: 요청 ID 추가 (선택사항)
```python
import uuid

async def dispatch(self, request: Request, call_next):
    """요청 처리 및 로깅"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]  # 짧은 요청 ID
    
    # 요청 ID를 request.state에 저장
    request.state.request_id = request_id
    
    # 로깅에 요청 ID 포함
    logger.info(f"[{request_id}] 요청 수신: {method} {path} - IP: {client_ip}")
    # ...
```

### 수정 5: 바디 크기 제한 (선택사항)
```python
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

if request.method in ["POST", "PUT", "PATCH"]:
    try:
        body = await request.body()
        
        # 바디 크기 확인
        if len(body) > MAX_BODY_SIZE:
            logger.warning(f"요청 바디가 너무 큽니다: {len(body)} bytes (최대: {MAX_BODY_SIZE})")
            # 바디 로깅 건너뛰기
        else:
            # 기존 로직...
```

---

## ✅ 검토 완료

**검토 항목**: `review_03_api_middleware`  
**상태**: 완료  
**다음 항목**: `review_04_api_error_handler`

