# Chat API 사용법 및 데이터 처리 흐름도

## 목차

1. [개요](#개요)
2. [API 엔드포인트 상세](#api-엔드포인트-상세)
3. [데이터 처리 흐름도](#데이터-처리-흐름도)
4. [단계별 상세 설명](#단계별-상세-설명)
5. [데이터 구조](#데이터-구조)
6. [실제 사용 예시](#실제-사용-예시)
7. [에러 처리](#에러-처리)

---

## 개요

법률 상담 챗봇은 **LangGraph 기반 상태 머신**으로 대화 흐름을 제어하며, **RAG 문서**를 참조하여 질문과 규칙을 동적으로 생성합니다. 사용자의 자유로운 입력을 받아 구조화된 상담 데이터로 변환하는 과정을 단계별로 관리합니다.

### 핵심 원칙

- **GPT는 해석 도구**: 엔티티 추출, 키워드 추출, 요약 생성만 담당
- **RAG는 기준 제공**: 모든 질문, 규칙, 포맷은 RAG 문서에 정의
- **LangGraph는 흐름 제어**: 분기, 반복, 검증을 담당
- **DB는 데이터 저장**: 구조화된 상담 정보를 영구 저장

---

## API 엔드포인트 상세

### 1. POST `/chat/start` - 상담 세션 시작

**설명**: 새로운 상담 세션을 생성하고 초기화합니다.

**요청**:
```json
POST http://localhost:8000/chat/start
Content-Type: application/json

{
  "channel": "web",
  "user_meta": {
    "user_id": "user_123",
    "device": "desktop"
  }
}
```

**파라미터**:
- `channel` (string, optional): 채널 구분 (기본값: "web")
- `user_meta` (object, optional): 사용자 메타데이터

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "state": "CASE_CLASSIFICATION",
    "bot_message": "안녕하세요. 법률 상담 챗봇입니다.\n\n상황을 3~5줄로 편하게 적어주세요. (언제/누가/무슨 일/금액/증거 여부 포함하면 더 좋아요)",
    "expected_input": {
      "type": "string",
      "description": "사건 상황 설명"
    }
  }
}
```

**처리 과정**:
1. 세션 ID 생성 (`sess_YYYYMMDD_XXXXXX` 형식)
2. `ChatSession` 테이블에 세션 레코드 생성
3. 초기 `StateContext` 생성
4. **INIT Node** 실행:
   - K0_Intake YAML에서 초기 메시지 로드
   - 긴급 상황 체크
   - 디스클레이머 출력
5. State를 `CASE_CLASSIFICATION`으로 전이
6. 응답 반환

**DB 저장**:
```sql
INSERT INTO chat_session (
    session_id, channel, current_state, status, completion_rate, started_at
) VALUES (
    'sess_20241223_abc123', 'web', 'CASE_CLASSIFICATION', 'ACTIVE', 0, NOW()
);
```

---

### 2. POST `/chat/message` - 사용자 메시지 처리

**설명**: 사용자 메시지를 받아 현재 State에 해당하는 Node를 실행하고 응답을 반환합니다.

**요청**:
```json
POST http://localhost:8000/chat/message
Content-Type: application/json

{
  "session_id": "sess_20241223_abc123",
  "user_message": "작년 10월에 계약했는데 5000만원을 안 줬어요. 계약서는 있어요."
}
```

**파라미터**:
- `session_id` (string, required): 세션 ID
- `user_message` (string, required): 사용자 메시지

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "current_state": "FACT_COLLECTION",
    "completion_rate": 45,
    "bot_message": "상대방의 성명 또는 상호를 알려주세요.",
    "expected_input": {
      "type": "string",
      "field": "counterparty",
      "description": "상대방 정보"
    }
  }
}
```

**처리 과정**:
1. 세션 ID 검증
2. 세션 상태 로드 (`chat_session_state` 테이블 또는 메모리)
3. `state["last_user_input"]` 업데이트
4. **현재 State에 해당하는 Node 실행**:
   - `CASE_CLASSIFICATION` → 분류 수행
   - `FACT_COLLECTION` → 사실 수집
   - `VALIDATION` → 검증 수행
   - `RE_QUESTION` → 재질문 생성
   - `SUMMARY` → 요약 생성
   - `COMPLETED` → 완료 처리
5. State 업데이트 및 저장
6. 응답 반환

**State별 처리**:

#### CASE_CLASSIFICATION State
```python
# 1. 키워드 추출
keywords = ["계약", "5000만원", "미지급"]

# 2. RAG K1 검색
rag_results = rag_searcher.search_by_knowledge_type(
    query="계약 미지급",
    knowledge_type="K1",
    top_k=3
)

# 3. GPT로 분류 확정
classification = gpt_client.classify_case(
    user_input=user_message,
    rag_context=rag_results
)
# 결과: {
#   "level1": "CIVIL",
#   "level2": "CIVIL_CONTRACT",
#   "scenario": "CONTRACT_NONPAYMENT"
# }

# 4. DB 저장
case_master = CaseMaster(
    session_id=session_id,
    main_case_type="CIVIL",
    sub_case_type="CIVIL_CONTRACT",
    case_stage="상담중"
)

# 5. State 전이
next_state = "FACT_COLLECTION"
```

#### FACT_COLLECTION State
```python
# 1. 엔티티 추출 (GPT API)
entities = gpt_client.extract_entities(user_message)
# 결과: {
#   "incident_date": "2023-10",
#   "amount": 50000000,
#   "evidence": True
# }

# 2. 사실과 감정 분리
facts, emotions = gpt_client.separate_facts_and_emotions(user_message)

# 3. RAG K2 조회 (필수 필드 및 질문)
k2_doc = rag_searcher.search_k2_by_scenario(
    scenario="CONTRACT_NONPAYMENT"
)
required_fields = k2_doc["required_fields"]  # ["incident_date", "counterparty", "amount"]

# 4. DB 저장
case_fact = CaseFact(
    case_id=case_id,
    fact_code="FACT_AMOUNT_KNOWN",
    fact_value="50000000",
    related_field="amount",
    confidence_score=95
)

# 5. Completion Rate 계산
collected_fields = ["incident_date", "amount", "evidence"]
completion_rate = (len(collected_fields) / len(required_fields)) * 100  # 45%

# 6. 다음 질문 선택
next_question = k2_doc["questions"][1]  # counterparty 질문

# 7. State 전이
next_state = "VALIDATION"
```

#### VALIDATION State
```python
# 1. 누락 필드 확인
missing_fields = set(required_fields) - set(collected_fields)
# 결과: ["counterparty"]

# 2. LEVEL4_FACT_Pattern 참조 (중요 사실 체크)
fact_pattern = rag_searcher.search_fact_pattern(
    scenario="CONTRACT_NONPAYMENT"
)
critical_facts = [f for f in fact_pattern["facts"] if f["critical"]]

# 3. 분기 결정
if len(missing_fields) > 0:
    next_state = "RE_QUESTION"
else:
    next_state = "SUMMARY"
```

#### RE_QUESTION State
```python
# 1. 누락 필드 우선순위 결정
# - CRITICAL=True인 필드 우선
# - QUESTION_ORDER가 낮은 필드 우선
priority_field = "counterparty"

# 2. K2 질문 템플릿 조회
question_template = k2_doc["questions"][1]
# {
#   "field": "counterparty",
#   "question": "상대방의 성명 또는 상호를 알려주세요.",
#   "answer_type": "string",
#   "required": true
# }

# 3. 재질문 생성
bot_message = question_template["question"]

# 4. State 전이 (Loop)
next_state = "FACT_COLLECTION"
```

#### SUMMARY State
```python
# 1. RAG K4 조회 (출력 포맷)
k4_doc = rag_searcher.search_k4_by_target(target="COUNSELOR")

# 2. GPT로 요약 생성
summary = gpt_client.generate_summary(
    facts=all_facts,
    format_template=k4_doc["sections"]
)

# 3. DB 저장
case_summary = CaseSummary(
    case_id=case_id,
    summary_text=summary["text"],
    structured_json=summary["structured_data"]
)

# 4. State 전이
next_state = "COMPLETED"
```

#### COMPLETED State
```python
# 1. RAG K3 조회 (리스크 규칙)
k3_doc = rag_searcher.search_k3_by_scenario(
    scenario="CONTRACT_NONPAYMENT"
)

# 2. 리스크 태그 추가
risk_tags = []
for rule in k3_doc["rules"]:
    if all(fact in collected_facts for fact in rule["trigger_facts"]):
        risk_tags.append(rule["risk_tag"])

# 3. 세션 종료 처리
session.status = "COMPLETED"
session.completion_rate = 100

# 4. State 전이
next_state = "END"
```

---

### 3. POST `/chat/end` - 상담 종료

**설명**: 상담 세션을 종료하고 최종 결과를 반환합니다.

**요청**:
```json
POST http://localhost:8000/chat/end
Content-Type: application/json

{
  "session_id": "sess_20241223_abc123"
}
```

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "final_state": "COMPLETED",
    "completion_rate": 100,
    "summary": {
      "summary_text": "2023년 10월 계약 체결 후 5000만원 미지급 사건...",
      "structured_data": {
        "case_type": "CIVIL / 계약",
        "incident_date": "2023-10",
        "amount": 50000000,
        "counterparty": "ABC회사"
      }
    }
  }
}
```

**처리 과정**:
1. 세션 검증
2. State가 `COMPLETED`가 아니면:
   - SUMMARY Node 실행
   - COMPLETED Node 실행
3. 최종 결과 조회 (`case_summary` 테이블)
4. 응답 반환

---

### 4. GET `/chat/status` - 상담 상태 조회

**설명**: 현재 상담 진행 상태를 조회합니다.

**요청**:
```
GET http://localhost:8000/chat/status?session_id=sess_20241223_abc123
```

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "state": "FACT_COLLECTION",
    "completion_rate": 45,
    "filled_fields": ["incident_date", "amount", "evidence"],
    "missing_fields": ["counterparty"]
  }
}
```

---

### 5. GET `/chat/result` - 최종 결과 조회

**설명**: 완료된 상담의 최종 결과를 조회합니다.

**요청**:
```
GET http://localhost:8000/chat/result?session_id=sess_20241223_abc123
```

**응답**:
```json
{
  "success": true,
  "data": {
    "case_summary_text": "2023년 10월 계약 체결 후 5000만원 미지급 사건...",
    "structured_data": {
      "case_type": "CIVIL / 계약",
      "scenario": "CONTRACT_NONPAYMENT",
      "facts": {
        "incident_date": "2023-10",
        "counterparty": "ABC회사",
        "amount": 50000000
      }
    },
    "completion_rate": 100
  }
}
```

---

## 데이터 처리 흐름도

### 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                    클라이언트 (프론트엔드)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /chat/start
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 서버                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /chat/start                                        │  │
│  │  1. SessionManager.create_session()                      │  │
│  │  2. create_initial_context()                             │  │
│  │  3. run_graph_step(state) → INIT Node                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Engine                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  INIT Node                                                │  │
│  │  ├─ K0_Intake YAML 로드                                   │  │
│  │  ├─ 초기 메시지 생성                                      │  │
│  │  └─ State: CASE_CLASSIFICATION                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 응답: bot_message
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    클라이언트                                    │
│  사용자 입력: "작년 10월에 계약했는데 5000만원을 안 줬어요"      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /chat/message
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 서버                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /chat/message                                       │  │
│  │  1. load_session_state()                                  │  │
│  │  2. state["last_user_input"] = user_message               │  │
│  │  3. run_graph_step(state) → CASE_CLASSIFICATION Node      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Engine                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CASE_CLASSIFICATION Node                                 │  │
│  │  ├─ keyword_extractor.extract_semantic_features()         │  │
│  │  ├─ RAG K1 검색 (키워드 매칭)                             │  │
│  │  ├─ GPT API: 분류 확정                                    │  │
│  │  ├─ DB 저장: case_master                                  │  │
│  │  └─ State: FACT_COLLECTION                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 응답: bot_message (다음 질문)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    클라이언트                                    │
│  사용자 입력: "ABC회사예요"                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /chat/message
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Engine                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FACT_COLLECTION Node                                     │  │
│  │  ├─ GPT API: 엔티티 추출 (날짜, 금액, 인물)               │  │
│  │  ├─ GPT API: 사실/감정 분리                               │  │
│  │  ├─ RAG K2 검색 (필수 필드, 질문 템플릿)                  │  │
│  │  ├─ DB 저장: case_fact, case_emotion                      │  │
│  │  ├─ Completion Rate 계산                                  │  │
│  │  └─ State: VALIDATION                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Engine                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VALIDATION Node                                          │  │
│  │  ├─ RAG K2: required_fields 조회                         │  │
│  │  ├─ 누락 필드 확인                                         │  │
│  │  ├─ RAG FACT: 중요 사실 체크                              │  │
│  │  └─ 분기: RE_QUESTION (누락) or SUMMARY (완료)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        │ (missing_fields 있음)                   │ (모든 필드 충족)
        ↓                                         ↓
┌───────────────────────────┐    ┌──────────────────────────────┐
│  RE_QUESTION Node        │    │  SUMMARY Node                │
│  ├─ 누락 필드 우선순위    │    │  ├─ RAG K4: 출력 포맷        │
│  ├─ K2 질문 템플릿 사용   │    │  ├─ GPT API: 요약 생성       │
│  └─ State: FACT_COLLECTION│    │  ├─ DB 저장: case_summary    │
│      (Loop)              │    │  └─ State: COMPLETED         │
└───────────┬───────────────┘    └──────────────────────────────┘
            │
            │ (Loop)
            └──────────→ FACT_COLLECTION
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Engine                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  COMPLETED Node                                          │  │
│  │  ├─ RAG K3: 리스크 규칙 조회                             │  │
│  │  ├─ 리스크 태그 추가                                      │  │
│  │  ├─ 세션 상태: COMPLETED                                  │  │
│  │  └─ State: END                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 응답: 최종 결과
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    클라이언트                                    │
│  상담 완료                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 단계별 상세 설명

### 1. INIT Node (초기화)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "INIT",
    "channel": "web"
}
```

**처리**:
1. **K0_Intake YAML 로드**
   ```yaml
   # data/rag/K0_intake/intake_messages.yaml
   messages:
     - step_code: START_MESSAGE
       order: 1
       message_text: "상황을 3~5줄로 적어주세요..."
       answer_type: string
       next_action: CLASSIFY
   ```

2. **초기 메시지 생성**
   ```python
   bot_message = "안녕하세요. 법률 상담 챗봇입니다.\n\n" + \
                 "상황을 3~5줄로 편하게 적어주세요..."
   ```

3. **DB 저장**
   ```sql
   INSERT INTO chat_session (
       session_id, channel, current_state, status, started_at
   ) VALUES (
       'sess_20241223_abc123', 'web', 'CASE_CLASSIFICATION', 'ACTIVE', NOW()
   );
   ```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "CASE_CLASSIFICATION",
    "bot_message": "상황을 3~5줄로 적어주세요...",
    "next_state": "CASE_CLASSIFICATION"
}
```

---

### 2. CASE_CLASSIFICATION Node (사건 분류)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "CASE_CLASSIFICATION",
    "last_user_input": "작년 10월에 계약했는데 5000만원을 안 줬어요"
}
```

**처리**:

#### 2.1 키워드 추출
```python
semantic_features = keyword_extractor.extract_semantic_features(
    "작년 10월에 계약했는데 5000만원을 안 줬어요"
)
# 결과:
# {
#   "keywords": ["계약", "5000만원", "미지급", "작년", "10월"],
#   "entities": {
#       "date": "2023-10",
#       "amount": 50000000
#   }
# }
```

#### 2.2 RAG K1 검색
```python
rag_results = rag_searcher.search_by_knowledge_type(
    query="계약 미지급",
    knowledge_type="K1",
    top_k=3
)
# 결과: [
#   {
#       "doc_id": "K1-CIVIL-CIVIL_CONTRACT",
#       "content": "LEVEL1: CIVIL\nLEVEL2: CIVIL_CONTRACT\n키워드: 계약, 대금, 미지급...",
#       "metadata": {
#           "level1": "CIVIL",
#           "level2_code": "CIVIL_CONTRACT",
#           "scenario_code": "CONTRACT_NONPAYMENT"
#       }
#   }
# ]
```

#### 2.3 GPT API로 분류 확정
```python
classification = gpt_client.classify_case(
    user_input="작년 10월에 계약했는데 5000만원을 안 줬어요",
    rag_context=rag_results,
    disambiguation_question=None  # 명확한 경우 None
)
# 결과:
# {
#   "level1": "CIVIL",
#   "level2": "CIVIL_CONTRACT",
#   "scenario": "CONTRACT_NONPAYMENT",
#   "confidence": 0.95
# }
```

#### 2.4 DB 저장
```python
case_master = CaseMaster(
    session_id="sess_20241223_abc123",
    main_case_type="CIVIL",
    sub_case_type="CIVIL_CONTRACT",
    case_stage="상담중",
    urgency_level="MID"
)
# case_id 자동 생성: 1
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "FACT_COLLECTION",
    "case_type": "CIVIL",
    "sub_case_type": "CIVIL_CONTRACT",
    "scenario": "CONTRACT_NONPAYMENT",
    "bot_message": "상대방의 성명 또는 상호를 알려주세요.",
    "next_state": "FACT_COLLECTION"
}
```

---

### 3. FACT_COLLECTION Node (사실 수집)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "FACT_COLLECTION",
    "last_user_input": "ABC회사예요",
    "case_type": "CIVIL",
    "sub_case_type": "CIVIL_CONTRACT",
    "scenario": "CONTRACT_NONPAYMENT"
}
```

