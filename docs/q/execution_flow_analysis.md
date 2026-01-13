# LangGraph 실행 흐름 분석 및 문제 원인 확인

## 개요
실제 작동에서 제대로 반응이 안 되는 문제를 해결하기 위해 실행 코드를 세분화하여 분석한 결과입니다.

**분석 일시**: 2026-01-09  
**분석 대상**: `src/langgraph/` 디렉토리 전체 실행 흐름

---

## 1. API 엔드포인트에서 그래프 실행까지의 흐름

### 1.1 `/chat/message` 엔드포인트 (`src/api/routers/chat.py`)

```python
@router.post("/message")
async def process_message(request: ChatMessageRequest, ...):
    # 1. 세션 상태 로드
    state = load_session_state(request.session_id)
    
    # 2. 사용자 입력 업데이트
    state["last_user_input"] = request.user_message
    
    # 3. LangGraph 1 step 실행
    result = run_graph_step(state)
    
    # 4. 상태 저장
    save_session_state(request.session_id, result)
    
    # 5. 응답 반환
    return success_response({
        "bot_message": result.get("bot_message", ""),
        "current_state": result.get("current_state", ""),
        ...
    })
```

**확인 사항**:
- ✅ 세션 상태 로드 정상
- ✅ 사용자 입력 업데이트 정상
- ⚠️ **문제 가능성**: `result.get("bot_message", "")`가 빈 문자열일 수 있음

---

## 2. `run_graph_step` 함수 분석 (`src/langgraph/graph.py`)

### 2.1 함수 구조

```python
def run_graph_step(state: StateContext) -> StateContext:
    # 1. 현재 state 확인
    current_state = state.get("current_state", "INIT")
    
    # 2. 노드 맵에서 해당 노드 함수 찾기
    node_func = node_map.get(current_state)
    
    # 3. 노드 실행
    result = node_func(state)
    
    # 4. next_state 확인 및 current_state 업데이트
    next_state = result.get("next_state")
    if next_state:
        result["current_state"] = next_state
        
        # 5. 특정 조건에서 연쇄 실행 (VALIDATION → RE_QUESTION)
        if current_state == "VALIDATION" and next_state in ["RE_QUESTION", "SUMMARY"]:
            next_node_func = node_map.get(next_state)
            next_result = next_node_func(result)
            
            # 6. next_result 병합
            if "bot_message" in next_result:
                result["bot_message"] = next_result["bot_message"]
    
    return result
```

**확인 사항**:
- ✅ 노드 실행 로직 정상
- ⚠️ **문제 가능성 1**: `result.get("bot_message")`가 None이거나 빈 문자열일 수 있음
- ⚠️ **문제 가능성 2**: 연쇄 실행 시 `next_result`의 `bot_message`가 제대로 병합되지 않을 수 있음

---

## 3. 노드별 실행 흐름 분석

### 3.1 INIT 노드 (`src/langgraph/nodes/init_node.py`)

**실행 흐름**:
1. 세션 ID 확인/생성
2. DB에 세션 생성
3. 사용자 입력 확인
   - 입력 있음 → `next_state: "CASE_CLASSIFICATION"` 반환
   - 입력 없음 → 초기 메시지 표시, `next_state: "CASE_CLASSIFICATION"` 반환

**반환값**:
```python
{
    "current_state": "INIT" or "CASE_CLASSIFICATION",
    "bot_message": "안녕하세요...",
    "next_state": "CASE_CLASSIFICATION"
}
```

**확인 사항**:
- ✅ 사용자 입력이 있을 때 `bot_message`가 없을 수 있음 (정상 동작)
- ✅ 사용자 입력이 없을 때는 `bot_message` 설정됨

---

### 3.2 CASE_CLASSIFICATION 노드 (`src/langgraph/nodes/case_classification_node.py`)

**실행 흐름**:
1. 사용자 입력에서 사건 유형 분류
2. 1차 서술 분석 (`post_classification_analysis`)
3. `next_state: "FACT_COLLECTION"` 반환

**반환값**:
```python
{
    "case_type": "CIVIL",
    "sub_case_type": "CIVIL_CONTRACT",
    "initial_description": "...",
    "initial_analysis": {...},
    "conversation_history": [],
    "skipped_fields": [...],
    "missing_fields": [...],
    "next_state": "FACT_COLLECTION"
}
```

**확인 사항**:
- ⚠️ **문제 가능성**: `bot_message`가 반환되지 않을 수 있음
- ✅ `missing_fields`는 설정됨

---

