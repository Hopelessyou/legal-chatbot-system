# Service GPT Logger 검토 보고서

## 검토 대상
- 파일: `src/services/gpt_logger.py`
- 검토 일자: 2024년
- 검토 범위: GPT 호출 로깅, DB 저장, 타이밍 측정

---

## ✅ 정상 동작 부분

### 1. DB 세션 관리 (Lines 39-50)
```python
if db_session is None:
    with db_manager.get_db_session() as session:
        GPTLogger._save_log(...)
else:
    GPTLogger._save_log(db_session, ...)
```
- ✅ 외부 세션 전달 지원
- ✅ 세션 자동 생성 지원
- ✅ 컨텍스트 매니저 사용

### 2. 타이밍 측정 헬퍼 (Lines 79-112)
```python
def log_with_timing(...):
    latency_ms = int((time.time() - start_time) * 1000)
    token_input = usage.get("prompt_tokens", 0)
    token_output = usage.get("completion_tokens", 0)
    GPTLogger.log_api_call(...)
```
- ✅ 시간 측정 자동화
- ✅ usage 딕셔너리에서 토큰 추출
- ✅ 밀리초 단위 변환

### 3. 에러 처리 (Lines 52-53)
```python
except Exception as e:
    logger.error(f"GPT API 로그 저장 실패: {str(e)}")
```
- ✅ 로그 저장 실패 시 예외 처리
- ✅ 에러 로깅

### 4. 전역 인스턴스 (Line 116)
```python
gpt_logger = GPTLogger()
```
- ✅ 싱글톤 패턴

---

## ⚠️ 발견된 문제점

### 1. 실제 사용되지 않음
**영향도**: 높음  
**문제**: 
- 코드베이스 전체에서 `gpt_logger`가 실제로 호출되는 곳을 찾을 수 없음
- `gpt_client.py`에서 로깅이 없음
- 다른 서비스들(`entity_extractor`, `summarizer`, `fact_emotion_splitter` 등)에서도 사용되지 않음

**권장 수정**:
- `gpt_client.py`의 `chat_completion`과 `embedding` 메서드에서 로깅 추가
- 또는 데코레이터 패턴으로 자동 로깅 구현

### 2. DB 트랜잭션 롤백 문제
**영향도**: 높음  
**문제**: 
- `_save_log`에서 `session.commit()`을 즉시 호출
- 외부 트랜잭션 내에서 호출 시 부분 커밋 발생 가능
- 트랜잭션 일관성 깨짐

**현재 코드**:
```python
def _save_log(...):
    log_entry = AIProcessLog(...)
    session.add(log_entry)
    session.commit()  # 즉시 커밋
```

**권장 수정**:
```python
def _save_log(..., auto_commit: bool = True):
    """로그 저장 (내부 함수)"""
    log_entry = AIProcessLog(...)
    session.add(log_entry)
    
    if auto_commit:
        session.commit()
    # 외부 세션이면 auto_commit=False로 호출하여 외부에서 커밋
```

또는:
```python
def log_api_call(..., db_session: Optional[Session] = None, auto_commit: bool = None):
    """
    auto_commit: None이면 db_session이 None일 때만 True
    """
    if db_session is None:
        auto_commit = True
        with db_manager.get_db_session() as session:
            GPTLogger._save_log(..., session, auto_commit=True)
    else:
        if auto_commit is None:
            auto_commit = False  # 외부 세션은 기본적으로 커밋하지 않음
        GPTLogger._save_log(..., db_session, auto_commit=auto_commit)
```

### 3. 에러 발생 시 조용히 실패
**영향도**: 중간  
**문제**: 
- 로그 저장 실패 시 예외를 잡아서 로깅만 하고 계속 진행
- 로그 저장 실패가 중요한 문제일 수 있지만 호출자에게 알리지 않음

**현재 코드**:
```python
except Exception as e:
    logger.error(f"GPT API 로그 저장 실패: {str(e)}")
    # 예외를 다시 발생시키지 않음
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"GPT API 로그 저장 실패: {str(e)}", exc_info=True)
    # 선택적: 중요한 로그인 경우 예외 재발생
    # raise
```

또는 옵션으로:
```python
def log_api_call(..., raise_on_error: bool = False):
    try:
        ...
    except Exception as e:
        logger.error(f"GPT API 로그 저장 실패: {str(e)}", exc_info=True)
        if raise_on_error:
            raise
```