**처리**:

#### 3.1 엔티티 추출 (GPT API)
```python
entities = gpt_client.extract_entities(
    "ABC회사예요",
    context="이전 대화: 계약했는데 5000만원을 안 줬어요"
)
# 결과:
# {
#   "counterparty": "ABC회사",
#   "counterparty_type": "법인"
# }
```

#### 3.2 사실과 감정 분리 (GPT API)
```python
facts, emotions = gpt_client.separate_facts_and_emotions(
    "작년 10월에 계약했는데 5000만원을 안 줬어요. 정말 화가 나요."
)
# facts: {
#   "incident_date": "2023-10",
#   "amount": 50000000,
#   "counterparty": "ABC회사",
#   "issue_description": "계약 대금 미지급"
# }
# emotions: [
#   {"emotion_type": "분노", "intensity": 0.8, "text": "정말 화가 나요"}
# ]
```

#### 3.3 RAG K2 조회
```python
k2_doc = rag_searcher.search_k2_by_scenario(
    scenario="CONTRACT_NONPAYMENT"
)
# 결과:
# {
#   "doc_id": "K2-CONTRACT_NONPAYMENT",
#   "required_fields": ["incident_date", "counterparty", "amount", "evidence"],
#   "questions": [
#       {"order": 1, "field": "incident_date", "question": "계약 또는 문제가 발생한 시점은 언제인가요?", ...},
#       {"order": 2, "field": "counterparty", "question": "상대방의 성명 또는 상호를 알려주세요.", ...},
#       ...
#   ]
# }
```

