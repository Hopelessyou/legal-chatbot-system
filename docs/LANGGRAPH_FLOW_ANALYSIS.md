# LangGraph Flow 상세 분석

## 📋 목차
1. [전체 구조 개요](#전체-구조-개요)
2. [State 정의](#state-정의)
3. [Node 구현 상세](#node-구현-상세)
4. [Edge 및 분기 로직](#edge-및-분기-로직)
5. [실행 모델](#실행-모델)
6. [데이터 흐름](#데이터-흐름)
7. [RAG 통합](#rag-통합)
8. [예외 처리](#예외-처리)

---

## 전체 구조 개요

### 핵심 설계 원칙
1. **GPT는 해석 도구일 뿐, 판단은 하지 않음**
   - GPT API는 엔티티 추출, 키워드 추출, 요약 생성만 담당
   - 판단, 분기, 검증은 LangGraph가 담당

2. **모든 기준은 RAG 문서(K0~K4)에 정의**
   - 질문, 규칙, 포맷은 YAML 파일에 정의
   - GPT 프롬프트 하드코딩 금지
   - 엑셀 수정 = 시스템 즉시 반영

3. **LangGraph가 분기, 반복, 검증을 담당**
   - State 전이는 명시적으로 관리
   - 무한 루프 방지 메커니즘 포함

### 그래프 구조
```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 세션 시작                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  INIT Node                                                    │
│  - 세션 생성                                                  │
│  - K0_Intake 참조 (START_MESSAGE, DISCLAIMER)                │
│  - 긴급 상황 체크 (EMERGENCY_CHECK)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  CASE_CLASSIFICATION Node                                     │
│  - 사용자 첫 입력 분석                                        │
│  - K1_Classification 참조 (키워드/표현 매칭)                  │
│  - LEVEL2/LEVEL3 분류                                         │
│  - 애매하면 DISAMBIGUATION_QUESTION 사용                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  FACT_COLLECTION Node                                        │
│  - 엔티티 추출 (날짜, 금액, 인물, 행위)                      │
│  - 사실/감정 분리                                            │
│  - K2_Questions 참조 (필수 필드 및 질문 템플릿)              │
│  - DB 저장 (case_fact, case_emotion)                         │
│  - Completion Rate 계산                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  VALIDATION Node                                             │
│  - K2_Questions에서 필수 필드 목록 조회                      │
│  - 누락 필드 확인                                             │
│  - LEVEL4_FACT_Pattern 참조 (중요 사실 체크)                 │
└───────┬───────────────────────────────────────┬─────────────┘
        │                                       │
        │ (missing_fields 있음)                 │ (모든 필드 충족)
        ↓                                       ↓
┌───────────────────────────┐    ┌──────────────────────────────┐
│  RE_QUESTION Node         │    │  SUMMARY Node                │
│  - 누락 필드 우선순위 결정 │    │  - K4_Output_Format 참조     │
│  - K2 질문 템플릿 사용      │    │  - GPT 요약 생성             │
│  - 재질문 생성             │    │  - case_summary 저장         │
└───────┬───────────────────┘    └───────┬──────────────────────┘
        │                                  │
        │ (Loop)                            │
        └──────────→ FACT_COLLECTION ←─────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  COMPLETED Node                                              │
│  - K3_Risk_Rules 참조 (리스크 태그)                           │
│  - 세션 종료 처리                                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
                    세션 종료
```

---

## State 정의

### State 목록

| State 코드 | State 명 | 설명 | 다음 가능한 State |
|-----------|---------|------|------------------|
| **INIT** | 상담 시작 | 세션 생성 직후 상태 | CASE_CLASSIFICATION |
| **CASE_CLASSIFICATION** | 사건 유형 분류 | 사건 분야 판단 | FACT_COLLECTION |
| **FACT_COLLECTION** | 사실관계 수집 | 핵심 정보 입력 단계 | VALIDATION |
| **VALIDATION** | 정보 검증 | 필수 정보 충족 여부 확인 | RE_QUESTION, SUMMARY |
| **RE_QUESTION** | 재질문 | 누락 정보 보완 | FACT_COLLECTION (Loop) |
| **SUMMARY** | 요약 생성 | 내부 전달용 정리 | COMPLETED |
| **COMPLETED** | 상담 종료 | 세션 종료 | END |

### StateContext 구조

```python
class StateContext(TypedDict, total=False):
    # 기본 필드
    session_id: str                          # 세션 ID
    current_state: str                       # 현재 State
    case_type: Optional[str]                 # 사건 유형 (LEVEL1)
    sub_case_type: Optional[str]             # 세부 사건 유형 (LEVEL2)
    
    # 사실 정보
    facts: Dict[str, Any]                    # 수집된 사실
    emotion: List[Dict[str, Any]]            # 감정 정보
    
    # 진행 상태
    completion_rate: int                     # 완성도 (0~100)
    missing_fields: List[str]                # 누락된 필수 필드
    asked_fields: List[str]                  # 이미 질문한 필드 (중복 방지)
    skipped_fields: List[str]                # 1차 서술에서 이미 답변된 필드
    
    # 대화 정보
    last_user_input: str                     # 마지막 사용자 입력
    bot_message: Optional[str]               # 봇 응답 메시지
    expected_input: Optional[Dict[str, Any]] # 기대 입력 타입
    
    # Q-A 매칭 방식 필드
    initial_description: Optional[str]       # 1차 서술 (초기 사용자 입력)
    initial_analysis: Optional[Dict[str, Any]] # 1차 서술 분석 결과
    conversation_history: List[Dict[str, Any]] # Q-A 쌍 리스트
    current_question: Optional[Dict[str, Any]] # 현재 질문 정보
```

---

## Node 구현 상세

### 1. INIT Node

**파일**: `src/langgraph/nodes/init_node.py`

**역할**: 상담 세션 초기화 및 초기 메시지 출력

**처리 과정**:
1. 세션 ID 생성 및 DB 저장
2. K0_Intake YAML 파일 로드
3. 메시지 순서대로 읽기:
   - `START_MESSAGE`: "상황을 3~5줄로 적어주세요..."
   - `DISCLAIMER`: "본 시스템은 법률 자문이 아닙니다..."
   - `EMERGENCY_CHECK`: "신체 위협/긴급 상황인가요?"
4. 긴급 상황이면 `EMERGENCY_STOP` → 세션 종료
5. 정상이면 `CLASSIFY` → 다음 단계로

**출력**:
- `bot_message`: K0의 START_MESSAGE
- `next_state`: `CASE_CLASSIFICATION`
- `expected_input`: 입력 타입 정의

**RAG 참조**: `K0_Intake` (`data/rag/K0_intake/intake_messages.yaml`)

**예외 처리**:
- K0 YAML 파일이 없으면 기본 메시지 반환
- DB 저장 실패 시 로깅만 하고 계속 진행

---

### 2. CASE_CLASSIFICATION Node

**파일**: `src/langgraph/nodes/case_classification_node.py`

**역할**: 사용자의 첫 입력을 분석하여 사건 유형 분류

**처리 과정**:
1. 사용자 입력 텍스트 수신 (`last_user_input`)
2. GPT API로 키워드/의미 추출
3. K1_Classification YAML에서 매칭:
   - `KEYWORDS` 리스트와 비교
   - `TYPICAL_EXPRESSIONS`와 유사도 계산
4. LEVEL2/LEVEL3 추정
5. 애매한 경우:
   - `DISAMBIGUATION_QUESTION` 사용
   - `DISAMBIGUATION_OPTIONS` 제시
   - 사용자 선택 대기
6. 확정되면 DB에 case_master 저장

**출력**:
- `case_type`: LEVEL1 (예: CIVIL)
- `sub_case_type`: LEVEL2_CODE (예: CIVIL_CONTRACT)
- `scenario`: LEVEL3_SCENARIO_CODE (예: CONTRACT_NONPAYMENT)
- `next_state`: `FACT_COLLECTION`
- `initial_description`: 1차 서술 저장

**RAG 참조**: `K1_Classification` (`data/rag/K1_classification/`)

**특이사항**:
- 분류가 애매하면 `DISAMBIGUATION_QUESTION`으로 재질문
- 사용자 선택을 기다린 후 다시 분류 시도

---

### 3. FACT_COLLECTION Node

**파일**: `src/langgraph/nodes/fact_collection_node.py`

**역할**: 사건의 핵심 사실 정보 수집 (Q-A 쌍 저장 및 다음 질문 생성)

**처리 과정**:
1. **사용자 입력 처리**:
   - `last_user_input` 확인
   - 사용자 입력이 없으면 이전 질문 유지 또는 새 질문 생성
   - 입력이 너무 짧으면(2자 미만) 이전 질문 유지

2. **Q-A 쌍 저장**:
   - `current_question`이 있으면:
     - 질문(`question`), 필드(`field`), 답변(`answer`)을 Q-A 쌍으로 저장
     - `conversation_history`에 추가
   - `current_question`이 없으면:
     - 이전 `bot_message`가 "구체적인 내용" 관련이면 `fact_description` 필드로 저장
     - 그 외에는 다음 VALIDATION 노드에서 처리

3. **다음 질문 생성** (`_generate_next_question`):
   - `conversation_history`에서 `asked_fields` 추출
   - `skipped_fields` 확인 (CASE_CLASSIFICATION에서 설정된 1차 서술 분석 결과)
   - `missing_fields` 확인 (CASE_CLASSIFICATION에서 설정된 누락 필드)
   - 제외 필드 계산: `excluded_fields = asked_fields | skipped_fields`
   - `missing_fields`에서 제외되지 않은 필드 선택
   - `missing_fields`가 없거나 모두 제외된 경우:
     - RAG K2_Questions에서 `required_fields` 조회
     - 전체 필수 필드에서 제외되지 않은 필드 선택
   - RAG에서 질문 템플릿 조회
   - 질문 템플릿이 없으면 YAML 파일에서 로드
   - 모든 필드 질문 완료 시 "추가로 알려주실 정보가 있으신가요?" 반환

4. **Completion Rate 계산**:
   - RAG에서 `required_fields` 조회
   - `asked_fields`와 `skipped_fields` 합집합으로 수집된 필드 계산
   - `completion_rate = (수집된 필드 수 / 전체 필수 필드 수) * 100`

**출력**:
- `conversation_history`: 업데이트된 Q-A 쌍 리스트
- `completion_rate`: 완성도 (0~100)
- `bot_message`: 다음 질문
- `current_question`: 현재 질문 정보 (question, field)
- `next_state`: `VALIDATION`

**중요**: 
- ❌ **엔티티 추출은 하지 않음** (VALIDATION 노드에서 수행)
- ❌ **DB 저장은 하지 않음** (VALIDATION 노드에서 수행)
- ❌ **사실/감정 분리는 하지 않음** (VALIDATION 노드에서 수행)
- ✅ **Q-A 쌍 저장만 수행**
- ✅ **다음 질문 생성만 수행**

**RAG 참조**: `K2_Questions` (`data/rag/K2_questions/`)

**특이사항**:
- 1차 서술에서 이미 답변된 정보는 `skipped_fields`에 저장 (CASE_CLASSIFICATION에서 설정)
- 중복 질문 방지를 위해 `asked_fields` 추적 (`conversation_history`에서 추출)
- `missing_fields`는 CASE_CLASSIFICATION 노드에서 설정된 값을 사용

---

### 4. VALIDATION Node

**파일**: `src/langgraph/nodes/validation_node.py`

**역할**: 필수 정보 충족 여부 확인

**처리 과정**:
1. GPT로 Q-A 쌍(`conversation_history`)에서 facts 추출
2. 1차 서술 분석 결과(`initial_analysis`) 병합
3. RAG K2_Questions에서 `required_fields` 목록 조회
4. 현재 수집된 `facts`와 비교
5. 누락 필드 산출:
   ```python
   missing_fields = required_fields - collected_fields
   ```
6. LEVEL4_FACT_Pattern 참조:
   - `CRITICAL=True`인 사실이 누락되었는지 확인
7. 분기 결정:
   - `missing_fields` 있음 → `RE_QUESTION`
   - 모든 필드 충족 → `SUMMARY`

**출력**:
- `missing_fields`: 누락된 필수 필드 리스트
- `next_state`: `RE_QUESTION` 또는 `SUMMARY` (조건부)

**조건부 분기**:
```python
def route_after_validation(state):
    missing_fields = state.get("missing_fields", [])
    if len(missing_fields) > 0:
        return "RE_QUESTION"
    else:
        return "SUMMARY"
```

**RAG 참조**: 
- `K2_Questions` (필수 필드 목록)
- `LEVEL4_FACT_Pattern` (중요 사실 체크)

**특이사항**:
- GPT를 사용하여 대화 기록에서 facts 추출 (Q-A 매칭 방식)
- 1차 서술 분석 결과와 병합하여 정확도 향상

---

### 5. RE_QUESTION Node

**파일**: `src/langgraph/nodes/re_question_node.py`

**역할**: 누락된 정보를 재질문

**처리 과정**:
1. `missing_fields`에서 우선순위 결정:
   - `CRITICAL=True`인 필드 우선
   - `QUESTION_ORDER`가 낮은 필드 우선
2. K2_Questions에서 해당 필드의 `question` 템플릿 조회
3. 이미 질문한 필드(`asked_fields`) 제외
4. 질문 생성 및 출력
5. Loop: `FACT_COLLECTION`으로 돌아가서 사용자 응답 대기

**출력**:
- `bot_message`: 재질문 메시지
- `expected_input`: 기대하는 입력 타입
- `next_state`: `FACT_COLLECTION` (Loop)
- `asked_fields`: 업데이트 (중복 방지)

**RAG 참조**: `K2_Questions` (재질문 템플릿)

**특이사항**:
- 무한 루프 방지를 위해 `asked_fields` 추적
- 우선순위 기반 질문 선택

---

### 6. SUMMARY Node

**파일**: `src/langgraph/nodes/summary_node.py`

**역할**: 내부 전달용 구조화된 요약 생성

**처리 과정**:
1. K4_Output_Format YAML 조회:
   - `sections` 리스트 확인
   - `content_rule`, `style_rule` 적용
2. GPT API로 요약 생성:
   - 수집된 모든 `facts` 기반
   - K4 포맷에 맞춰 구조화
3. DB에 `case_summary` 저장
4. 리스크 태그 추가 (K3 참조)

**출력**:
- `summary`: 구조화된 요약 딕셔너리
- `risk_tags`: 리스크 태그 리스트
- `next_state`: `COMPLETED`

**RAG 참조**: `K4_Output_Format` (`data/rag/K4_output_format/`)

**특이사항**:
- GPT를 사용하여 요약 생성
- RAG 포맷 규칙에 따라 구조화

---

### 7. COMPLETED Node

**파일**: `src/langgraph/nodes/completed_node.py`

**역할**: 세션 종료 처리

**처리 과정**:
1. K3_Risk_Rules 참조:
   - `trigger_facts`와 수집된 사실 비교
   - 조건 만족 시 `risk_tag` 추가
2. 세션 상태를 `COMPLETED`로 업데이트
3. 종료 시간 기록
4. 최종 응답 반환

**출력**:
- `session_status`: `COMPLETED`
- `risk_tags`: 리스크 태그 리스트
- `next_state`: `END`

**RAG 참조**: `K3_Risk_Rules` (`data/rag/K3_risk_rules/`)

---

## Edge 및 분기 로직

### 일반 Edge (순차 진행)

```python
# graph.py에서 정의
workflow.set_entry_point("INIT")
workflow.add_edge("INIT", "CASE_CLASSIFICATION")
workflow.add_edge("CASE_CLASSIFICATION", "FACT_COLLECTION")
workflow.add_edge("FACT_COLLECTION", "VALIDATION")

# Loop: RE_QUESTION → FACT_COLLECTION
workflow.add_edge("RE_QUESTION", "FACT_COLLECTION")

# SUMMARY → COMPLETED
workflow.add_edge("SUMMARY", "COMPLETED")

# COMPLETED → END
workflow.add_edge("COMPLETED", END)
```

### 조건부 Edge

**VALIDATION → RE_QUESTION or SUMMARY**

```python
# src/langgraph/edges/conditional_edges.py
def route_after_validation(state: StateContext) -> Literal["RE_QUESTION", "SUMMARY"]:
    missing_fields = state.get("missing_fields", [])
    
    if len(missing_fields) > 0:
        logger.debug(f"누락 필드 존재: {missing_fields} → RE_QUESTION")
        return "RE_QUESTION"
    else:
        logger.debug("모든 필수 필드 충족 → SUMMARY")
        return "SUMMARY"
```

**그래프 연결**:
```python
workflow.add_conditional_edges(
    "VALIDATION",
    route_after_validation,
    {
        "RE_QUESTION": "RE_QUESTION",
        "SUMMARY": "SUMMARY"
    }
)
```

---

## 실행 모델

### 1 Step 실행 모델

**핵심**: 각 API 요청마다 현재 State에 해당하는 Node만 실행

**구현 위치**: `src/langgraph/graph.py::run_graph_step()`

**처리 과정**:
1. 현재 State 확인 (`state.get("current_state")`)
2. 재귀 제한 확인 (`_check_recursion_limit`)
3. 현재 State에 해당하는 Node 실행
4. Node 실행 결과로 State 업데이트
5. `next_state` 결정
6. 응답 반환

**예시 플로우**:
```
1. POST /chat/start
   → INIT Node 실행
   → K0_Intake 메시지 출력
   → State: CASE_CLASSIFICATION

2. POST /chat/message {"text": "작년 10월에 계약했는데 돈을 안 줬어요"}
   → CASE_CLASSIFICATION Node 실행
   → K1_Classification 참조하여 분류
   → State: FACT_COLLECTION

3. POST /chat/message {"text": "5000만원이요"}
   → FACT_COLLECTION Node 실행
   → K2_Questions 참조하여 질문
   → State: VALIDATION

4. VALIDATION Node 실행 (내부)
   → missing_fields 확인
   → State: RE_QUESTION (필드 누락 시) 또는 SUMMARY (완료 시)

5. (Loop) RE_QUESTION → FACT_COLLECTION → VALIDATION
   → 모든 필드 수집될 때까지 반복

6. SUMMARY Node 실행
   → K4_Output_Format 참조하여 요약 생성
   → State: COMPLETED

7. COMPLETED Node 실행
   → K3_Risk_Rules 참조하여 리스크 태그 추가
   → 세션 종료
```

### 무한 루프 방지

**구현 위치**: `src/langgraph/graph.py::_check_recursion_limit()`

**메커니즘**:
1. 세션별 실행 횟수 추적 (`_session_step_count`)
2. 기본 재귀 제한: 50회 (`DEFAULT_RECURSION_LIMIT`)
3. 제한 초과 시:
   - 로그 기록
   - State를 `COMPLETED`로 강제 변경
   - 에러 메시지 반환
   - 세션 카운트 리셋

```python
def _check_recursion_limit(session_id: str) -> bool:
    global _session_step_count
    recursion_limit = getattr(settings, 'graph_recursion_limit', DEFAULT_RECURSION_LIMIT)
    
    if session_id not in _session_step_count:
        _session_step_count[session_id] = 0
    
    _session_step_count[session_id] += 1
    
    if _session_step_count[session_id] > recursion_limit:
        logger.error(f"재귀 제한 초과: {_session_step_count[session_id]} > {recursion_limit}")
        return True  # 제한 초과
    
    return False
```

---

## 데이터 흐름

### 1. 세션 시작 → INIT

```
사용자: POST /chat/start
  ↓
INIT Node 실행
  ↓
State 생성:
{
  "session_id": "sess_abc123",
  "current_state": "INIT",
  "facts": {},
  "completion_rate": 0,
  ...
}
  ↓
K0_Intake YAML 로드
  ↓
bot_message 생성
  ↓
next_state: "CASE_CLASSIFICATION"
```

### 2. 분류 → FACT_COLLECTION

```
사용자: "작년 10월에 계약했는데 돈을 안 줬어요"
  ↓
CASE_CLASSIFICATION Node 실행
  ↓
GPT로 키워드 추출
  ↓
K1_Classification 매칭
  ↓
State 업데이트:
{
  "case_type": "CIVIL",
  "sub_case_type": "CIVIL_CONTRACT",
  "initial_description": "작년 10월에 계약했는데...",
  "next_state": "FACT_COLLECTION"
}
  ↓
DB에 case_master 저장
```

### 3. 사실 수집 → VALIDATION

```
사용자: "5000만원이요"
  ↓
FACT_COLLECTION Node 실행
  ↓
GPT로 엔티티 추출:
{
  "amount": 50000000,
  "incident_date": "2023-10"
}
  ↓
K2_Questions 조회
  ↓
다음 질문 선택
  ↓
conversation_history 업데이트:
[
  {
    "question": "계약 또는 문제가 발생한 시점은 언제인가요?",
    "answer": "작년 10월에 계약했는데 돈을 안 줬어요",
    "extracted_facts": {"incident_date": "2023-10"}
  },
  {
    "question": "문제가 된 금액은 얼마인가요?",
    "answer": "5000만원이요",
    "extracted_facts": {"amount": 50000000}
  }
]
  ↓
completion_rate 계산: 40% (2/5 필드)
  ↓
next_state: "VALIDATION"
```

### 4. 검증 → 분기

```
VALIDATION Node 실행
  ↓
GPT로 conversation_history에서 facts 추출
  ↓
RAG에서 required_fields 조회:
["incident_date", "counterparty", "amount", "location", "evidence"]
  ↓
누락 필드 계산:
missing_fields = ["counterparty", "location", "evidence"]
  ↓
조건부 분기:
if len(missing_fields) > 0:
    next_state = "RE_QUESTION"
else:
    next_state = "SUMMARY"
  ↓
(예시) next_state: "RE_QUESTION"
```

### 5. 재질문 → Loop

```
RE_QUESTION Node 실행
  ↓
missing_fields 우선순위 결정:
["counterparty", "location", "evidence"]
  ↓
K2_Questions에서 질문 템플릿 조회
  ↓
bot_message: "계약 상대방은 누구인가요?"
  ↓
asked_fields 업데이트: ["counterparty"]
  ↓
next_state: "FACT_COLLECTION" (Loop)
  ↓
(다시 FACT_COLLECTION으로 돌아감)
```

### 6. 요약 → 완료

```
SUMMARY Node 실행
  ↓
모든 facts 수집 완료 확인
  ↓
K4_Output_Format 조회
  ↓
GPT로 요약 생성:
{
  "사건 유형": "민사 / 계약",
  "핵심 사실관계": "2023년 10월 계약, 대금 5000만원 미지급...",
  ...
}
  ↓
DB에 case_summary 저장
  ↓
next_state: "COMPLETED"
```

---

## RAG 통합

### RAG 문서 매핑

| LangGraph Node | 참조 RAG 문서 | 경로 | 용도 |
|---------------|--------------|------|------|
| **INIT** | K0_Intake | `data/rag/K0_intake/intake_messages.yaml` | 초기 메시지, 디스클레이머, 긴급 체크 |
| **CASE_CLASSIFICATION** | K1_Classification | `data/rag/K1_classification/` | 사건 유형 분류 기준 (키워드, 표현, 확인 질문) |
| **FACT_COLLECTION** | K2_Questions | `data/rag/K2_questions/` | 필수 필드 목록, 질문 템플릿 |
| **VALIDATION** | K2_Questions, LEVEL4_FACT_Pattern | `data/rag/K2_questions/`, `data/rag/K4_fact_patterns/` | 필수 필드 검증, 중요 사실 체크 |
| **RE_QUESTION** | K2_Questions | `data/rag/K2_questions/` | 재질문 템플릿 |
| **SUMMARY** | K4_Output_Format | `data/rag/K4_output_format/` | 요약 포맷, 스타일 규칙 |
| **COMPLETED** | K3_Risk_Rules | `data/rag/K3_risk_rules/` | 리스크 태그, 주의사항 |

### RAG 검색 과정

**구현 위치**: `src/rag/searcher.py`

**사용 예시**:
```python
from src.rag.searcher import rag_searcher

# K2_Questions에서 필수 필드 조회
rag_results = rag_searcher.search(
    query="필수 필드",
    knowledge_type="K2",
    main_case_type=case_type,
    sub_case_type=sub_case_type,
    top_k=1
)
```

**검색 전략**:
1. `knowledge_type`으로 RAG 문서 타입 지정
2. `main_case_type`, `sub_case_type`으로 범위 좁히기
3. `query`로 의미 검색
4. `top_k`로 상위 결과만 반환

---

## 예외 처리

### 1. 재귀 제한 초과

**상황**: 무한 루프 감지

**처리**:
- State를 `COMPLETED`로 강제 변경
- 에러 메시지 반환
- 세션 카운트 리셋

**코드**:
```python
if _check_recursion_limit(session_id):
    state["current_state"] = "COMPLETED"
    state["bot_message"] = "죄송합니다. 시스템 오류가 발생했습니다..."
    _reset_session_step_count(session_id)
    return state
```

### 2. RAG 파일 없음

**상황**: K0 YAML 파일을 찾을 수 없음

**처리**:
- 기본 메시지 반환
- 로그 기록
- 계속 진행

**코드**:
```python
if not k0_path.exists():
    logger.warning(f"K0 YAML 파일을 찾을 수 없습니다: {k0_path}")
    return "안녕하세요. 법률 상담을 도와드리겠습니다."
```

### 3. Node 실행 실패

**상황**: Node 실행 중 예외 발생

**처리**:
- 에러 로그 기록
- 세션 카운트 리셋
- 예외 재발생 (상위 레이어에서 처리)

**코드**:
```python
except Exception as e:
    session_id = state.get("session_id", "unknown")
    logger.error(f"[{session_id}] Graph step 실행 실패: {str(e)}", exc_info=True)
    _reset_session_step_count(session_id)
    raise
```

### 4. State 검증 실패

**상황**: 유효하지 않은 State 코드

**처리**:
- 현재 State 유지
- 로그 기록
- 계속 진행

**코드**:
```python
node_func = node_map.get(current_state)
if not node_func:
    logger.error(f"[{session_id}] 알 수 없는 State: {current_state}")
    return state  # 현재 상태 유지
```

---

## 핵심 설계 원칙 요약

### 1. GPT는 해석만 수행
- GPT API는 엔티티 추출, 키워드 추출, 요약 생성만 담당
- 판단, 분기, 검증은 LangGraph가 담당

### 2. RAG는 기준만 제공
- 모든 질문, 규칙, 포맷은 RAG 문서에 정의
- GPT 프롬프트 하드코딩 금지
- 엑셀 수정 = 시스템 즉시 반영

### 3. State는 명시적으로 관리
- 모든 State 전이는 로깅됨 (`chat_session_state_log`)
- State 변경은 Node 실행 결과로만 가능
- 예외 상황도 State로 관리

### 4. 완전 분리 구조
- RAG (기준 문서) ↔ LangGraph (흐름 제어) ↔ DB (데이터 저장)
- 각 레이어는 독립적으로 수정 가능
- 확장성과 유지보수성 보장

---

## 확장 가능성

### 새로운 시나리오 추가
1. 엑셀에 K1, K2, K3 시트에 행 추가
2. `python scripts/generate_all_yaml.py` 실행
3. 자동으로 YAML 생성 및 RAG 인덱싱
4. LangGraph 코드 수정 불필요

### 새로운 질문 추가
1. 엑셀 K2_Questions 시트에 행 추가
2. YAML 재생성
3. 다음 실행부터 자동 반영

### 새로운 리스크 규칙 추가
1. 엑셀 K3_Risk_Rules 시트에 행 추가
2. YAML 재생성
3. COMPLETED Node에서 자동 적용

---

## 문제 해결 가이드

### 분류가 애매한 경우
- **해결**: K1_Classification의 `DISAMBIGUATION_QUESTION` 사용
- 사용자에게 선택지 제시
- 명확해질 때까지 반복 가능

### 필수 필드가 계속 누락되는 경우
- **해결**: RE_QUESTION → FACT_COLLECTION Loop
- 최대 반복 횟수 제한 가능 (추가 구현 필요)
- 우선순위 기반 질문 순서 조정

### 긴급 상황 처리
- **해결**: INIT Node에서 EMERGENCY_CHECK
- 긴급 상황 감지 시 즉시 세션 종료
- 적절한 안내 메시지 제공

---

## 참고 문서

- `docs/LANGGRAPH_FLOW.md`: 전체 흐름 가이드
- `docs/LANGGRAPH.md`: LangGraph 구조 설명
- `docs/ARCHITECTURE.md`: 전체 아키텍처
- `docs/NODES_DETAILED_EXPLANATION.md`: Node 상세 설명