# API 채팅 라우터 검토 보고서

## 검토 대상
- 파일: `src/api/routers/chat.py`
- 검토 일자: 2024년
- 검토 범위: 10개 엔드포인트, 요청/응답 검증, 세션 관리, DB 세션 처리

---

## ✅ 정상 동작 부분

### 1. 엔드포인트 구조 (10개)
1. ✅ `POST /start` - 상담 세션 시작
2. ✅ `POST /message` - 사용자 메시지 처리
3. ✅ `POST /end` - 상담 종료
4. ✅ `GET /status` - 현재 상담 상태 조회
5. ✅ `GET /detail` - 세션 상세 정보 조회
6. ✅ `GET /result` - 최종 결과 조회
7. ✅ `POST /upload` - 파일 업로드
8. ✅ `GET /list` - 세션 목록 조회
9. ✅ `GET /files` - 세션 파일 목록 조회
10. ✅ `GET /file/{file_id}/download` - 파일 다운로드

### 2. API 키 인증
- ✅ 9개 엔드포인트에 `Depends(verify_api_key)` 적용
- ⚠️ `/list` 엔드포인트에 인증 없음 (관리자용이라고 하지만)

### 3. 요청/응답 모델
- ✅ Pydantic 모델 사용
- ✅ `ChatStartRequest`에 `model_validator`로 `user_meta` 자동 구성

### 4. DB 세션 관리 (대부분)
- ✅ `with db_manager.get_db_session()` 패턴 사용
- ✅ 컨텍스트 매니저로 자동 정리

### 5. 에러 처리
- ✅ 커스텀 예외 (`SessionNotFoundError`, `InvalidInputError`) 사용
- ✅ 적절한 HTTP 상태 코드

---

## ⚠️ 발견된 문제점

### 1. 파일 업로드 - 파일당 새로운 DB 세션 (Lines 523-535)
```python
for file in files:
    # ... 파일 저장 ...
    
    # DB에 파일 정보 저장
    with db_manager.get_db_session() as db_session:  # 파일마다 새 세션
        chat_file = ChatFile(...)
        db_session.add(chat_file)
        db_session.commit()
```
**영향도**: 중간  
**문제**: 
- 파일마다 새로운 DB 세션 생성
- 트랜잭션 일관성 부족
- 하나의 파일 저장 실패 시 다른 파일은 이미 저장됨

**권장 수정**:
```python
# 모든 파일을 하나의 트랜잭션으로 저장
with db_manager.get_db_session() as db_session:
    for file in files:
        # ... 파일 저장 ...
        
        chat_file = ChatFile(...)
        db_session.add(chat_file)
    
    # 모든 파일 저장 후 한 번에 커밋
    db_session.commit()
```

### 2. 파일 업로드 - 보안 검증 부족 (Lines 493-508)
```python
# 파일 크기 검증만 있음
if file_size > max_file_size:
    raise HTTPException(...)

if file_size == 0:
    raise HTTPException(...)

# 파일 확장자 및 MIME 타입 확인만 (검증 없음)
file_ext = Path(file.filename).suffix.lower()
mime_type, _ = mimetypes.guess_type(file.filename)
```
**영향도**: 높음  
**문제**: 
- 허용된 파일 확장자 검증 없음
- MIME 타입 검증 없음
- 악성 파일 업로드 가능
- 파일명 경로 탐색 공격 가능 (`../` 등)

**권장 수정**:
```python
# 허용된 확장자 목록
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg", "image/png", "text/plain"
}

# 파일 확장자 검증
if file_ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(
        status_code=400,
        detail=f"허용되지 않은 파일 형식입니다: {file_ext}"
    )

# MIME 타입 검증
if mime_type and mime_type not in ALLOWED_MIME_TYPES:
    raise HTTPException(
        status_code=400,
        detail=f"허용되지 않은 MIME 타입입니다: {mime_type}"
    )

# 파일명 정규화 (경로 탐색 방지)
safe_filename = Path(file.filename).name  # 경로 제거
if ".." in safe_filename or "/" in safe_filename or "\\" in safe_filename:
    raise HTTPException(
        status_code=400,
        detail="파일명에 경로 문자가 포함되어 있습니다."
    )
```