### 4. 파라미터 검증 없음
**영향도**: 중간  
**문제**: 
- `session_id`, `node_name`, `model` 등 필수 파라미터 검증 없음
- `token_input`, `token_output`, `latency_ms`가 음수일 수 있음

**권장 수정**:
```python
def log_api_call(
    session_id: str,
    node_name: str,
    model: str,
    token_input: int,
    token_output: int,
    latency_ms: int,
    db_session: Optional[Session] = None
):
    if not session_id:
        raise ValueError("session_id는 필수입니다.")
    if not node_name:
        raise ValueError("node_name은 필수입니다.")
    if not model:
        raise ValueError("model은 필수입니다.")
    if token_input < 0:
        raise ValueError(f"token_input은 0 이상이어야 합니다: {token_input}")
    if token_output < 0:
        raise ValueError(f"token_output은 0 이상이어야 합니다: {token_output}")
    if latency_ms < 0:
        raise ValueError(f"latency_ms는 0 이상이어야 합니다: {latency_ms}")
    ...
```

### 5. `usage` 딕셔너리 키 검증 없음
**영향도**: 낮음  
**문제**: 
- `log_with_timing`에서 `usage.get("prompt_tokens", 0)` 사용
- `usage`가 None이거나 잘못된 형식일 경우 처리 없음

**현재 코드**:
```python
token_input = usage.get("prompt_tokens", 0)
token_output = usage.get("completion_tokens", 0)
```

**권장 수정**:
```python
def log_with_timing(..., usage: Dict[str, int], ...):
    if not isinstance(usage, dict):
        raise TypeError(f"usage는 딕셔너리여야 합니다: {type(usage)}")
    
    token_input = usage.get("prompt_tokens", 0)
    token_output = usage.get("completion_tokens", 0)
    
    if not isinstance(token_input, int) or token_input < 0:
        token_input = 0
    if not isinstance(token_output, int) or token_output < 0:
        token_output = 0
    ...
```

### 6. `start_time` 검증 없음
**영향도**: 낮음  
**문제**: 
- `start_time`이 미래 시간이거나 잘못된 값일 경우 음수 `latency_ms` 발생 가능

**권장 수정**:
```python
def log_with_timing(..., start_time: float, ...):
    import time
    current_time = time.time()
    
    if start_time > current_time:
        logger.warning(f"start_time이 현재 시간보다 미래입니다: {start_time} > {current_time}")
        latency_ms = 0
    else:
        latency_ms = int((current_time - start_time) * 1000)
    ...
```

### 7. 로깅 레벨 부적절
**영향도**: 낮음  
**문제**: 
- 로그 저장 성공 시 로깅 없음
- 디버깅 시 추적 어려움

**권장 수정**:
```python
def _save_log(...):
    log_entry = AIProcessLog(...)
    session.add(log_entry)
    session.commit()
    logger.debug(f"GPT API 로그 저장 완료: session_id={session_id}, node={node_name}, tokens={token_input+token_output}")
```

### 8. `time` 모듈 임포트 위치
**영향도**: 낮음  
**문제**: 
- `log_with_timing` 내부에서 `import time` 사용
- 파일 상단에서 임포트하는 것이 일반적

**현재 코드**:
```python
def log_with_timing(...):
    import time
    latency_ms = int((time.time() - start_time) * 1000)
```

**권장 수정**:
```python
import time
from typing import Dict, Any, Optional
...
```

### 9. 추가 정보 부족
**영향도**: 낮음  
**문제**: 
- 에러 정보, 프롬프트 길이, 응답 길이 등 추가 정보 없음
- 비용 분석이나 성능 분석에 제한적

**권장 수정**:
- `AIProcessLog` 모델에 추가 필드 고려:
  - `error_message`: 에러 발생 시 메시지
  - `prompt_length`: 프롬프트 문자 수
  - `response_length`: 응답 문자 수
  - `cost_estimate`: 예상 비용 (선택적)

### 10. 배치 로깅 미지원
**영향도**: 낮음  
**문제**: 
- 여러 API 호출을 한 번에 로깅하는 기능 없음
- 성능 최적화 기회 상실

**권장 수정**:
```python
@staticmethod
def log_batch_api_calls(
    logs: List[Dict[str, Any]],
    db_session: Optional[Session] = None
):
    """
    여러 API 호출 로그를 배치로 저장
    
    Args:
        logs: 로그 딕셔너리 리스트
        db_session: DB 세션
    """
    try:
        if db_session is None:
            with db_manager.get_db_session() as session:
                _save_batch_logs(session, logs)
        else:
            _save_batch_logs(db_session, logs)
    except Exception as e:
        logger.error(f"배치 로그 저장 실패: {str(e)}", exc_info=True)

def _save_batch_logs(session: Session, logs: List[Dict[str, Any]]):
    log_entries = [
        AIProcessLog(**log) for log in logs
    ]
    session.add_all(log_entries)
    session.commit()
```

