# Q-A 매칭 방식 설계안

## 목차
1. [현재 방식의 문제점](#현재-방식의-문제점)
2. [Q-A 매칭 방식 개요](#q-a-매칭-방식-개요)
3. [상세 설계](#상세-설계)
4. [구현 방안](#구현-방안)
5. [장점 및 기대 효과](#장점-및-기대-효과)
6. [마이그레이션 전략](#마이그레이션-전략)

---

## 현재 방식의 문제점

### 1. 복잡한 엔티티 추출 로직
```python
# 현재 방식: 각 필드별로 별도의 추출 함수 호출
extracted_date = extract_date_from_input(user_input, facts.get("incident_date"))
extracted_amount = extract_amount_from_input(user_input, facts.get("amount"))
extracted_counterparty = extract_counterparty_from_input(user_input, facts.get("counterparty"))
extract_evidence_from_input(user_input, facts.get("evidence"))

# 문제점:
# - 날짜 패턴, 금액 패턴 등 복잡한 정규식 처리
# - "어제", "내일" 같은 상대 날짜 처리
# - "모름", "없음" 같은 특수 케이스 처리
# - 필드 간 충돌 (날짜가 금액으로 인식되는 등)
```

### 2. 중복 질문 방지 로직의 복잡성
```python
# 현재 방식: facts 업데이트 여부를 수동으로 확인
facts_before_update = copy.deepcopy(facts)
# ... 엔티티 추출 ...
field_updated = (facts.get(expected_field) != facts_before_update.get(expected_field))

# 문제점:
# - None에서 값으로 변경된 경우 vs 값이 변경된 경우 구분
# - 여러 필드가 동시에 업데이트된 경우 처리
# - extracted 되었지만 실제로는 의미 없는 값인 경우
```

### 3. 에러 발생 가능성
- 정규식 패턴 매칭 실패
- 날짜 파싱 오류
- 금액 형식 인식 실패 (예: "30만원" vs "300만원")
- 증거 키워드 매칭 실패

---

## Q-A 매칭 방식 개요

### 핵심 아이디어
**"질문에 대한 답변을 그대로 저장하고, GPT가 최종적으로 구조화된 데이터로 변환"**

### 추가 개선안: 1차 서술 분석
**"초기 사용자 입력(1차 서술)을 GPT로 분석하여 이미 포함된 정보를 추출하고, 해당 질문을 자동으로 패스"**

### 기본 원칙
1. **1차 서술 분석**: 초기 사용자 입력을 GPT로 분석하여 포함된 정보 추출
2. **질문 필터링**: 이미 답변된 질문은 질문 리스트에서 제외
3. **질문-답변 쌍 저장**: 각 질문과 사용자의 답변을 쌍으로 저장
4. **자연스러운 대화**: 사용자가 자유롭게 답변 가능
5. **최종 정리는 GPT**: 모든 Q-A 쌍을 GPT에 넘겨서 구조화된 데이터 추출
6. **에러 최소화**: 복잡한 추출 로직 제거, GPT의 자연어 이해 능력 활용

---

## 상세 설계

### 0. 1차 서술 분석 단계 (CASE_CLASSIFICATION 이후)

#### 흐름도
```
CASE_CLASSIFICATION → 1차 서술 분석 (GPT) → 질문 리스트 필터링 → FACT_COLLECTION
```

#### 1차 서술 분석 함수
```python
def _analyze_initial_description(
    initial_description: str,
    case_type: str,
    required_fields: List[str]
) -> Dict[str, Any]:
    """
    1차 서술(초기 사용자 입력)을 GPT로 분석하여 포함된 정보 추출
    
    Args:
        initial_description: 초기 사용자 입력 ("친구가 2024년 1월 2일에 300만원을 빌려갔는데...")
        case_type: 사건 유형 (CIVIL, CRIMINAL, etc.)
        required_fields: 필수 필드 목록 (RAG K2에서 가져온 것)
    
    Returns:
        {
            "extracted_facts": {...},  # 추출된 정보
            "answered_fields": ["incident_date", "amount", "counterparty"],  # 이미 답변된 필드
            "missing_fields": ["evidence", "evidence_type"]  # 질문해야 할 필드
        }
    """
    prompt = f"""다음은 법률 상담 챗봇에 처음 입력한 사용자의 사건 서술입니다.
사건 유형: {case_type}

사용자 서술:
{initial_description}

위 서술에서 다음 필드에 대한 정보가 포함되어 있는지 분석하고, 포함된 정보를 추출해주세요.

필수 필드 목록:
{', '.join(required_fields)}

각 필드별 설명:
- incident_date: 사건 발생 날짜
- amount: 금액 또는 손해액
- counterparty: 상대방 이름 또는 설명
- counterparty_type: 상대방 유형 (개인/법인/기관)
- evidence: 증거 유무
- evidence_type: 증거 종류

다음 JSON 형식으로 반환해주세요:
{{
    "extracted_facts": {{
        "incident_date": "날짜가 있으면 YYYY-MM-DD 형식으로, 없으면 null",
        "amount": "금액이 있으면 숫자만, 없으면 null",
        "counterparty": "상대방이 있으면 이름, 없으면 null",
        "counterparty_type": "상대방 유형이 있으면, 없으면 null",
        "evidence": "증거 언급이 있으면 true/false, 없으면 null",
        "evidence_type": "증거 종류가 있으면, 없으면 null"
    }},
    "answered_fields": ["이미 답변된 필드 목록"],
    "missing_fields": ["질문해야 할 필드 목록"]
}}

주의사항:
- 서술에 명시적으로 언급된 정보만 추출 (추측하지 않음)
- 날짜는 "2024년 1월 2일", "24년 1월 2일", "1월 2일" 등 다양한 형식을 YYYY-MM-DD로 변환
- 금액은 "300만원", "3백만원", "3,000,000원" 등을 숫자만 추출
- "없음", "모름" 등은 해당 필드가 null로 처리
- 정보가 불확실하면 null로 처리

JSON만 반환하세요:
"""
    
    response = gpt_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response["content"])
    return result
```

### 1. State Context 구조 변경

#### 기존 구조
```python
{
    "facts": {
        "incident_date": "2024-10-15",
        "amount": 3000000,
        "counterparty": "친구",
        ...
    },
    "asked_fields": ["incident_date", "amount"],
    "expected_input": {"field": "evidence", "type": "boolean"}
}
```

#### 새로운 구조
```python
{
    "initial_description": "친구가 2024년 1월 2일에 300만원을 빌려갔는데 변제를 하지 않음",
    "initial_analysis": {
        "extracted_facts": {
            "incident_date": "2024-01-02",
            "amount": 3000000,
            "counterparty": "친구",
            "counterparty_type": "개인",
            "evidence": null,
            "evidence_type": null
        },
        "answered_fields": ["incident_date", "amount", "counterparty", "counterparty_type"],
        "missing_fields": ["evidence", "evidence_type"]
    },
    "conversation_history": [
        {
            "question": "사건과 관련된 구체적인 내용을 알려주세요.",
            "field": "fact_description",
            "answer": "친구가 돈을 빌려갔는데 변제를 하지 않음",
            "source": "initial_description",  # 1차 서술에서 추출
            "timestamp": "2024-01-15T10:30:00"
        },
        {
            "question": "관련 증거를 가지고 계신가요?",
            "field": "evidence",
            "answer": "네 있음",
            "timestamp": "2024-01-15T10:31:00"
        }
    ],
    "current_question": {
        "question": "증거의 종류를 알려주세요.",
        "field": "evidence_type",
        "asked_at": "2024-01-15T10:34:00"
    },
    "skipped_fields": ["incident_date", "amount", "counterparty"]  # 1차 서술에서 이미 답변되어 패스
}
```

### 2. CASE_CLASSIFICATION Node 이후 추가 단계

#### CASE_CLASSIFICATION 완료 후
```python
@log_execution_time(logger)
def post_classification_analysis(state: StateContext) -> Dict[str, Any]:
    """
    CASE_CLASSIFICATION 이후 1차 서술 분석
    
    Returns:
        분석 결과를 포함한 state 업데이트
    """
    session_id = state["session_id"]
    initial_description = state.get("last_user_input", "")  # CASE_CLASSIFICATION에서 받은 입력
    case_type = state.get("case_type")
    
    # RAG에서 필수 필드 목록 가져오기
    rag_results = rag_searcher.search(
        query="필수 필드",
        knowledge_type="K2",
        main_case_type=case_type,
        top_k=1
    )
    required_fields = extract_required_fields_from_rag(rag_results)
    if not required_fields:
        required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
    
    # 1차 서술 분석 (GPT)
    analysis_result = _analyze_initial_description(
        initial_description,
        case_type,
        required_fields
    )
    
    # State 업데이트
    state["initial_description"] = initial_description
    state["initial_analysis"] = analysis_result
    
    # 1차 서술에서 추출된 정보를 conversation_history에 추가
    extracted_facts = analysis_result.get("extracted_facts", {})
    answered_fields = analysis_result.get("answered_fields", [])
    
    conversation_history = []
    for field in answered_fields:
        if extracted_facts.get(field) is not None:
            # RAG에서 해당 필드의 질문 템플릿 가져오기 (로깅용)
            question = get_question_message(field, case_type)
            conversation_history.append({
                "question": question,
                "field": field,
                "answer": str(extracted_facts[field]),
                "source": "initial_description",
                "timestamp": get_kst_now().isoformat()
            })
    
    state["conversation_history"] = conversation_history
    state["skipped_fields"] = answered_fields
    state["missing_fields"] = analysis_result.get("missing_fields", [])
    
    logger.info(f"[{session_id}] 1차 서술 분석 완료: answered_fields={answered_fields}, missing_fields={state['missing_fields']}")
    
    return state
```

### 3. FACT_COLLECTION Node 변경

#### 기존 로직
```python
# 복잡한 엔티티 추출
entities = entity_extractor.extract_all_entities(user_input, entity_fields)
facts = _update_facts_from_entities(facts, entities, user_input, expected_field, session_id)
facts = _update_facts_from_evidence(facts, user_input, expected_input, session_id)

# Facts 업데이트 여부 확인
field_updated = (facts.get(expected_field) != facts_before_update.get(expected_field))
```

#### 새로운 로직
```python
# 단순히 Q-A 쌍으로 저장
current_question = state.get("current_question")
if current_question and user_input:
    qa_pair = {
        "question": current_question["question"],
        "field": current_question["field"],
        "answer": user_input,
        "timestamp": get_kst_now().isoformat()
    }
    conversation_history = state.get("conversation_history", [])
    conversation_history.append(qa_pair)
    state["conversation_history"] = conversation_history
```

### 4. VALIDATION Node 변경

#### 기존 로직
```python
# RAG에서 필수 필드 조회
required_fields = extract_required_fields_from_rag(rag_results)

# 누락 필드 확인
missing_fields = [field for field in required_fields if facts.get(field) is None]
```

#### 새로운 로직
```python
# GPT로 Q-A 쌍에서 구조화된 데이터 추출
conversation_history = state.get("conversation_history", [])

# GPT에게 Q-A 쌍을 넘겨서 facts 추출
facts = _extract_facts_from_conversation(conversation_history, case_type)

# RAG에서 필수 필드 조회
required_fields = extract_required_fields_from_rag(rag_results)

# 질문한 필드 확인
asked_fields = [qa["field"] for qa in conversation_history]

# 누락 필드 확인 (질문하지 않은 필드)
missing_fields = [field for field in required_fields if field not in asked_fields]
```

### 5. GPT 기반 Facts 추출 함수

```python
def _extract_facts_from_conversation(
    conversation_history: List[Dict[str, str]],
    case_type: str
) -> Dict[str, Any]:
    """
    Q-A 대화 기록에서 구조화된 facts 추출
    
    Args:
        conversation_history: 질문-답변 쌍 리스트
        case_type: 사건 유형
    
    Returns:
        구조화된 facts 딕셔너리
    """
    # Q-A 쌍을 텍스트로 변환
    qa_text = "\n\n".join([
        f"Q: {qa['question']}\nA: {qa['answer']}"
        for qa in conversation_history
    ])
    
    # GPT 프롬프트 구성
    prompt = f"""다음은 법률 상담 챗봇과 사용자의 질문-답변 대화입니다.
사건 유형: {case_type}

대화 내용:
{qa_text}

위 대화 내용에서 다음 정보를 추출하여 JSON 형식으로 반환해주세요:
{{
    "incident_date": "사건 발생 날짜 (YYYY-MM-DD 형식, 없으면 null)",
    "amount": "금액 (숫자만, 없으면 null)",
    "counterparty": "상대방 이름 또는 설명 (없으면 null)",
    "counterparty_type": "상대방 유형 (개인/법인/기관, 없으면 null)",
    "evidence": "증거 유무 (true/false/null)",
    "evidence_type": "증거 종류 (없으면 null)",
    "action_description": "행위 설명 (간단히, 없으면 null)"
}}

주의사항:
- 날짜는 "25년 1월 2일" → "2025-01-02" 형식으로 변환
- 금액은 "300만원" → 3000000 형식으로 변환
- 증거 질문에 "네", "있음", "있습니다" 등 긍정 답변은 evidence: true
- 증거 질문에 "없음", "모름" 등 부정 답변은 evidence: false
- 정보가 없으면 null로 반환
- 추측하지 말고 대화 내용에 있는 정보만 추출

JSON만 반환하세요 (설명 없이):
"""
    
    # GPT API 호출
    response = gpt_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # 낮은 온도로 일관성 확보
        response_format={"type": "json_object"}  # JSON 형식 강제
    )
    
    # JSON 파싱
    import json
    facts = json.loads(response["content"])
    
    return facts
```

---

## 구현 방안

### 1. CASE_CLASSIFICATION Node 수정 (1차 서술 분석 추가)

```python
@log_execution_time(logger)
def case_classification_node(state: StateContext) -> Dict[str, Any]:
    """
    CASE_CLASSIFICATION Node 실행 (1차 서술 분석 포함)
    """
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "")
        
        # ... 기존 사건 유형 분류 로직 ...
        
        # 1차 서술 분석 수행
        state = post_classification_analysis(state)
        
        # State 업데이트
        state["bot_message"] = "사건과 관련된 구체적인 내용을 알려주세요."
        
        # 1차 서술에서 이미 답변된 필드가 있으면 안내
        skipped_fields = state.get("skipped_fields", [])
        if skipped_fields:
            logger.info(f"[{session_id}] 1차 서술에서 이미 답변된 필드: {skipped_fields}")
            # (선택적) 사용자에게 이미 파악한 정보 알림
            # state["bot_message"] = f"네, {', '.join(skipped_fields)} 정보는 이미 확인했습니다."
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }
    
    except Exception as e:
        logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }
```

### 2. FACT_COLLECTION Node 수정

```python
@log_execution_time(logger)
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    """
    FACT_COLLECTION Node 실행 (Q-A 매칭 방식)
    """
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "").strip()
        current_question = state.get("current_question")
        
        # 사용자 입력이 없으면 이전 질문 유지
        if not user_input:
            if not state.get("bot_message"):
                # 다음 질문 생성
                next_question = _generate_next_question(state)
                state["bot_message"] = next_question["question"]
                state["current_question"] = next_question
            return {
                **state,
                "next_state": "FACT_COLLECTION"
            }
        
        # Q-A 쌍 저장
        if current_question and user_input:
            qa_pair = {
                "question": current_question["question"],
                "field": current_question["field"],
                "answer": user_input,
                "timestamp": get_kst_now().isoformat()
            }
            conversation_history = state.get("conversation_history", [])
            conversation_history.append(qa_pair)
            state["conversation_history"] = conversation_history
            
            logger.info(f"[{session_id}] Q-A 쌍 저장: field={current_question['field']}, answer={user_input[:50]}")
        
        # 다음 질문 생성
        next_question = _generate_next_question(state)
        state["bot_message"] = next_question["question"]
        state["current_question"] = next_question
        
        return {
            **state,
            "next_state": "VALIDATION"
        }
    
    except Exception as e:
        logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}", exc_info=True)
        return {
            **state,
            "bot_message": "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.",
            "next_state": "VALIDATION"
        }
```

### 3. VALIDATION Node 수정

```python
@log_execution_time(logger)
def validation_node(state: StateContext) -> Dict[str, Any]:
    """
    VALIDATION Node 실행 (Q-A 매칭 방식)
    """
    try:
        session_id = state["session_id"]
        conversation_history = state.get("conversation_history", [])
        case_type = state.get("case_type")
        
        # GPT로 Q-A 쌍에서 facts 추출 (1차 서술 포함)
        # conversation_history에는 이미 1차 서술에서 추출된 정보가 포함됨
        facts = _extract_facts_from_conversation(conversation_history, case_type)
        
        # 1차 서술 분석 결과도 병합 (더 정확한 정보 우선)
        initial_analysis = state.get("initial_analysis", {})
        if initial_analysis:
            initial_facts = initial_analysis.get("extracted_facts", {})
            # conversation_history의 최신 정보가 우선, 없으면 initial_facts 사용
            for key, value in initial_facts.items():
                if facts.get(key) is None and value is not None:
                    facts[key] = value
        
        state["facts"] = facts
        
        logger.info(f"[{session_id}] GPT로 facts 추출 완료: {list(facts.keys())}")
        
        # RAG에서 필수 필드 조회
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=case_type,
            top_k=1
        )
        required_fields = extract_required_fields_from_rag(rag_results)
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
        
        # 질문한 필드 확인
        asked_fields = [qa["field"] for qa in conversation_history]
        
        # 누락 필드 확인 (질문하지 않은 필수 필드)
        missing_fields = [
            field for field in required_fields
            if field not in asked_fields
        ]
        
        state["missing_fields"] = missing_fields
        
        # DB 저장
        _save_facts_to_database(session_id, facts, [], "", state.get("completion_rate", 0))
        
        # 조건부 분기
        if missing_fields:
            return {
                **state,
                "next_state": "RE_QUESTION"
            }
        else:
            return {
                **state,
                "bot_message": "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다.",
                "next_state": "SUMMARY"
            }
    
    except Exception as e:
        logger.error(f"VALIDATION Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백: 기존 conversation_history 기반으로 처리
        return {
            **state,
            "next_state": "RE_QUESTION" if state.get("missing_fields") else "SUMMARY"
        }
```

### 6. _generate_next_question 함수 수정

```python
def _generate_next_question(state: StateContext) -> Dict[str, Any]:
    """
    다음 질문 생성 (Q-A 매칭 방식, 1차 서술 분석 반영)
    """
    conversation_history = state.get("conversation_history", [])
    asked_fields = [qa["field"] for qa in conversation_history]
    skipped_fields = state.get("skipped_fields", [])  # 1차 서술에서 이미 답변된 필드
    missing_fields = state.get("missing_fields", [])  # 1차 서술 분석 결과
    case_type = state.get("case_type")
    
    # 아직 질문하지 않은 필수 필드 찾기
    # 1차 서술에서 이미 답변된 필드(skipped_fields)와 이미 질문한 필드(asked_fields)는 제외
    next_field = None
    excluded_fields = set(asked_fields) | set(skipped_fields)
    
    for field in missing_fields:
        if field not in excluded_fields:
            next_field = field
            break
    
    # missing_fields가 없거나 모두 제외된 경우, 전체 필수 필드에서 다시 확인
    if not next_field:
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=case_type,
            top_k=1
        )
        required_fields = extract_required_fields_from_rag(rag_results)
        if not required_fields:
            required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(case_type, [])
        
        for field in required_fields:
            if field not in excluded_fields:
                next_field = field
                break
    
    if not next_field:
        # 모든 필수 필드 질문 완료
        return {
            "question": "추가로 알려주실 정보가 있으신가요?",
            "field": "additional_info"
        }
    
    # RAG에서 질문 템플릿 조회
    try:
        rag_results = rag_searcher.search(
            query=f"{next_field} 질문",
            knowledge_type="K2",
            main_case_type=case_type,
            top_k=1
        )
        question = extract_question_template_from_rag(rag_results, next_field)
    except:
        question = None
    
    if not question:
        question = get_question_message(next_field, case_type)
    
    logger.info(f"[{state.get('session_id', 'unknown')}] 다음 질문 생성: {next_field} (제외된 필드: {excluded_fields})")
    
    return {
        "question": question,
        "field": next_field
    }
```

---

## 장점 및 기대 효과

### 1. 에러 최소화 ✅
- **기존**: 정규식 패턴 매칭 실패, 날짜 파싱 오류 등
- **개선**: GPT의 자연어 이해 능력으로 다양한 형식 자동 처리
- **예시**: "25년 1월 2일" → GPT가 자동으로 "2025-01-02"로 변환

### 2. 코드 단순화 ✅
- **기존**: 각 필드별 추출 함수 (10개 이상)
- **개선**: 단일 GPT 호출 함수
- **유지보수**: 새로운 필드 추가 시 GPT 프롬프트만 수정

### 3. 자연스러운 대화 ✅
- **기존**: "25년 1월 2일" 같은 정확한 형식 요구
- **개선**: "어제", "지난달", "작년 3월" 등 자연스러운 표현 허용
- **사용자 경험**: 더 자연스러운 대화 흐름

### 4. 중복 질문 방지 개선 ✅
- **기존**: Facts 업데이트 여부를 수동으로 확인
- **개선**: Q-A 쌍으로 명확하게 추적, 이미 질문한 필드는 자동 제외
- **추가 개선**: 1차 서술 분석으로 처음부터 포함된 정보 파악, 해당 질문 자동 패스

### 4-1. 효율적인 대화 흐름 ✅
- **기존**: 모든 필드에 대해 순차적으로 질문
- **개선**: 1차 서술에 이미 답변된 정보는 질문하지 않음
- **예시**: 사용자가 "2024년 1월 2일에 300만원"이라고 처음에 말하면, 날짜/금액 질문 자동 패스

### 5. 확장성 ✅
- **기존**: 새로운 필드 추가 시 추출 함수 작성 필요
- **개선**: GPT 프롬프트에 필드만 추가하면 자동 처리

---

## 마이그레이션 전략

### Phase 1: 하이브리드 방식 (권장)
- 기존 엔티티 추출 로직 유지
- Q-A 쌍도 동시에 저장
- GPT 추출 결과와 기존 추출 결과 비교/검증

### Phase 2: 점진적 전환
- 간단한 필드부터 GPT 방식으로 전환
- 날짜, 금액 등 복잡한 필드는 마지막에 전환

### Phase 3: 완전 전환
- 모든 엔티티 추출 로직 제거
- Q-A 매칭 방식으로 완전 전환

### 테스트 전략
1. **단위 테스트**: `_extract_facts_from_conversation()` 함수 테스트
2. **통합 테스트**: 전체 대화 흐름 테스트
3. **A/B 테스트**: 기존 방식 vs 새 방식 비교

---

## 비용 분석

### GPT API 호출 횟수
- **기존**: 필드별로 엔티티 추출 (여러 번 호출)
- **새 방식**: VALIDATION 노드에서 1회 호출 (전체 대화 정리)
- **비용**: 실제로는 비슷하거나 더 저렴할 수 있음 (요청 횟수 감소)

### 모델 선택
- **gpt-4o-mini**: 비용 효율적, 정확도 양호 (권장)
- **gpt-4o**: 더 높은 정확도 필요 시
- **gpt-3.5-turbo**: 저비용이 최우선일 때

---

## 구현 우선순위

1. **High**: `_analyze_initial_description()` 함수 구현 (1차 서술 분석)
2. **High**: `post_classification_analysis()` 함수 구현
3. **High**: `_extract_facts_from_conversation()` 함수 구현
4. **High**: CASE_CLASSIFICATION Node 수정 (1차 서술 분석 통합)
5. **High**: FACT_COLLECTION Node 수정
6. **Medium**: VALIDATION Node 수정 (1차 서술 결과 병합)
7. **Medium**: _generate_next_question 함수 수정 (skipped_fields 반영)
8. **Low**: 기존 엔티티 추출 로직 제거 (안정화 후)

---

## 예시 시나리오

### 시나리오 1: 1차 서술에 많은 정보 포함

**사용자 입력 (CASE_CLASSIFICATION 단계)**:
```
"친구가 2024년 1월 2일에 300만원을 빌려갔는데 변제를 하지 않습니다. 
계약서도 있고, 증거로 대화 내역도 있습니다."
```

**1차 서술 분석 결과**:
```json
{
    "extracted_facts": {
        "incident_date": "2024-01-02",
        "amount": 3000000,
        "counterparty": "친구",
        "counterparty_type": "개인",
        "evidence": true,
        "evidence_type": "계약서, 대화내역"
    },
    "answered_fields": ["incident_date", "amount", "counterparty", "counterparty_type", "evidence", "evidence_type"],
    "missing_fields": []
}
```

**결과**:
- 모든 필수 필드가 1차 서술에 포함됨
- 추가 질문 없이 바로 SUMMARY로 이동
- 대화 시간 단축, 사용자 경험 개선

### 시나리오 2: 1차 서술에 일부 정보만 포함

**사용자 입력**:
```
"친구가 돈을 빌려갔는데 갚지 않아요"
```

**1차 서술 분석 결과**:
```json
{
    "extracted_facts": {
        "incident_date": null,
        "amount": null,
        "counterparty": "친구",
        "counterparty_type": "개인",
        "evidence": null,
        "evidence_type": null
    },
    "answered_fields": ["counterparty", "counterparty_type"],
    "missing_fields": ["incident_date", "amount", "evidence", "evidence_type"]
}
```

**결과**:
- 날짜, 금액, 증거 질문만 추가로 진행
- 상대방 정보는 질문하지 않음
- 효율적인 대화 흐름

---

## 결론

Q-A 매칭 방식 + 1차 서술 분석은 현재의 복잡한 엔티티 추출 로직을 크게 단순화하고, 에러를 최소화하며, 더 자연스럽고 효율적인 대화를 가능하게 합니다.

**핵심 포인트**:
- ✅ 에러 최소화: 복잡한 정규식 제거
- ✅ 코드 단순화: 단일 GPT 호출로 대체
- ✅ 자연스러운 대화: 다양한 표현 허용
- ✅ 확장성: 새로운 필드 추가 용이
- ✅ **효율성**: 1차 서술 분석으로 불필요한 질문 자동 패스
- ✅ **사용자 경험**: 처음에 많은 정보를 제공하면 추가 질문 최소화

이 방식으로 전환하면 유지보수성이 크게 향상되고, 사용자 경험도 크게 개선될 것입니다.