### 3.3 FACT_COLLECTION 노드 (`src/langgraph/nodes/fact_collection_node.py`)

**실행 흐름**:
1. 사용자 입력 확인
2. `current_question`이 있으면 Q-A 쌍 저장
3. 다음 질문 생성 (`_generate_next_question`)
4. `bot_message` 설정
5. `next_state: "VALIDATION"` 반환

**반환값**:
```python
{
    "conversation_history": [...],
    "bot_message": "다음 질문...",
    "current_question": {...},
    "next_state": "VALIDATION"
}
```

**확인 사항**:
- ✅ `bot_message`는 항상 설정됨
- ✅ Q-A 쌍 저장 정상

---

### 3.4 VALIDATION 노드 (`src/langgraph/nodes/validation_node.py`)

**실행 흐름**:
1. `conversation_history`에서 facts 추출
2. 필수 필드 확인
3. `missing_fields` 계산
4. 분기 결정:
   - `missing_fields` 있음 → `next_state: "RE_QUESTION"`
   - `missing_fields` 없음 → `next_state: "SUMMARY"`

**반환값**:
```python
# missing_fields가 있는 경우
{
    "missing_fields": ["incident_date", "amount"],
    "bot_message": "추가 정보가 필요합니다.",  # 기본 메시지
    "next_state": "RE_QUESTION"
}

# missing_fields가 없는 경우
{
    "missing_fields": [],
    "bot_message": "모든 필수 정보가 수집되었습니다...",
    "next_state": "SUMMARY"
}
```

**확인 사항**:
- ⚠️ **문제 가능성**: `missing_fields`가 있을 때 `bot_message`가 기본 메시지로 설정됨
- ⚠️ **문제 가능성**: `graph.py`에서 연쇄 실행 시 RE_QUESTION 노드의 `bot_message`로 덮어쓰여야 하는데, 덮어쓰이지 않을 수 있음

---

### 3.5 RE_QUESTION 노드 (`src/langgraph/nodes/re_question_node.py`)

**실행 흐름**:
1. `missing_fields` 확인
2. 다음 질문할 필드 선택
3. RAG에서 질문 템플릿 조회
4. `bot_message` 생성
5. `next_state: "FACT_COLLECTION"` 반환

**반환값**:
```python
{
    "bot_message": "사건이 발생한 날짜를 알려주세요.",
    "current_question": {
        "question": "...",
        "field": "incident_date"
    },
    "expected_input": {...},
    "next_state": "FACT_COLLECTION"
}
```

**확인 사항**:
- ✅ `bot_message`는 항상 설정됨
- ✅ `missing_fields`가 없으면 SUMMARY로 전이

---

## 4. 핵심 문제점 분석

### 4.1 문제 1: VALIDATION → RE_QUESTION 연쇄 실행 시 bot_message 덮어쓰기

**위치**: `src/langgraph/graph.py:270-337`

**문제 코드**:
```python
if is_chain_condition:  # VALIDATION → RE_QUESTION
    next_result = next_node_func(result)
    
    # bot_message 병합
    if "bot_message" in next_result:
        result["bot_message"] = next_result["bot_message"]
    else:
        # ⚠️ 문제: next_result에 bot_message가 없으면 기본 메시지 설정
        if not result.get("bot_message"):
            result["bot_message"] = "추가 정보가 필요합니다."
```

**문제점**:
- RE_QUESTION 노드는 항상 `bot_message`를 반환하지만, 예외 발생 시 반환하지 않을 수 있음
- `next_result`에 `bot_message`가 없을 때 기본 메시지로 설정하는 로직이 있지만, 실제로는 RE_QUESTION 노드에서 항상 반환해야 함

**해결 방안**:
1. RE_QUESTION 노드에서 예외 발생 시에도 `bot_message`를 반환하도록 보장
2. `graph.py`에서 `next_result`의 `bot_message`가 없을 때 경고 로그 추가

---

### 4.2 문제 2: CASE_CLASSIFICATION 노드에서 bot_message 미반환

**위치**: `src/langgraph/nodes/case_classification_node.py`

**문제 코드**:
```python
def case_classification_node(state: StateContext) -> Dict[str, Any]:
    # ... 사건 분류 로직 ...
    
    # ⚠️ 문제: bot_message를 반환하지 않음
    return {
        **state,
        "case_type": case_type,
        "next_state": "FACT_COLLECTION"
    }
```

**문제점**:
- CASE_CLASSIFICATION 노드가 `bot_message`를 반환하지 않음
- 사용자가 첫 메시지를 보낸 후 응답이 없을 수 있음

