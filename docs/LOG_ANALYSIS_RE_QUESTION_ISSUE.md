# 로그 분석: RE_QUESTION "(메시지 없음)" 문제 원인 분석

## 분석 일시
2026-01-09

## 문제 요약
RE_QUESTION 상태에서 `bot_message`가 "(메시지 없음)"으로 반환되는 문제가 반복적으로 발생

## 로그 분석 결과

### 1. 문제 발생 패턴

#### 케이스 1: RE_QUESTION 노드가 실행되지 않는 경우 (10673-10677)
```
2026-01-06 03:21:00 [INFO] src.langgraph.nodes.validation_node: [sess_9ef090bc1440] VALIDATION 완료: 누락 필드 2개, 다음 State=RE_QUESTION
2026-01-06 03:21:00 [INFO] src.langgraph.graph: [sess_9ef090bc1440] State 전이: VALIDATION → RE_QUESTION
2026-01-06 03:21:00 [INFO] src.langgraph.graph: [sess_9ef090bc1440] State 변경: VALIDATION → RE_QUESTION
2026-01-06 03:21:00 [INFO] src.api.routers.chat: 메시지 처리 완료: new_state=RE_QUESTION, bot_message=(메시지 없음)
```

**문제점**:
- ✅ VALIDATION 노드는 정상 완료
- ✅ State 전이는 정상 (VALIDATION → RE_QUESTION)
- ❌ **RE_QUESTION 노드가 실행되지 않음** (RE_QUESTION Node 실행 로그 없음)
- ❌ bot_message가 "(메시지 없음)"으로 반환

#### 케이스 2: RE_QUESTION 노드가 실행되지만 missing_fields가 비어있는 경우 (10681-10682)
```
2026-01-06 03:21:16 [INFO] src.langgraph.graph: [sess_9ef090bc1440] Node 실행: RE_QUESTION
2026-01-06 03:21:16 [INFO] src.langgraph.nodes.re_question_node: [sess_9ef090bc1440] RE_QUESTION Node 실행: missing_fields=[], case_type=CIVIL, sub_case_type=대여금
```

**문제점**:
- ✅ RE_QUESTION 노드는 실행됨
- ❌ **missing_fields가 빈 리스트 `[]`**
- 이 경우 RE_QUESTION 노드는 SUMMARY로 전이하고 기본 메시지를 설정하지만, 이전 요청에서는 이미 "(메시지 없음)"이 반환됨

### 2. 정상 작동 패턴

#### 정상 케이스 (11164-11172)
```
2026-01-06 03:39:00 [INFO] src.langgraph.nodes.validation_node: [sess_7ef9072162e7] VALIDATION 완료: 누락 필드 2개, 다음 State=RE_QUESTION
2026-01-06 03:39:00 [INFO] src.langgraph.nodes.re_question_node: [sess_7ef9072162e7] RE_QUESTION Node 실행: missing_fields=['amount', 'evidence'], case_type=CIVIL, sub_case_type=대여금
2026-01-06 03:39:00 [INFO] src.langgraph.nodes.re_question_node: [sess_7ef9072162e7] 다음 질문 필드: amount (우선순위 기반, asked_fields: [])
2026-01-06 03:39:00 [INFO] src.langgraph.nodes.re_question_node: [sess_7ef9072162e7] RE_QUESTION 완료: 필드=amount, asked_fields=['amount']
2026-01-06 03:39:00 [INFO] src.langgraph.graph: [sess_7ef9072162e7] State 전이: VALIDATION → FACT_COLLECTION
2026-01-06 03:39:00 [INFO] src.api.routers.chat: 메시지 처리 완료: new_state=FACT_COLLECTION, bot_message=문제가 된 금액은 얼마인가요?...
```

**정상 동작**:
- ✅ VALIDATION 완료
- ✅ RE_QUESTION 노드 실행
- ✅ missing_fields가 정상적으로 전달됨
- ✅ bot_message 정상 생성
- ✅ State 전이: VALIDATION → FACT_COLLECTION (RE_QUESTION이 즉시 FACT_COLLECTION으로 전이)

