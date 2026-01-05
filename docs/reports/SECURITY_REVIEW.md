# 보안 검토 보고서

**검토 일자**: 2025-01-XX  
**검토 대상**: RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템  
**검토 범위**: 인증/인가, 입력 검증, 파일 업로드, 데이터 보호, 로깅, 에러 처리

---

## 🔴 심각 (Critical) - 즉시 수정 필요

### 1. API 인증 미적용
**위치**: `src/api/routers/chat.py`, `src/api/routers/rag.py`

**문제점**:
- `verify_api_key` 함수가 정의되어 있지만 실제 라우터에서 사용되지 않음
- 모든 API 엔드포인트가 인증 없이 접근 가능
- 세션 생성, 메시지 처리, 파일 업로드 등 모든 기능이 무인증으로 접근 가능

**영향**:
- 무단 API 사용 가능
- 세션 생성 및 데이터 조회 가능
- 파일 업로드/다운로드 가능
- 서버 리소스 남용 가능

**수정 방안**:
```python
# src/api/routers/chat.py
from src.api.auth import verify_api_key

@router.post("/start")
async def start_chat(
    request: ChatStartRequest,
    api_key: str = Depends(verify_api_key)  # 인증 추가
):
    ...
```

**권장사항**:
- 모든 관리자용 엔드포인트에 인증 적용
- 사용자용 엔드포인트는 세션 기반 인증 고려
- API 키 대신 JWT 토큰 사용 검토

---

### 2. 파일 업로드 보안 취약점
**위치**: `src/api/routers/chat.py:462-563`

**문제점**:
1. **파일 확장자 검증 부족**: 허용된 확장자 목록이 없음
2. **파일 내용 검증 없음**: 실제 파일 타입 확인 없이 MIME 타입만 신뢰
3. **Path Traversal 취약점**: `file.filename`을 직접 사용하여 경로 조작 가능
4. **악성 파일 업로드 가능**: 실행 파일, 스크립트 파일 업로드 가능

**영향**:
- 악성 파일 업로드로 서버 침해 가능
- Path Traversal을 통한 임의 파일 접근
- 서버 측 스크립트 실행 가능

**수정 방안**:
```python
# 허용된 확장자 목록
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg', 'image/png', 'text/plain'
}

# 파일명 정규화 및 검증
import os
from pathlib import Path

# Path Traversal 방지
safe_filename = os.path.basename(file.filename)
if not safe_filename or safe_filename != file.filename:
    raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")

# 확장자 검증
file_ext = Path(safe_filename).suffix.lower()
if file_ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(status_code=400, detail="허용되지 않은 파일 형식입니다.")

# MIME 타입 검증
if mime_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(status_code=400, detail="허용되지 않은 파일 타입입니다.")

# 파일 내용 검증 (magic bytes 확인)
import magic
file_type = magic.from_buffer(file_content, mime=True)
if file_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(status_code=400, detail="파일 내용이 선언된 타입과 일치하지 않습니다.")
```

---

### 3. 로깅에 민감 정보 노출
**위치**: `logs/app.log`, `logs/error.log`

**문제점**:
- 로그 파일에 비밀번호 길이 정보 노출 (`password_len: 9`)
- 데이터베이스 연결 실패 시 사용자명 노출
- 에러 메시지에 상세한 시스템 정보 포함

**영향**:
- 공격자가 비밀번호 길이 추측 가능
- 시스템 구조 파악 가능
- 정보 수집을 통한 추가 공격 가능

**수정 방안**:
```python
# src/utils/logger.py 또는 에러 핸들러에서
def sanitize_log_message(message: str) -> str:
    """로그 메시지에서 민감 정보 제거"""
    # 비밀번호 관련 정보 제거
    message = re.sub(r'password[_\s]*[:=]\s*\S+', 'password=***', message, flags=re.IGNORECASE)
    message = re.sub(r'password_len[_\s]*[:=]\s*\d+', 'password_len=***', message, flags=re.IGNORECASE)
    # API 키 마스킹
    message = re.sub(r'(api[_\s]*key|secret[_\s]*key)[_\s]*[:=]\s*(\S+)', 
                     r'\1=***', message, flags=re.IGNORECASE)
    return message
```

---

## 🟠 높음 (High) - 우선 수정 권장

### 4. 입력 검증 및 XSS 방지 부족
**위치**: `src/api/routers/chat.py`, 모든 사용자 입력 처리 부분

**문제점**:
- 사용자 입력(`user_message`)에 대한 XSS 방지 처리 없음
- HTML 태그, 스크립트 태그 필터링 없음
- 입력 길이 제한 없음 (DoS 공격 가능)

