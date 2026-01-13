# Uvicorn 로깅 설정 가이드

## 문제

uvicorn이 로그를 캡처해서 터미널에 LangGraph 실행 과정이 보이지 않음.

## 해결 방법

### 방법 1: uvicorn 실행 시 로그 레벨 설정

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

또는 더 상세한 로그를 보려면:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### 방법 2: uvicorn 실행 스크립트 수정

`scripts/` 디렉토리에 있는 실행 스크립트를 수정:

```python
# run_server.py 또는 유사한 파일
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"  # 또는 "debug"
    )
```

### 방법 3: 환경변수 설정

```bash
# Windows PowerShell
$env:LOG_LEVEL="INFO"
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Linux/Mac
export LOG_LEVEL=INFO
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 현재 구현

코드에서 다음을 수행합니다:

1. **os.write(2, ...)**: stderr에 직접 쓰기 (uvicorn이 캡처해도 보이도록)
2. **logger.info()**: 로거를 통한 출력 (콘솔 핸들러 추가됨)
3. **콘솔 핸들러**: `graph.py`, `validation_node.py`, `re_question_node.py`에 StreamHandler 추가

## 확인 방법

서버 실행 후 다음 출력이 보여야 합니다:

```
======================================================================
🔄 [GRAPH] 노드 실행 시작: VALIDATION
📌 세션 ID: sess_xxx
======================================================================
▶️  노드 함수 실행: VALIDATION
...
```

출력이 보이지 않으면:
1. uvicorn 실행 시 `--log-level info` 또는 `--log-level debug` 추가
2. 서버 재시작
3. 테스트 요청 전송
4. 터미널 확인

## 참고

- uvicorn의 기본 로그 레벨은 `info`입니다
- `--log-level debug`를 사용하면 더 상세한 로그를 볼 수 있습니다
- 로그는 stderr로 출력되므로 터미널에서 확인할 수 있습니다