### 3. `/list` 엔드포인트 인증 없음 (Line 566)
```python
@router.get("/list")
async def list_sessions(
    limit: int = 50,
    status: Optional[str] = None,
    offset: int = 0
):
    """세션 목록 조회 (관리자용)"""
```
**영향도**: 높음  
**문제**: 
- 관리자용이라고 하지만 인증 없음
- 모든 세션 정보 노출 가능
- 민감한 정보 유출 위험

**권장 수정**:
```python
@router.get("/list")
async def list_sessions(
    limit: int = 50,
    status: Optional[str] = None,
    offset: int = 0,
    _: str = Depends(verify_api_key)  # 인증 추가
):
```

### 4. HTTPException 직접 사용 (에러 핸들러 우회)
**영향도**: 낮음  
**문제**: 
- 일부 엔드포인트에서 `HTTPException` 직접 사용
- 커스텀 예외를 사용하는 것이 더 일관적

**예시** (Lines 153, 156, 159):
```python
except SessionNotFoundError as e:
    logger.error(...)
    raise HTTPException(status_code=404, detail=str(e))  # 예외를 다시 raise하면 에러 핸들러가 처리
```
**현황**: 커스텀 예외를 raise하면 에러 핸들러가 처리하므로 문제 없음  
**권장사항**: `HTTPException` 대신 커스텀 예외를 raise

### 5. 파일 다운로드 - 경로 검증 부족 (Lines 708-709)
```python
upload_dir = Path(settings.upload_dir)
file_path = upload_dir / chat_file.file_path
```
**영향도**: 중간  
**문제**: 
- `chat_file.file_path`에 `../` 포함 가능
- 경로 탐색 공격 가능

**권장 수정**:
```python
upload_dir = Path(settings.upload_dir).resolve()
file_path = (upload_dir / chat_file.file_path).resolve()

# 경로 검증
if not str(file_path).startswith(str(upload_dir)):
    raise HTTPException(
        status_code=403,
        detail="접근할 수 없는 파일 경로입니다."
    )
```

### 6. 입력 검증 - limit/offset 제한 없음 (Lines 568-570)
```python
async def list_sessions(
    limit: int = 50,
    status: Optional[str] = None,
    offset: int = 0
):
```
**영향도**: 낮음  
**문제**: 
- `limit`에 최대값 제한 없음 (메모리 부족 가능)
- 음수 값 허용 가능

**권장 수정**:
```python
from pydantic import Field

async def list_sessions(
    limit: int = Field(default=50, ge=1, le=1000),
    status: Optional[str] = None,
    offset: int = Field(default=0, ge=0)
):
```

### 7. 에러 로깅 일관성
**영향도**: 낮음  
**현황**: 
- 일부는 `exc_info=True` 사용
- 일부는 사용하지 않음

**권장사항**: 모든 예외 로깅에 `exc_info=True` 추가

---

## 🔍 추가 검토 사항

### 1. 세션 상태 관리
- ✅ `load_session_state`, `save_session_state` 사용
- ✅ 상태 일관성 유지

### 2. LangGraph 통합
- ✅ `run_graph_step` 사용
- ✅ 상태 전이 적절

### 3. 파일 저장 경로
- ✅ 세션별 디렉토리 분리
- ✅ 고유 파일명 생성

### 4. 응답 형식
- ✅ `success_response` 유틸리티 사용
- ✅ 일관된 응답 형식

---

## 📊 종합 평가

### 강점
1. ✅ 10개 엔드포인트 체계적 구현
2. ✅ 대부분의 엔드포인트에 인증 적용
3. ✅ Pydantic 모델로 요청/응답 검증
4. ✅ DB 세션 관리 대부분 적절
5. ✅ 커스텀 예외 활용

