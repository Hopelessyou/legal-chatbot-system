# 실행 코드 문제 원인 요약

## 발견된 주요 문제점

### 🔴 심각도 높음 (즉시 수정 필요)

#### 1. CASE_CLASSIFICATION 노드에서 bot_message 미반환
- **파일**: `src/langgraph/nodes/case_classification_node.py`
- **문제**: 사건 분류 후 `bot_message`를 반환하지 않아 사용자에게 응답이 없을 수 있음
- **영향**: 첫 메시지 전송 후 응답이 빈 문자열로 반환될 수 있음
- **해결**: 노드 반환값에 `bot_message` 추가

#### 2. INIT 노드에서 사용자 입력이 있을 때 bot_message 미반환
- **파일**: `src/langgraph/nodes/init_node.py` (라인 169-178)
- **문제**: 사용자가 첫 메시지를 보냈을 때 `bot_message` 없이 CASE_CLASSIFICATION으로 전이
- **영향**: 첫 메시지 전송 후 즉시 응답이 없을 수 있음
- **해결**: INIT 노드 반환값에 기본 `bot_message` 추가

### 🟡 심각도 중간 (모니터링 필요)

#### 3. VALIDATION → RE_QUESTION 연쇄 실행 시 bot_message 덮어쓰기 실패 가능성
- **파일**: `src/langgraph/graph.py` (라인 270-337)
- **문제**: RE_QUESTION 노드에서 예외 발생 시 `bot_message`가 제대로 병합되지 않을 수 있음
- **영향**: RE_QUESTION 노드 실행 후 응답이 기본 메시지로 대체될 수 있음
- **해결**: 연쇄 실행 로직에서 `bot_message` 병합 검증 강화

---

## 실행 흐름 문제 시나리오

### 시나리오 1: 첫 메시지 전송 (문제 발생 가능)
```
1. /chat/start → INIT 노드 → 초기 메시지 반환 ✅
2. 사용자 메시지 전송 → /chat/message 호출
3. INIT 노드 실행 → 사용자 입력 있음 → next_state: "CASE_CLASSIFICATION" (bot_message 없음) ⚠️
4. CASE_CLASSIFICATION 노드 실행 → bot_message 없음 ⚠️
5. API 응답 → bot_message: "" ❌
```

### 시나리오 2: FACT_COLLECTION → VALIDATION → RE_QUESTION (정상 동작)
```
1. FACT_COLLECTION → bot_message: "다음 질문..." ✅
2. VALIDATION → missing_fields 있음 → next_state: "RE_QUESTION" ✅
3. RE_QUESTION (연쇄 실행) → bot_message: "사건이 발생한 날짜를 알려주세요." ✅
4. API 응답 → bot_message 정상 ✅
```

---

## 수정 권장 사항

### 1. CASE_CLASSIFICATION 노드 수정
```python
# src/langgraph/nodes/case_classification_node.py
return {
    **state,
    "case_type": case_type,
    "sub_case_type": sub_case_type,
    "bot_message": "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다.",  # 추가
    "next_state": "FACT_COLLECTION"
}
```

### 2. INIT 노드 수정
```python
# src/langgraph/nodes/init_node.py
if user_input and len(user_input) >= 2:
    return {
        **state,
        "current_state": "CASE_CLASSIFICATION",
        "next_state": "CASE_CLASSIFICATION",
        "bot_message": "처리 중입니다..."  # 추가
    }
```

### 3. graph.py 연쇄 실행 로직 개선
```python
# src/langgraph/graph.py
if "bot_message" in next_result and next_result["bot_message"]:
    result["bot_message"] = next_result["bot_message"]
    logger.info(f"✅ bot_message 병합 완료")
else:
    logger.warning(f"⚠️  {next_state} 노드에서 bot_message가 없거나 비어있음!")
```

---

## 테스트 체크리스트

- [ ] 첫 메시지 전송 후 응답 메시지 확인 (빈 문자열이면 안 됨)
- [ ] CASE_CLASSIFICATION 노드 실행 후 응답 메시지 확인
- [ ] VALIDATION → RE_QUESTION 연쇄 실행 후 응답 메시지 확인
- [ ] RE_QUESTION → FACT_COLLECTION 루프에서 응답 메시지 확인

---

## 참고 문서

- 상세 분석: `docs/q/execution_flow_analysis.md`
- 관련 파일:
  - `src/langgraph/graph.py`
  - `src/langgraph/nodes/init_node.py`
  - `src/langgraph/nodes/case_classification_node.py`
  - `src/langgraph/nodes/fact_collection_node.py`
  - `src/langgraph/nodes/validation_node.py`
  - `src/langgraph/nodes/re_question_node.py`
  - `src/api/routers/chat.py`
