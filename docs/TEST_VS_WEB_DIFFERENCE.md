# 테스트 vs 실제 웹 차이점 분석

## 문제 상황
- ✅ 테스트 스크립트 (`test_nodes_sequential.py`)는 정상 작동
- ❌ 실제 웹 (`chat_gpt.html`)에서는 RE_QUESTION에서 "(메시지 없음)" 문제 발생

## 차이점

### 1. 실행 경로 차이

#### 테스트 (기존 방식)
```python
# 각 노드를 직접 호출
state = init_node(state)
state = case_classification_node(state)
state = validation_node(state)
state = re_question_node(state)  # 직접 호출
```

**특징:**
- 체인 실행 로직을 거치지 않음
- 각 노드를 명시적으로 호출
- `missing_fields`가 직접 전달됨

#### 실제 웹
```python
# run_graph_step을 통해 실행
result = run_graph_step(state)  # 내부에서 체인 실행 로직 처리
```

**특징:**
- `run_graph_step` 내부에서 체인 실행 로직 처리
- VALIDATION → RE_QUESTION 전이 시 자동으로 RE_QUESTION 노드 실행
- `missing_fields`가 체인 실행 로직을 통해 전달되어야 함

### 2. 체인 실행 로직

`run_graph_step`에서 VALIDATION → RE_QUESTION 전이 시:

```python
is_chain_condition = current_state == "VALIDATION" and next_state in ["RE_QUESTION", "SUMMARY"]
if is_chain_condition:
    # RE_QUESTION 노드를 즉시 실행
    next_result = next_node_func(result)
    # 결과 병합
    result["bot_message"] = next_result["bot_message"]
    result["missing_fields"] = next_result.get("missing_fields", [])
```

**문제 가능성:**
1. `is_chain_condition`이 `False`로 평가됨
2. `missing_fields`가 `result`에서 손실됨
3. RE_QUESTION 노드가 실행되지 않음
4. RE_QUESTION 노드가 실행되더라도 `bot_message`가 병합되지 않음

## 해결 방법

### 1. `run_graph_step` 사용 테스트 실행

실제 웹과 동일한 방식으로 테스트:

```powershell
python tests/test_nodes_sequential.py --mode sequential --use-graph-step
```

이렇게 하면:
- `run_graph_step`을 사용하여 테스트
- 체인 실행 로직이 실제로 작동하는지 확인
- `missing_fields` 손실 문제 재현 가능

### 2. 로그 확인

실제 웹에서 다음 로그를 확인:

```powershell
Get-Content logs\app.log -Wait -Tail 100 | Select-String -Pattern "체인조건|VALIDATION.*RE_QUESTION|missing_fields|RE_QUESTION 노드 실행"
```

확인할 로그:
- `🔍 [DEBUG] State 전이 감지: VALIDATION → RE_QUESTION, 체인조건=True`
- `🔄 VALIDATION → RE_QUESTION 전이 감지`
- `📋 missing_fields: [...]`
- `▶️  RE_QUESTION 노드 실행 시작...`
- `✅ RE_QUESTION 노드 실행 완료`
- `💬 반환 bot_message: ...`

### 3. 문제 진단

#### 체인 조건이 False인 경우
```
🔍 [DEBUG] State 전이 감지: VALIDATION → RE_QUESTION, 체인조건=False
```
→ `is_chain_condition` 로직 확인 필요

#### missing_fields가 손실된 경우
```
📋 missing_fields: []
```
→ VALIDATION 노드에서 `missing_fields` 반환 확인 필요

#### RE_QUESTION 노드가 실행되지 않은 경우
```
✅ State 전이: VALIDATION → RE_QUESTION
(RE_QUESTION 노드 실행 로그 없음)
```
→ 체인 실행 로직이 실행되지 않음

#### bot_message가 병합되지 않은 경우
```
✅ RE_QUESTION 노드 실행 완료
💬 반환 bot_message: ...
(하지만 최종 result에 bot_message 없음)
```
→ 결과 병합 로직 확인 필요

## 수정된 테스트 스크립트 사용법

### 기본 테스트 (노드 직접 호출)
```powershell
python tests/test_nodes_sequential.py --mode sequential
```

### 실제 웹과 동일한 방식 테스트
```powershell
python tests/test_nodes_sequential.py --mode sequential --use-graph-step
```

### 둘 다 실행
```powershell
python tests/test_nodes_sequential.py --mode both --use-graph-step
```

## 예상 결과

### 정상 작동 시
```
🔄 VALIDATION → RE_QUESTION 전이 감지
📋 missing_fields: ['location', 'counterparty']
▶️  RE_QUESTION 노드 실행 시작...
✅ RE_QUESTION 노드 실행 완료
💬 반환 bot_message: 사건 발생 장소는 어디인가요?
✅ bot_message 병합 완료: 사건 발생 장소는 어디인가요?...
```

### 문제 발생 시
```
🔄 VALIDATION → RE_QUESTION 전이 감지
📋 missing_fields: []  # ❌ 손실됨
▶️  RE_QUESTION 노드 실행 시작...
✅ RE_QUESTION 노드 실행 완료
💬 반환 bot_message: (없음)  # ❌ 메시지 없음
```

## 다음 단계

1. `--use-graph-step` 옵션으로 테스트 실행
2. 실제 웹과 동일한 문제가 재현되는지 확인
3. 로그를 통해 문제 지점 파악
4. 문제 해결 후 다시 테스트
