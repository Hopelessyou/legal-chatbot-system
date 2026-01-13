# LangGraph 실행 흐름 분석 문서

## 개요

실제 작동에서 제대로 반응이 안 되는 문제를 해결하기 위해 실행 코드를 세분화하여 분석한 결과입니다.

**분석 일시**: 2026-01-09  
**분석 대상**: `src/langgraph/` 디렉토리 전체 실행 흐름

---

## 문서 목록

### 1. [execution_flow_analysis.md](./execution_flow_analysis.md)
**상세 분석 문서**

- API 엔드포인트에서 그래프 실행까지의 전체 흐름
- 각 노드별 실행 흐름 상세 분석
- 핵심 문제점 분석 (4가지 주요 문제)
- 실행 흐름 시나리오별 분석
- 해결 방안 및 수정 코드 예시
- 테스트 시나리오

**권장 읽기 순서**: 문제를 깊이 이해하고 싶을 때

---

### 2. [issue_summary.md](./issue_summary.md)
**문제 요약 문서**

- 발견된 주요 문제점 요약 (심각도별 분류)
- 실행 흐름 문제 시나리오
- 수정 권장 사항 (코드 예시 포함)
- 테스트 체크리스트

**권장 읽기 순서**: 빠르게 문제를 파악하고 수정하고 싶을 때

---

### 3. [execution_flow_diagram.md](./execution_flow_diagram.md)
**실행 흐름 다이어그램**

- 전체 실행 흐름 다이어그램
- 노드 실행 흐름 다이어그램
- 문제 발생 시나리오 시각화
- state 전이 다이어그램
- bot_message 전달 경로

**권장 읽기 순서**: 시각적으로 흐름을 이해하고 싶을 때

---

## 발견된 주요 문제점

### 🔴 심각도 높음 (즉시 수정 필요)

1. **CASE_CLASSIFICATION 노드에서 bot_message 미반환**
   - 파일: `src/langgraph/nodes/case_classification_node.py`
   - 영향: 첫 메시지 전송 후 응답이 빈 문자열로 반환될 수 있음

2. **INIT 노드에서 사용자 입력이 있을 때 bot_message 미반환**
   - 파일: `src/langgraph/nodes/init_node.py` (라인 169-178)
   - 영향: 첫 메시지 전송 후 즉시 응답이 없을 수 있음

### 🟡 심각도 중간 (모니터링 필요)

3. **VALIDATION → RE_QUESTION 연쇄 실행 시 bot_message 덮어쓰기 실패 가능성**
   - 파일: `src/langgraph/graph.py` (라인 270-337)
   - 영향: RE_QUESTION 노드 실행 후 응답이 기본 메시지로 대체될 수 있음

---

## 빠른 수정 가이드

### 1. CASE_CLASSIFICATION 노드 수정

**파일**: `src/langgraph/nodes/case_classification_node.py`

```python
return {
    **state,
    "case_type": case_type,
    "sub_case_type": sub_case_type,
    "bot_message": "사건 유형을 확인했습니다. 추가 정보를 수집하겠습니다.",  # 추가
    "next_state": "FACT_COLLECTION"
}
```

### 2. INIT 노드 수정

**파일**: `src/langgraph/nodes/init_node.py`

```python
if user_input and len(user_input) >= 2:
    return {
        **state,
        "current_state": "CASE_CLASSIFICATION",
        "next_state": "CASE_CLASSIFICATION",
        "bot_message": "처리 중입니다..."  # 추가
    }
```

### 3. graph.py 연쇄 실행 로직 개선 (선택사항)

**파일**: `src/langgraph/graph.py`

```python
if "bot_message" in next_result and next_result["bot_message"]:
    result["bot_message"] = next_result["bot_message"]
    logger.info(f"✅ bot_message 병합 완료")
else:
    logger.warning(f"⚠️  {next_state} 노드에서 bot_message가 없거나 비어있음!")
```

---

## 테스트 체크리스트

수정 후 다음 시나리오를 테스트하세요:

- [ ] 첫 메시지 전송 후 응답 메시지 확인 (빈 문자열이면 안 됨)
- [ ] CASE_CLASSIFICATION 노드 실행 후 응답 메시지 확인
- [ ] VALIDATION → RE_QUESTION 연쇄 실행 후 응답 메시지 확인
- [ ] RE_QUESTION → FACT_COLLECTION 루프에서 응답 메시지 확인

---

## 관련 파일

- `src/langgraph/graph.py`: 그래프 실행 로직
- `src/langgraph/nodes/init_node.py`: INIT 노드
- `src/langgraph/nodes/case_classification_node.py`: CASE_CLASSIFICATION 노드
- `src/langgraph/nodes/fact_collection_node.py`: FACT_COLLECTION 노드
- `src/langgraph/nodes/validation_node.py`: VALIDATION 노드
- `src/langgraph/nodes/re_question_node.py`: RE_QUESTION 노드
- `src/api/routers/chat.py`: API 엔드포인트
- `src/services/session_manager.py`: 세션 상태 관리

---

## 분석 방법론

1. **API 엔드포인트 분석**: `/chat/message` 엔드포인트에서 `run_graph_step` 호출까지의 흐름 확인
2. **그래프 실행 로직 분석**: `run_graph_step` 함수의 노드 실행 및 state 전이 로직 확인
3. **노드별 분석**: 각 노드의 실행 흐름, 반환값, `bot_message` 설정 여부 확인
4. **시나리오 분석**: 실제 사용 시나리오별로 실행 흐름 추적
5. **문제점 도출**: 각 시나리오에서 `bot_message`가 누락되거나 빈 문자열이 되는 지점 확인

---

## 수정 완료 ✅

**수정 일시**: 2026-01-09

모든 주요 문제점이 수정되었습니다:
- ✅ INIT 노드에서 사용자 입력이 있을 때 `bot_message` 추가
- ✅ CASE_CLASSIFICATION 노드에서 `bot_message` 보장 로직 추가
- ✅ graph.py 연쇄 실행 로직 개선

**수정 사항 상세**: [fixes_applied.md](./fixes_applied.md)

## 다음 단계

1. **테스트**: 수정 후 모든 시나리오 테스트
2. **모니터링**: 실제 운영 환경에서 모니터링
3. **문서화**: 수정 사항 커밋

---

## 문의

분석 과정에서 추가 질문이나 확인이 필요한 사항이 있으면 알려주세요.
