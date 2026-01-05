# API RAG 라우터 검토 보고서

## 검토 대상
- 파일: `src/api/routers/rag.py`
- 검토 일자: 2024년
- 검토 범위: 문서 인덱싱, 검색 상태, 백그라운드 작업 처리

---

## ✅ 정상 동작 부분

### 1. 엔드포인트 구조 (3개)
1. ✅ `POST /index` - 문서 인덱싱 시작
2. ✅ `GET /status` - 인덱싱 상태 조회
3. ✅ `DELETE /index` - 인덱스 초기화

### 2. API 키 인증
- ✅ 모든 엔드포인트에 `Depends(verify_api_key)` 적용

### 3. 백그라운드 작업 처리 (Lines 96-143)
```python
background_tasks.add_task(
    _index_documents,
    clear_existing=request.clear_existing,
    directory=str(rag_dir) if request.directory else None
)
```
- ✅ FastAPI의 `BackgroundTasks` 사용
- ✅ 인덱싱이 오래 걸려도 즉시 응답 반환

### 4. 중복 인덱싱 방지 (Lines 114-118)
```python
if _indexing_status["is_indexing"]:
    raise HTTPException(
        status_code=409,
        detail="이미 인덱싱이 진행 중입니다. 잠시 후 다시 시도해주세요."
    )
```
- ✅ 동시 인덱싱 방지

### 5. 인덱싱 상태 조회 (Lines 146-168)
- ✅ 실시간 Chunk 개수 확인
- ✅ 인덱싱 진행 상태 반환

### 6. 인덱스 초기화 시 인덱싱 중 체크 (Lines 181-185)
- ✅ 인덱싱 중에는 초기화 불가

---

## ⚠️ 발견된 문제점

### 1. 전역 변수로 상태 관리 - 동시성 문제 (Lines 47-52)
```python
# 전역 인덱싱 상태 관리
_indexing_status = {
    "is_indexing": False,
    "last_indexed": None,
    "total_chunks": None
}
```
**영향도**: 높음  
**문제**: 
- 멀티프로세스 환경에서 상태 공유 불가
- 멀티스레드 환경에서 Race condition 가능
- 서버 재시작 시 상태 손실
- 여러 서버 인스턴스 간 상태 불일치

**권장 수정**:
- Redis 또는 DB에 상태 저장
- 또는 파일 기반 상태 저장
- 또는 단일 프로세스에서만 사용 (문서화)

### 2. 디렉토리 경로 검증 부족 (Lines 121-130)
```python
if request.directory:
    rag_dir = Path(request.directory)
else:
    rag_dir = Path(__file__).parent.parent.parent.parent / "data" / "rag"
```
**영향도**: 높음  
**문제**: 
- 경로 탐색 공격 가능 (`../../../etc/passwd`)
- 임의의 디렉토리 접근 가능
- 시스템 파일 노출 위험

**권장 수정**:
```python
if request.directory:
    rag_dir = Path(request.directory).resolve()
    
    # 허용된 디렉토리 경로 검증
    allowed_base = Path(__file__).parent.parent.parent.parent / "data"
    allowed_base = allowed_base.resolve()
    
    # 경로 탐색 공격 방지
    try:
        rag_dir.relative_to(allowed_base)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="허용되지 않은 디렉토리 경로입니다."
        )
else:
    rag_dir = allowed_base / "rag"
```

### 3. 백그라운드 작업 에러 처리 (Lines 90-93)
```python
except Exception as e:
    _indexing_status["is_indexing"] = False
    logger.error(f"인덱싱 실패: {str(e)}", exc_info=True)
    raise
```
**영향도**: 중간  
**문제**: 
- `raise`만 하고 있어 에러가 무시될 수 있음
- 백그라운드 작업의 예외는 클라이언트에 전달되지 않음
- 에러 상태를 추적할 방법 없음

**권장 수정**:
```python
except Exception as e:
    _indexing_status["is_indexing"] = False
    _indexing_status["error"] = str(e)  # 에러 상태 추가
    _indexing_status["error_time"] = datetime.utcnow().isoformat()
    logger.error(f"인덱싱 실패: {str(e)}", exc_info=True)
    # raise하지 않고 에러 상태만 저장
```

