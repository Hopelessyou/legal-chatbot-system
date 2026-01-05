# Utils Constants 검토 보고서

## 검토 대상
- 파일: `src/utils/constants.py`
- 검토 일자: 2024년
- 검토 범위: 시스템 상수, 매핑, 제한값

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-7)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 모두 포함 (`Enum`, `Dict`, `List`)
- ✅ 섹션별로 잘 구분된 구조

### 2. 사건 유형 매핑 (Lines 9-26)
- ✅ `CASE_TYPE_MAPPING`: 한글 → 영문 매핑
- ✅ `CASE_TYPE_REVERSE_MAPPING`: 영문 → 한글 매핑
- ✅ 일관된 매핑 구조

### 3. 필수 필드 목록 (Lines 29-47)
- ✅ `REQUIRED_FIELDS`: 기본 필수 필드
- ✅ `REQUIRED_FIELDS_BY_CASE_TYPE`: 사건 유형별 필수 필드
- ✅ 확장 가능한 구조

### 4. 증거 관련 상수 (Lines 50-94)
- ✅ `EVIDENCE_TYPE_KEYWORDS`: 증거 타입 키워드 매핑
- ✅ `EVIDENCE_KEYWORDS_POSITIVE`: 긍정 키워드
- ✅ `EVIDENCE_KEYWORDS_NEGATIVE`: 부정 키워드
- ✅ `EVIDENCE_SIMPLE_POSITIVE_KEYWORDS`: 단순 긍정 키워드
- ✅ `EVIDENCE_EXPLICIT_KEYWORDS`: 명시적 증거 키워드

### 5. Enum 클래스 (Lines 118-134)
- ✅ `SessionStatus`: 세션 상태 Enum
- ✅ `CaseStage`: 사건 단계 Enum
- ✅ `str, Enum` 상속으로 문자열과 호환

### 6. 제한값 클래스 (Lines 216-241)
- ✅ `Limits` 클래스: 모든 제한값을 한 곳에 모음
- ✅ 명확한 카테고리 구분 (문자열 길이, 금액, GPT API 토큰, 완성도, 기타)

### 7. 한글 숫자 매핑 (Lines 248-253)
- ✅ `KOREAN_NUMBER_MAPPING`: 한글 숫자를 아라비아 숫자로 변환

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: `CaseStage` Enum 불완전

**문제**: `CaseStage` Enum에 `"수임"`과 `"거절"` 단계가 없습니다. `CaseMaster` 모델의 `CheckConstraint`에는 이 값들이 포함되어 있습니다.

**영향도**: 낮음  
**수정 권장**: 누락된 단계 추가

**수정 예시**:
```python
class CaseStage(str, Enum):
    """사건 단계 Enum"""
    BEFORE_CONSULTATION = "상담전"
    IN_CONSULTATION = "상담중"
    CONSULTATION_COMPLETED = "상담완료"
    ACCEPTED = "수임"
    REJECTED = "거절"
```

---

### 2. 🟢 **낮음**: Deprecated 상수에 대한 명확한 경고 부족

**문제**: `FIELD_PRIORITY_ORDER`와 `FIELD_PRIORITY_BY_CASE_TYPE`에 주석으로 "deprecated"라고 표시되어 있지만, 실제로 사용 중인지 확인이 필요합니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는다면 제거, 사용 중이라면 `warnings` 모듈 사용 (선택적)

**참고**: 현재는 주석으로 충분히 표시되어 있으므로 큰 문제는 아닙니다.

---

### 3. 🟢 **낮음**: 타입 힌팅 일관성

**문제**: 대부분의 상수에 타입 힌팅이 있지만, 일부는 없습니다. 예를 들어 `DEFAULT_CASE_TYPE`과 `DEFAULT_SUB_CASE_TYPE`에는 타입 힌팅이 없습니다.

**영향도**: 낮음  
**수정 권장**: 모든 상수에 타입 힌팅 추가 (선택적)

**참고**: 현재는 대부분의 상수에 타입 힌팅이 있어서 큰 문제는 아닙니다.

---

### 4. 🟢 **낮음**: 상수 검증 로직 부재

**문제**: 상수 값들이 런타임에 검증되지 않습니다. 예를 들어 `REQUIRED_FIELDS_BY_CASE_TYPE`에 잘못된 사건 유형이 포함될 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (런타임 검증은 오버헤드가 있을 수 있음)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 4개 (CaseStage Enum 불완전, Deprecated 상수 경고, 타입 힌팅 일관성, 상수 검증 로직 부재)

### 우선순위별 수정 권장
1. 🟢 **낮음**: `CaseStage` Enum에 누락된 단계 추가
2. 🟢 **낮음**: 타입 힌팅 일관성 개선 (선택적)
3. 🟢 **낮음**: Deprecated 상수 처리 (선택적)
4. 🟢 **낮음**: 상수 검증 로직 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: CaseStage Enum에 누락된 단계 추가

```python
class CaseStage(str, Enum):
    """사건 단계 Enum"""
    BEFORE_CONSULTATION = "상담전"
    IN_CONSULTATION = "상담중"
    CONSULTATION_COMPLETED = "상담완료"
    ACCEPTED = "수임"
    REJECTED = "거절"
```

---

## ✅ 결론

`utils/constants.py` 모듈은 전반적으로 매우 잘 구현되어 있습니다. 하드코딩 개선 작업이 완료되어 모든 상수가 한 곳에 잘 정리되어 있습니다. **`CaseStage` Enum에 누락된 단계 추가**를 권장합니다.

**우선순위**:
1. 🟢 **낮음**: `CaseStage` Enum에 누락된 단계 추가
2. 🟢 **낮음**: 타입 힌팅 일관성 개선 (선택적)
3. 🟢 **낮음**: Deprecated 상수 처리 (선택적)
4. 🟢 **낮음**: 상수 검증 로직 추가 (선택적)