### 개선 필요
1. 🔴 **높음**: `/list` 엔드포인트 인증 추가
2. 🔴 **높음**: 파일 업로드 보안 검증 강화
3. 🟡 **중간**: 파일 업로드 DB 세션 통합
4. 🟡 **중간**: 파일 다운로드 경로 검증
5. 🟢 **낮음**: 입력 검증 강화

### 우선순위
- **높음**: `/list` 인증 추가, 파일 업로드 보안 강화
- **중간**: 파일 업로드 DB 세션 통합, 파일 다운로드 경로 검증
- **낮음**: 입력 검증 강화, 에러 로깅 일관성

---

## 📝 권장 수정 사항

### 수정 1: `/list` 엔드포인트 인증 추가
```python
@router.get("/list")
async def list_sessions(
    limit: int = Field(default=50, ge=1, le=1000),
    status: Optional[str] = None,
    offset: int = Field(default=0, ge=0),
    _: str = Depends(verify_api_key)  # 추가
):
```

### 수정 2: 파일 업로드 보안 강화
```python
# 파일 확장자 및 MIME 타입 허용 목록
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg", "image/png", "text/plain"
}

for file in files:
    # 파일명 정규화
    safe_filename = Path(file.filename).name
    if ".." in safe_filename or "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(
            status_code=400,
            detail="파일명에 경로 문자가 포함되어 있습니다."
        )
    
    # 파일 확장자 검증
    file_ext = Path(safe_filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않은 파일 형식입니다: {file_ext}"
        )
    
    # MIME 타입 검증
    mime_type, _ = mimetypes.guess_type(safe_filename)
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않은 MIME 타입입니다: {mime_type}"
        )
    
    # ... 나머지 로직 ...
```

### 수정 3: 파일 업로드 DB 세션 통합
```python
# 모든 파일을 하나의 트랜잭션으로 저장
with db_manager.get_db_session() as db_session:
    for file in files:
        # ... 파일 저장 로직 ...
        
        chat_file = ChatFile(
            session_id=session_id,
            file_name=safe_filename,
            file_path=str(file_path.relative_to(upload_dir)),
            file_size=file_size,
            file_type=mime_type or "application/octet-stream",
            file_extension=file_ext,
            description=description
        )
        db_session.add(chat_file)
    
    # 모든 파일 저장 후 한 번에 커밋
    db_session.commit()
    
    # 업로드된 파일 정보 조회
    for chat_file in db_session.query(ChatFile).filter(
        ChatFile.session_id == session_id
    ).order_by(ChatFile.uploaded_at.desc()).limit(len(files)).all():
        uploaded_files.append({
            "id": chat_file.id,
            "file_name": chat_file.file_name,
            # ...
        })
```

### 수정 4: 파일 다운로드 경로 검증
```python
@router.get("/file/{file_id}/download")
async def download_file(file_id: int, _: str = Depends(verify_api_key)):
    """파일 다운로드"""
    try:
        with db_manager.get_db_session() as db_session:
            chat_file = db_session.query(ChatFile).filter(
                ChatFile.id == file_id
            ).first()
            
            if not chat_file:
                raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
            
            # 경로 검증
            upload_dir = Path(settings.upload_dir).resolve()
            file_path = (upload_dir / chat_file.file_path).resolve()
            
            # 경로 탐색 공격 방지
            if not str(file_path).startswith(str(upload_dir)):
                raise HTTPException(
                    status_code=403,
                    detail="접근할 수 없는 파일 경로입니다."
                )
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")
            
            return FileResponse(
                path=str(file_path),
                filename=chat_file.file_name,
                media_type=chat_file.file_type
            )
    # ...
```

---

## ✅ 검토 완료

**검토 항목**: `review_05_api_chat_router`  
**상태**: 완료  
**다음 항목**: `review_06_api_rag_router`