#### 3.4 DB 저장
```python
# CaseFact 저장
case_fact = CaseFact(
    case_id=1,
    fact_code="FACT_PARTY_IDENTIFIED",
    fact_value="ABC회사",
    related_field="counterparty",
    confidence_score=95,
    source="user_input"
)

# CaseEmotion 저장
case_emotion = CaseEmotion(
    case_id=1,
    emotion_type="분노",
    intensity_score=80,
    emotion_text="정말 화가 나요"
)
```

#### 3.5 Completion Rate 계산
```python
collected_fields = ["incident_date", "counterparty", "amount", "evidence"]
required_fields = ["incident_date", "counterparty", "amount", "evidence"]
completion_rate = (len(collected_fields) / len(required_fields)) * 100  # 100%
```

#### 3.6 다음 질문 선택
```python
# 모든 필수 필드 수집 완료
# 다음 질문 없음 → VALIDATION으로 이동
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "VALIDATION",
    "facts": {
        "incident_date": "2023-10",
        "counterparty": "ABC회사",
        "amount": 50000000,
        "evidence": True
    },
    "completion_rate": 100,
    "next_state": "VALIDATION"
}
```

---

### 4. VALIDATION Node (검증)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "VALIDATION",
    "facts": {
        "incident_date": "2023-10",
        "counterparty": "ABC회사",
        "amount": 50000000,
        "evidence": True
    },
    "scenario": "CONTRACT_NONPAYMENT"
}
```

**처리**:

#### 4.1 필수 필드 확인
```python
required_fields = ["incident_date", "counterparty", "amount", "evidence"]
collected_fields = list(state["facts"].keys())
missing_fields = set(required_fields) - set(collected_fields)
# 결과: set() (빈 집합, 모든 필드 수집 완료)
```

#### 4.2 중요 사실 체크 (RAG FACT)
```python
fact_pattern = rag_searcher.search_fact_pattern(
    scenario="CONTRACT_NONPAYMENT"
)
# 결과:
# {
#   "facts": [
#       {"fact_code": "FACT_DATE_KNOWN", "critical": True, ...},
#       {"fact_code": "FACT_PARTY_IDENTIFIED", "critical": True, ...},
#       {"fact_code": "FACT_AMOUNT_KNOWN", "critical": True, ...},
#       {"fact_code": "FACT_EVIDENCE_AVAILABLE", "critical": True, ...}
#   ]
# }

# 수집된 사실과 비교
collected_fact_codes = ["FACT_DATE_KNOWN", "FACT_PARTY_IDENTIFIED", 
                        "FACT_AMOUNT_KNOWN", "FACT_EVIDENCE_AVAILABLE"]
critical_facts = [f for f in fact_pattern["facts"] if f["critical"]]
all_critical_collected = all(
    f["fact_code"] in collected_fact_codes 
    for f in critical_facts
)
# 결과: True (모든 중요 사실 수집 완료)
```

#### 4.3 분기 결정
```python
if len(missing_fields) == 0 and all_critical_collected:
    next_state = "SUMMARY"
else:
    next_state = "RE_QUESTION"
# 결과: "SUMMARY"
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "SUMMARY",
    "missing_fields": [],
    "next_state": "SUMMARY"
}
```

---

### 5. RE_QUESTION Node (재질문) - Loop 케이스

**입력** (누락 필드가 있는 경우):
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "RE_QUESTION",
    "missing_fields": ["counterparty"],
    "scenario": "CONTRACT_NONPAYMENT"
}
```

**처리**:

#### 5.1 우선순위 결정
```python
# CRITICAL=True인 필드 우선
# QUESTION_ORDER가 낮은 필드 우선
priority_field = "counterparty"  # CRITICAL=True, order=2
```

#### 5.2 K2 질문 템플릿 조회
```python
k2_doc = rag_searcher.search_k2_by_scenario(
    scenario="CONTRACT_NONPAYMENT"
)
question = next(
    q for q in k2_doc["questions"] 
    if q["field"] == "counterparty"
)
# 결과:
# {
#   "order": 2,
#   "field": "counterparty",
#   "question": "상대방의 성명 또는 상호를 알려주세요.",
#   "answer_type": "string",
#   "required": True
# }
```

#### 5.3 재질문 생성
```python
bot_message = question["question"]
expected_input = {
    "type": question["answer_type"],
    "field": question["field"],
    "required": question["required"]
}
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "FACT_COLLECTION",
    "bot_message": "상대방의 성명 또는 상호를 알려주세요.",
    "expected_input": {
        "type": "string",
        "field": "counterparty",
        "required": True
    },
    "next_state": "FACT_COLLECTION"  # Loop
}
```

---

