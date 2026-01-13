# A/B 테스트 가이드

## 개요

이 문서는 기존 엔티티 추출 방식과 새로운 Q-A 매칭 방식을 비교하기 위한 A/B 테스트 환경 구축 가이드입니다.

## 목적

- 기존 방식과 Q-A 매칭 방식의 성능 비교
- 사용자 경험 개선 정도 측정
- 오류율 및 성공률 비교
- 비용 효율성 분석

## 구조

### 1. A/B 테스트 관리자 (`ab_test_manager.py`)

세션별로 방식을 할당하고 통계를 추적합니다.

```python
from src.services.ab_test_manager import ab_test_manager

# 세션에 방식 할당
method = ab_test_manager.assign_method(session_id)

# 세션의 방식 확인
if ab_test_manager.is_qa_matching_method(session_id):
    # Q-A 매칭 방식 사용
    pass
else:
    # 기존 방식 사용
    pass
```

### 2. 방식 할당 전략

#### 랜덤 할당 (50:50)
```python
# settings.py 또는 환경 변수
AB_TEST_ENABLED = True
FACT_EXTRACTION_METHOD = "auto"  # auto는 랜덤 할당
```

#### 특정 방식 고정
```python
# 모든 세션에 Q-A 매칭 방식 사용
FACT_EXTRACTION_METHOD = "qa_matching"

# 모든 세션에 기존 방식 사용
FACT_EXTRACTION_METHOD = "legacy"
```

#### 세션 ID 기반 할당
```python
# 세션 ID의 해시값으로 할당 (일관성 유지)
import hashlib
hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
method = "qa_matching" if (hash_value % 2 == 0) else "legacy"
```

## 통합 방법

### 1. VALIDATION Node에서 방식 선택

```python
from src.services.ab_test_manager import ab_test_manager

def validation_node(state: StateContext) -> Dict[str, Any]:
    session_id = state.get("session_id")
    
    if ab_test_manager.is_qa_matching_method(session_id):
        # Q-A 매칭 방식
        facts = _extract_facts_from_conversation(
            state.get("conversation_history", []),
            state.get("case_type")
        )
    else:
        # 기존 방식
        facts = _extract_entities_legacy(state)
    
    # 통계 기록
    try:
        # ... 처리 로직 ...
        ab_test_manager.record_success(session_id)
    except Exception as e:
        ab_test_manager.record_error(session_id, str(e))
```

### 2. FACT_COLLECTION Node에서 방식 선택

```python
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    session_id = state.get("session_id")
    
    if ab_test_manager.is_qa_matching_method(session_id):
        # Q-A 매칭 방식: Q-A 쌍 저장
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "question": current_question,
            "field": expected_field,
            "answer": user_input,
            "timestamp": get_kst_now().isoformat()
        })
        state["conversation_history"] = conversation_history
    else:
        # 기존 방식: 엔티티 추출
        entities = extract_entities_parallel(user_input, expected_field)
        facts = _update_facts_from_entities(state["facts"], entities)
        state["facts"] = facts
```

## 통계 조회

### API 엔드포인트 추가 (선택적)

```python
@router.get("/ab-test/stats")
async def get_ab_test_stats(_: str = Depends(verify_api_key)):
    """A/B 테스트 통계 조회"""
    stats = ab_test_manager.get_stats()
    return success_response(stats)
```

### 통계 예시

```json
{
    "legacy": {
        "session_count": 100,
        "success_count": 85,
        "error_count": 15,
        "success_rate": 85.0,
        "error_rate": 15.0
    },
    "qa_matching": {
        "session_count": 100,
        "success_count": 95,
        "error_count": 5,
        "success_rate": 95.0,
        "error_rate": 5.0
    }
}
```

## 측정 지표

### 1. 성공률 (Success Rate)
- 세션 완료율
- 필수 필드 수집 완료율

### 2. 오류율 (Error Rate)
- GPT API 실패율
- JSON 파싱 오류율
- 예외 발생율

### 3. 사용자 경험
- 평균 질문 수
- 중복 질문 발생률
- 대화 완료 시간

### 4. 비용
- 세션당 평균 GPT API 호출 횟수
- 세션당 평균 비용
- 토큰 사용량

## 테스트 실행 방법

### 1. 환경 변수 설정

```bash
# .env 파일
AB_TEST_ENABLED=true
FACT_EXTRACTION_METHOD=auto  # auto는 랜덤 할당
```

### 2. 코드 통합

각 노드에서 `ab_test_manager`를 사용하여 방식을 선택합니다.

### 3. 통계 모니터링

정기적으로 통계를 조회하여 두 방식의 성능을 비교합니다.

## 주의사항

1. **일관성**: 세션 시작 시 방식이 할당되면 세션 종료까지 동일한 방식 사용
2. **로깅**: 각 방식의 사용 여부를 로그에 기록
3. **폴백**: 한 방식이 실패하면 다른 방식으로 폴백하지 않음 (순수 비교를 위해)
4. **데이터 수집**: 충분한 샘플 수 확보 (최소 100세션 이상 권장)

## 결과 분석

### 성공적인 전환 기준

- Q-A 매칭 방식의 성공률이 기존 방식보다 5% 이상 높음
- 오류율이 기존 방식보다 5% 이상 낮음
- 사용자 경험 지표가 개선됨
- 비용이 허용 범위 내

### 전환 결정

모든 지표가 개선되면 Q-A 매칭 방식을 기본 방식으로 설정:

```python
# settings.py
FACT_EXTRACTION_METHOD = "qa_matching"
AB_TEST_ENABLED = False
```

## 향후 개선

1. **자동 전환**: 통계 기반 자동 전환 로직
2. **세그먼트별 테스트**: 사용자 그룹별 다른 방식 할당
3. **실시간 모니터링**: 대시보드에서 실시간 통계 확인
4. **A/A 테스트**: 동일 방식으로 테스트하여 시스템 안정성 확인

