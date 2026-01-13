# Q-A 매칭 방식 전환 작업 TODO 리스트

## 개요
DESIGN_QA_MATCHING_APPROACH.md 설계안을 바탕으로 기존 엔티티 추출 방식에서 Q-A 매칭 방식으로 전환하는 작업 목록입니다.

---

## Phase 1: 핵심 함수 구현 (High Priority)

### ✅ TODO-01: 1차 서술 분석 함수 구현
- **함수**: `_analyze_initial_description()`
- **위치**: `src/langgraph/nodes/case_classification_node.py` 또는 새로운 유틸리티 파일
- **기능**: 
  - GPT로 초기 사용자 입력 분석
  - 포함된 정보 추출 (날짜, 금액, 당사자, 증거 등)
  - answered_fields와 missing_fields 반환
- **GPT 프롬프트**: JSON 형식 강제, temperature=0.1
- **테스트**: 다양한 형식의 날짜/금액 입력 테스트

### ✅ TODO-02: post_classification_analysis() 함수 구현
- **함수**: `post_classification_analysis()`
- **위치**: `src/langgraph/nodes/case_classification_node.py`
- **기능**:
  - RAG에서 필수 필드 목록 조회
  - `_analyze_initial_description()` 호출
  - State에 initial_description, initial_analysis, skipped_fields, conversation_history 저장
- **의존성**: TODO-01 완료 필요

### ✅ TODO-03: GPT 기반 Facts 추출 함수 구현
- **함수**: `_extract_facts_from_conversation()`
- **위치**: `src/langgraph/nodes/validation_node.py` 또는 공통 유틸리티
- **기능**:
  - conversation_history (Q-A 쌍)를 GPT에 전달
  - 구조화된 facts 딕셔너리 반환
  - 날짜/금액 형식 변환 처리
- **GPT 프롬프트**: JSON 형식 강제, temperature=0.1
- **테스트**: 다양한 Q-A 쌍 조합 테스트

---

## Phase 2: State 구조 변경 (High Priority)

### ✅ TODO-04: State Context 구조 변경
- **파일**: `src/langgraph/state.py`
- **변경 사항**:
  ```python
  class StateContext(TypedDict, total=False):
      # 기존 필드 유지
      ...
      # 새 필드 추가
      initial_description: str
      initial_analysis: Dict[str, Any]
      conversation_history: List[Dict[str, Any]]
      skipped_fields: List[str]
      current_question: Dict[str, Any]
  ```
- **검증**: StateContextModel (Pydantic)에도 반영

---

## Phase 3: 노드 수정 (High Priority)

### ✅ TODO-05: CASE_CLASSIFICATION Node 수정
- **파일**: `src/langgraph/nodes/case_classification_node.py`
- **변경 사항**:
  - 기존 사건 유형 분류 로직 유지
  - `post_classification_analysis()` 호출 추가
  - skipped_fields 로깅 추가
- **의존성**: TODO-02 완료 필요

### ✅ TODO-06: FACT_COLLECTION Node 수정
- **파일**: `src/langgraph/nodes/fact_collection_node.py`
- **변경 사항**:
  - 복잡한 엔티티 추출 로직 제거
  - Q-A 쌍 저장 방식으로 단순화
  - `_generate_next_question()` 호출하여 다음 질문 생성
- **제거할 로직**:
  - `_extract_entities_parallel()`
  - `_update_facts_from_entities()`
  - `_update_facts_from_evidence()`
  - `facts_before_update` 비교 로직
- **의존성**: TODO-07 완료 필요

### ✅ TODO-07: _generate_next_question() 함수 수정
- **파일**: `src/langgraph/nodes/fact_collection_node.py`
- **변경 사항**:
  - skipped_fields 반영하여 질문 필터링
  - asked_fields와 skipped_fields를 모두 제외
  - missing_fields 기반으로 다음 질문 선택
- **로직**: `excluded_fields = set(asked_fields) | set(skipped_fields)`

### ✅ TODO-08: VALIDATION Node 수정
- **파일**: `src/langgraph/nodes/validation_node.py`
- **변경 사항**:
  - `_extract_facts_from_conversation()` 호출하여 facts 추출
  - 1차 서술 분석 결과(initial_analysis) 병합
  - asked_fields는 conversation_history에서 추출
  - missing_fields는 asked_fields 제외하여 계산