### 4. 응답 형식 일관성 (Lines 197-200)
```python
return {
    "success": True,
    "message": "인덱스가 초기화되었습니다."
}
```
**영향도**: 낮음  
**문제**: 
- 다른 엔드포인트는 `IndexResponse` 모델 사용
- `success_response` 유틸리티 사용 안 함

**권장 수정**:
```python
return success_response({
    "message": "인덱스가 초기화되었습니다."
})
```

### 5. 인덱싱 상태 Race Condition (Lines 60, 84, 91)
```python
_indexing_status["is_indexing"] = True  # Line 60
# ...
_indexing_status["is_indexing"] = False  # Line 84, 91
```
**영향도**: 중간  
**문제**: 
- 멀티스레드 환경에서 동시 수정 가능
- `is_indexing` 체크와 설정 사이에 Race condition

**권장 수정**:
```python
import threading

_indexing_lock = threading.Lock()

def _index_documents(clear_existing: bool, directory: Optional[str] = None):
    global _indexing_status
    
    with _indexing_lock:
        if _indexing_status["is_indexing"]:
            logger.warning("이미 인덱싱이 진행 중입니다.")
            return
        
        _indexing_status["is_indexing"] = True
    
    try:
        # ... 인덱싱 로직 ...
    finally:
        with _indexing_lock:
            _indexing_status["is_indexing"] = False
```

### 6. 디렉토리 경로 하드코딩 (Lines 66, 124)
```python
rag_dir = Path(__file__).parent.parent.parent.parent / "data" / "rag"
```
**영향도**: 낮음  
**문제**: 
- 상대 경로 계산이 복잡하고 오류 가능
- 설정 파일에서 관리하는 것이 더 나음

**권장 수정**:
```python
from config.settings import settings

rag_dir = Path(settings.rag_data_directory or "./data/rag")
```

### 7. 사용되지 않는 import (Line 6)
```python
from typing import Optional, Dict, Any
```
**영향도**: 낮음  
**문제**: `Dict`, `Any`가 사용되지 않음

### 8. 에러 상태 추적 없음
**영향도**: 중간  
**문제**: 
- 인덱싱 실패 시 에러 정보를 조회할 방법 없음
- `/status` 엔드포인트에 에러 정보 포함 필요

**권장 수정**:
```python
class IndexStatusResponse(BaseModel):
    is_indexing: bool
    last_indexed: Optional[str] = None
    total_chunks: Optional[int] = None
    error: Optional[str] = None  # 에러 메시지 추가
    error_time: Optional[str] = None  # 에러 발생 시간 추가
```

---

## 🔍 추가 검토 사항

### 1. 인덱싱 진행률 추적
- 현재: 진행률 정보 없음
- 권장: 현재 처리 중인 파일, 진행률(%) 추가

### 2. 인덱싱 취소 기능
- 현재: 취소 불가
- 권장: 인덱싱 취소 엔드포인트 추가

### 3. 인덱싱 이력 관리
- 현재: 마지막 인덱싱 시간만 저장
- 권장: 인덱싱 이력 DB 저장

### 4. 백그라운드 작업 모니터링
- 현재: FastAPI BackgroundTasks 사용 (제한적)
- 권장: Celery 등 작업 큐 시스템 고려

---

## 📊 종합 평가

### 강점
1. ✅ 3개 엔드포인트 체계적 구현
2. ✅ 모든 엔드포인트에 인증 적용
3. ✅ 백그라운드 작업으로 비동기 처리
4. ✅ 중복 인덱싱 방지
5. ✅ 인덱싱 상태 조회 기능

### 개선 필요
1. 🔴 **높음**: 전역 변수 상태 관리 → Redis/DB 저장
2. 🔴 **높음**: 디렉토리 경로 검증 강화
3. 🟡 **중간**: 백그라운드 작업 에러 처리 개선
4. 🟡 **중간**: Race condition 방지 (Lock 사용)
5. 🟢 **낮음**: 응답 형식 일관성, import 정리

### 우선순위
- **높음**: 상태 관리 개선, 경로 검증 강화
- **중간**: 에러 처리 개선, Race condition 방지
- **낮음**: 응답 형식 일관성, import 정리