### 6. SUMMARY Node (요약 생성)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "SUMMARY",
    "facts": {
        "incident_date": "2023-10",
        "counterparty": "ABC회사",
        "amount": 50000000,
        "evidence": True
    },
    "case_type": "CIVIL",
    "sub_case_type": "CIVIL_CONTRACT",
    "scenario": "CONTRACT_NONPAYMENT"
}
```

**처리**:

#### 6.1 RAG K4 조회
```python
k4_doc = rag_searcher.search_k4_by_target(target="COUNSELOR")
# 결과:
# {
#   "doc_id": "K4_COUNSELOR_SUMMARY",
#   "target": "COUNSELOR",
#   "sections": [
#       {
#           "order": 1,
#           "key": "overview",
#           "title": "사건 개요",
#           "content_rule": "사용자 표현을 쉬운 말로 요약",
#           "source": "summary",
#           "style": "친절한 톤"
#       },
#       ...
#   ]
# }
```

#### 6.2 GPT API로 요약 생성
```python
summary = gpt_client.generate_summary(
    facts=state["facts"],
    format_template=k4_doc["sections"],
    case_type=state["case_type"],
    sub_case_type=state["sub_case_type"]
)
# 결과:
# {
#   "text": "2023년 10월 계약 체결 후 5000만원 미지급 사건입니다. 상대방은 ABC회사이며, 계약서를 보유하고 있습니다.",
#   "structured_data": {
#       "overview": "2023년 10월 계약 체결 후 5000만원 미지급",
#       "missing": [],
#       "emotion": ["분노"],
#       "handoff": "상담 연결 가이드"
#   }
# }
```

#### 6.3 DB 저장
```python
case_summary = CaseSummary(
    case_id=1,
    summary_text=summary["text"],
    structured_json=summary["structured_data"],
    target_audience="COUNSELOR"
)
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "COMPLETED",
    "summary": summary,
    "next_state": "COMPLETED"
}
```

---

### 7. COMPLETED Node (완료)

**입력**:
```python
state = {
    "session_id": "sess_20241223_abc123",
    "current_state": "COMPLETED",
    "scenario": "CONTRACT_NONPAYMENT",
    "facts": {...}
}
```

**처리**:

#### 7.1 RAG K3 조회 (리스크 규칙)
```python
k3_doc = rag_searcher.search_k3_by_scenario(
    scenario="CONTRACT_NONPAYMENT"
)
# 결과:
# {
#   "rules": [
#       {
#           "rule_code": "RISK_CONTRACT_NONPAYMENT_CORE",
#           "trigger_facts": ["FACT_DATE_KNOWN", "FACT_PARTY_IDENTIFIED", ...],
#           "risk_level": "HIGH",
#           "risk_tag": "대금 미지급_핵심충족"
#       }
#   ]
# }
```

#### 7.2 리스크 태그 추가
```python
collected_fact_codes = ["FACT_DATE_KNOWN", "FACT_PARTY_IDENTIFIED", 
                        "FACT_AMOUNT_KNOWN", "FACT_EVIDENCE_AVAILABLE"]
risk_tags = []
for rule in k3_doc["rules"]:
    if all(fact in collected_fact_codes for fact in rule["trigger_facts"]):
        risk_tags.append(rule["risk_tag"])
# 결과: ["대금 미지급_핵심충족"]
```

#### 7.3 세션 종료 처리
```python
session.status = "COMPLETED"
session.completion_rate = 100
session.completed_at = datetime.utcnow()
```

**출력**:
```python
{
    "session_id": "sess_20241223_abc123",
    "current_state": "END",
    "risk_tags": ["대금 미지급_핵심충족"],
    "session_status": "COMPLETED"
}
```

---

## 데이터 구조

### StateContext 구조

```python
StateContext = {
    "session_id": str,                    # 세션 ID
    "current_state": str,                 # 현재 State (INIT, CASE_CLASSIFICATION, ...)
    "case_type": Optional[str],           # LEVEL1 (CIVIL, CRIMINAL, FAMILY, ADMIN)
    "sub_case_type": Optional[str],       # LEVEL2 (CIVIL_CONTRACT, ...)
    "scenario": Optional[str],            # LEVEL3 (CONTRACT_NONPAYMENT, ...)
    "facts": Dict[str, Any],              # 수집된 사실
    "emotion": List[Dict[str, Any]],      # 감정 정보
    "completion_rate": int,               # 완성도 (0~100)
    "last_user_input": str,               # 마지막 사용자 입력
    "missing_fields": List[str],          # 누락된 필수 필드
    "bot_message": Optional[str],         # 봇 응답 메시지
    "expected_input": Optional[Dict],      # 기대하는 입력 정보
    "next_state": Optional[str]           # 다음 State
}
```

### DB 테이블 구조

#### chat_session
```sql
CREATE TABLE chat_session (
    session_id VARCHAR(50) PRIMARY KEY,
    channel VARCHAR(20),
    user_hash VARCHAR(64),
    current_state VARCHAR(30),
    status VARCHAR(20),              -- ACTIVE, COMPLETED, ABORTED
    completion_rate INT,             -- 0~100
    started_at DATETIME,
    completed_at DATETIME
);
```

#### case_master
```sql
CREATE TABLE case_master (
    case_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(50) UNIQUE,
    main_case_type VARCHAR(50),      -- CIVIL, CRIMINAL, FAMILY, ADMIN
    sub_case_type VARCHAR(50),     -- CIVIL_CONTRACT, ...
    case_stage VARCHAR(30),        -- 상담전, 상담중, 상담완료
    urgency_level VARCHAR(20),    -- LOW, MID, HIGH
    estimated_value BIGINT,
    created_at DATETIME,
    updated_at DATETIME
);
```

#### case_fact
```sql
CREATE TABLE case_fact (
    fact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id BIGINT,
    fact_code VARCHAR(50),         -- FACT_DATE_KNOWN, FACT_AMOUNT_KNOWN, ...
    fact_value TEXT,
    related_field VARCHAR(50),     -- incident_date, amount, ...
    confidence_score INT,          -- 0~100
    source VARCHAR(50),            -- user_input, gpt_extraction, ...
    created_at DATETIME
);
```

#### case_emotion
```sql
CREATE TABLE case_emotion (
    emotion_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id BIGINT,
    emotion_type VARCHAR(50),      -- 분노, 불안, 슬픔, ...
    intensity_score INT,           -- 0~100
    emotion_text TEXT,
    created_at DATETIME
);
```

#### case_summary
```sql
CREATE TABLE case_summary (
    summary_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id BIGINT UNIQUE,
    summary_text TEXT,
    structured_json JSON,
    target_audience VARCHAR(50),   -- COUNSELOR, LAWYER, CRM, INTERNAL
    created_at DATETIME
);
```

---

## 실제 사용 예시

### 시나리오: 계약 대금 미지급 상담

#### Step 1: 세션 시작
```bash
curl -X POST http://localhost:8000/chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "user_meta": {"user_id": "user_123"}
  }'
```

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "state": "CASE_CLASSIFICATION",
    "bot_message": "안녕하세요. 법률 상담 챗봇입니다.\n\n상황을 3~5줄로 편하게 적어주세요...",
    "expected_input": {
      "type": "string",
      "description": "사건 상황 설명"
    }
  }
}
```

#### Step 2: 첫 입력 (사건 설명)
```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_20241223_abc123",
    "user_message": "작년 10월에 계약했는데 5000만원을 안 줬어요. 계약서는 있어요."
  }'
```

**처리 과정**:
1. **CASE_CLASSIFICATION Node 실행**
   - 키워드 추출: ["계약", "5000만원", "미지급", "작년", "10월"]
   - RAG K1 검색 → `CIVIL_CONTRACT / CONTRACT_NONPAYMENT` 매칭
   - GPT 분류 확정
   - DB 저장: `case_master` 생성

2. **FACT_COLLECTION Node 실행**
   - 엔티티 추출: `incident_date="2023-10"`, `amount=50000000`, `evidence=True`
   - 사실/감정 분리
   - DB 저장: `case_fact` 3개 레코드 생성
   - Completion Rate: 45% (4개 중 3개 수집)

3. **VALIDATION Node 실행**
   - 누락 필드: `["counterparty"]`
   - 분기: `RE_QUESTION`

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "current_state": "FACT_COLLECTION",
    "completion_rate": 45,
    "bot_message": "상대방의 성명 또는 상호를 알려주세요.",
    "expected_input": {
      "type": "string",
      "field": "counterparty",
      "required": true
    }
  }
}
```

#### Step 3: 상대방 정보 입력
```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_20241223_abc123",
    "user_message": "ABC회사예요"
  }'
