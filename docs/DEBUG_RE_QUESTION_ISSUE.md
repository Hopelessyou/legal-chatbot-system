# RE_QUESTION 노드 bot_message 문제 디버깅 가이드

## 문제 현상

RE_QUESTION 상태에서 `botMessage: '(메시지 없음)'`이 표시되고, 사용자 입력 없이 RE_QUESTION → SUMMARY로 자동 전이됨.

## 가능한 원인

### 1. missing_fields 전달 문제
- VALIDATION 노드가 `missing_fields`를 설정하지만 RE_QUESTION 노드에 전달되지 않음
- `graph.py`에서 `result`를 state로 전달할 때 `missing_fields`가 누락됨

### 2. RE_QUESTION 노드 로직 문제
- `missing_fields`를 받지만 `unasked_missing_fields`가 비어있어서 SUMMARY로 전이
- `asked_fields`나 `skipped_fields`에 모든 `missing_fields`가 포함되어 있다고 잘못 판단

### 3. 연쇄 전이 문제
- RE_QUESTION → SUMMARY 연쇄 전이 시 SUMMARY 노드가 `bot_message`를 덮어씀
- RE_QUESTION 노드의 `bot_message`가 보존되지 않음

## 디버깅 방법

### 1. 서버 로그 확인

다음 로그를 확인하세요:

```
[STEP 4] VALIDATION 노드 실행
누락 필드 분석 완료: required_fields=..., asked_fields=..., missing_fields=...
VALIDATION 완료: 누락 필드 X개, 다음 State=RE_QUESTION

VALIDATION → RE_QUESTION 전이 감지
전달할 state: missing_fields=[...], conversation_history=X개
✅ RE_QUESTION 노드에 missing_fields 전달: [...]

[STEP 5] RE_QUESTION 노드 실행
❓ 누락 필드: [...]
📋 state.keys(): [...]
🔍 [RE_QUESTION] 필드 분석
missing_fields: [...]
asked_fields: [...]
skipped_fields: [...]
unasked_missing_fields: [...]
```

### 2. 확인할 포인트

1. **VALIDATION 노드가 missing_fields를 설정하는가?**
   - 로그: `누락 필드 분석 완료: missing_fields=[...]`
   - `missing_fields`가 비어있으면 문제

2. **RE_QUESTION 노드에 missing_fields가 전달되는가?**
   - 로그: `✅ RE_QUESTION 노드에 missing_fields 전달: [...]`
   - 전달되지 않으면 `graph.py`의 전달 로직 문제

3. **RE_QUESTION 노드가 missing_fields를 받는가?**
   - 로그: `❓ 누락 필드: [...]`
   - 비어있으면 전달 문제

4. **unasked_missing_fields가 비어있는가?**
   - 로그: `unasked_missing_fields: [...]`
   - 비어있으면 `asked_fields`나 `skipped_fields`에 모든 필드가 포함된 것

5. **RE_QUESTION 노드가 bot_message를 생성하는가?**
   - 로그: `✅ bot_message 설정 완료: ...`
   - 없으면 질문 생성 실패

6. **연쇄 전이 시 bot_message가 보존되는가?**
   - 로그: `RE_QUESTION → SUMMARY 연쇄 전이 감지`
   - `RE_QUESTION bot_message 보존: ...` 확인

## 수정 사항

### 1. graph.py
- RE_QUESTION 노드에 `missing_fields` 전달 검증 추가
- RE_QUESTION → SUMMARY 연쇄 전이 시 `bot_message` 보존 로직 추가

### 2. re_question_node.py
- `missing_fields`가 있으면 무조건 질문하도록 수정
- `unasked_missing_fields`가 비어있어도 `missing_fields`가 있으면 강제 질문
- `bot_message` 반환값 명시적 설정 및 검증 추가
- 상세 디버깅 로그 추가

## 다음 단계

1. **서버 재시작**: 변경사항 반영
2. **테스트 실행**: 상담 플로우 테스트
3. **서버 로그 확인**: 위의 로그 포인트 확인
4. **문제 지점 파악**: 로그에서 문제 발생 지점 확인
5. **추가 수정**: 필요시 추가 수정

## 예상되는 로그 출력

정상 작동 시:
```
[STEP 5] RE_QUESTION 노드 실행
❓ 누락 필드: ['incident_date', 'amount']
🔍 [RE_QUESTION] 필드 분석
missing_fields: ['incident_date', 'amount']
asked_fields: []
skipped_fields: []
unasked_missing_fields: ['incident_date', 'amount']
✅ 선택된 질문 필드: incident_date
✅ bot_message 설정 완료: 사건이 발생한 날짜를 알려주세요.
✅ RE_QUESTION 반환값: bot_message=사건이 발생한 날짜를 알려주세요...., next_state=FACT_COLLECTION
```

문제 발생 시:
```
[STEP 5] RE_QUESTION 노드 실행
❓ 누락 필드: []  ← 문제!
⚠️  누락 필드가 없습니다.
```

또는:
```
❓ 누락 필드: ['incident_date', 'amount']
unasked_missing_fields: []  ← 문제!
⚠️  missing_fields가 있지만 모두 질문한 것으로 간주됨
```

## 추가 디버깅

서버 로그에서 다음을 확인하세요:

1. VALIDATION 노드의 `missing_fields` 설정
2. RE_QUESTION 노드에 전달되는 `missing_fields`
3. RE_QUESTION 노드의 필드 분석 결과
4. `bot_message` 생성 및 반환 과정
5. 연쇄 전이 시 `bot_message` 보존 여부