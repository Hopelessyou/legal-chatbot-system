# LangGraph 실행 흐름 다이어그램

## 전체 실행 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    API 엔드포인트 (/chat/message)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  1. load_session_state(session_id)    │
        │     - DB에서 세션 상태 로드              │
        │     - current_state 확인               │
        └───────────────────┬───────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  2. state["last_user_input"] = msg    │
        │     - 사용자 입력 업데이트               │
        └───────────────────┬─────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  3. run_graph_step(state)             │
        │     - 현재 state에 해당하는 노드 실행   │
        └───────────────────┬─────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  4. save_session_state(session_id,     │
        │                      result)           │
        │     - DB에 상태 저장                    │
        └───────────────────┬─────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  5. return success_response({           │
        │       "bot_message": result.get(...),  │
        │       "current_state": ...             │
        │     })                                  │
        └───────────────────────────────────────┘
```

---

## 노드 실행 흐름

```
                    ┌─────────┐
                    │  INIT   │
                    └────┬────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │ CASE_CLASSIFICATION            │
        │ - 사건 유형 분류                │
        │ - 1차 서술 분석                 │
        │ ⚠️ bot_message 없음 (문제)      │
        └────┬───────────────────────────┘
             │
             ▼
        ┌────────────────────────────────┐
        │ FACT_COLLECTION               │
        │ - Q-A 쌍 저장                  │
        │ - 다음 질문 생성               │
        │ ✅ bot_message 있음            │
        └────┬───────────────────────────┘
             │
             ▼
        ┌────────────────────────────────┐
        │ VALIDATION                     │
        │ - facts 추출                   │
        │ - missing_fields 계산          │
        │ - 분기 결정                    │
        └────┬───────────────────────────┘
             │
             ├─────────────────┬─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │RE_QUESTION  │   │   SUMMARY   │   │  COMPLETED  │
    │✅ bot_msg    │   │✅ bot_msg   │   │✅ bot_msg   │
    └──────┬───────┘   └──────┬──────┘   └──────┬──────┘
           │                  │                 │
           │                  │                 │
           └──────────────────┴─────────────────┘
                              │
                              ▼
                         ┌─────────┐
                         │   END   │
                         └─────────┘
```

---

## 문제 발생 시나리오

### 시나리오 1: 첫 메시지 전송 (문제 발생)

```
사용자 → /chat/message
         │
         ├─> load_session_state
         │   └─> current_state: "INIT"
         │
         ├─> run_graph_step(state)
         │   │
         │   ├─> INIT 노드 실행
         │   │   ├─> user_input 있음
         │   │   └─> return {
         │   │       "next_state": "CASE_CLASSIFICATION"
         │   │       ⚠️ "bot_message" 없음
         │   │   }
         │   │
         │   ├─> current_state 업데이트: "CASE_CLASSIFICATION"
         │   │
         │   └─> CASE_CLASSIFICATION 노드 실행
         │       └─> return {
         │           "case_type": "CIVIL",
         │           "next_state": "FACT_COLLECTION"
         │           ⚠️ "bot_message" 없음
         │       }
         │
         └─> API 응답
             └─> bot_message: "" ❌
```

### 시나리오 2: VALIDATION → RE_QUESTION 연쇄 실행 (정상)

```
사용자 → /chat/message
         │
         ├─> load_session_state
         │   └─> current_state: "FACT_COLLECTION"
         │
         ├─> run_graph_step(state)
         │   │
         │   ├─> FACT_COLLECTION 노드 실행
         │   │   ├─> Q-A 쌍 저장
         │   │   └─> return {
         │   │       "bot_message": "다음 질문...",
         │   │       "next_state": "VALIDATION"
         │   │   }
         │   │
         │   ├─> VALIDATION 노드 실행
         │   │   ├─> missing_fields: ["incident_date"]
         │   │   └─> return {
         │   │       "missing_fields": ["incident_date"],
         │   │       "next_state": "RE_QUESTION"
         │   │   }
         │   │
         │   ├─> 연쇄 실행 감지 (VALIDATION → RE_QUESTION)
         │   │
         │   └─> RE_QUESTION 노드 실행
         │       └─> return {
         │           "bot_message": "사건이 발생한 날짜를 알려주세요.",
         │           "next_state": "FACT_COLLECTION"
         │       }
         │
         └─> API 응답
             └─> bot_message: "사건이 발생한 날짜를 알려주세요." ✅
```

---

## state 전이 다이어그램

```
INIT
 │
 │ (사용자 입력 있음)
 ▼
CASE_CLASSIFICATION ⚠️ bot_message 없음
 │
 │ (next_state: "FACT_COLLECTION")
 ▼
FACT_COLLECTION ✅ bot_message 있음
 │
 │ (next_state: "VALIDATION")
 ▼
VALIDATION
 │
 │ ├─ missing_fields 있음
 │ │
 │ ▼
 │ RE_QUESTION ✅ bot_message 있음 (연쇄 실행)
 │ │
 │ │ (next_state: "FACT_COLLECTION")
 │ │
 │ └─────────────────┐
 │                   │
 │ └─ missing_fields 없음
 │   │
 │   ▼
 │   SUMMARY ✅ bot_message 있음 (연쇄 실행)
 │   │
 │   │ (next_state: "COMPLETED")
 │   │
 │   ▼
 │   COMPLETED ✅ bot_message 있음
 │
 └───────────────────┘
```

---

## bot_message 전달 경로

```
노드 실행
  │
  ├─> 노드 함수 반환값
  │   └─> result["bot_message"]
  │
  ├─> graph.py에서 처리
  │   ├─> 연쇄 실행 시 병합
  │   └─> result["bot_message"] 업데이트
  │
  ├─> save_session_state
  │   └─> DB에 저장 (conversation_history만, bot_message는 저장 안 함)
  │
  └─> API 응답
      └─> response["bot_message"] = result.get("bot_message", "")
```

**문제점**: 
- CASE_CLASSIFICATION 노드에서 `bot_message`가 없으면 빈 문자열 반환
- INIT 노드에서 사용자 입력이 있을 때 `bot_message`가 없으면 빈 문자열 반환

---

## 해결 후 예상 흐름

### 수정 후 시나리오 1: 첫 메시지 전송

```
INIT 노드 실행
  │
  ├─> user_input 있음
  │   └─> return {
  │       "next_state": "CASE_CLASSIFICATION",
  │       "bot_message": "처리 중입니다..." ✅ (추가됨)
  │   }
  │
  └─> CASE_CLASSIFICATION 노드 실행
      └─> return {
          "case_type": "CIVIL",
          "next_state": "FACT_COLLECTION",
          "bot_message": "사건 유형을 확인했습니다..." ✅ (추가됨)
      }
```

---

## 참고

- 상세 분석: `execution_flow_analysis.md`
- 문제 요약: `issue_summary.md`