```

**처리 과정**:
1. **FACT_COLLECTION Node 실행**
   - 엔티티 추출: `counterparty="ABC회사"`
   - DB 저장: `case_fact` 추가
   - Completion Rate: 100%

2. **VALIDATION Node 실행**
   - 누락 필드: `[]` (없음)
   - 분기: `SUMMARY`

3. **SUMMARY Node 실행**
   - RAG K4 조회 → 출력 포맷 로드
   - GPT 요약 생성
   - DB 저장: `case_summary` 생성

4. **COMPLETED Node 실행**
   - RAG K3 조회 → 리스크 규칙 확인
   - 리스크 태그 추가: `["대금 미지급_핵심충족"]`
   - 세션 종료

**응답**:
```json
{
  "success": true,
  "data": {
    "session_id": "sess_20241223_abc123",
    "current_state": "COMPLETED",
    "completion_rate": 100,
    "bot_message": "상담이 완료되었습니다. 요약 정보는 /chat/result 엔드포인트에서 확인할 수 있습니다.",
    "expected_input": null
  }
}
```

#### Step 4: 최종 결과 조회
```bash
curl http://localhost:8000/chat/result?session_id=sess_20241223_abc123
```

**응답**:
```json
{
  "success": true,
  "data": {
    "case_summary_text": "2023년 10월 계약 체결 후 5000만원 미지급 사건입니다. 상대방은 ABC회사이며, 계약서를 보유하고 있습니다.",
    "structured_data": {
      "overview": "2023년 10월 계약 체결 후 5000만원 미지급",
      "missing": [],
      "emotion": ["분노"],
      "handoff": "상담 연결 가이드: 핵심 사실이 충분히 확인된 상태로 상담 연결 및 사건 검토 진행 권장"
    },
    "completion_rate": 100
  }
}
```

---

## 데이터 변환 흐름

### 사용자 입력 → 구조화된 데이터

```
사용자 입력 (자연어)
    ↓
[GPT API: 엔티티 추출]
    ↓
구조화된 사실 (Dict)
    ↓
[DB 저장: case_fact]
    ↓
영구 저장 (MySQL)
```

### 예시 변환

**입력**:
```
"작년 10월에 계약했는데 5000만원을 안 줬어요. ABC회사예요. 정말 화가 나요."
```

**변환 과정**:

1. **엔티티 추출**:
   ```python
   {
       "incident_date": "2023-10",
       "amount": 50000000,
       "counterparty": "ABC회사",
       "evidence": True  # "계약서는 있어요" → True
   }
   ```

2. **사실/감정 분리**:
   ```python
   facts = {
       "incident_date": "2023-10",
       "amount": 50000000,
       "counterparty": "ABC회사",
       "issue_description": "계약 대금 미지급"
   }
   emotions = [
       {"emotion_type": "분노", "intensity": 80, "text": "정말 화가 나요"}
   ]
   ```

3. **DB 저장**:
   ```sql
   -- case_fact 테이블
   INSERT INTO case_fact (case_id, fact_code, fact_value, related_field, confidence_score)
   VALUES
   (1, 'FACT_DATE_KNOWN', '2023-10', 'incident_date', 95),
   (1, 'FACT_AMOUNT_KNOWN', '50000000', 'amount', 95),
   (1, 'FACT_PARTY_IDENTIFIED', 'ABC회사', 'counterparty', 95),
   (1, 'FACT_CONTRACT_EXIST', 'true', 'contract_type', 90),
   (1, 'FACT_NONPERFORMANCE', 'true', 'issue_description', 95);

   -- case_emotion 테이블
   INSERT INTO case_emotion (case_id, emotion_type, intensity_score, emotion_text)
   VALUES
   (1, '분노', 80, '정말 화가 나요');
   ```

4. **요약 생성**:
   ```python
   {
       "summary_text": "2023년 10월 계약 체결 후 5000만원 미지급 사건...",
       "structured_data": {
           "overview": "2023년 10월 계약 체결 후 5000만원 미지급",
           "facts": {
               "incident_date": "2023-10",
               "counterparty": "ABC회사",
               "amount": 50000000
           }
       }
   }
   ```

---

## State 전이 상세

### State 전이 다이어그램

```
┌─────────┐
│  INIT   │
└────┬────┘
     │ (항상)
     ↓
┌─────────────────────┐
│ CASE_CLASSIFICATION │
└────┬────────────────┘
     │ (항상)
     ↓
┌─────────────────┐
│ FACT_COLLECTION │
└────┬────────────┘
     │ (항상)
     ↓
┌─────────────┐
│ VALIDATION  │
└───┬─────┬───┘
    │     │
    │     │ (모든 필드 충족)
    │     ↓
    │ ┌─────────┐
    │ │ SUMMARY │
    │ └────┬────┘
    │      │ (항상)
    │      ↓
    │ ┌───────────┐
    │ │ COMPLETED │
    │ └─────┬─────┘
    │       │ (항상)
    │       ↓
    │      END
    │
    │ (누락 필드 있음)
    ↓
┌─────────────┐
│ RE_QUESTION │
└─────┬───────┘
      │ (항상, Loop)
      └────→ FACT_COLLECTION
```

### State 전이 조건

| 현재 State | 다음 State | 조건 |
|-----------|-----------|------|
| INIT | CASE_CLASSIFICATION | 항상 |
| CASE_CLASSIFICATION | FACT_COLLECTION | 항상 |
| FACT_COLLECTION | VALIDATION | 항상 |
| VALIDATION | RE_QUESTION | `len(missing_fields) > 0` |
| VALIDATION | SUMMARY | `len(missing_fields) == 0` |
| RE_QUESTION | FACT_COLLECTION | 항상 (Loop) |
| SUMMARY | COMPLETED | 항상 |
| COMPLETED | END | 항상 |

---

## 에러 처리

### 일반적인 에러

#### 1. 세션을 찾을 수 없음
```json
{
  "success": false,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "세션을 찾을 수 없습니다: sess_20241223_abc123"
  }
}
```

**해결**: `/chat/start`로 새 세션 생성

#### 2. 유효하지 않은 세션 ID
```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "유효하지 않은 세션 ID 형식입니다.",
    "field": "session_id"
  }
}
```

**해결**: 올바른 세션 ID 형식 사용 (`sess_YYYYMMDD_XXXXXX`)

#### 3. 상담이 아직 완료되지 않음
```json
{
  "success": false,
  "error": {
    "code": "SESSION_NOT_COMPLETED",
    "message": "상담이 아직 완료되지 않았습니다."
  }
}
```

**해결**: `/chat/end`로 상담 종료 후 `/chat/result` 호출

### State별 에러 처리

#### CASE_CLASSIFICATION 실패
- **원인**: 분류가 애매하거나 RAG 문서를 찾을 수 없음
- **처리**: `DISAMBIGUATION_QUESTION` 사용 또는 기본 분류 적용

#### FACT_COLLECTION 실패
- **원인**: 엔티티 추출 실패
- **처리**: 사용자에게 재입력 요청

#### VALIDATION 실패
- **원인**: 필수 필드 누락
- **처리**: `RE_QUESTION`으로 재질문

---

## RAG 문서 매핑 상세

| LangGraph Node | RAG 문서 타입 | 검색 방법 | 사용 목적 |
|---------------|-------------|----------|----------|
| **INIT** | K0_Intake | `search_k0_messages()` | 초기 메시지, 디스클레이머, 긴급 체크 |
| **CASE_CLASSIFICATION** | K1_Classification | `search_by_knowledge_type("K1")` | 사건 유형 분류 기준 (키워드, 표현, 확인 질문) |
| **FACT_COLLECTION** | K2_Questions | `search_k2_by_scenario()` | 필수 필드 목록, 질문 템플릿 |
| **VALIDATION** | K2_Questions, FACT | `search_k2_by_scenario()`, `search_fact_pattern()` | 필수 필드 검증, 중요 사실 체크 |
| **RE_QUESTION** | K2_Questions | `search_k2_by_scenario()` | 재질문 템플릿 |
| **SUMMARY** | K4_Output_Format | `search_k4_by_target()` | 요약 포맷, 스타일 규칙 |
| **COMPLETED** | K3_Risk_Rules | `search_k3_by_scenario()` | 리스크 태그, 주의사항 |

---

## 성능 최적화

### 1. RAG 검색 캐싱
- 동일한 시나리오의 K2, K3, K4 문서는 캐싱
- 세션 내에서 재사용

### 2. GPT API 호출 최소화
- 엔티티 추출과 사실/감정 분리를 한 번에 수행
- 배치 처리 가능한 경우 배치로 처리

### 3. DB 쿼리 최적화
- 세션 상태는 메모리 캐시 사용
- 자주 조회하는 데이터는 인덱스 활용

---

## 확장 가능성

### 새로운 시나리오 추가
1. 엑셀에 K1, K2, K3, FACT 시트에 행 추가
2. `python scripts/generate_all_yaml.py` 실행
3. `POST /rag/index` 호출하여 재인덱싱
4. LangGraph 코드 수정 불필요

### 새로운 질문 추가
1. 엑셀 K2_Questions 시트에 행 추가
2. YAML 재생성 및 재인덱싱
3. 다음 실행부터 자동 반영

### 새로운 리스크 규칙 추가
1. 엑셀 K3_Risk_Rules 시트에 행 추가
2. YAML 재생성 및 재인덱싱
3. COMPLETED Node에서 자동 적용

---

## 모니터링 및 로깅

### 주요 로그 포인트
- 세션 생성/종료
- State 전이
- RAG 검색 결과
- GPT API 호출
- DB 저장 성공/실패
- 에러 발생

### 로그 예시
```
2025-12-23 19:00:00 [INFO] 세션 생성: sess_20241223_abc123
2025-12-23 19:00:01 [INFO] State 전이: INIT → CASE_CLASSIFICATION
2025-12-23 19:00:02 [INFO] RAG 검색: K1, top_k=3, 결과=1개
2025-12-23 19:00:03 [INFO] GPT API 호출: classify_case, 소요시간=1.2초
2025-12-23 19:00:04 [INFO] DB 저장: case_master, case_id=1
2025-12-23 19:00:05 [INFO] State 전이: CASE_CLASSIFICATION → FACT_COLLECTION
```

---

## 보안 고려사항

### 1. 세션 관리
- 세션 ID는 예측 불가능한 형식 사용
- 세션 타임아웃 설정 (예: 30분)

### 2. 개인정보 보호
- 민감한 정보는 DB에 암호화 저장
- 로그에 개인정보 포함 금지

### 3. 입력 검증
- 사용자 입력 길이 제한
- SQL Injection 방지 (ORM 사용)
- XSS 방지 (입력 sanitization)

---

---

## 세션 상태 관리 상세

### 세션 상태 저장/로드 메커니즘

세션 상태는 **요청 간에 DB를 통해 유지**됩니다. 각 요청마다 상태를 로드하고, Node 실행 후 상태를 저장합니다.

#### 상태 로드 과정 (`load_session_state`)

```python
# 1. ChatSession 테이블에서 기본 정보 로드
session = db_session.query(ChatSession).filter(
    ChatSession.session_id == session_id
).first()

