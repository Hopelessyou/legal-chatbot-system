# 적용된 수정 사항

## 수정 일시
2026-01-09

## 수정된 파일

### 1. `src/langgraph/nodes/init_node.py`

**문제**: 사용자 입력이 있을 때 `bot_message` 미반환

**수정 내용**:
```python
# 수정 전
return {
    **state,
    "current_state": "CASE_CLASSIFICATION",
    "next_state": "CASE_CLASSIFICATION"
}

# 수정 후
return {
    **state,
    "current_state": "CASE_CLASSIFICATION",
    "next_state": "CASE_CLASSIFICATION",
    "bot_message": "처리 중입니다. 잠시만 기다려주세요."  # 추가
}
```

**영향**: 첫 메시지 전송 후 즉시 응답 메시지가 반환됨

---

### 2. `src/langgraph/nodes/case_classification_node.py`

**문제**: `bot_message`가 없을 경우 빈 문자열 반환 가능성

**수정 내용**:
```python
# 수정 전
return {
    **state,
    "next_state": "FACT_COLLECTION"
}

# 수정 후
# bot_message가 없으면 기본 메시지 설정
if not final_bot_message:
    state["bot_message"] = "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다."
    logger.warning(f"[{session_id}] ⚠️  bot_message가 없어 기본 메시지 설정")

return {
    **state,
    "bot_message": state.get("bot_message", "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다."),  # 명시적으로 포함
    "next_state": "FACT_COLLECTION"
}
```

**영향**: CASE_CLASSIFICATION 노드 실행 후 항상 적절한 응답 메시지가 반환됨

---

### 3. `src/langgraph/graph.py`

**문제**: 연쇄 실행 시 `bot_message` 병합 검증이 약함

**수정 내용**:
```python
# 수정 전
if "bot_message" in next_result:
    result["bot_message"] = next_result["bot_message"]
    ...
else:
    logger.warning(...)
if not result.get("bot_message"):
    result["bot_message"] = "추가 정보가 필요합니다." ...

# 수정 후
if "bot_message" in next_result and next_result["bot_message"]:
    result["bot_message"] = next_result["bot_message"]
    ...
else:
    logger.warning(...)
    # bot_message가 없으면 기본 메시지 설정
    result["bot_message"] = "추가 정보가 필요합니다." ...
```

**영향**: 연쇄 실행 시 `bot_message`가 비어있을 경우 더 엄격하게 검증하고 기본 메시지 설정

---

## 예상 효과

1. **첫 메시지 전송 시**: INIT 노드에서 "처리 중입니다. 잠시만 기다려주세요." 메시지 반환
2. **CASE_CLASSIFICATION 노드 실행 후**: 항상 적절한 응답 메시지 반환 (기본값 포함)
3. **연쇄 실행 시**: `bot_message`가 비어있을 경우 더 안전하게 처리

---

## 테스트 권장 사항

다음 시나리오를 테스트하세요:

1. **첫 메시지 전송**
   - `/chat/start` 호출 → 초기 메시지 확인
   - 사용자 메시지 전송 → "처리 중입니다. 잠시만 기다려주세요." 메시지 확인

2. **CASE_CLASSIFICATION 노드 실행**
   - 사건 분류 후 응답 메시지 확인 (빈 문자열이면 안 됨)

3. **VALIDATION → RE_QUESTION 연쇄 실행**
   - 연쇄 실행 후 응답 메시지 확인

4. **RE_QUESTION → FACT_COLLECTION 루프**
   - 질문-답변 루프에서 응답 메시지 확인

---

## 참고

- 상세 분석: `execution_flow_analysis.md`
- 문제 요약: `issue_summary.md`
- 실행 흐름 다이어그램: `execution_flow_diagram.md`