**영향**:
- XSS 공격 가능
- 악성 스크립트 주입 가능
- 대용량 입력으로 서버 리소스 고갈

**수정 방안**:
```python
from html import escape
import bleach

# 입력 길이 제한
MAX_MESSAGE_LENGTH = 5000

@router.post("/message")
async def process_message(request: ChatMessageRequest):
    # 입력 길이 검증
    if len(request.user_message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"메시지는 {MAX_MESSAGE_LENGTH}자를 초과할 수 없습니다.")
    
    # XSS 방지: HTML 이스케이프
    sanitized_message = escape(request.user_message)
    
    # 또는 bleach 사용 (더 강력한 필터링)
    # sanitized_message = bleach.clean(request.user_message, tags=[], strip=True)
    
    state["last_user_input"] = sanitized_message
    ...
```

---

### 5. CORS 설정이 너무 관대함
**위치**: `src/api/main.py:40-46`

**문제점**:
- `allow_origins`가 개발 환경용으로 설정되어 있음
- 프로덕션 환경에서도 모든 오리진 허용 가능성
- `allow_methods=["*"]`, `allow_headers=["*"]`로 모든 메서드/헤더 허용

**영향**:
- CSRF 공격 가능
- 임의 도메인에서 API 호출 가능
- 크로스 오리진 요청으로 인한 데이터 유출

**수정 방안**:
```python
# config/settings.py
class Settings(BaseSettings):
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    
    @property
    def cors_origins_list(self) -> List[str]:
        if self.environment == "production":
            # 프로덕션에서는 특정 도메인만 허용
            return [
                "https://yourdomain.com",
                "https://app.yourdomain.com"
            ]
        return [origin.strip() for origin in self.cors_origins.split(",")]

# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # 필요한 메서드만 허용
    allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만 허용
)
```

---

### 6. 에러 메시지에 상세 정보 노출
**위치**: `src/api/error_handler.py`, `src/api/routers/chat.py`

**문제점**:
- 에러 메시지에 스택 트레이스, 파일 경로 등 상세 정보 포함
- 데이터베이스 에러 메시지가 그대로 노출됨
- 내부 시스템 구조 정보 노출

**영향**:
- 공격자가 시스템 구조 파악 가능
- 취약점 탐색에 활용 가능
- 정보 수집을 통한 추가 공격 가능

**수정 방안**:
```python
# src/api/error_handler.py
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    # 프로덕션 환경에서는 상세 정보 숨김
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

### 7. 세션 ID 예측 가능성
**위치**: `src/utils/helpers.py:103-110`

**문제점**:
- 세션 ID가 `sess_` + UUID 12자리로 구성
- UUID 12자리는 충분히 랜덤하지만, 더 긴 세션 ID 권장
- 세션 ID 검증이 형식만 확인하고 존재 여부는 DB 조회로 확인

**영향**:
- 세션 하이재킹 가능성 (낮지만 존재)
- 무작위 대입 공격 가능

**수정 방안**:
```python
def generate_session_id() -> str:
    """
    세션 ID 생성 (더 긴 랜덤 문자열)
    """
    # 32자리 hex 문자열 사용 (더 안전)
    return f"sess_{uuid.uuid4().hex}"

# 또는 더 강력한 랜덤 생성
import secrets
def generate_session_id() -> str:
    return f"sess_{secrets.token_urlsafe(32)}"
```

---

## 🟡 중간 (Medium) - 개선 권장

### 8. Rate Limiting 미적용
**위치**: `config/settings.py:45`, `src/api/main.py`

**문제점**:
- `rate_limit_per_minute` 설정은 있지만 실제 미들웨어에서 적용되지 않음
- API 요청 제한이 없어 DoS 공격에 취약

**영향**:
- 무차별 요청으로 서버 리소스 고갈
- GPT API 비용 증가
- 서비스 가용성 저하

**수정 방안**:
```python
# requirements.txt에 추가
# slowapi>=0.1.9  # 이미 있음

# src/api/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 라우터에 적용
@router.post("/message")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def process_message(request: Request, chat_request: ChatMessageRequest):
    ...