context = {
    "session_id": session_id,
    "current_state": session.current_state,  # 예: "FACT_COLLECTION"
    "completion_rate": session.completion_rate  # 예: 45
}

# 2. CaseMaster에서 사건 정보 로드
case = db_session.query(CaseMaster).filter(
    CaseMaster.session_id == session_id
).first()

if case:
    context["case_type"] = case.main_case_type  # 예: "CIVIL"
    context["sub_case_type"] = case.sub_case_type  # 예: "CIVIL_CONTRACT"

# 3. CaseFact에서 facts 복원
facts = {}
case_facts = db_session.query(CaseFact).filter(
    CaseFact.case_id == case.case_id
).all()

for fact in case_facts:
    if fact.related_field == "incident_date":
        facts["incident_date"] = fact.fact_value  # 예: "2025-12-10"
    elif fact.related_field == "amount":
        facts["amount"] = int(fact.fact_value)  # 예: 20000000
    # ... 기타 필드

# 4. CaseParty에서 counterparty 복원
case_parties = db_session.query(CaseParty).filter(
    CaseParty.case_id == case.case_id,
    CaseParty.party_role == "상대방"
).all()

if case_parties:
    party = case_parties[0]
    facts["counterparty"] = party.party_description  # 예: "ABC회사"
    facts["counterparty_type"] = party.party_type  # 예: "법인"

# 5. CaseEvidence에서 evidence 복원
case_evidences = db_session.query(CaseEvidence).filter(
    CaseEvidence.case_id == case.case_id
).all()

if case_evidences:
    evidence = case_evidences[0]
    facts["evidence"] = evidence.available  # 예: True

context["facts"] = facts
```

#### 상태 저장 과정 (`save_session_state`)

```python
# 각 Node 실행 후 자동 호출
def save_session_state(session_id: str, state: StateContext):
    with db_manager.get_db_session() as db_session:
        # 1. ChatSession 업데이트
        session = db_session.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        session.current_state = state["current_state"]
        session.completion_rate = state.get("completion_rate", 0)
        
        # 2. CaseMaster 업데이트 (있는 경우)
        case = db_session.query(CaseMaster).filter(
            CaseMaster.session_id == session_id
        ).first()
        
        if case:
            case.main_case_type = state.get("case_type")
            case.sub_case_type = state.get("sub_case_type")
        
        # 3. Facts는 각 Node에서 직접 저장
        # (CaseFact, CaseParty, CaseEvidence 테이블에 저장)
        
        db_session.commit()
```

### 상태 저장 시점

| Node | 저장 시점 | 저장 내용 |
|------|----------|----------|
| **INIT** | Node 실행 후 | `ChatSession.current_state = "CASE_CLASSIFICATION"` |
| **CASE_CLASSIFICATION** | Node 실행 후 | `CaseMaster` 생성/업데이트, `ChatSession.current_state` |
| **FACT_COLLECTION** | Node 실행 후 | `CaseFact`, `CaseParty`, `CaseEvidence` 저장, `ChatSession.current_state` |
| **VALIDATION** | Node 실행 후 | `CaseFact`, `CaseParty`, `CaseEvidence` 업데이트, `ChatSession.current_state` |
| **RE_QUESTION** | Node 실행 후 | `ChatSession.current_state` |
| **SUMMARY** | Node 실행 후 | `CaseSummary` 생성, `ChatSession.current_state` |
| **COMPLETED** | Node 실행 후 | `ChatSession.status = "COMPLETED"`, `ChatSession.current_state = "COMPLETED"` |

---

## 프롬프트 파일 시스템

### 프롬프트 파일 구조

요약 생성 프롬프트는 케이스 타입별로 별도 파일로 관리됩니다.

```
src/prompts/summary/
├── default.txt              # 기본 프롬프트
├── family_divorce.txt       # 이혼 사건
├── family_inheritance.txt   # 상속 사건
├── civil_loan.txt           # 대여금 사건
├── civil_contract.txt       # 계약 분쟁 사건
├── civil_damages.txt        # 손해배상 사건
├── criminal_fraud.txt       # 사기 사건
├── criminal_assault.txt     # 폭행 사건
├── criminal_theft.txt       # 절도 사건
└── admin_default.txt        # 행정처분 사건
```

### 프롬프트 로드 메커니즘

```python
# 1. 케이스 타입에 따른 프롬프트 파일명 결정
prompt_name = prompt_loader.get_summary_prompt_name(
    main_case_type="CRIMINAL",
    sub_case_type="사기"
)
# 결과: "criminal_fraud"

# 2. 프롬프트 파일 로드
prompt_template = prompt_loader.load_prompt(
    template_name="criminal_fraud",
    sub_dir="summary"
)

# 3. 변수 치환
prompt = prompt_template.format(
    case_type="CRIMINAL / 사기",
    facts={"incident_date": "2025-12-10", "amount": 20000000},
    emotions=[],
    completion_rate=100,
    user_inputs_section="사용자 입력 내용...",
    sections_info="섹션 정보...",
    important_info_guide_first="피해 금액, 사기 수법..."
)
```

### 프롬프트 파일 형식

```txt
다음 정보를 바탕으로 사기 상담용 사건 요약을 작성하세요.

사건 유형: {case_type}
수집된 사실: {facts}
감정 정보: {emotions}
완성도: {completion_rate}%
{user_inputs_section}

요약 섹션 구성:
{sections_info}

