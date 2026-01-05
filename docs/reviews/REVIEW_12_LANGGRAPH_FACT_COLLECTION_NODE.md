# LangGraph FACT_COLLECTION 노드 검토 보고서

## 검토 대상
- 파일: `src/langgraph/nodes/fact_collection_node.py`
- 검토 일자: 2024년
- 검토 범위: 사실 수집, 엔티티 추출, DB 저장, 완성도 계산

---

## ✅ 정상 동작 부분

### 1. 병렬 처리 (Lines 77-109)
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    entities_future = executor.submit(...)
    fact_emotion_future = executor.submit(...)
    rag_future = executor.submit(...)
    entities = entities_future.result()
    fact_emotion = fact_emotion_future.result()
    rag_results = rag_future.result()
```
- ✅ 엔티티 추출, 사실/감정 분리, RAG 검색을 병렬로 처리
- ✅ 성능 최적화

### 2. 조건부 엔티티 추출 (Lines 62-72)
```python
if expected_input and isinstance(expected_input, dict):
    expected_field = expected_input.get("field")
    entity_fields = FIELD_ENTITY_MAPPING.get(expected_field)
```
- ✅ expected_input에 따라 특정 필드만 추출
- ✅ 조건부 엔티티 추출

### 3. Facts 업데이트 로직 (Lines 115-310)
- ✅ expected_input에 따른 필드별 집중 추출
- ✅ 폴백 로직 (엔티티 추출 실패 시 사용자 입력에서 직접 추출)
- ✅ 증거 키워드 매칭

### 4. DB 저장 (Lines 317-400)
```python
with db_manager.get_db_session() as db_session:
    # CaseFact, CaseParty, CaseEmotion, CaseEvidence 저장
```
- ✅ 여러 모델 저장
- ✅ 기존 데이터 삭제 후 새로 추가 (CaseParty, CaseEvidence)

### 5. 완성도 계산 (Lines 402-404)
```python
completion_rate = _calculate_completion_rate(state, rag_results)
state["completion_rate"] = completion_rate
```
- ✅ 완성도 계산 및 상태 업데이트

### 6. 실행 시간 측정 (Line 38)
```python
@log_execution_time(logger)
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
```
- ✅ 데코레이터로 실행 시간 측정

---

## ⚠️ 발견된 문제점

### 1. 사용되지 않는 Import (Line 4)
```python
import asyncio
```
**영향도**: 낮음  
**문제**: `asyncio`를 import하지만 사용하지 않음  
**수정**: 제거

### 2. 중복된 DB 세션 열기 (Lines 318, 407)
**영향도**: 중간  
**문제**: 
- DB 세션을 두 번 열고 닫음
- 트랜잭션 분리로 인한 일관성 문제 가능

**현재 코드**:
```python
# 첫 번째 DB 세션 (Lines 318-400)
with db_manager.get_db_session() as db_session:
    # CaseFact, CaseParty, CaseEmotion, CaseEvidence 저장
    db_session.commit()

# 두 번째 DB 세션 (Lines 407-413)
with db_manager.get_db_session() as db_session:
    chat_session.completion_rate = completion_rate
    db_session.commit()
```

**권장 수정**:
```python
# 단일 DB 세션으로 통합
with db_manager.get_db_session() as db_session:
    # case_master 조회
    case = db_session.query(CaseMaster).filter(...).first()
    
    if case:
        # CaseFact, CaseParty, CaseEmotion, CaseEvidence 저장
        # ...
    
    # 세션 completion_rate 업데이트
    chat_session = db_session.query(ChatSession).filter(...).first()
    if chat_session:
        chat_session.completion_rate = completion_rate
    
    db_session.commit()
```

### 3. expected_input 변수 중복 할당 (Lines 64, 216, 270)
**영향도**: 낮음  
**문제**: 
- `expected_input`을 여러 번 재할당
- 불필요한 중복

**현재 코드**:
```python
expected_input = state.get("expected_input")  # Line 64
# ...
expected_input = state.get("expected_input")  # Line 216
# ...
expected_input = state.get("expected_input")  # Line 270
```

**수정**: 한 번만 할당하고 재사용

### 4. 날짜 파싱 에러 처리 없음 (Line 330)
**영향도**: 중간  
**문제**: 
- `datetime.strptime`에서 예외 발생 시 처리 없음
- 잘못된 날짜 형식으로 인한 애플리케이션 중단 가능

**현재 코드**:
```python
incident_date=datetime.strptime(facts["incident_date"], "%Y-%m-%d").date() if facts.get("incident_date") else None,
```

**권장 수정**:
```python
from src.utils.helpers import parse_date

