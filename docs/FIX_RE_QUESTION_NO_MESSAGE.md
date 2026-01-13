# RE_QUESTION "(메시지 없음)" 문제 해결 가이드

## 문제 현상
- VALIDATION → RE_QUESTION 전이 시 `bot_message`가 "(메시지 없음)"으로 반환
- RE_QUESTION → SUMMARY 전이 시에도 `bot_message`가 "(메시지 없음)"으로 반환
- `missing_fields`가 손실되어 빈 리스트 `[]`로 전달됨

## 근본 원인
1. **체인 실행 로직이 실행되지 않음**: VALIDATION → RE_QUESTION 전이 시 RE_QUESTION 노드가 즉시 실행되지 않음
2. **`missing_fields` 손실**: VALIDATION 노드에서 설정한 `missing_fields`가 다음 요청에서 손실됨

## 해결 방법

### 1. 서버 재시작 (필수)
코드를 수정한 후 **반드시 서버를 재시작**해야 합니다:

```powershell
# 현재 서버 중지 (Ctrl+C)
# 서버 재시작
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

또는 `run_server_debug.py` 사용:
```powershell
python run_server_debug.py
```

### 2. 코드 확인
다음 코드가 `src/langgraph/graph.py`에 있는지 확인:
- `[PRE]` 디버깅 로그 (174-181번 라인)
- `[POST]` 디버깅 로그 (185-192번 라인)
- `[CRITICAL DEBUG]` 디버깅 로그 (200번 라인 이후)
- 체인 실행 로직 (251번 라인 이후)

### 3. 로그 확인
서버 재시작 후 로그 파일에서 다음을 확인:
- `🔍 [PRE]` - 노드 실행 전
- `🔍 [POST]` - 노드 실행 직후
- `🔍 [CRITICAL DEBUG]` - 노드 실행 후 즉시 체크
- `🔄 VALIDATION → RE_QUESTION 전이 감지` - 체인 실행

### 4. 로그 모니터링
다른 터미널에서 실시간 로그 모니터링:
```powershell
Get-Content logs\app.log -Wait -Tail 100 | Select-String -Pattern "\[PRE\]|\[POST\]|CRITICAL DEBUG|VALIDATION.*RE_QUESTION|missing_fields"
```

## 수정된 코드 위치
- `src/langgraph/graph.py`: 체인 실행 로직 추가
- `src/langgraph/nodes/validation_node.py`: `missing_fields` 명시적 반환 추가
- `src/langgraph/nodes/re_question_node.py`: `missing_fields` 처리 강화

## 테스트 방법
1. 서버 재시작
2. 브라우저에서 새로고침
3. 세션 시작 버튼 클릭
4. 메시지 입력하여 VALIDATION → RE_QUESTION 전이 확인
5. 로그 파일에서 디버깅 로그 확인

## 예상 로그 출력
```
🔍 [PRE] 노드 실행 전: current_state=VALIDATION
🔍 [POST] 노드 실행 직후: result 타입=<class 'dict'>
🔍 [CRITICAL DEBUG] 노드 실행 후 즉시 체크
current_state=VALIDATION
next_state=RE_QUESTION
missing_fields=['amount', 'counterparty', 'evidence']
🔄 VALIDATION → RE_QUESTION 전이 감지
📋 missing_fields: ['amount', 'counterparty', 'evidence']
▶️  RE_QUESTION 노드 실행 시작...
✅ RE_QUESTION 노드 실행 완료
💬 반환 bot_message: 문제가 된 금액은 얼마인가요?
```