중요 지침:
1. 사용자 입력 내용에 언급된 모든 중요한 사실을 반드시 포함하세요
2. 피해 금액, 사기 수법을 명시적으로 기록하세요
...
```

### 프롬프트 수정 방법

1. **파일 직접 수정**: `src/prompts/summary/` 디렉토리의 `.txt` 파일 편집
2. **서버 재시작**: 변경사항은 서버 재시작 후 적용 (매 요청마다 파일 로드)
3. **변수 사용**: `{variable_name}` 형식으로 변수 사용 가능

---

## 날짜 해석 로직 상세

### 문제 상황

사기 케이스에서 날짜의 의미가 모호할 수 있습니다:
- **"12월 10일에 인지"**: 피해 인지 날짜 (사기 발생 날짜 아님)
- **"12월 10일에 계약"**: 사기 발생/계약 체결 날짜

### 해결 방법

#### 1. 키워드 기반 날짜 맥락 감지

```python
# 사용자 입력 분석
user_input = "12월 10일에 인지"

# 날짜 맥락 키워드 확인
date_context_keywords = {
    "피해 인지": ["인지", "알게", "발견", "알았", "깨달"],
    "사기 발생": ["계약", "체결", "송금", "입금", "발생"]
}

# 맥락 결정
if any(kw in user_input for kw in date_context_keywords["피해 인지"]):
    date_context = "피해 인지 날짜"
elif any(kw in user_input for kw in date_context_keywords["사기 발생"]):
    date_context = "사기 발생 날짜"
```

#### 2. 프롬프트에 맥락 정보 포함

```python
# summarizer.py에서 자동 감지
if main_case_type == "CRIMINAL" and sub_case_type == "사기":
    if any(keyword in user_inputs for keyword in ["인지", "알게", "발견"]):
        date_context_note = """
⚠️ 중요: 사용자 입력에 '인지', '알게', '발견' 등의 키워드가 있습니다. 
incident_date는 '사기 발생 날짜'가 아니라 '피해 인지 날짜'로 해석해야 합니다.
"""
```

#### 3. 프롬프트 파일에 지침 포함

```txt
5. 날짜 정보 해석 주의사항:
   - 사용자 입력에 "인지", "알게", "발견" 등의 키워드가 있으면 
     incident_date는 "피해 인지 날짜"입니다
   - "계약", "체결", "송금", "입금" 등의 키워드가 있으면 
     해당 날짜는 "사기 발생/계약 체결 날짜"입니다
   - 사용자 입력을 정확히 확인하여 날짜의 의미를 올바르게 해석하세요
```

### 실제 처리 예시

**입력**: "12월 10일에 인지"

**처리 과정**:
1. `validation_node`에서 날짜 추출: `incident_date = "2025-12-10"`
2. 키워드 감지: "인지" → 피해 인지 날짜로 해석
3. `summarizer`에서 프롬프트에 경고 메시지 추가
4. GPT가 요약 생성 시: "2025년 12월 10일에 사기 피해를 인지했다" (올바른 해석)

---

## 증거 추출 로직 상세

### 증거 추출 개선 사항

이전에는 너무 관대한 키워드 매칭으로 인해 잘못된 추출이 발생했습니다.

#### 이전 문제점

```python
# 문제: "있음", "있어" 같은 일반 키워드
evidence_keywords = ["있음", "있어", "네", "그래", "예"]

# "연락이 되지 않고 있음" → "있음" 매칭 → evidence=True (잘못됨)
```

#### 개선된 로직

```python
# 1. 명시적 증거 키워드만 사용
evidence_keywords_positive = [
    "증거", "계약서", "카톡", "이체", "내역", "대화", "송금",
    "대화내역", "송금내역", "계좌이체", "문서", "사진", "영상", "녹음", "증빙", "자료"
]

# 2. 단어 경계 확인 (정확한 매칭)
import re
for keyword in evidence_keywords_positive:
    pattern = r'\b' + re.escape(keyword) + r'\b'
    if re.search(pattern, user_input_lower):
        evidence = True
        break

# 3. 일반 응답 키워드 제거
# "있음", "있어", "네", "그래", "예" 제거
```

### 증거 추출 시나리오

| 사용자 입력 | 키워드 매칭 | 결과 | 설명 |
|-----------|-----------|------|------|
| "계약서 있어요" | "계약서" | `evidence=True` | ✅ 정확 |
| "카톡 대화내역 있음" | "카톡", "대화내역" | `evidence=True` | ✅ 정확 |
| "연락이 되지 않고 있음" | 없음 | `evidence=None` | ✅ 정확 (이전에는 True였음) |
| "증거 없어요" | "증거" + 부정 키워드 | `evidence=False` | ✅ 정확 |
| "투자 계약서 있음" | "계약서" | `evidence=True` | ✅ 정확 |

---

## 병렬 처리 최적화

### FACT_COLLECTION Node의 병렬 처리

엔티티 추출, 사실/감정 분리, RAG 검색을 병렬로 실행하여 지연 시간을 줄입니다.

```python
from concurrent.futures import ThreadPoolExecutor

# 병렬 실행
with ThreadPoolExecutor(max_workers=3) as executor:
    # 1. 엔티티 추출 (GPT API)
    future_entities = executor.submit(
        entity_extractor.extract_all_entities,
        user_input,
        fields_to_extract=fields_to_extract
    )
    
    # 2. 사실/감정 분리 (GPT API)
    future_fact_emotion = executor.submit(
        fact_emotion_splitter.split_fact_emotion,
        user_input,
        case_type=case_type
    )
    
    # 3. RAG 검색 (벡터 검색)
    future_rag = executor.submit(
        rag_searcher.search,
        query=user_input,
        knowledge_type="K2",
        main_case_type=case_type,
        sub_case_type=sub_case_type,
        top_k=3
    )
    
    # 결과 대기
    entities = future_entities.result()
    fact_emotion = future_fact_emotion.result()
    rag_results = future_rag.result()
```

### 성능 개선 효과

| 처리 방식 | 소요 시간 | 개선율 |
|---------|---------|--------|
| 순차 처리 | ~15초 | - |
| 병렬 처리 | ~5초 | **66% 감소** |

---

## 실제 대화 예시 (전체 흐름)

### 시나리오: 사기 피해 상담

#### Step 1: 세션 시작
```
POST /chat/start
{
  "channel": "web",
  "user_meta": {"user_id": "user_123"}
}

응답:
{
  "session_id": "sess_7308ab7176a9",
  "state": "CASE_CLASSIFICATION",
  "bot_message": "안내: 본 서비스는 법률 자문이 아니라...\n\n어떤 일로 상담이 필요하신가요?",
  "expected_input": {"type": "choice", "description": "선택"}
}
```

#### Step 2: 첫 입력 (사건 설명)
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "사기를 당했어요"
}

처리:
1. CASE_CLASSIFICATION Node 실행
   - 키워드 추출: ["사기"]
   - RAG K1 검색 → CRIMINAL / 사기 매칭
   - GPT 분류 확정: main_case_type="CRIMINAL", sub_case_type="사기"
   - DB 저장: CaseMaster 생성

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "FACT_COLLECTION",
  "bot_message": "사건과 관련된 구체적인 내용을 알려주세요.",
  "expected_input": {"type": "string", "description": "사건 상세 설명"}
}
```

#### Step 3: 상세 설명
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "현재 새로나온 종목에 투자하면 높은 이익을 얻을수 있다고 해서 투자를 했는데 연락이 되지 않고 있음"
}

처리:
1. FACT_COLLECTION Node 실행 (병렬 처리)
   - 엔티티 추출: action_description="투자 사기"
   - 사실/감정 분리: facts=[], emotions=[{"type": "불안", "intensity": 70}]
   - RAG K2 검색: required_fields=["incident_date", "counterparty", "amount", "evidence"]
   - 증거 추출: "있음" 키워드 없음 → evidence=None (개선된 로직)
   - DB 저장: CaseFact, CaseEmotion 저장