incident_date = None
if facts.get("incident_date"):
    try:
        incident_date = parse_date(facts["incident_date"])
    except (ValueError, TypeError) as e:
        logger.warning(f"[{session_id}] 날짜 파싱 실패: {facts['incident_date']}, 오류: {str(e)}")
        incident_date = None
```

### 5. 병렬 처리에서 예외 처리 없음 (Lines 80-109)
**영향도**: 중간  
**문제**: 
- `executor.submit()`에서 발생한 예외가 `result()` 호출 시까지 전파됨
- 하나의 작업 실패 시 전체 실패

**권장 수정**:
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    entities_future = executor.submit(...)
    fact_emotion_future = executor.submit(...)
    rag_future = executor.submit(...)
    
    # 결과 대기 (예외 처리)
    entities = {}
    fact_emotion = {"facts": [], "emotions": []}
    rag_results = []
    
    try:
        entities = entities_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] 엔티티 추출 실패: {str(e)}")
    
    try:
        fact_emotion = fact_emotion_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] 사실/감정 분리 실패: {str(e)}")
    
    try:
        rag_results = rag_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] RAG 검색 실패: {str(e)}")
```

### 6. RAG 결과를 활용하지 않음 (Lines 415-416, 453-483)
**영향도**: 중간  
**문제**: 
- `_generate_next_question`에서 `rag_results`를 받지만 사용하지 않음
- RAG K2 질문 템플릿을 활용하지 않음

**현재 코드**:
```python
def _generate_next_question(state: StateContext, rag_results: list) -> Dict[str, Any]:
    # rag_results를 사용하지 않음
    if not facts.get("incident_date"):
        return {
            "message": get_question_message("incident_date", case_type),
            ...
        }
```

**권장 수정**:
```python
def _generate_next_question(state: StateContext, rag_results: list) -> Dict[str, Any]:
    """다음 질문 생성 (RAG K2 질문 템플릿 활용)"""
    facts = state.get("facts", {})
    case_type = state.get("case_type")
    
    # RAG 결과에서 질문 템플릿 추출 시도
    if rag_results:
        best_match = rag_results[0]
        metadata = best_match.get("metadata", {})
        question_templates = metadata.get("question_templates", {})
        
        # 누락 필드에 대한 질문 템플릿 사용
        if not facts.get("incident_date") and "incident_date" in question_templates:
            return {
                "message": question_templates["incident_date"],
                "expected_input": {"type": "date", "field": "incident_date"}
            }
        # ... 다른 필드들도 동일하게 처리
    
    # RAG 결과가 없으면 기본 질문 사용
    if not facts.get("incident_date"):
        return {
            "message": get_question_message("incident_date", case_type),
            "expected_input": {"type": "date", "field": "incident_date"}
        }
    # ...
```

### 7. 코드 중복 (날짜/금액/당사자 추출 로직)
**영향도**: 중간  
**문제**: 
- expected_input이 있을 때와 없을 때 유사한 로직이 중복됨
- 유지보수 어려움

**현재 코드**:
- Lines 119-132: expected_input이 "incident_date"일 때 날짜 추출
- Lines 171-182: expected_input이 없을 때 날짜 추출
- 유사한 패턴이 금액, 당사자에도 반복

**권장 수정**: 공통 함수로 추출
```python
def _extract_field_value(
    field_name: str,
    entities: Dict[str, Any],
    user_input: str,
    entity_extractor
) -> Optional[Any]:
    """필드 값 추출 (공통 로직)"""
    if field_name == "incident_date":
        extracted_date = entities.get("date")
        if extracted_date:
            return extracted_date
        return entity_extractor.extract_date(user_input)
    
    elif field_name == "amount":
        if entities.get("amount"):
            return entities["amount"]
        # 사용자 입력에서 숫자 추출
        import re
        numbers = re.findall(r'\d+', user_input.replace(',', '').replace('만', '0000').replace('천', '000'))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                return None
        return None
    
    elif field_name == "counterparty":
        if entities.get("party"):
            party = entities["party"]
            party_name = party.get("name") or party.get("type")
            if party_name and party_name not in ["없음", "None", ""]:
                return party_name
        if user_input and user_input.strip() and user_input not in ["없음", "None", ""]:
            return user_input.strip()
        return None
    
    return None
```

