# 보안 검토 보고서

## 검토 대상
- 전체 시스템 보안
- 검토 일자: 2024년
- 검토 범위: 인증/인가, 입력 검증, SQL 인젝션 방지, XSS 방지, 민감 정보 처리

---

## ✅ 정상 동작 부분

### 1. 인증/인가
- ✅ API 키 인증: 모든 엔드포인트에 `verify_api_key` 적용
- ✅ HTTP Bearer 토큰 사용: 표준 인증 방식
- ✅ 인증 실패 시 적절한 HTTP 401 응답

### 2. SQL 인젝션 방지
- ✅ SQLAlchemy ORM 사용: 파라미터화된 쿼리로 대부분 방어됨
- ✅ 사용자 입력이 직접 쿼리에 포함되지 않음

### 3. 민감 정보 처리
- ✅ 개인정보 마스킹 함수 존재: `mask_sensitive_info()` (전화번호, 이메일, 주민등록번호)
- ✅ API 키 로깅 시 마스킹: `token[:10]...` 형식으로 일부만 로깅

### 4. 파일 업로드
- ✅ 파일 크기 검증: `max_file_size_mb` 설정으로 제한
- ✅ 세션 검증: 업로드 전 세션 존재 확인

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 입력 검증 및 XSS 방지 부족

**문제**: 사용자 입력(`user_message`)에 대한 길이 제한이나 XSS 방지 처리가 없습니다.

**영향도**: 중간  
**위험성**: 
- XSS 공격 가능 (프론트엔드에서 HTML 렌더링 시)
- 대용량 입력으로 서버 리소스 고갈 (DoS 공격)
- 악성 스크립트 주입 가능

**현재 상황**:
- `ChatMessageRequest` 모델에 길이 제한 없음
- 사용자 입력이 그대로 처리됨 (이스케이프 없음)

**수정 권장**: 
```python
# src/api/routers/chat.py
from html import escape

MAX_MESSAGE_LENGTH = 5000  # 상수 정의

@router.post("/message")
async def process_message(request: ChatMessageRequest, _: str = Depends(verify_api_key)):
    # 입력 길이 검증
    if len(request.user_message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"메시지는 {MAX_MESSAGE_LENGTH}자를 초과할 수 없습니다."
        )
    
    # XSS 방지: HTML 이스케이프 (필요시)
    # sanitized_message = escape(request.user_message)
    # 또는 사용자 입력을 그대로 사용 (백엔드 처리이므로 선택적)
    
    state["last_user_input"] = request.user_message
    ...
```

---

### 2. 🟡 **중간**: 파일 업로드 보안 취약점

**문제**: 
1. 파일 확장자 검증 부족
2. Path Traversal 취약점 가능성
3. 파일 내용 검증 없음 (MIME 타입만 신뢰)

**영향도**: 중간  
**위험성**: 
- 악성 파일 업로드 가능 (실행 파일, 스크립트)
- Path Traversal을 통한 임의 파일 접근
- 서버 측 스크립트 실행 가능

**현재 상황**:
- 파일 크기 검증만 있음
- 확장자 검증 없음
- `file.filename`을 직접 사용

**수정 권장**: 
```python
# 허용된 확장자 목록
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt'}

@router.post("/upload")
async def upload_file(...):
    for file in files:
        # 파일명 정규화 (Path Traversal 방지)
        safe_filename = Path(file.filename).name  # 경로 제거
        
        # 확장자 검증
        file_ext = Path(safe_filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"허용되지 않은 파일 형식입니다: {file_ext}"
            )
        
        # 파일명 안전하게 생성 (UUID 사용 권장)
        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = session_upload_dir / safe_filename
        ...
```

---

### 3. 🟢 **낮음**: CORS 설정이 너무 관대함

**문제**: 
- `allow_methods=["*"]`, `allow_headers=["*"]`로 모든 메서드/헤더 허용
- 프로덕션 환경에서도 개발 환경용 설정 사용 가능

**영향도**: 낮음  
**위험성**: 
- 불필요한 HTTP 메서드 허용
- 프로덕션 환경에서 보안 취약점

**현재 상황**:
```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # 환경 변수로 제어
    allow_credentials=True,
    allow_methods=["*"],  # 모든 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)
```

**수정 권장**: 
```python
# 프로덕션 환경에서는 제한적 설정
if settings.environment == "production":
    allow_methods = ["GET", "POST"]
    allow_headers = ["Content-Type", "Authorization"]
else:
    allow_methods = ["*"]
    allow_headers = ["*"]
```

---

### 4. 🟢 **낮음**: Rate Limiting 부재

**문제**: API 요청에 대한 Rate Limiting이 없습니다.

**영향도**: 낮음  
**위험성**: 
- DoS 공격 가능
- API 남용 가능

**현재 상황**:
- `settings.rate_limit_per_minute` 설정은 있지만 실제 적용되지 않음

**수정 권장**: 
```python
# slowapi 사용
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/message")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def process_message(...):
    ...
```

---

### 5. 🟢 **낮음**: 로그에 민감 정보 노출 가능성

**문제**: 로그에 사용자 입력이나 세션 정보가 그대로 기록될 수 있습니다.

**영향도**: 낮음  
**위험성**: 
- 로그 파일에 개인정보 노출
- 로그 유출 시 개인정보 침해

**현재 상황**:
- `mask_sensitive_info()` 함수는 있지만 로그에 자동 적용되지 않음
- 사용자 입력이 로그에 그대로 기록됨