---

## 🔍 추가 검토 사항

### 1. 실제 사용 여부 확인
- 코드베이스 전체에서 `gpt_logger` 호출 위치 확인
- 사용되지 않는다면 통합 필요

### 2. 성능 영향
- 로그 저장이 동기적으로 수행됨
- 고빈도 호출 시 성능 저하 가능
- 비동기 로깅 또는 배치 로깅 고려

### 3. 데이터 보존 정책
- 오래된 로그 삭제 정책
- 로그 아카이빙 전략

### 4. 모니터링 및 알림
- 토큰 사용량 임계값 초과 시 알림
- 평균 응답 시간 모니터링
- 에러율 추적

---

## 📊 종합 평가

### 강점
1. ✅ 간단하고 명확한 인터페이스
2. ✅ DB 세션 관리 유연성
3. ✅ 타이밍 측정 헬퍼 제공
4. ✅ 에러 처리 기본 구현

### 개선 필요
1. 🔴 **높음**: 실제 사용되지 않음 (통합 필요)
2. 🔴 **높음**: DB 트랜잭션 롤백 문제
3. 🟡 **중간**: 에러 발생 시 조용히 실패
4. 🟡 **중간**: 파라미터 검증 없음
5. 🟢 **낮음**: `usage` 딕셔너리 키 검증
6. 🟢 **낮음**: `start_time` 검증
7. 🟢 **낮음**: 로깅 레벨 부적절
8. 🟢 **낮음**: `time` 모듈 임포트 위치
9. 🟢 **낮음**: 추가 정보 부족
10. 🟢 **낮음**: 배치 로깅 미지원

### 우선순위
- **높음**: 실제 사용 통합, DB 트랜잭션 롤백 문제
- **중간**: 에러 처리, 파라미터 검증
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: GPT Client에 로깅 통합
```python
# src/services/gpt_client.py
from src.services.gpt_logger import gpt_logger

def chat_completion(self, ..., session_id: Optional[str] = None, node_name: Optional[str] = None):
    import time
    start_time = time.time()
    
    try:
        response = self._retry_with_backoff(_call)
        ...
        
        # 로깅
        if session_id and node_name:
            gpt_logger.log_with_timing(
                session_id=session_id,
                node_name=node_name,
                model=result["model"],
                usage=result["usage"],
                start_time=start_time
            )
        
        return result
    except Exception as e:
        # 에러 로깅도 고려
        raise
```

### 수정 2: DB 트랜잭션 롤백 문제 해결
```python
def log_api_call(
    ...,
    db_session: Optional[Session] = None,
    auto_commit: Optional[bool] = None
):
    """
    auto_commit: None이면 db_session이 None일 때만 True
    """
    if db_session is None:
        auto_commit = True
        with db_manager.get_db_session() as session:
            GPTLogger._save_log(..., session, auto_commit=True)
    else:
        if auto_commit is None:
            auto_commit = False  # 외부 세션은 기본적으로 커밋하지 않음
        GPTLogger._save_log(..., db_session, auto_commit=auto_commit)

def _save_log(..., session: Session, auto_commit: bool = True):
    log_entry = AIProcessLog(...)
    session.add(log_entry)
    if auto_commit:
        session.commit()
```

### 수정 3: 파라미터 검증 추가
```python
def log_api_call(...):
    if not session_id:
        raise ValueError("session_id는 필수입니다.")
    if not node_name:
        raise ValueError("node_name은 필수입니다.")
    if not model:
        raise ValueError("model은 필수입니다.")
    if token_input < 0:
        raise ValueError(f"token_input은 0 이상이어야 합니다: {token_input}")
    if token_output < 0:
        raise ValueError(f"token_output은 0 이상이어야 합니다: {token_output}")
    if latency_ms < 0:
        raise ValueError(f"latency_ms는 0 이상이어야 합니다: {latency_ms}")
    ...
```

### 수정 4: 파일 상단에 time 임포트
```python
import time
from typing import Dict, Any, Optional
from datetime import datetime
...
```

---

## ✅ 검토 완료

**검토 항목**: `review_26_service_gpt_logger`  
**상태**: 완료  
**다음 항목**: `review_27_service_entity_extractor`