### 8. 에러 발생 시 raise만 함 (Lines 428-430)
**영향도**: 중간  
**문제**: 
- 예외 발생 시 raise만 하고 사용자에게 친화적인 응답 없음
- 애플리케이션 중단 가능

**현재 코드**:
```python
except Exception as e:
    logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}")
    raise
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리: 기존 facts 유지하고 다음 질문 생성
    facts = state.get("facts", {})
    next_question = _generate_next_question(state, [])
    
    return {
        **state,
        "bot_message": next_question.get("message", "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."),
        "expected_input": next_question.get("expected_input"),
        "next_state": "VALIDATION"
    }
```

### 9. emotion 리스트 초기화 확인 없음 (Line 315)
**영향도**: 낮음  
**문제**: 
- `state["emotion"]`이 리스트가 아닐 수 있음
- `extend()` 호출 시 에러 가능

**현재 코드**:
```python
state["emotion"].extend(emotions)
```

**권장 수정**:
```python
if "emotion" not in state or not isinstance(state.get("emotion"), list):
    state["emotion"] = []
state["emotion"].extend(emotions)
```

### 10. 완성도 계산에서 RAG 결과 미활용 (Lines 433-450)
**영향도**: 낮음  
**문제**: 
- `_calculate_completion_rate`에서 `rag_results`를 받지만 사용하지 않음
- 주석에 "RAG 결과에서 필수 필드 목록 추출"이라고 되어 있지만 실제로는 `REQUIRED_FIELDS` 사용

**현재 코드**:
```python
def _calculate_completion_rate(state: StateContext, rag_results: list) -> int:
    if not rag_results:
        return 0
    
    # RAG 결과에서 필수 필드 목록 추출
    # 실제로는 RAG 결과를 파싱하여 필수 필드 추출
    # 현재는 기본 필수 필드 사용
    required_fields = REQUIRED_FIELDS
```

**권장 수정**:
```python
def _calculate_completion_rate(state: StateContext, rag_results: list) -> int:
    """완성도 계산 (RAG 결과 활용)"""
    facts = state.get("facts", {})
    
    # RAG 결과에서 필수 필드 목록 추출 시도
    required_fields = REQUIRED_FIELDS  # 기본값
    
    if rag_results:
        best_match = rag_results[0]
        metadata = best_match.get("metadata", {})
        rag_required_fields = metadata.get("required_fields")
        
        if rag_required_fields and isinstance(rag_required_fields, list):
            required_fields = rag_required_fields
            logger.debug(f"RAG 결과에서 필수 필드 추출: {required_fields}")
    
    if not required_fields:
        return 0
    
    filled_count = sum(1 for field in required_fields if facts.get(field) is not None)
    completion_rate = int((filled_count / len(required_fields)) * 100)
    return min(completion_rate, 100)
```

### 11. import 위치 (Line 78)
**영역도**: 낮음  
**문제**: 
- `concurrent.futures`를 함수 내부에서 import
- 파일 상단에서 import하는 것이 일반적

**수정**: 파일 상단으로 이동

### 12. 증거 타입 추출 로직 중복 (Lines 244-253, 280-291)
**영역도**: 낮음  
**문제**: 
- 증거 타입 추출 로직이 두 곳에 중복

**권장 수정**: 공통 함수로 추출

---

## 🔍 추가 검토 사항

### 1. 병렬 처리 타임아웃
- 현재: 타임아웃 없음
- 권장: 각 작업에 타임아웃 설정

### 2. DB 트랜잭션 롤백
- 현재: 예외 발생 시 롤백 처리 없음
- 권장: try-except로 롤백 처리

### 3. Facts 검증
- 현재: Facts 값 검증 없음
- 권장: 값 형식 및 범위 검증

### 4. RAG 결과 활용
- 현재: RAG 결과를 거의 활용하지 않음
- 권장: RAG 결과를 질문 생성 및 완성도 계산에 활용

---

## 📊 종합 평가

### 강점
1. ✅ 병렬 처리로 성능 최적화
2. ✅ 조건부 엔티티 추출
3. ✅ 폴백 로직 구현
4. ✅ 여러 DB 모델 저장
5. ✅ 완성도 계산

