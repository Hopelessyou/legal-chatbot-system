# 터미널 로깅 가이드

## 문제

uvicorn이 로그를 캡처해서 터미널에 LangGraph 실행 과정이 보이지 않음.

## 해결 방법

### 방법 1: run_server_debug.py 사용 (가장 확실)

```bash
python run_server_debug.py
```

이 스크립트는:
- uvicorn 로깅 설정을 직접 제어
- LangGraph 로그를 stderr로 강제 출력
- access log 비활성화하여 LangGraph 로그가 더 잘 보임

### 방법 2: uvicorn 실행 시 stderr 리다이렉트

Windows PowerShell:
```powershell
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --no-access-log 2>&1
```

Linux/Mac:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --no-access-log 2>&1 | tee langgraph.log
```

### 방법 3: 별도 터미널에서 로그 파일 모니터링

```bash
# 터미널 1: 서버 실행
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2: 로그 파일 모니터링 (Windows PowerShell)
Get-Content logs/app.log -Wait -Tail 50

# 또는 Linux/Mac
tail -f logs/app.log
```

## 현재 구현

코드에서 다음을 수행합니다:

1. **os.write(2, ...)**: stderr에 직접 바이트 쓰기 (가장 확실)
2. **sys.stderr.write()**: Python stderr에 쓰기
3. **logger.info()**: 로거를 통한 출력 (콘솔 핸들러 추가됨)

## 확인 방법

`run_server_debug.py` 실행 후 다음 출력이 보여야 합니다:

```
======================================================================
🔄 [GRAPH] 노드 실행 시작: VALIDATION
📌 세션 ID: sess_xxx
======================================================================
▶️  노드 함수 실행: VALIDATION

======================================================================
📍 [STEP 4] VALIDATION 노드 실행
📌 세션 ID: sess_xxx
🏷️  사건 유형: CRIMINAL (음주운전)
💬 대화 기록: 2개 Q-A 쌍
======================================================================
📋 누락 필드 분석 완료
   required_fields: [...]
   asked_fields: [...]
   missing_fields: ['incident_date', 'amount']
➡️  VALIDATION → RE_QUESTION 전이 (누락 필드 2개)

======================================================================
🔄 VALIDATION → RE_QUESTION 전이 감지
📋 missing_fields: ['incident_date', 'amount']
💬 conversation_history: 2개
======================================================================
▶️  RE_QUESTION 노드 실행 시작...

======================================================================
📍 [STEP 5] RE_QUESTION 노드 실행
📌 세션 ID: sess_xxx
❓ 누락 필드: ['incident_date', 'amount']
🚫 excluded_fields: set()
❓ unasked_missing_fields: ['incident_date', 'amount']
✅ 선택된 질문 필드: incident_date
✅ bot_message 설정: 사건이 발생한 날짜를 알려주세요.
✅ RE_QUESTION 노드 완료
💬 반환 bot_message: 사건이 발생한 날짜를 알려주세요.
➡️  반환 next_state: FACT_COLLECTION
======================================================================
```

## 문제 해결

출력이 여전히 보이지 않으면:

1. **서버 재시작**: 변경사항 반영
2. **run_server_debug.py 사용**: 가장 확실한 방법
3. **로그 파일 확인**: `logs/app.log` 파일 확인
4. **터미널 확인**: 다른 터미널 창에서 확인

## 참고

- `os.write(2, ...)`는 가장 낮은 레벨의 출력으로 uvicorn이 캡처하기 어려움
- `sys.stderr.write()`는 Python 레벨의 stderr 출력
- `logger.info()`는 로깅 시스템을 통한 출력
- 세 가지를 모두 사용하여 최대한 확실하게 출력