## 근본 원인 분석

### 원인 1: graph.py의 체인 실행 로직 문제

`graph.py`의 `run_graph_step` 함수에서:
1. VALIDATION 노드 실행
2. VALIDATION → RE_QUESTION 전이 감지
3. **RE_QUESTION 노드를 즉시 실행해야 함**
4. 하지만 일부 경우에 RE_QUESTION 노드가 실행되지 않고 바로 응답 반환

**가능한 원인**:
- `next_node_func`가 `None`인 경우
- 예외가 발생했지만 처리되지 않은 경우
- State 전이 로직에서 RE_QUESTION 노드 실행이 누락된 경우

### 원인 2: missing_fields 전달 문제

VALIDATION 노드에서 RE_QUESTION으로 전이할 때:
- `missing_fields`가 state에 제대로 설정되어야 함
- 하지만 일부 경우에 `missing_fields`가 빈 리스트로 전달됨

**가능한 원인**:
- VALIDATION 노드에서 `missing_fields`를 설정하지 않은 경우
- State 병합 과정에서 `missing_fields`가 손실된 경우

### 원인 3: bot_message 병합 로직 문제

RE_QUESTION 노드 실행 후:
- `bot_message`가 `next_result`에 포함되어야 함
- `result`에 병합되어야 함
- 하지만 일부 경우에 병합이 누락됨

## 해결 방안

### 1. graph.py 수정 필요 사항

```python
# VALIDATION → RE_QUESTION 전이 시
if current_state == "VALIDATION" and next_state in ["RE_QUESTION", "SUMMARY"]:
    # RE_QUESTION 노드 실행
    next_node_func = NODES.get(next_state)
    if next_node_func:
        try:
            next_result = next_node_func(result)
            # bot_message 병합 확인
            if "bot_message" in next_result:
                result["bot_message"] = next_result["bot_message"]
            else:
                # bot_message가 없으면 경고 및 기본 메시지 설정
                logger.warning(f"⚠️  {next_state} 노드에서 bot_message가 반환되지 않았습니다!")
                result["bot_message"] = "추가 정보가 필요합니다."
        except Exception as e:
            logger.error(f"❌ {next_state} 노드 실행 중 오류: {e}")
            result["bot_message"] = "오류가 발생했습니다. 다시 시도해주세요."
    else:
        logger.error(f"❌ {next_state} 노드 함수를 찾을 수 없습니다!")
        result["bot_message"] = "시스템 오류가 발생했습니다."
```

### 2. RE_QUESTION 노드 수정 필요 사항

```python
# missing_fields가 비어있을 때 처리
if not missing_fields:
    logger.warning(f"[{session_id}] ⚠️  누락 필드가 없습니다.")
    # missing_fields를 state에서 다시 확인
    missing_fields = state.get("missing_fields", [])
    if not missing_fields:
        # VALIDATION 노드에서 설정하지 않았을 수 있음
        # required_fields에서 asked_fields를 제외하여 계산
        # ...
```

### 3. 로깅 강화

- RE_QUESTION 노드 실행 전/후 로그 추가
- bot_message 설정/병합 과정 로그 추가
- missing_fields 전달 과정 로그 추가

## 권장 조치 사항

1. **즉시 조치**: `graph.py`의 체인 실행 로직에 예외 처리 및 로깅 강화
2. **검증**: RE_QUESTION 노드 실행 여부를 로그로 확인
3. **테스트**: VALIDATION → RE_QUESTION 전이 시나리오 반복 테스트
4. **모니터링**: "(메시지 없음)" 발생 빈도 추적

## 참고 로그 위치

- 문제 케이스: `logs/app.log` 라인 10673-10677
- 정상 케이스: `logs/app.log` 라인 11164-11172
- 최근 세션: `logs/app.log` 라인 32817-32829 (sess_14ea07b33bef)