### 개선 필요
1. 🟡 **중간**: 중복된 DB 세션 통합
2. 🟡 **중간**: 날짜 파싱 에러 처리
3. 🟡 **중간**: 병렬 처리 예외 처리
4. 🟡 **중간**: RAG 결과 활용
5. 🟡 **중간**: 코드 중복 제거
6. 🟡 **중간**: 에러 처리 개선
7. 🟢 **낮음**: 사용되지 않는 import 제거
8. 🟢 **낮음**: 변수 중복 할당 제거
9. 🟢 **낮음**: emotion 리스트 초기화 확인

### 우선순위
- **중간**: DB 세션 통합, 날짜 파싱 에러 처리, 병렬 처리 예외 처리, RAG 결과 활용, 코드 중복 제거
- **낮음**: import 정리, 변수 정리

---

## 📝 권장 수정 사항

### 수정 1: Import 정리 및 병렬 처리 개선
```python
"""
FACT_COLLECTION Node 구현 (핵심)
"""
import concurrent.futures
from typing import Dict, Any, List, Optional
from src.langgraph.state import StateContext
# ... 나머지 imports ...
```

### 수정 2: DB 세션 통합
```python
# 단일 DB 세션으로 통합
with db_manager.get_db_session() as db_session:
    try:
        case = db_session.query(CaseMaster).filter(...).first()
        
        if case:
            # CaseFact, CaseParty, CaseEmotion, CaseEvidence 저장
            # ...
        
        # 세션 completion_rate 업데이트
        chat_session = db_session.query(ChatSession).filter(...).first()
        if chat_session:
            chat_session.completion_rate = completion_rate
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"[{session_id}] DB 저장 실패: {str(e)}")
        raise
```

### 수정 3: 날짜 파싱 에러 처리
```python
from src.utils.helpers import parse_date

incident_date = None
if facts.get("incident_date"):
    try:
        incident_date = parse_date(facts["incident_date"])
    except (ValueError, TypeError) as e:
        logger.warning(f"[{session_id}] 날짜 파싱 실패: {facts['incident_date']}, 오류: {str(e)}")
        incident_date = None
```

### 수정 4: 병렬 처리 예외 처리
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    entities_future = executor.submit(...)
    fact_emotion_future = executor.submit(...)
    rag_future = executor.submit(...)
    
    entities = {}
    fact_emotion = {"facts": [], "emotions": []}
    rag_results = []
    
    try:
        entities = entities_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] 엔티티 추출 실패: {str(e)}")
    
    try:
        fact_emotion = fact_emotion_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] 사실/감정 분리 실패: {str(e)}")
    
    try:
        rag_results = rag_future.result(timeout=30)
    except Exception as e:
        logger.error(f"[{session_id}] RAG 검색 실패: {str(e)}")
```

### 수정 5: RAG 결과 활용
```python
def _generate_next_question(state: StateContext, rag_results: list) -> Dict[str, Any]:
    """다음 질문 생성 (RAG K2 질문 템플릿 활용)"""
    facts = state.get("facts", {})
    case_type = state.get("case_type")
    
    # RAG 결과에서 질문 템플릿 추출 시도
    if rag_results:
        best_match = rag_results[0]
        metadata = best_match.get("metadata", {})
        question_templates = metadata.get("question_templates", {})
        
        # 누락 필드에 대한 질문 템플릿 사용
        if not facts.get("incident_date") and "incident_date" in question_templates:
            return {
                "message": question_templates["incident_date"],
                "expected_input": {"type": "date", "field": "incident_date"}
            }
        # ... 다른 필드들도 동일하게 처리
    
    # RAG 결과가 없으면 기본 질문 사용
    # ... 기존 로직 ...
```

### 수정 6: 에러 처리 개선
```python
except Exception as e:
    logger.error(f"FACT_COLLECTION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리
    facts = state.get("facts", {})
    next_question = _generate_next_question(state, [])
    
    return {
        **state,
        "bot_message": next_question.get("message", "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."),
        "expected_input": next_question.get("expected_input"),
        "next_state": "VALIDATION"
    }
```

---

## ✅ 검토 완료

**검토 항목**: `review_12_langgraph_fact_collection_node`  
**상태**: 완료  
**다음 항목**: `review_13_langgraph_validation_node`

