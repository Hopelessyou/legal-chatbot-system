# 하드코딩 개선 작업 완료 요약

## 📋 개요

프로젝트 내 하드코딩된 값들을 상수 파일로 통합하여 유지보수성을 크게 향상시켰습니다.

---

## ✅ 완료된 작업

### 1. 상수 파일 생성
- **`src/utils/constants.py`**: 모든 하드코딩된 상수 통합 관리
- **`src/db/constants.py`**: DB 필드 길이 상수 정의

### 2. 주요 개선 사항

#### ✅ 높은 우선순위 (완료)
1. **증거 타입 키워드 매핑 통합** (3곳 중복 제거)
   - `fact_collection_node.py`의 3곳에 중복 정의된 `evidence_type_keywords` 통합
   - `src/utils/constants.py`의 `EVIDENCE_TYPE_KEYWORDS`로 통합

2. **필수 필드 목록 상수화** (4곳 중복 제거)
   - `missing_field_manager.py`, `completion_calculator.py`, `validation_node.py`, `fact_collection_node.py`에서 중복 제거
   - `REQUIRED_FIELDS` 및 `REQUIRED_FIELDS_BY_CASE_TYPE`로 통합

3. **사건 유형 매핑 통합** (3곳 중복 제거)
   - `case_classification_node.py`, `fact_collection_node.py`, `summary_node.py`에서 통합
   - `CASE_TYPE_MAPPING`으로 통합

4. **증거 키워드 리스트 상수화** (2곳 중복 제거)
   - `fact_collection_node.py`와 `validation_node.py`에서 통합
   - `EVIDENCE_KEYWORDS_POSITIVE`, `EVIDENCE_KEYWORDS_NEGATIVE`, `EVIDENCE_SIMPLE_POSITIVE_KEYWORDS`로 통합

5. **매직 넘버 상수화**
   - 문자열 길이: `Limits.LOG_PREVIEW_LENGTH`, `Limits.DESCRIPTION_MAX_LENGTH` 등
   - 금액 임계값: `Limits.MIN_AMOUNT_THRESHOLD` (1000원)
   - GPT API 토큰 제한: `Limits.MAX_TOKENS_*` 시리즈

#### ✅ 추가 완료 항목
6. **필드-엔티티 매핑 상수화**
   - `FIELD_ENTITY_MAPPING`으로 통합

7. **입력 타입 매핑 상수화**
   - `FIELD_INPUT_TYPE_MAPPING`으로 통합

8. **한글 숫자 매핑 모듈화**
   - `KOREAN_NUMBER_MAPPING`으로 통합

9. **당사자 타입 검증 로직 통합**
   - `VALID_PARTY_TYPES`, `DEFAULT_PARTY_TYPE`, `PARTY_ROLES`로 통합

10. **세션 상태 Enum 생성**
    - `SessionStatus` Enum 클래스 생성 (ACTIVE, COMPLETED, ABORTED)
    - 모든 세션 상태 관련 코드에서 Enum 사용

11. **사건 단계 상수화**
    - `CaseStage` Enum 클래스 생성

12. **DB 필드 길이 상수화**
    - `src/db/constants.py`의 `FieldLength` 클래스 생성

---

## 📝 수정된 파일 목록

### 핵심 파일
- `src/utils/constants.py` (신규 생성)
- `src/db/constants.py` (신규 생성)

### LangGraph 노드
- `src/langgraph/nodes/case_classification_node.py`
- `src/langgraph/nodes/fact_collection_node.py`
- `src/langgraph/nodes/validation_node.py`
- `src/langgraph/nodes/re_question_node.py`
- `src/langgraph/nodes/summary_node.py`
- `src/langgraph/nodes/init_node.py`
- `src/langgraph/nodes/completed_node.py`

### 서비스 레이어
- `src/services/missing_field_manager.py`
- `src/services/completion_calculator.py`
- `src/services/entity_extractor.py`
- `src/services/session_manager.py`

### API 레이어
- `src/api/routers/chat.py`

---

## 🎯 개선 효과

### 1. 중복 제거
- **증거 타입 키워드**: 3곳 → 1곳
- **필수 필드 목록**: 4곳 → 1곳
- **사건 유형 매핑**: 3곳 → 1곳
- **증거 키워드**: 2곳 → 1곳

### 2. 유지보수성 향상
- 모든 상수를 한 곳에서 관리
- 변경 시 한 곳만 수정하면 됨
- 타입 안정성 확보 (Enum 사용)

### 3. 확장성 향상
- 사건 유형별 필수 필드 지원 준비
- 사건 유형별 우선순위 지원 준비
- 새로운 상수 추가가 용이

---

## 📊 통계

- **생성된 파일**: 2개
- **수정된 파일**: 13개
- **제거된 중복 코드**: 약 200줄 이상
- **통합된 상수**: 20개 이상

---

## 🔄 남은 작업 (낮은 우선순위)

다음 항목들은 향후 개선 가능:

1. **질문 텍스트 외부화**
   - RAG K2 문서에서 동적으로 로드하거나 YAML 파일로 관리

2. **폴백 키워드 설정 파일화**
   - `config/fallback_keywords.py`로 분리

3. **우선순위 순서 설정 파일화**
   - `config/priority.py`로 분리하고 사건 유형별 우선순위 완전 지원

---

## 💡 사용 예시

### Before (하드코딩)
```python
evidence_type_keywords = {
    "계약서": "계약서",
    "카톡": "대화내역",
    # ...
}
```

### After (상수 사용)
```python
from src.utils.constants import EVIDENCE_TYPE_KEYWORDS

evidence_type = EVIDENCE_TYPE_KEYWORDS.get("카톡")
```

### Before (하드코딩)
```python
status = "ACTIVE"
if status == "COMPLETED":
    # ...
```

### After (Enum 사용)
```python
from src.utils.constants import SessionStatus

status = SessionStatus.ACTIVE.value
if status == SessionStatus.COMPLETED.value:
    # ...
```

---

**작성 일시**: 2025-12-30  
**작업 완료율**: 12/15 (80%)

