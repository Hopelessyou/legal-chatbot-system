# LangGraph 노드 코드 상세 설명

## 목차
1. [노드 구조 개요](#노드-구조-개요)
2. [INIT Node](#init-node)
3. [CASE_CLASSIFICATION Node](#case_classification-node)
4. [FACT_COLLECTION Node](#fact_collection-node)
5. [VALIDATION Node](#validation-node)
6. [RE_QUESTION Node](#re_question-node)
7. [SUMMARY Node](#summary-node)
8. [COMPLETED Node](#completed-node)
9. [노드 간 데이터 흐름](#노드-간-데이터-흐름)

---

## 노드 구조 개요

### 전체 흐름도
```
INIT → CASE_CLASSIFICATION → FACT_COLLECTION → VALIDATION
                                                     ↓
                                              (조건부 분기)
                                                    ↓
                                    ┌───────────────┴───────────────┐
                                    ↓                               ↓
                              RE_QUESTION                      SUMMARY
                                    ↓                               ↓
                              FACT_COLLECTION                  COMPLETED
                                    ↑                               ↓
                                    └──────────────(루프)───────────┘
```

### State Context 구조
```python
{
    "session_id": str,              # 세션 식별자
    "current_state": str,           # 현재 노드 상태
    "case_type": str,               # 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMINISTRATIVE)
    "sub_case_type": str,           # 세부 사건 유형
    "facts": Dict[str, Any],        # 수집된 사실 정보
    "emotion": List[Dict],          # 감정 정보
    "completion_rate": int,         # 완성도 (0-100)
    "last_user_input": str,         # 마지막 사용자 입력
    "missing_fields": List[str],    # 누락된 필수 필드 목록
    "asked_fields": List[str],      # 이미 질문한 필드 목록 (중복 방지)
    "bot_message": str,             # 봇 응답 메시지
    "expected_input": Dict,         # 기대하는 입력 형식
    # Q-A 매칭 방식 추가 필드
    "initial_description": str,     # 1차 서술 (초기 사용자 입력)
    "initial_analysis": Dict,       # 1차 서술 분석 결과
    "conversation_history": List[Dict],  # Q-A 쌍 리스트
    "skipped_fields": List[str],    # 1차 서술에서 이미 답변된 필드
    "current_question": Dict,      # 현재 질문 정보
}
```

---

## INIT Node

### 목적
세션 초기화 및 첫 인사 메시지 표시

### 주요 기능
1. **세션 ID 생성 및 DB 저장**
   - 새 세션이면 `ChatSession` 테이블에 생성
   - 기존 세션이면 재사용

2. **K0 메시지 로드**
   - `data/rag/K0_intake/intake_messages.yaml` 파일 로드
   - 초기 안내 메시지 구성

3. **사용자 입력 감지**
   - 사용자 입력이 있으면 → `CASE_CLASSIFICATION`으로 즉시 이동
   - 없으면 → 초기 메시지 표시 후 `CASE_CLASSIFICATION`으로 이동

### 핵심 로직

```python
# 사용자 입력이 있으면 바로 CASE_CLASSIFICATION으로 이동
if user_input and len(user_input) >= 2:
    return {
        **state,
        "current_state": "CASE_CLASSIFICATION",
        "next_state": "CASE_CLASSIFICATION"
    }

# 사용자 입력이 없으면 초기 메시지 표시
k0_data = _load_k0_messages()
bot_message, expected_input = _build_initial_message(k0_data)
```

### 반환값
- `next_state`: 항상 `"CASE_CLASSIFICATION"`
- `bot_message`: 초기 안내 메시지 또는 사용자 입력 감지 시 상태 전이만
- `current_state`: `"INIT"` 또는 `"CASE_CLASSIFICATION"`

### 에러 처리
- DB 오류 시에도 계속 진행 (메모리 상태 유지)
- K0 파일 로드 실패 시 기본 메시지 사용

---

## CASE_CLASSIFICATION Node

### 목적
사용자 입력을 분석하여 사건 유형 분류

### 주요 기능
1. **키워드 및 의미 추출**
   - `keyword_extractor`로 키워드 추출
   - 의미적 특징 분석

2. **RAG K1 조회**
   - 사건 유형 분류 기준 검색
   - `top_k=3`로 유사도 높은 결과 조회

3. **GPT 기반 최종 분류**
   - RAG 결과를 참고하여 GPT로 최종 분류
   - JSON 형식으로 `main_case_type`, `sub_case_type` 반환

4. **폴백 처리**
   - GPT 실패 시 키워드 기반 간단한 분류 사용
   - `get_fallback_case_type()` 함수 활용

5. **1차 서술 분석 (Q-A 매칭 방식)**
   - `post_classification_analysis()` 함수 호출
   - GPT로 초기 사용자 입력 분석하여 포함된 정보 추출
   - `initial_analysis`, `conversation_history`, `skipped_fields` 설정

6. **DB 저장**
   - `CaseMaster` 테이블에 사건 정보 저장
   - `ChatSession` 상태 업데이트

### 핵심 로직

```python
# 1. 키워드 추출
semantic_features = keyword_extractor.extract_semantic_features(user_input)
keywords = semantic_features.get("keywords", [])

# 2. RAG K1 조회
rag_results = rag_searcher.search_by_knowledge_type(
    query=" ".join(keywords),
    knowledge_type="K1",
    top_k=3
)

# 3. GPT 최종 분류 (RAG 결과 참고)
if not main_case_type:
    response = gpt_client.chat_completion(
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0.3
    )
    # JSON 파싱 및 추출
```

### 사건 유형 매핑
- 한글 → 영문 변환: `CASE_TYPE_MAPPING`
- 예: "민사" → "CIVIL", "형사" → "CRIMINAL"

### 반환값
- `case_type`: 영문 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMINISTRATIVE)
- `sub_case_type`: 세부 유형 (예: "대여금", "사기", "이혼")
- `bot_message`: "사건과 관련된 구체적인 내용을 알려주세요."
- `next_state`: `"FACT_COLLECTION"`

---

## FACT_COLLECTION Node

### 목적
**핵심 노드**: Q-A 매칭 방식으로 사용자 입력을 질문-답변 쌍으로 저장

### 주요 기능 (Q-A 매칭 방식)
1. **Q-A 쌍 저장**
   - 사용자 입력을 `current_question`과 매칭하여 Q-A 쌍 생성
   - `conversation_history`에 추가
   - 복잡한 엔티티 추출 로직 제거 (GPT가 VALIDATION에서 처리)

2. **다음 질문 생성**
   - `_generate_next_question()` 함수 사용
   - `skipped_fields` (1차 서술에서 답변된 필드) 제외
   - `asked_fields` (이미 질문한 필드) 제외
   - RAG K2에서 질문 템플릿 조회

3. **완성도 계산**
   - `conversation_history`와 `skipped_fields` 기반
   - 질문한 필드 수 / 전체 필수 필드 수 * 100

### 핵심 로직 (Q-A 매칭 방식)

```python
# 1. Q-A 쌍 저장
if current_question and user_input:
    qa_pair = {
        "question": current_question.get("question", ""),
        "field": current_question.get("field", ""),
        "answer": user_input,
        "timestamp": get_kst_now().isoformat()
    }
    conversation_history.append(qa_pair)
    state["conversation_history"] = conversation_history

# 2. 다음 질문 생성
next_question = _generate_next_question(state)
state["bot_message"] = next_question["question"]
state["current_question"] = next_question

# 3. 완성도 계산
asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
skipped_fields = state.get("skipped_fields", [])
total_answered = len(set(asked_fields) | set(skipped_fields))
completion_rate = int((total_answered / len(required_fields)) * 100)
```

### Facts 구조
```python
{
    "incident_date": str,        # 사건 발생 날짜 (예: "2024-10-15")
    "amount": float,             # 금액 (예: 3000000)
    "counterparty": str,         # 상대방 (예: "친구")
    "counterparty_type": str,    # 상대방 유형 (예: "개인")
    "evidence": bool,            # 증거 유무
    "evidence_type": str,        # 증거 타입 (예: "계약서", "진단서")
    "action_description": str    # 행위 설명
}
```

### 반환값
- `facts`: 업데이트된 사실 정보
- `completion_rate`: 완성도 (0-100)
- `bot_message`: 다음 질문 또는 안내 메시지
- `expected_input`: 기대하는 입력 형식 (`field`, `type`)
- `next_state`: `"VALIDATION"`

### 특이사항
- **가장 복잡한 노드**: 엔티티 추출, DB 저장, 중복 방지 등 많은 로직 포함
- **병렬 처리**: 3개 작업을 동시에 실행하여 성능 최적화
- **중복 질문 방지**: `asked_fields`와 `field_updated` 체크로 같은 질문 반복 방지

---

## VALIDATION Node

### 목적
Q-A 대화 기록에서 구조화된 facts 추출 및 누락 필드 확인

### 주요 기능 (Q-A 매칭 방식)
1. **GPT로 Q-A 쌍에서 facts 추출**
   - `_extract_facts_from_conversation()` 함수 사용
   - `conversation_history`를 GPT에 전달하여 구조화된 facts 추출
   - GPT API 실패 시 기존 엔티티 추출 방식으로 폴백

2. **1차 서술 분석 결과 병합**
   - `initial_analysis`의 `extracted_facts`와 병합
   - conversation_history의 최신 정보가 우선

3. **RAG K2에서 필수 필드 조회**
   - 사건 유형별 필수 필드 목록 조회
   - `extract_required_fields_from_rag()` 함수 사용

4. **누락 필드 확인**
   - `conversation_history`에서 질문한 필드 확인
   - `required_fields`와 비교하여 누락 필드 수집
   - `evidence=True`인데 `evidence_type` 없으면 추가 질문 필요

5. **DB 저장**
   - `CaseFact`, `CaseParty`, `CaseEvidence` 테이블에 facts 저장
   - `CaseMissingField` 테이블에 누락 필드 저장

6. **조건부 분기**
   - 누락 필드 있으면 → `RE_QUESTION`
   - 없으면 → `SUMMARY`

### 핵심 로직 (Q-A 매칭 방식)

```python
# 1. GPT로 Q-A 쌍에서 facts 추출
conversation_history = state.get("conversation_history", [])
facts = _extract_facts_from_conversation(conversation_history, case_type)

# 2. 1차 서술 분석 결과 병합
initial_analysis = state.get("initial_analysis", {})
if initial_analysis:
    initial_facts = initial_analysis.get("extracted_facts", {})
    for key, value in initial_facts.items():
        if facts.get(key) is None and value is not None:
            facts[key] = value

# 3. RAG에서 필수 필드 조회
required_fields = extract_required_fields_from_rag(rag_results)

# 4. 누락 필드 확인
asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
missing_fields = [
    field for field in required_fields
    if field not in asked_fields and facts.get(field) is None
]

# 5. 조건부 분기
if missing_fields:
    next_state = "RE_QUESTION"
else:
    next_state = "SUMMARY"
```

### 반환값
- `missing_fields`: 누락된 필수 필드 목록
- `facts`: 업데이트된 사실 정보
- `bot_message`: 누락 필드 없을 때만 "모든 필수 정보가 수집되었습니다..."
- `next_state`: `"RE_QUESTION"` 또는 `"SUMMARY"`

### 조건부 엣지
`graph.py`에서 `route_after_validation()` 함수로 분기:
```python
if missing_fields:
    return "RE_QUESTION"
else:
    return "SUMMARY"
```

---

## RE_QUESTION Node

### 목적
누락된 필수 필드에 대한 재질문 생성

### 주요 기능 (Q-A 매칭 방식)
1. **우선순위 기반 필드 선택**
   - `get_next_missing_field()` 함수 사용
   - 사건 유형별 우선순위 고려
   - `asked_fields`와 `skipped_fields` 모두 제외

2. **RAG K2에서 질문 템플릿 조회**
   - `"{field} 질문"` 쿼리로 검색
   - 질문 템플릿 추출

3. **질문 생성**
   - RAG 결과 우선 사용
   - 실패 시 YAML 파일에서 로드 (`get_question_message()`)

4. **current_question 업데이트**
   - Q-A 매칭 방식으로 `current_question` 설정
   - FACT_COLLECTION에서 Q-A 쌍 저장 시 사용

### 핵심 로직 (Q-A 매칭 방식)

```python
# 1. asked_fields와 skipped_fields 모두 제외
conversation_history = state.get("conversation_history", [])
asked_fields = [qa.get("field") for qa in conversation_history if qa.get("field")]
skipped_fields = state.get("skipped_fields", [])
excluded_fields = set(asked_fields) | set(skipped_fields)
unasked_missing_fields = [f for f in missing_fields if f not in excluded_fields]

if unasked_missing_fields:
    # 2. 우선순위 기반으로 다음 필드 선택
    next_field = get_next_missing_field(unasked_missing_fields, case_type)
    
    # 3. RAG에서 질문 템플릿 조회
    rag_results = rag_searcher.search(
        query=f"{next_field} 질문",
        knowledge_type="K2",
        main_case_type=case_type,
        top_k=1
    )
    
    # 4. 질문 생성
    question = extract_question_template_from_rag(rag_results, next_field)
    if not question:
        question = get_question_message(next_field, case_type)
    
    # 5. current_question 업데이트 (Q-A 매칭 방식)
    state["current_question"] = {
        "question": question,
        "field": next_field
    }
```

### 반환값
- `bot_message`: 생성된 질문 메시지
- `expected_input`: 기대하는 입력 형식 (`field`, `type`)
- `next_state`: `"FACT_COLLECTION"` (루프)

### 특이사항
- **루프 구조**: `RE_QUESTION` → `FACT_COLLECTION` → `VALIDATION` → `RE_QUESTION`...
- **모든 필드 질문 완료 시**: `SUMMARY`로 이동

---

## SUMMARY Node

### 목적
수집된 사실 정보를 바탕으로 최종 요약 생성

### 주요 기능
1. **전체 Context 취합**
   - DB의 `CaseFact`에서 `source_text` 수집
   - `last_user_input` 추가
   - 모든 사용자 입력 텍스트 통합

2. **RAG K4 포맷 조회**
   - 요약 포맷 템플릿 조회
   - 사건 유형별 요약 구조 추출

3. **GPT API로 요약 생성**
   - `summarizer.generate_final_summary()` 함수 사용
   - 구조화된 데이터 (`structured_data`) 생성
   - 요약 텍스트 (`summary_text`) 생성

4. **DB 저장**
   - `CaseSummary` 테이블에 저장
   - `summary_text`: 전체 요약 텍스트
   - `structured_json`: 구조화된 데이터 (JSON)

### 핵심 로직

```python
# 1. 전체 Context 취합
context = {
    "case_type": state.get("case_type"),
    "sub_case_type": state.get("sub_case_type"),
    "facts": facts,
    "emotion": state.get("emotion", []),
    "completion_rate": state.get("completion_rate", 0),
    "user_inputs": user_input_text  # 모든 사용자 입력 통합
}

# 2. RAG K4 포맷 조회
rag_results = rag_searcher.search(
    query="요약 포맷",
    knowledge_type="K4",
    main_case_type=main_case_type_en,
    top_k=1
)
format_template = extract_k4_format_from_rag(rag_results)

# 3. GPT로 요약 생성
summary_result = summarizer.generate_final_summary(
    context=context,
    format_template=format_template
)

# 4. DB 저장
summary = CaseSummary(
    case_id=case.case_id,
    summary_text=summary_result["summary_text"],
    structured_json=summary_result["structured_data"]
)
```

### 반환값
- `bot_message`: "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
- `next_state`: `"COMPLETED"`

### 요약 구조
```json
{
    "summary_text": "전체 요약 텍스트...",
    "structured_data": {
        "사건_유형": "대여금",
        "핵심_사실관계": "...",
        "금액_및_증거": "...",
        "특이사항": "..."
    }
}
```

---

## COMPLETED Node

### 목적
세션 완료 처리 및 최종 메시지 표시

### 주요 기능
1. **세션 상태 업데이트**
   - `ChatSession.status = "COMPLETED"`
   - `ChatSession.current_state = "COMPLETED"`
   - `ChatSession.ended_at` 설정
   - `completion_rate` 최종 저장

2. **State 전이 로깅**
   - `log_state_transition()` 함수 호출
   - SUMMARY → COMPLETED 전이 기록

### 핵심 로직

```python
# 1. 세션 상태 업데이트
chat_session.status = SessionStatus.COMPLETED.value
chat_session.current_state = "COMPLETED"
chat_session.ended_at = get_kst_now()
chat_session.completion_rate = state.get("completion_rate", 0)
db_session.commit()

# 2. State 업데이트
state["current_state"] = "COMPLETED"
state["bot_message"] = "상담에 필요한 정보를 확인했습니다..."
```

### 반환값
- `bot_message`: 완료 메시지
- `next_state`: `None` (종료)

### 종료 조건
- `next_state = None`일 때 LangGraph가 `END`로 이동

---

## 노드 간 데이터 흐름

### 1. INIT → CASE_CLASSIFICATION
```python
# INIT에서 전달
{
    "session_id": "sess_xxx",
    "last_user_input": "친구가 돈을 빌려갔는데...",
    "current_state": "CASE_CLASSIFICATION"
}

# CASE_CLASSIFICATION에서 반환
{
    "case_type": "CIVIL",
    "sub_case_type": "대여금",
    "bot_message": "사건과 관련된 구체적인 내용을 알려주세요.",
    "next_state": "FACT_COLLECTION"
}
```

### 2. FACT_COLLECTION → VALIDATION
```python
# FACT_COLLECTION에서 전달
{
    "facts": {
        "incident_date": "2024-10-15",
        "amount": 3000000,
        "counterparty": "친구",
        "evidence": True
    },
    "completion_rate": 50,
    "bot_message": "관련 증거를 가지고 계신가요?",
    "expected_input": {"field": "evidence", "type": "boolean"}
}

# VALIDATION에서 반환
{
    "missing_fields": ["evidence_type"],
    "next_state": "RE_QUESTION"
}
```

### 3. RE_QUESTION → FACT_COLLECTION (루프)
```python
# RE_QUESTION에서 반환
{
    "bot_message": "증거의 종류를 알려주세요.",
    "expected_input": {"field": "evidence_type", "type": "text"},
    "asked_fields": ["incident_date", "amount", "counterparty", "evidence", "evidence_type"],
    "next_state": "FACT_COLLECTION"
}

# FACT_COLLECTION으로 다시 이동 (사용자 입력 처리)
```

### 4. VALIDATION → SUMMARY → COMPLETED
```python
# VALIDATION에서 반환 (누락 필드 없음)
{
    "missing_fields": [],
    "next_state": "SUMMARY"
}

# SUMMARY에서 반환
{
    "bot_message": "모든 필수 정보가 수집되었습니다...",
    "next_state": "COMPLETED"
}

# COMPLETED에서 반환
{
    "current_state": "COMPLETED",
    "bot_message": "상담에 필요한 정보를 확인했습니다...",
    "next_state": None  # 종료
}
```

---

## 주요 특징

### 1. **RAG (Retrieval Augmented Generation) 활용**
- **K0**: 초기 안내 메시지
- **K1**: 사건 유형 분류 기준
- **K2**: 질문 템플릿 및 필수 필드
- **K4**: 요약 포맷 템플릿

### 2. **중복 질문 방지**
- `asked_fields` 리스트로 추적
- 사용자 입력 처리 여부 확인 (`field_updated`)
- 최대 5번까지 다른 필드로 강제 이동

### 3. **병렬 처리**
- `FACT_COLLECTION` 노드에서 3개 작업 동시 실행
- 엔티티 추출, 사실/감정 분리, RAG 검색

### 4. **에러 처리 및 폴백**
- GPT 실패 시 키워드 기반 분류
- RAG 실패 시 기본 값 사용
- DB 오류 시에도 계속 진행 (메모리 상태 유지)

### 5. **상태 전이 관리**
- `next_state`로 다음 노드 지정
- LangGraph 엣지가 자동으로 라우팅
- 직접 노드 호출 제거 (그래프 흐름 일관성)

---

## 주요 개선 사항 (최근 수정)

### Q-A 매칭 방식 전환 (VER2.0.0)
1. **FACT_COLLECTION Node 간소화**
   - 복잡한 엔티티 추출 로직 제거
   - Q-A 쌍 저장 방식으로 변경
   - `conversation_history`에 질문-답변 쌍 저장

2. **VALIDATION Node 개선**
   - GPT로 Q-A 쌍에서 facts 추출
   - 1차 서술 분석 결과 병합
   - GPT API 실패 시 기존 엔티티 추출 방식으로 폴백

3. **1차 서술 분석 추가**
   - CASE_CLASSIFICATION 이후 `post_classification_analysis()` 수행
   - 초기 사용자 입력을 GPT로 분석하여 포함된 정보 추출
   - `skipped_fields`로 이미 답변된 필드 추적

4. **에러 처리 및 폴백 로직**
   - GPT API 실패 시 기존 엔티티 추출 방식으로 폴백
   - 상세한 에러 로깅 및 경고 메시지

5. **로깅 개선**
   - 1차 서술 분석 결과, skipped_fields, conversation_history 변경사항 상세 로깅
   - 디버그 레벨 로깅 추가

### 이전 개선 사항
1. **직접 노드 호출 제거**: `validation_node`에서 `re_question_node`, `summary_node` 직접 호출 제거
2. **중복 질문 방지 강화**: `asked_fields`와 `skipped_fields` 체크로 같은 질문 반복 방지
3. **에러 처리 개선**: 모든 노드에 폴백 로직 추가
4. **로깅 강화**: 모든 `logger.error` 호출에 `exc_info=True` 추가

---

## 관련 파일

- `src/langgraph/nodes/__init__.py`: 노드 함수 export
- `src/langgraph/graph.py`: LangGraph 그래프 구성
- `src/langgraph/state.py`: State Context 타입 정의
- `src/langgraph/edges/conditional_edges.py`: 조건부 엣지 로직

---

## 참고사항

- 각 노드는 독립적으로 실행 가능 (단일 책임 원칙)
- State는 불변(immutable)하지 않지만, 노드 간 전달 시 새로운 딕셔너리 생성
- DB 저장은 각 노드에서 필요 시 수행 (트랜잭션 단위로 관리)
- 로깅은 모든 노드에서 상세히 수행하여 디버깅 용이