---

## 📝 권장 수정 사항

### 수정 1: 상태 관리를 Redis/DB로 변경
```python
# Redis 사용 예시
import redis
from config.settings import settings

redis_client = redis.Redis.from_url(settings.redis_url) if hasattr(settings, 'redis_url') else None

def get_indexing_status():
    """인덱싱 상태 조회"""
    if redis_client:
        return {
            "is_indexing": redis_client.get("rag:is_indexing") == b"true",
            "last_indexed": redis_client.get("rag:last_indexed").decode() if redis_client.get("rag:last_indexed") else None,
            "total_chunks": int(redis_client.get("rag:total_chunks") or 0)
        }
    else:
        # 폴백: 전역 변수 사용
        return _indexing_status

def set_indexing_status(key: str, value: Any):
    """인덱싱 상태 설정"""
    if redis_client:
        if value is None:
            redis_client.delete(f"rag:{key}")
        else:
            redis_client.set(f"rag:{key}", str(value))
    else:
        _indexing_status[key] = value
```

### 수정 2: 디렉토리 경로 검증 강화
```python
from pathlib import Path
from config.settings import settings

ALLOWED_BASE_DIRS = [
    Path(settings.rag_data_directory or "./data/rag").resolve(),
    Path("./data/rag").resolve()
]

def validate_directory_path(directory: Optional[str]) -> Path:
    """디렉토리 경로 검증"""
    if directory:
        rag_dir = Path(directory).resolve()
        
        # 허용된 디렉토리인지 확인
        is_allowed = any(
            str(rag_dir).startswith(str(base_dir))
            for base_dir in ALLOWED_BASE_DIRS
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"허용되지 않은 디렉토리 경로입니다: {directory}"
            )
        
        if not rag_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"디렉토리를 찾을 수 없습니다: {rag_dir}"
            )
        
        return rag_dir
    else:
        # 기본 디렉토리
        rag_dir = ALLOWED_BASE_DIRS[0]
        if not rag_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"기본 RAG 디렉토리를 찾을 수 없습니다: {rag_dir}"
            )
        return rag_dir
```

### 수정 3: Race Condition 방지
```python
import threading

_indexing_lock = threading.Lock()

def _index_documents(clear_existing: bool, directory: Optional[str] = None):
    """백그라운드에서 문서 인덱싱 수행"""
    global _indexing_status
    
    # Lock으로 동시 실행 방지
    with _indexing_lock:
        if _indexing_status["is_indexing"]:
            logger.warning("이미 인덱싱이 진행 중입니다.")
            return
        
        _indexing_status["is_indexing"] = True
        _indexing_status["error"] = None
        _indexing_status["error_time"] = None
    
    try:
        # ... 인덱싱 로직 ...
    except Exception as e:
        with _indexing_lock:
            _indexing_status["is_indexing"] = False
            _indexing_status["error"] = str(e)
            _indexing_status["error_time"] = datetime.utcnow().isoformat()
        logger.error(f"인덱싱 실패: {str(e)}", exc_info=True)
    else:
        with _indexing_lock:
            _indexing_status["is_indexing"] = False
            _indexing_status["last_indexed"] = datetime.utcnow().isoformat()
            _indexing_status["total_chunks"] = total_chunks
```

### 수정 4: 에러 상태 포함
```python
class IndexStatusResponse(BaseModel):
    is_indexing: bool
    last_indexed: Optional[str] = None
    total_chunks: Optional[int] = None
    error: Optional[str] = None
    error_time: Optional[str] = None

# _indexing_status에 error, error_time 추가
_indexing_status = {
    "is_indexing": False,
    "last_indexed": None,
    "total_chunks": None,
    "error": None,
    "error_time": None
}
```

### 수정 5: 응답 형식 일관성
```python
@router.delete("/index")
async def clear_index(_: str = Depends(verify_api_key)):
    """RAG 문서 인덱스 초기화"""
    # ...
    return success_response({
        "message": "인덱스가 초기화되었습니다."
    })
```

---

## ✅ 검토 완료

**검토 항목**: `review_06_api_rag_router`  
**상태**: 완료  
**다음 항목**: `review_07_langgraph_state`