**해결 방안**:
- CASE_CLASSIFICATION 노드에서 적절한 `bot_message` 반환 (예: "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다.")

---

### 4.3 문제 3: state 저장 시 bot_message 누락 가능성

**위치**: `src/services/session_manager.py:206-232`

**문제 코드**:
```python
def _update_session(session: Session, session_id: str, state: StateContext):
    chat_session.current_state = current_state
    chat_session.completion_rate = state.get("completion_rate", 0)
    
    # ⚠️ 문제: bot_message를 DB에 저장하지 않음
    # conversation_history만 저장
    if "conversation_history" in state:
        chat_session.conversation_history = state.get("conversation_history", [])
```

**문제점**:
- `bot_message`는 메모리에만 존재하고 DB에 저장되지 않음
- 다음 요청에서 `load_session_state`로 로드할 때 `bot_message`가 없음
- 하지만 이는 정상 동작 (매 요청마다 새로 생성되어야 함)

---

### 4.4 문제 4: INIT 노드에서 사용자 입력이 있을 때 bot_message 미반환

**위치**: `src/langgraph/nodes/init_node.py:169-178`

**문제 코드**:
```python
# 사용자 입력이 있으면 CASE_CLASSIFICATION으로 바로 이동
if user_input and len(user_input) >= 2:
    return {
        **state,
        "current_state": "CASE_CLASSIFICATION",
        "next_state": "CASE_CLASSIFICATION"
        # ⚠️ 문제: bot_message가 없음
    }
```

**문제점**:
- 사용자가 첫 메시지를 보냈을 때 즉시 응답이 없을 수 있음
- CASE_CLASSIFICATION 노드가 실행되어야 응답이 생성됨

**해결 방안**:
- INIT 노드에서 사용자 입력이 있을 때도 기본 메시지 반환
- 또는 CASE_CLASSIFICATION 노드에서 즉시 응답 생성

---

## 5. 실행 흐름 시나리오별 분석

### 시나리오 1: 첫 메시지 전송 (INIT → CASE_CLASSIFICATION)

**흐름**:
1. `/chat/start` 호출 → INIT 노드 실행 → 초기 메시지 반환 ✅
2. 사용자 메시지 전송 → `/chat/message` 호출
3. `load_session_state` → `current_state: "INIT"`
4. INIT 노드 실행 → 사용자 입력 있음 → `next_state: "CASE_CLASSIFICATION"` 반환 (bot_message 없음) ⚠️
5. `graph.py`에서 `current_state` 업데이트 → `"CASE_CLASSIFICATION"`
6. CASE_CLASSIFICATION 노드 실행 → `bot_message` 없음 ⚠️
7. API 응답 → `bot_message: ""` ❌

**문제**: INIT에서 CASE_CLASSIFICATION으로 전이할 때 `bot_message`가 없음

---

### 시나리오 2: FACT_COLLECTION → VALIDATION → RE_QUESTION

**흐름**:
1. 사용자 메시지 전송 → FACT_COLLECTION 노드 실행
2. FACT_COLLECTION → `bot_message: "다음 질문..."` ✅
3. VALIDATION 노드 실행 → `missing_fields: ["incident_date"]` → `next_state: "RE_QUESTION"` ✅
4. `graph.py`에서 연쇄 실행 → RE_QUESTION 노드 실행
5. RE_QUESTION → `bot_message: "사건이 발생한 날짜를 알려주세요."` ✅
6. `graph.py`에서 병합 → `result["bot_message"] = next_result["bot_message"]` ✅
7. API 응답 → `bot_message: "사건이 발생한 날짜를 알려주세요."` ✅

**정상 동작**: 이 시나리오는 정상적으로 작동해야 함

---

### 시나리오 3: RE_QUESTION → FACT_COLLECTION (루프)

**흐름**:
1. RE_QUESTION 노드 실행 → `bot_message: "질문..."` ✅
2. `next_state: "FACT_COLLECTION"` 반환
3. 사용자 메시지 전송 → FACT_COLLECTION 노드 실행
4. Q-A 쌍 저장 ✅
5. 다음 질문 생성 → `bot_message: "다음 질문..."` ✅
6. API 응답 → 정상 ✅

**정상 동작**: 이 시나리오도 정상적으로 작동해야 함

---

## 6. 발견된 문제 요약

### 심각도 높음 (즉시 수정 필요)

1. **CASE_CLASSIFICATION 노드에서 bot_message 미반환**
   - 위치: `src/langgraph/nodes/case_classification_node.py`
   - 영향: 첫 메시지 전송 후 응답이 없을 수 있음