- **의존성**: TODO-03 완료 필요

### ✅ TODO-09: RE_QUESTION Node 수정
- **파일**: `src/langgraph/nodes/re_question_node.py`
- **변경 사항**:
  - skipped_fields 반영
  - `_generate_next_question()` 사용 (통합)
  - 또는 skipped_fields 고려하여 질문 생성

---

## Phase 4: 기존 로직 제거 (Medium Priority)

### ✅ TODO-10: DB 저장 로직 확인 및 수정
- **파일**: `src/langgraph/nodes/fact_collection_node.py`의 `_save_facts_to_database()`
- **변경 사항**:
  - conversation_history를 DB에 저장할지 결정
  - 필요시 새로운 테이블 또는 기존 테이블에 필드 추가
- **참고**: 현재는 facts만 저장하므로 큰 변경 없을 수 있음

### ✅ TODO-11: 기존 엔티티 추출 함수들 제거 또는 비활성화
- **파일들**:
  - `src/utils/field_extractors.py`
  - `src/services/entity_extractor.py`
- **처리 방법**:
  - 완전 제거 전에 deprecation warning 추가
  - 단계적으로 비활성화
  - 최종 검증 후 제거
- **주의**: 다른 곳에서 사용 중이면 점진적 제거

---

## Phase 5: 테스트 및 검증 (High Priority)

### ✅ TODO-12: 단위 테스트 작성
- **테스트 파일**: `tests/test_qa_matching.py` (새로 생성)
- **테스트 항목**:
  - `_analyze_initial_description()` 테스트
    - 다양한 날짜 형식 ("25년 1월 2일", "2024-01-02", "어제")
    - 다양한 금액 형식 ("300만원", "3백만원", "3,000,000원")
    - 증거 언급 ("계약서 있음", "없음", "모름")
  - `_extract_facts_from_conversation()` 테스트
    - 여러 Q-A 쌍 조합
    - 누락된 정보 처리
  - `_generate_next_question()` 테스트
    - skipped_fields 필터링 확인
    - asked_fields 필터링 확인

### ✅ TODO-13: 통합 테스트 작성
- **테스트 파일**: `tests/test_integration_qa_flow.py` (새로 생성)
- **테스트 시나리오**:
  1. 1차 서술에 많은 정보 포함 → 질문 최소화
  2. 1차 서술에 일부 정보만 포함 → 필요한 질문만 진행
  3. 전체 대화 흐름: INIT → CASE_CLASSIFICATION → FACT_COLLECTION → VALIDATION → SUMMARY
  4. 중복 질문 방지 확인
  5. 에러 처리 및 폴백 확인

### ✅ TODO-14: 에러 처리 및 폴백 로직 추가
- **처리 항목**:
  - GPT API 실패 시 기존 방식으로 폴백
  - JSON 파싱 실패 처리
  - 타임아웃 처리
  - 부분 실패 시 부분 결과 활용
- **위치**: 각 GPT 호출 함수에 try-except 추가

---

## Phase 6: 모니터링 및 최적화 (Medium Priority)

### ✅ TODO-15: 로깅 개선
- **로깅 항목 추가**:
  - 1차 서술 분석 결과 (answered_fields, missing_fields)
  - skipped_fields 정보
  - conversation_history 변경사항
  - GPT API 호출 성공/실패
- **파일**: 각 노드의 로깅 코드 수정

### ✅ TODO-16: A/B 테스트 준비
- **작업 내용**:
  - 기존 방식과 Q-A 매칭 방식 동시 운영 가능하도록 플래그 추가
  - 설정 파일에 `USE_QA_MATCHING` 플래그 추가
  - 로그에서 어떤 방식 사용했는지 추적 가능하도록

### ✅ TODO-17: 성능 최적화
- **최적화 항목**:
  - GPT API 호출 배치 처리 (여러 요청 동시 처리)
  - 캐싱 전략 (1차 서술 분석 결과 캐싱)
  - 불필요한 API 호출 제거
- **모니터링**: API 호출 시간 측정

