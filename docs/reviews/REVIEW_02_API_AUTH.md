# API 인증 검토 보고서

## 검토 대상
- 파일: `src/api/auth.py`
- 검토 일자: 2024년
- 검토 범위: API 키 검증 로직, 보안 취약점, 인증 실패 처리

---

## ✅ 정상 동작 부분

### 1. HTTPBearer 인증 방식 (Lines 4-11)
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()
```
- ✅ 표준 HTTP Bearer 토큰 인증 사용
- ✅ FastAPI의 Security 의존성 활용

### 2. API 키 검증 함수 (Lines 14-36)
```python
def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    
    if token != settings.api_secret_key:
        logger.warning(f"잘못된 API 키 시도: {token[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API 키입니다."
        )
    
    return token
```
- ✅ 인증 실패 시 적절한 HTTP 상태 코드 (401)
- ✅ 실패 시도 로깅 (일부 마스킹)
- ✅ 명확한 에러 메시지

### 3. 모든 엔드포인트에 적용 (chat.py, rag.py)
- ✅ 10개 chat 엔드포인트 모두 `Depends(verify_api_key)` 적용
- ✅ 3개 rag 엔드포인트 모두 `Depends(verify_api_key)` 적용
- ✅ 일관된 인증 적용

---

## ⚠️ 발견된 보안 취약점

### 1. 타이밍 공격 취약점 (Line 29)
```python
if token != settings.api_secret_key:
```
**영향도**: 중간  
**문제**: 문자열 비교(`!=`)는 타이밍 공격에 취약함. 키 길이에 따라 비교 시간이 달라질 수 있음.  
**권장 수정**: 
```python
import secrets

# 상수 시간 비교 사용
if not secrets.compare_digest(token, settings.api_secret_key):
```

### 2. 단일 API 키만 지원 (Line 29)
```python
if token != settings.api_secret_key:
```
**영향도**: 중간  
**문제**: 
- 다중 클라이언트 지원 불가
- 키별 권한 관리 불가
- 키 회전/만료 관리 불가
- 키별 사용량 추적 불가

**권장 개선**:
- DB에 API 키 테이블 추가
- 키별 메타데이터 (만료일, 권한, 사용량 등)
- 키 해싱 저장 (bcrypt 등)

### 3. API 키 로깅 부분 마스킹 (Line 30)
```python
logger.warning(f"잘못된 API 키 시도: {token[:10]}...")
```
**영향도**: 낮음  
**문제**: 
- 처음 10자만 로깅하지만, 로그에 노출됨
- 로그 파일 보안이 약하면 키 일부 유출 가능

**권장 수정**:
```python
# 해시 기반 마스킹
import hashlib
token_hash = hashlib.sha256(token.encode()).hexdigest()[:8]
logger.warning(f"잘못된 API 키 시도: {token_hash}...")
```

### 4. Rate Limiting 없음
**영향도**: 높음  
**문제**: 
- 무제한 API 호출 가능
- 브루트포스 공격에 취약
- DDoS 공격에 취약

**권장 추가**:
- IP 기반 Rate Limiting
- API 키별 Rate Limiting
- FastAPI의 `slowapi` 또는 `starlette-rate-limit` 사용

### 5. API 키 만료/회전 기능 없음
**영향도**: 중간  
**문제**: 
- 키가 유출되어도 만료 없음
- 키 회전 시 애플리케이션 재시작 필요
- 키 이력 관리 불가

**권장 추가**:
- 키 만료일 필드
- 키 활성화/비활성화 플래그
- 키 이력 테이블

### 6. API 키 검증 실패 상세 정보 (Line 33)
```python
detail="유효하지 않은 API 키입니다."
```
**영향도**: 낮음  
**현황**: 적절한 수준의 정보 제공 (키 존재 여부 노출하지 않음)  
**권장사항**: 현재 상태 유지

### 7. Settings에서 API 키 관리 (Line 29)
```python
if token != settings.api_secret_key:
```
**영향도**: 낮음  
**현황**: 환경변수에서 로드되므로 코드에 하드코딩되지 않음  
**주의사항**: 
- `.env` 파일이 버전 관리에 포함되지 않아야 함
- 프로덕션에서는 환경변수로 직접 설정 권장

---

## 🔍 추가 검토 사항

### 1. API 키 형식 검증
- 현재: 형식 검증 없음
- 권장: 최소 길이, 문자셋 검증 추가

### 2. 인증 실패 횟수 추적
- 현재: 로깅만 수행
- 권장: 실패 횟수 추적 및 일시적 차단

### 3. HTTPS 강제
- 현재: 코드 레벨에서 확인 없음
- 권장: 프로덕션에서는 HTTPS 강제 (미들웨어 또는 리버스 프록시)

### 4. API 키 생성/관리 인터페이스
- 현재: 수동으로 환경변수 설정
- 권장: 관리자 API로 키 생성/관리

---

## 📊 종합 평가

### 강점
1. ✅ 표준 HTTP Bearer 토큰 인증 사용
2. ✅ 모든 엔드포인트에 일관된 인증 적용
3. ✅ 적절한 HTTP 상태 코드 및 에러 메시지
4. ✅ 환경변수 기반 키 관리 (하드코딩 없음)

### 보안 취약점
1. 🔴 **높음**: Rate Limiting 없음
2. 🟡 **중간**: 타이밍 공격 취약점
3. 🟡 **중간**: 단일 API 키만 지원
4. 🟡 **중간**: API 키 만료/회전 기능 없음
5. 🟢 **낮음**: 로깅 마스킹 개선 필요

### 우선순위
- **높음**: Rate Limiting 추가
- **중간**: 타이밍 공격 방지 (secrets.compare_digest)
- **중간**: 다중 API 키 지원 (DB 기반)
- **낮음**: 로깅 마스킹 개선

---

## 📝 권장 수정 사항

### 수정 1: 타이밍 공격 방지
```python
import secrets

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    
    # 상수 시간 비교 사용
    if not secrets.compare_digest(token, settings.api_secret_key):
        # 해시 기반 로깅
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:8]
        logger.warning(f"잘못된 API 키 시도: {token_hash}...")
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API 키입니다."
        )
    
    return token
```

### 수정 2: Rate Limiting 추가
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# main.py에 추가
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# auth.py에 추가
@limiter.limit("10/minute")  # IP당 분당 10회
def verify_api_key(...):
    # ...
```

### 수정 3: 다중 API 키 지원 (DB 기반)
```python
# 새로운 모델: APIKey
class APIKey(BaseModel):
    key_hash: str  # bcrypt 해시
    name: str
    expires_at: Optional[datetime]
    is_active: bool
    rate_limit: int
    created_at: datetime

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    
    # DB에서 키 조회 및 검증
    with db_manager.get_db_session() as db_session:
        # 키 해시로 조회
        key_hash = hash_api_key(token)
        api_key = db_session.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key:
            raise HTTPException(status_code=401, detail="유효하지 않은 API 키입니다.")
        
        # 만료 확인
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="만료된 API 키입니다.")
        
        # Rate limit 확인
        # ...
    
    return token
```

---

## ✅ 검토 완료

**검토 항목**: `review_02_api_auth`  
**상태**: 완료  
**다음 항목**: `review_03_api_middleware`