```

---

### 9. SQL Injection 방어 확인 필요
**위치**: 전체 DB 쿼리 부분

**문제점**:
- SQLAlchemy ORM 사용으로 대부분 방어되지만, raw SQL 사용 시 주의 필요
- 사용자 입력이 직접 쿼리에 포함되는 부분 확인 필요

**현재 상태**:
- ✅ SQLAlchemy ORM 사용 (대부분 안전)
- ✅ 파라미터화된 쿼리 사용
- ⚠️ 동적 쿼리 생성 시 주의 필요

**권장사항**:
- 모든 사용자 입력은 ORM 필터를 통해 처리
- Raw SQL 사용 시 반드시 파라미터화
- 정기적인 코드 리뷰로 동적 쿼리 확인

---

### 10. 환경 변수 관리
**위치**: `.env` 파일, `config/settings.py`

**문제점**:
- `.env` 파일이 `.gitignore`에 포함되어 있는지 확인 필요
- 환경 변수 기본값에 하드코딩된 비밀번호 존재

**수정 방안**:
```python
# config/settings.py
class Settings(BaseSettings):
    # 기본값 제거, 필수로 설정
    database_url: str  # 기본값 제거
    openai_api_key: str  # 이미 필수
    api_secret_key: str  # 이미 필수
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
```

**확인 사항**:
- `.gitignore`에 `.env` 포함 확인
- `env.example`에는 실제 값 없이 예시만 포함 (✅ 확인됨)

---

### 11. 파일 다운로드 보안
**위치**: `src/api/routers/chat.py:694-726`

**문제점**:
- 파일 ID만으로 다운로드 가능
- 세션 소유권 확인 없음
- Path Traversal 가능성 (상대 경로 사용)

**수정 방안**:
```python
@router.get("/file/{file_id}/download")
async def download_file(
    file_id: int,
    session_id: Optional[str] = None  # 세션 ID 검증 추가
):
    """파일 다운로드"""
    with db_manager.get_db_session() as db_session:
        chat_file = db_session.query(ChatFile).filter(
            ChatFile.id == file_id
        ).first()
        
        if not chat_file:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 세션 소유권 확인
        if session_id and chat_file.session_id != session_id:
            raise HTTPException(status_code=403, detail="파일 접근 권한이 없습니다.")
        
        # Path Traversal 방지
        upload_dir = Path(settings.upload_dir).resolve()
        file_path = (upload_dir / chat_file.file_path).resolve()
        
        # 업로드 디렉토리 밖으로 나가는지 확인
        if not str(file_path).startswith(str(upload_dir)):
            raise HTTPException(status_code=403, detail="잘못된 파일 경로입니다.")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일이 서버에 존재하지 않습니다.")
        
        return FileResponse(...)
```

---

## 🟢 낮음 (Low) - 개선 고려

### 12. HTTPS 강제 없음
**권장사항**:
- 프로덕션 환경에서 HTTPS 강제
- HSTS 헤더 설정
- SSL/TLS 인증서 관리

### 13. 세션 만료 정리 자동화
**위치**: `src/services/session_manager.py:253-274`

**현재 상태**:
- `cleanup_expired_sessions()` 함수는 있지만 자동 실행되지 않음

**권장사항**:
- 백그라운드 태스크로 주기적 실행
- 또는 Celery/APScheduler 사용

### 14. 감사 로그 (Audit Log)
**권장사항**:
- 중요한 작업(세션 생성, 파일 업로드, 데이터 조회)에 대한 감사 로그
- IP 주소, 사용자 정보, 작업 시간 기록

---

## 📋 보안 체크리스트

### 즉시 수정 필요 (Critical)
- [ ] API 인증 적용 (모든 관리자 엔드포인트)
- [ ] 파일 업로드 보안 강화 (확장자, 내용 검증, Path Traversal 방지)
- [ ] 로깅에서 민감 정보 제거

### 우선 수정 권장 (High)
- [ ] 입력 검증 및 XSS 방지
- [ ] CORS 설정 강화 (프로덕션 환경)
- [ ] 에러 메시지 일반화
- [ ] 세션 ID 생성 강화

### 개선 권장 (Medium)
- [ ] Rate Limiting 적용
- [ ] 파일 다운로드 보안 강화
- [ ] 환경 변수 관리 확인

### 개선 고려 (Low)
- [ ] HTTPS 강제
- [ ] 세션 만료 정리 자동화
- [ ] 감사 로그 구현

---

## 🔧 보안 강화 우선순위

1. **1주차 (Critical)**
   - API 인증 적용
   - 파일 업로드 보안 강화
   - 로깅 민감 정보 제거

2. **2주차 (High)**
   - 입력 검증 및 XSS 방지
   - CORS 설정 강화
   - 에러 메시지 일반화

3. **3주차 (Medium)**
   - Rate Limiting 적용
   - 파일 다운로드 보안
   - 환경 변수 관리

4. **4주차 (Low)**
   - HTTPS 강제
   - 세션 만료 자동화
   - 감사 로그

---

## 📚 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security.html)

---

**보고서 작성자**: AI Security Reviewer  
**다음 검토 예정일**: 수정 완료 후 재검토 권장