### ✅ TODO-18: 비용 모니터링
- **추적 항목**:
  - GPT API 호출 횟수
  - 사용된 토큰 수
  - 비용 계산
- **구현**: 로깅 또는 별도 모니터링 시스템

---

## Phase 7: 문서화 (Low Priority)

### ✅ TODO-19: 문서 업데이트
- **파일**: `docs/NODES_DETAILED_EXPLANATION.md`
- **변경 사항**:
  - FACT_COLLECTION Node 설명 업데이트
  - VALIDATION Node 설명 업데이트
  - Q-A 매칭 방식 설명 추가
  - 1차 서술 분석 설명 추가

### ✅ TODO-20: 프론트엔드 확인
- **파일**: `static/chat_gpt.html`
- **확인 사항**:
  - conversation_history 구조 변경 필요 여부
  - State 구조 변경에 따른 프론트엔드 수정 필요 여부
  - (현재는 영향 없을 것으로 예상, 확인만 필요)

---

## 작업 우선순위 요약

### 🔴 High Priority (필수)
1. TODO-01: 1차 서술 분석 함수 구현
2. TODO-02: post_classification_analysis() 함수 구현
3. TODO-03: GPT 기반 Facts 추출 함수 구현
4. TODO-04: State Context 구조 변경
5. TODO-05: CASE_CLASSIFICATION Node 수정
6. TODO-06: FACT_COLLECTION Node 수정
7. TODO-07: _generate_next_question() 함수 수정
8. TODO-08: VALIDATION Node 수정
9. TODO-12: 단위 테스트 작성
10. TODO-13: 통합 테스트 작성

### 🟡 Medium Priority (중요)
11. TODO-09: RE_QUESTION Node 수정
12. TODO-14: 에러 처리 및 폴백 로직 추가
13. TODO-15: 로깅 개선
14. TODO-16: A/B 테스트 준비

### 🟢 Low Priority (나중에)
15. TODO-10: DB 저장 로직 확인 및 수정
16. TODO-11: 기존 엔티티 추출 함수들 제거
17. TODO-17: 성능 최적화
18. TODO-18: 비용 모니터링
19. TODO-19: 문서 업데이트
20. TODO-20: 프론트엔드 확인

---

## 의존성 관계

```
TODO-01 (1차 서술 분석)
    ↓
TODO-02 (post_classification_analysis)
    ↓
TODO-04 (State 구조 변경) ← 병렬 진행 가능
    ↓
TODO-05 (CASE_CLASSIFICATION 수정)
    ↓
TODO-03 (Facts 추출 함수) ← 병렬 진행 가능
    ↓
TODO-07 (_generate_next_question) ← 병렬 진행 가능
    ↓
TODO-06 (FACT_COLLECTION 수정)
    ↓
TODO-08 (VALIDATION 수정)
    ↓
TODO-09 (RE_QUESTION 수정)
    ↓
TODO-12, TODO-13 (테스트)
```

---

## 예상 소요 시간

- **Phase 1 (핵심 함수 구현)**: 2-3일
- **Phase 2 (State 구조 변경)**: 0.5일
- **Phase 3 (노드 수정)**: 3-4일
- **Phase 4 (기존 로직 제거)**: 1-2일
- **Phase 5 (테스트)**: 2-3일
- **Phase 6 (모니터링)**: 1-2일
- **Phase 7 (문서화)**: 0.5-1일

**총 예상 시간**: 약 10-15일 (1명 기준)

---

## 체크리스트

### 개발 시작 전
- [ ] 설계안 검토 및 승인
- [ ] 개발 환경 준비
- [ ] GPT API 키 및 설정 확인

### 개발 중
- [ ] 각 TODO 완료 시 체크
- [ ] 코드 리뷰
- [ ] 단위 테스트 통과 확인
- [ ] 통합 테스트 통과 확인

### 배포 전
- [ ] 모든 High Priority TODO 완료
- [ ] 테스트 커버리지 확인
- [ ] 문서 업데이트 완료
- [ ] A/B 테스트 환경 준비

### 배포 후
- [ ] 모니터링 설정
- [ ] 비용 추적 시작
- [ ] 사용자 피드백 수집
- [ ] 성능 지표 분석

