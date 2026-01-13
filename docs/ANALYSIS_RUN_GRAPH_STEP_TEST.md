# `run_graph_step` 테스트 결과 분석

## 테스트 실행 결과 요약

`--use-graph-step` 옵션으로 실제 웹과 동일한 방식으로 테스트한 결과:

### ✅ 정상 작동한 부분

1. **체인 실행 로직 작동 확인**
   ```
   🔍 [DEBUG] State 전이 감지: VALIDATION → SUMMARY, 체인조건=True
   🔄 VALIDATION → SUMMARY 전이 감지
   ▶️  SUMMARY 노드 실행 시작...
   ✅ SUMMARY 노드 실행 완료
   ✅ bot_message 병합 완료
   ```

2. **노드 실행 순서**
   - INIT → CASE_CLASSIFICATION ✅
   - CASE_CLASSIFICATION → FACT_COLLECTION ✅
   - FACT_COLLECTION → VALIDATION ✅
   - VALIDATION → SUMMARY (체인 실행) ✅
   - SUMMARY → COMPLETED (연쇄 전이) ✅

3. **State 전이 및 병합**
   - `bot_message` 병합 정상 작동 ✅
   - `missing_fields` 전달 정상 작동 ✅

## ⚠️ 발견된 문제

### 1. VALIDATION 노드가 `missing_fields`를 빈 배열로 만듦

**로그:**
```
[FACT_COLLECTION 실행 후]
누락 필드: ['counterparty', 'amount']

[VALIDATION 실행 후]
missing_fields=[]  # ❌ 빈 배열로 변경됨
```

**원인 분석:**
```python
# VALIDATION 노드 실행 로그
[sess_7da395efe3e6] 누락 필드 분석 완료: 
  required_fields=['incident_date', 'counterparty', 'amount', 'evidence']
  asked_fields=['incident_date', 'evidence', 'counterparty']
  missing_fields=[]  # ❌ 'amount'가 추출되었다고 판단
```

**문제:**
- FACT_COLLECTION에서 `missing_fields=['counterparty', 'amount']`로 설정
- VALIDATION 노드가 conversation_history를 분석하여 facts를 추출
- GPT가 `amount=5000000`을 추출했다고 판단
- `asked_fields`에는 `amount`가 없지만, facts에 `amount`가 있으면 `missing_fields`를 빈 배열로 만듦

**실제 로그:**
```
[sess_7da395efe3e6] 추출된 facts 상세: 
  [('incident_date', '2023-10-02'), 
   ('amount', 5000000),  # ✅ GPT가 추출함
   ('counterparty', '음주운전을 하다가 전봇대를 박았어요.'), 
   ('evidence', False)]
```

### 2. `missing_fields` 계산 로직 문제

**현재 로직 (validation_node.py):**
```python
# asked_fields는 conversation_history 기반
asked_fields = [qa.get('field') for qa in conversation_history]

# missing_fields는 required_fields - asked_fields
missing_fields = [f for f in required_fields if f not in asked_fields]
```

**문제점:**
- `asked_fields`는 "질문한 필드"만 추적
- 하지만 GPT가 conversation_history에서 facts를 추출할 때, 질문하지 않았던 필드도 추출 가능
- 예: `amount`는 질문하지 않았지만, 사용자가 "피해금액은 약 500만원입니다"라고 말해서 GPT가 추출함
- 이 경우 `missing_fields`는 빈 배열이 되지만, 실제로는 질문해야 할 필드가 있을 수 있음

### 3. 테스트 시나리오 문제

**테스트 코드:**
```python
# 5. VALIDATION 노드 테스트 (체인 실행 로직 테스트)
state["current_state"] = "VALIDATION"
state["last_user_input"] = "어제"
# missing_fields를 강제로 설정하여 RE_QUESTION으로 전이하도록 함
state["missing_fields"] = ["location", "counterparty"]  # 테스트용
```

**문제:**
- 테스트에서 `missing_fields=["location", "counterparty"]`로 강제 설정했지만
- VALIDATION 노드가 실행되면서 conversation_history를 분석하여 다시 계산
- 결과적으로 `missing_fields=[]`가 되어 RE_QUESTION이 아닌 SUMMARY로 전이

## 실제 웹에서 발생하는 문제와의 연관성

### 실제 웹에서의 문제 시나리오

1. **사용자 입력:**
   - "어제 음주운전 사고를 냈어요"
   - "음주운전을 하다가 전봇대를 박았어요. 피해금액은 약 500만원입니다"

2. **VALIDATION 노드 실행:**
   - GPT가 conversation_history에서 facts 추출
   - `incident_date`, `amount`, `counterparty`, `evidence` 모두 추출됨
   - `asked_fields`에는 `incident_date`, `evidence`, `counterparty`만 포함
   - 하지만 facts에 `amount`가 있으므로 `missing_fields=[]`로 계산
   - **RE_QUESTION으로 전이해야 하지만 SUMMARY로 전이**

3. **결과:**
   - RE_QUESTION 노드가 실행되지 않음
   - `bot_message`가 없음 → "(메시지 없음)" 표시

## 해결 방안

### 1. `missing_fields` 계산 로직 개선

**현재:**
```python
missing_fields = [f for f in required_fields if f not in asked_fields]
```

**개선안:**
```python
# facts에 값이 있고, conversation_history에 명시적으로 Q-A 쌍이 있는 경우만 수집 완료로 판단
collected_fields = set()
for qa in conversation_history:
    field = qa.get('field')
    answer = qa.get('answer', '').strip()
    if field and answer:  # 명시적인 Q-A 쌍이 있는 경우만
        collected_fields.add(field)

missing_fields = [f for f in required_fields if f not in collected_fields]
```

### 2. facts 추출과 `missing_fields` 계산 분리

**문제:** GPT가 추출한 facts와 실제로 질문한 필드를 구분해야 함

**해결:**
- facts 추출: GPT가 conversation_history에서 가능한 모든 facts 추출
- `missing_fields` 계산: conversation_history에 명시적인 Q-A 쌍이 있는 필드만 제외

### 3. 테스트 시나리오 개선

RE_QUESTION으로 전이하는 경우를 테스트하려면:
```python
# conversation_history에 명시적인 Q-A 쌍이 없는 필드를 missing_fields로 설정
state["conversation_history"] = [
    {"field": "incident_date", "question": "사건이 발생한 날짜는?", "answer": "어제"}
]
# amount는 conversation_history에 없으므로 missing_fields에 포함되어야 함
```

## 다음 단계

1. ✅ `run_graph_step` 체인 실행 로직은 정상 작동 확인
2. ❌ VALIDATION 노드의 `missing_fields` 계산 로직 개선 필요
3. ❌ 테스트 시나리오 개선 필요 (RE_QUESTION 전이 케이스)

## 결론

**테스트는 정상 작동했지만**, 실제 웹에서 문제가 발생하는 이유는:
- VALIDATION 노드가 GPT로 추출한 facts를 기반으로 `missing_fields`를 계산
- 질문하지 않았던 필드도 GPT가 추출하면 `missing_fields`가 빈 배열이 됨
- 결과적으로 RE_QUESTION으로 전이하지 않고 SUMMARY로 바로 전이
- RE_QUESTION 노드가 실행되지 않아 `bot_message`가 없음

**해결책:** `missing_fields` 계산 시 GPT 추출 facts가 아닌 명시적인 Q-A 쌍만 고려해야 함
