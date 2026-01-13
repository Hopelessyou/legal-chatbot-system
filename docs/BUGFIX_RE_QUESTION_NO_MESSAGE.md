# 버그 수정: RE_QUESTION 상태에서 질문이 표시되지 않는 문제

## 문제 현상

`chat_gpt.html`에서 상담을 진행할 때, RE_QUESTION 상태로 전이된 후 질문 메시지가 표시되지 않는 문제가 발생했습니다.

### 로그 분석

```
[오전 5:31:46] 봇 응답 수신 {
  state: 'VALIDATION', 
  botMessage: '사건이 발생한 날짜를 알려주세요.',
  ...
}

[오전 5:31:50] 봇 응답 수신 {
  state: 'RE_QUESTION', 
  botMessage: '(메시지 없음)',
  hasBotMessage: false,
  expectedInput: null,
  ...
}
```

### 문제 흐름

1. 사용자가 "어제"라고 답변
2. FACT_COLLECTION 노드 실행 → VALIDATION으로 전이
3. VALIDATION 노드 실행 → `next_state: "RE_QUESTION"` 반환
4. State가 RE_QUESTION으로 업데이트되지만 **RE_QUESTION 노드가 실행되지 않음**
5. 결과: `bot_message`가 없어서 프론트엔드에 "(메시지 없음)" 표시

---

## 원인 분석

### 핵심 원인

`run_graph_step()` 함수가 **현재 State의 노드만 실행**하고, `next_state`가 있어도 **다음 노드를 실행하지 않음**:

```python
# graph.py (수정 전)
def run_graph_step(state: StateContext) -> StateContext:
    current_state = state.get("current_state", "INIT")
    node_func = node_map.get(current_state)
    result = node_func(state)  # 현재 노드만 실행
    
    next_state = result.get("next_state")
    if next_state:
        result["current_state"] = next_state  # State만 업데이트
        # ❌ 다음 노드를 실행하지 않음!
    
    return result
```

### 문제 시나리오

1. **VALIDATION 노드 실행**
   - `missing_fields` 확인
   - `next_state: "RE_QUESTION"` 반환
   - `bot_message: "추가 정보가 필요합니다."` (기본 메시지)

2. **State 전이**
   - `current_state`가 "RE_QUESTION"으로 업데이트
   - 하지만 **RE_QUESTION 노드가 실행되지 않음**

3. **프론트엔드 응답**
   - `bot_message`가 없거나 기본 메시지만 있음
   - RE_QUESTION 노드가 생성해야 할 구체적인 질문이 없음

---

## 해결 방법

### 수정 내용

`run_graph_step()` 함수에서 **VALIDATION → RE_QUESTION 전이 시 RE_QUESTION 노드를 즉시 실행**하도록 수정:

```python
# graph.py (수정 후)
if next_state:
    result["current_state"] = next_state
    
    # VALIDATION → RE_QUESTION 전이 시 RE_QUESTION 노드 즉시 실행
    if current_state == "VALIDATION" and next_state in ["RE_QUESTION", "SUMMARY"]:
        logger.info(f"VALIDATION → {next_state} 전이 감지, {next_state} 노드 즉시 실행")
        next_node_func = node_map.get(next_state)
        if next_node_func:
            next_result = next_node_func(result)  # 다음 노드 실행
            
            # RE_QUESTION 노드가 생성한 bot_message 사용
            if next_result.get("bot_message"):
                result["bot_message"] = next_result["bot_message"]
            
            # expected_input, conversation_history 등도 병합
            if next_result.get("expected_input"):
                result["expected_input"] = next_result["expected_input"]
            
            # RE_QUESTION → FACT_COLLECTION 전이도 처리
            if next_result.get("next_state"):
                result["current_state"] = next_result["next_state"]
```

### 수정 효과

1. **VALIDATION → RE_QUESTION 전이 시**
   - RE_QUESTION 노드가 즉시 실행됨
   - 누락 필드에 대한 구체적인 질문 생성
   - `bot_message`에 질문 텍스트 설정
   - `expected_input` 설정

2. **VALIDATION → SUMMARY 전이 시**
   - SUMMARY 노드가 즉시 실행됨
   - 요약 생성 및 완료 처리

3. **사용자 경험 개선**
   - 한 번의 API 호출로 질문까지 받을 수 있음
   - 중간에 빈 메시지가 표시되지 않음

---

## 수정된 코드 위치

- **파일**: `src/langgraph/graph.py`
- **함수**: `run_graph_step()`
- **라인**: 146-180 (수정 전) → 146-220 (수정 후)

---

## 테스트 시나리오

### 시나리오 1: 필수 필드 누락 시

1. 사용자 입력: "어제 음주운전으로 사고가 발생함"
2. FACT_COLLECTION 노드 실행
3. VALIDATION 노드 실행
   - `missing_fields: ["incident_date", "amount", ...]` 감지
   - `next_state: "RE_QUESTION"` 반환
4. **RE_QUESTION 노드 즉시 실행** (수정 후)
   - `bot_message: "사건이 발생한 날짜를 알려주세요."` 생성
   - `expected_input: {type: "date", field: "incident_date"}` 설정
5. 프론트엔드에 질문 표시 ✅

### 시나리오 2: 모든 필드 충족 시

1. 사용자 입력: "2024년 1월 1일, 5000만원, 개인"
2. FACT_COLLECTION 노드 실행
3. VALIDATION 노드 실행
   - `missing_fields: []` (모든 필드 충족)
   - `next_state: "SUMMARY"` 반환
4. **SUMMARY 노드 즉시 실행** (수정 후)
   - 요약 생성
   - `bot_message: "모든 필수 정보가 수집되었습니다..."` 설정
5. 프론트엔드에 완료 메시지 표시 ✅

---

## 관련 파일

- `src/langgraph/graph.py`: State 전이 로직 수정
- `src/langgraph/nodes/validation_node.py`: VALIDATION 노드 구현
- `src/langgraph/nodes/re_question_node.py`: RE_QUESTION 노드 구현
- `static/chat_gpt.html`: 프론트엔드 (수정 불필요)

---

## 추가 고려사항

### 무한 루프 방지

현재 구현은 `_check_recursion_limit()`으로 무한 루프를 방지합니다:
- 세션별 실행 횟수 추적
- 기본 제한: 50회
- 제한 초과 시 COMPLETED로 강제 전이

### 성능 영향

- **이전**: VALIDATION → RE_QUESTION 전이 시 2번의 API 호출 필요
- **수정 후**: 1번의 API 호출로 질문까지 받음
- **결과**: 사용자 경험 개선, API 호출 횟수 감소

### 확장성

다른 State 전이도 동일한 패턴으로 처리 가능:
- `FACT_COLLECTION → VALIDATION`: 이미 자동 실행됨
- `RE_QUESTION → FACT_COLLECTION`: Loop이므로 사용자 입력 대기
- `SUMMARY → COMPLETED`: 즉시 실행 가능 (추가 구현 가능)

---

## 결론

**문제**: VALIDATION → RE_QUESTION 전이 시 RE_QUESTION 노드가 실행되지 않아 질문이 표시되지 않음

**해결**: `run_graph_step()`에서 VALIDATION → RE_QUESTION 전이 시 RE_QUESTION 노드를 즉시 실행하도록 수정

**효과**: 
- ✅ RE_QUESTION 상태에서 질문이 정상적으로 표시됨
- ✅ 사용자 경험 개선 (빈 메시지 없음)
- ✅ API 호출 횟수 감소 (1회로 질문까지 받음)