2. VALIDATION Node 실행
   - 누락 필드: ["incident_date", "counterparty", "amount", "evidence"]
   - 분기: RE_QUESTION

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "FACT_COLLECTION",
  "bot_message": "사건이 발생한 날짜를 알려주세요.",
  "expected_input": {"type": "date", "field": "incident_date"}
}
```

#### Step 4: 날짜 입력
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "12월 10일에 인지"
}

처리:
1. VALIDATION Node 실행
   - 날짜 패턴 감지: "월", "일", "인지" → 날짜로 해석
   - 날짜 추출: incident_date="2025-12-10"
   - "인지" 키워드 감지 → 피해 인지 날짜로 기록
   - DB 저장: CaseFact 저장

2. FACT_COLLECTION Node 실행
   - 엔티티 추출: incident_date="2025-12-10"
   - DB 저장: CaseFact 업데이트

3. VALIDATION Node 실행
   - 누락 필드: ["counterparty", "amount", "evidence"]
   - 분기: RE_QUESTION

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "FACT_COLLECTION",
  "bot_message": "문제가 된 금액은 얼마인가요?",
  "expected_input": {"type": "number", "field": "amount"}
}
```

#### Step 5: 금액 입력
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "2000만원"
}

처리:
1. FACT_COLLECTION Node 실행
   - 엔티티 추출: amount=20000000
   - DB 저장: CaseFact 저장

2. VALIDATION Node 실행
   - 누락 필드: ["counterparty", "evidence"]
   - 분기: RE_QUESTION

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "FACT_COLLECTION",
  "bot_message": "계약 상대방은 누구인가요?",
  "expected_input": {"type": "string", "field": "counterparty"}
}
```

#### Step 6: 상대방 정보 입력
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "지인이 추천한 투자 전문가"
}

처리:
1. VALIDATION Node 실행
   - counterparty 저장: "지인이 추천한 투자 전문가"
   - DB 저장: CaseParty 저장

2. FACT_COLLECTION Node 실행
   - 엔티티 추출: counterparty="지인이 추천한 투자 전문가"
   - DB 저장: CaseParty 업데이트

3. VALIDATION Node 실행
   - 누락 필드: ["evidence"]
   - 분기: RE_QUESTION

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "FACT_COLLECTION",
  "bot_message": "계약서나 관련 증거를 가지고 계신가요?",
  "expected_input": {"type": "boolean", "field": "evidence"}
}
```

#### Step 7: 증거 입력
```
POST /chat/message
{
  "session_id": "sess_7308ab7176a9",
  "user_message": "투자 계약서 있음"
}

처리:
1. VALIDATION Node 실행
   - 증거 키워드 매칭: "계약서" → evidence=True
   - DB 저장: CaseEvidence 저장

2. FACT_COLLECTION Node 실행
   - 증거 추출: evidence=True
   - DB 저장: CaseEvidence 업데이트

3. VALIDATION Node 실행
   - 누락 필드: [] (없음)
   - 분기: SUMMARY

4. SUMMARY Node 실행
   - RAG K4 조회: 출력 포맷 로드
   - 프롬프트 로드: criminal_fraud.txt
   - 날짜 맥락 감지: "인지" 키워드 → 피해 인지 날짜로 해석
   - GPT 요약 생성
   - DB 저장: CaseSummary 생성

5. COMPLETED Node 실행
   - 세션 종료 처리
   - 최종 메시지 생성

응답:
{
  "session_id": "sess_7308ab7176a9",
  "current_state": "COMPLETED",
  "bot_message": "상담에 필요한 정보를 확인했습니다. 자료 확인 후 상담 전화를 드리오니 받아 주시기 부탁드립니다.",
  "expected_input": null
}
```

---

## 에러 처리 상세

### Node별 에러 처리

#### CASE_CLASSIFICATION Node 에러

**에러 케이스 1: GPT 분류 실패**
```python
try:
    classification = gpt_client.classify_case(...)
except Exception as e:
    logger.error(f"GPT 분류 실패: {str(e)}")
    # 폴백: 키워드 기반 간단한 분류
    if any(kw in user_input for kw in ["돈", "빌려", "대여금"]):
        main_case_type = "CIVIL"
        sub_case_type = "CIVIL_CONTRACT"
    elif any(kw in user_input for kw in ["사기", "절도", "폭행"]):
        main_case_type = "CRIMINAL"
        sub_case_type = "CRIMINAL_FRAUD"
```

**에러 케이스 2: RAG 검색 실패**
```python
try:
    rag_results = rag_searcher.search(...)
except Exception as e:
    logger.warning(f"RAG 검색 실패: {str(e)}")
    rag_results = []  # 빈 결과로 계속 진행
```

#### FACT_COLLECTION Node 에러

**에러 케이스 1: 엔티티 추출 실패**
```python
try:
    entities = entity_extractor.extract_all_entities(...)
except Exception as e:
    logger.error(f"엔티티 추출 실패: {str(e)}")
    entities = {}  # 빈 딕셔너리로 계속 진행
```

**에러 케이스 2: 병렬 처리 실패**
```python
try:
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 병렬 실행
        ...
except Exception as e:
    logger.error(f"병렬 처리 실패: {str(e)}")
    # 순차 처리로 폴백
    entities = entity_extractor.extract_all_entities(...)
    fact_emotion = fact_emotion_splitter.split_fact_emotion(...)
    rag_results = rag_searcher.search(...)
```

#### VALIDATION Node 에러

**에러 케이스 1: 날짜 추출 실패**
```python
try:
    extracted_date = entity_extractor.extract_date(user_input)
except Exception as e:
    logger.warning(f"날짜 추출 실패: {str(e)}")
    extracted_date = None  # 날짜 없이 계속 진행
```

**에러 케이스 2: DB 저장 실패**
```python
try:
    case_fact = CaseFact(...)
    db_session.add(case_fact)
    db_session.commit()
except Exception as e:
    logger.error(f"DB 저장 실패: {str(e)}")
    db_session.rollback()
    # State는 업데이트하되 DB 저장은 건너뛰기
```

#### SUMMARY Node 에러

**에러 케이스 1: 프롬프트 로드 실패**
```python
try:
    prompt_template = prompt_loader.load_prompt(...)
except Exception as e:
    logger.warning(f"프롬프트 로드 실패: {str(e)}")
    prompt_template = None  # 기본 프롬프트 사용
```

**에러 케이스 2: GPT 요약 생성 실패**
```python
try:
    summary = gpt_client.generate_summary(...)
except Exception as e:
    logger.error(f"요약 생성 실패: {str(e)}")
    # 빈 요약으로 저장
    summary = {
        "summary_text": "요약 생성 중 오류가 발생했습니다.",
        "structured_data": {}
    }
```

---

## 성능 최적화 상세

### 1. RAG 검색 캐싱

```python
# 세션 내에서 동일한 시나리오의 K2 문서는 캐싱
k2_cache = {}

def get_k2_document(scenario: str):
    if scenario in k2_cache:
        return k2_cache[scenario]
    
    # RAG 검색
    k2_doc = rag_searcher.search_k2_by_scenario(scenario)
    k2_cache[scenario] = k2_doc
    return k2_doc
```

### 2. GPT API 호출 최적화

#### 통합 엔티티 추출
```python
# 이전: 각 엔티티마다 별도 호출 (5회)
date = extract_date(user_input)      # 1회
amount = extract_amount(user_input)   # 1회
party = extract_party(user_input)    # 1회
action = extract_action(user_input)  # 1회
evidence = extract_evidence(user_input)  # 1회

# 개선: 한 번의 호출로 모든 엔티티 추출 (1회)
entities = extract_all_entities(
    user_input,
    fields_to_extract=["date", "amount", "party", "action"]
)
```

#### 조건부 엔티티 추출
```python
# expected_input이 있으면 해당 필드만 추출
if expected_input and expected_input.get("field") == "amount":
    entities = extract_all_entities(
        user_input,
        fields_to_extract=["amount"]  # amount만 추출
    )
```

### 3. DB 쿼리 최적화

```python
# 이전: N+1 쿼리 문제
for fact_code in fact_codes:
    fact = db_session.query(CaseFact).filter(
        CaseFact.fact_code == fact_code
    ).first()  # N번 쿼리

# 개선: 한 번의 쿼리로 모든 데이터 로드
facts = db_session.query(CaseFact).filter(
    CaseFact.case_id == case_id
).all()  # 1번 쿼리

# 메모리에서 필터링
fact_dict = {f.fact_code: f for f in facts}
```

---

## 참고 문서

- [LangGraph 흐름 가이드](./LANGGRAPH_FLOW.md)
- [시스템 아키텍처](./ARCHITECTURE.md)
- [Excel to YAML 변환](./EXCEL_TO_YAML.md)
- [데이터베이스 설정](./DATABASE_SETUP.md)