2. **INIT 노드에서 사용자 입력이 있을 때 bot_message 미반환**
   - 위치: `src/langgraph/nodes/init_node.py:169-178`
   - 영향: 첫 메시지 전송 후 즉시 응답이 없을 수 있음

### 심각도 중간 (모니터링 필요)

3. **VALIDATION → RE_QUESTION 연쇄 실행 시 bot_message 덮어쓰기 실패 가능성**
   - 위치: `src/langgraph/graph.py:270-337`
   - 영향: RE_QUESTION 노드에서 예외 발생 시 기본 메시지로 대체됨

### 심각도 낮음 (개선 권장)

4. **state 저장 시 bot_message 누락 (정상 동작이지만 로깅 개선 가능)**
   - 위치: `src/services/session_manager.py`
   - 영향: 없음 (매 요청마다 새로 생성되어야 함)

---

## 7. 해결 방안

### 7.1 CASE_CLASSIFICATION 노드 수정

```python
def case_classification_node(state: StateContext) -> Dict[str, Any]:
    # ... 기존 로직 ...
    
    return {
        **state,
        "case_type": case_type,
        "sub_case_type": sub_case_type,
        "bot_message": "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다.",  # 추가
        "next_state": "FACT_COLLECTION"
    }
```

### 7.2 INIT 노드 수정

```python
# 사용자 입력이 있으면 CASE_CLASSIFICATION으로 바로 이동
if user_input and len(user_input) >= 2:
    return {
        **state,
        "current_state": "CASE_CLASSIFICATION",
        "next_state": "CASE_CLASSIFICATION",
        "bot_message": "처리 중입니다..."  # 추가
    }
```

### 7.3 graph.py 연쇄 실행 로직 개선

```python
if is_chain_condition:
    next_result = next_node_func(result)
    
    # bot_message 병합 (더 엄격한 검증)
    if "bot_message" in next_result and next_result["bot_message"]:
        result["bot_message"] = next_result["bot_message"]
        logger.info(f"✅ bot_message 병합 완료: {result['bot_message'][:100]}")
    else:
        logger.warning(f"⚠️  {next_state} 노드에서 bot_message가 없거나 비어있음!")
        if not result.get("bot_message"):
            result["bot_message"] = "추가 정보가 필요합니다."
```

---

## 8. 테스트 시나리오

### 테스트 1: 첫 메시지 전송
1. `/chat/start` 호출 → 초기 메시지 확인
2. 사용자 메시지 전송 → 응답 메시지 확인 (빈 문자열이면 안 됨)

### 테스트 2: FACT_COLLECTION → VALIDATION → RE_QUESTION
1. 사용자 메시지 전송 (FACT_COLLECTION)
2. VALIDATION 실행 → RE_QUESTION 자동 실행
3. 응답에 `bot_message` 확인 (빈 문자열이면 안 됨)

### 테스트 3: RE_QUESTION → FACT_COLLECTION 루프
1. RE_QUESTION 노드 실행 후 응답 확인
2. 사용자 메시지 전송
3. 다음 질문 응답 확인

---

## 9. 결론

**주요 문제점**:
1. CASE_CLASSIFICATION 노드에서 `bot_message` 미반환
2. INIT 노드에서 사용자 입력이 있을 때 `bot_message` 미반환
3. 연쇄 실행 시 `bot_message` 덮어쓰기 실패 가능성

**우선순위**:
1. CASE_CLASSIFICATION 노드 수정 (즉시)
2. INIT 노드 수정 (즉시)
3. graph.py 연쇄 실행 로직 개선 (모니터링 후 필요 시)

**예상 효과**:
- 첫 메시지 전송 후 즉시 응답 생성
- 모든 노드 전이 시 적절한 `bot_message` 반환
- 사용자 경험 개선

---

## 10. 참고 파일

- `src/langgraph/graph.py`: 그래프 실행 로직
- `src/langgraph/nodes/init_node.py`: INIT 노드
- `src/langgraph/nodes/case_classification_node.py`: CASE_CLASSIFICATION 노드
- `src/langgraph/nodes/fact_collection_node.py`: FACT_COLLECTION 노드
- `src/langgraph/nodes/validation_node.py`: VALIDATION 노드
- `src/langgraph/nodes/re_question_node.py`: RE_QUESTION 노드
- `src/api/routers/chat.py`: API 엔드포인트
- `src/services/session_manager.py`: 세션 상태 관리