**수정 권장**: 
```python
# 로그 메시지에서 민감 정보 제거
def sanitize_log_message(message: str) -> str:
    """로그 메시지에서 민감 정보 제거"""
    # 개인정보 마스킹
    message = mask_sensitive_info(message)
    
    # API 키 마스킹
    message = re.sub(
        r'(api[_\s]*key|secret[_\s]*key)[_\s]*[:=]\s*(\S+)', 
        r'\1=***', 
        message, 
        flags=re.IGNORECASE
    )
    return message

# 로거에서 사용
logger.info(sanitize_log_message(f"메시지 처리: {user_message}"))
```

---

### 6. 🟢 **낮음**: 파일 다운로드 보안

**문제**: 파일 ID만으로 다운로드 가능하며, 세션 소유권 확인이 없습니다.

**영향도**: 낮음  
**위험성**: 
- 다른 사용자의 파일 다운로드 가능
- 세션 ID만 알면 모든 파일 접근 가능

**현재 상황**:
- 파일 ID로만 다운로드 가능
- 세션 소유권 확인 없음

**수정 권장**: 
```python
@router.get("/file/{file_id}/download")
async def download_file(file_id: int, session_id: str, _: str = Depends(verify_api_key)):
    """파일 다운로드 (세션 소유권 확인)"""
    with db_manager.get_db_session() as db_session:
        file = db_session.query(ChatFile).filter(
            ChatFile.id == file_id,
            ChatFile.session_id == session_id  # 세션 소유권 확인
        ).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        ...
```

---

### 7. 🟢 **낮음**: 환경 변수 관리

**문제**: 
- `.env` 파일이 `.gitignore`에 포함되어 있는지 확인 필요
- 환경 변수 기본값에 하드코딩된 값 존재

**영향도**: 낮음  
**수정 권장**: 
- `.gitignore`에 `.env` 포함 확인
- 프로덕션 환경에서는 환경 변수 필수로 설정

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 2개 (입력 검증/XSS 방지, 파일 업로드 보안)
- 🟢 **낮음**: 5개 (CORS 설정, Rate Limiting, 로그 민감 정보, 파일 다운로드, 환경 변수)

### 우선순위별 수정 권장
1. 🟡 **중간**: 입력 검증 및 XSS 방지 추가 (권장)
2. 🟡 **중간**: 파일 업로드 보안 강화 (권장)
3. 🟢 **낮음**: Rate Limiting 적용 (선택적)
4. 🟢 **낮음**: CORS 설정 개선 (선택적)
5. 🟢 **낮음**: 로그 민감 정보 처리 (선택적)
6. 🟢 **낮음**: 파일 다운로드 보안 강화 (선택적)
7. 🟢 **낮음**: 환경 변수 관리 확인 (선택적)

---

## 🔧 수정 제안

### 수정 1: 입력 검증 추가

#### `src/api/routers/chat.py` 수정
```python
from src.utils.constants import Limits

MAX_MESSAGE_LENGTH = 10000  # 또는 Limits에 추가

@router.post("/message")
async def process_message(request: ChatMessageRequest, _: str = Depends(verify_api_key)):
    """사용자 메시지 처리"""
    # 입력 길이 검증
    if len(request.user_message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"메시지는 {MAX_MESSAGE_LENGTH}자를 초과할 수 없습니다."
        )
    
    # 빈 메시지 검증
    if not request.user_message.strip():
        raise HTTPException(
            status_code=400,
            detail="메시지가 비어있습니다."
        )
    
    # ... 기존 로직 ...
```

---

### 수정 2: 파일 업로드 보안 강화

#### `src/api/routers/chat.py` 수정
```python
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt', '.xlsx', '.xls'}

@router.post("/upload")
async def upload_file(...):
    for file in files:
        # 파일명 정규화 (Path Traversal 방지)
        original_filename = file.filename
        safe_filename = Path(original_filename).name  # 경로 제거
        
        # 확장자 검증
        file_ext = Path(safe_filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"허용되지 않은 파일 형식입니다: {file_ext}. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 안전한 파일명 생성 (UUID 사용)
        safe_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = session_upload_dir / safe_filename
        
        # 파일 저장
        with open(file_path, 'wb') as f:
            f.write(file_content)
        ...
```

---

### 수정 3: Rate Limiting 적용 (선택적)

#### `requirements.txt`에 추가
```
slowapi>=0.1.9
```

#### `src/api/main.py` 수정
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

#### `src/api/routers/chat.py` 수정
```python
from fastapi import Request
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/message")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def process_message(
    request: Request,
    chat_request: ChatMessageRequest,
    _: str = Depends(verify_api_key)
):
    ...
```

---

## ✅ 결론

전체 시스템 보안은 전반적으로 잘 구성되어 있지만, **입력 검증**과 **파일 업로드 보안** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: 입력 검증 및 XSS 방지 추가 (권장)
2. 🟡 **중간**: 파일 업로드 보안 강화 (권장)
3. 🟢 **낮음**: Rate Limiting 적용 (선택적)
4. 🟢 **낮음**: CORS 설정 개선 (선택적)
5. 🟢 **낮음**: 로그 민감 정보 처리 (선택적)
6. 🟢 **낮음**: 파일 다운로드 보안 강화 (선택적)
7. 🟢 **낮음**: 환경 변수 관리 확인 (선택적)

**참고**: 
- SQL 인젝션 방지는 SQLAlchemy ORM 사용으로 잘 방어됨
- 인증/인가는 모든 엔드포인트에 적용되어 있음
- 개인정보 마스킹 함수가 존재하나 로그에 자동 적용되지 않음

