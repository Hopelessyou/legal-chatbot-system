# 하드코딩된 부분 체크리스트

## 📋 개요

이 문서는 프로젝트 내 하드코딩된 값들을 정리하고, 개선 방안을 제시합니다.

---

## 🔴 1. 사건 유형 매핑 (Case Type Mapping)

### 위치
- `src/langgraph/nodes/case_classification_node.py` (122-127줄)
- `src/langgraph/nodes/fact_collection_node.py` (67-71줄)
- `src/langgraph/nodes/summary_node.py` (75-78줄)

### 하드코딩 내용
```python
case_type_mapping = {
    "민사": "CIVIL",
    "형사": "CRIMINAL",
    "가사": "FAMILY",
    "행정": "ADMIN"
}
```

### 문제점
- 여러 파일에 중복 정의
- 새로운 사건 유형 추가 시 여러 곳 수정 필요
- 한글/영문 변환 로직이 분산

### 개선 방안
```python
# src/utils/constants.py 또는 config/case_types.py
CASE_TYPE_MAPPING = {
    "민사": "CIVIL",
    "형사": "CRIMINAL",
    "가사": "FAMILY",
    "행정": "ADMIN"
}
```

---

## 🔴 2. 필수 필드 목록 (Required Fields)

### 위치
- `src/services/missing_field_manager.py` (38줄)
- `src/services/completion_calculator.py` (39줄)
- `src/langgraph/nodes/fact_collection_node.py` (498줄)
- `src/langgraph/nodes/validation_node.py` (188줄)

### 하드코딩 내용
```python
required_fields = ["incident_date", "counterparty", "amount", "evidence"]
```

### 문제점
- 여러 파일에 중복 정의
- 사건 유형별로 필수 필드가 다를 수 있음 (현재는 모든 유형 동일)
- RAG K2 문서에서 동적으로 가져와야 하는데 하드코딩됨

### 개선 방안
```python
# RAG K2 문서에서 동적으로 로드하거나
# config/required_fields.py에 사건 유형별로 정의
REQUIRED_FIELDS_BY_CASE_TYPE = {
    "CIVIL": ["incident_date", "counterparty", "amount", "evidence"],
    "CRIMINAL": ["incident_date", "counterparty", "amount", "evidence"],
    # ...
}
```

---

## 🔴 3. 증거 타입 키워드 매핑 (Evidence Type Keywords)

### 위치
- `src/langgraph/nodes/fact_collection_node.py` (247-261줄, 302-316줄, 422-435줄)
- `src/langgraph/nodes/validation_node.py` (94줄)

### 하드코딩 내용
```python
evidence_type_keywords = {
    "계약서": "계약서",
    "카톡": "대화내역",
    "대화": "대화내역",
    "대화내역": "대화내역",
    "이체": "이체내역",
    "송금": "이체내역",
    "송금내역": "이체내역",
    "계좌이체": "이체내역",
    "사진": "사진",
    "영상": "영상",
    "녹음": "녹음",
    "문서": "문서",
    "증빙": "증빙",
    "자료": "기타"
}
```

### 문제점
- **3곳에 중복 정의** (fact_collection_node.py에만 3번)
- 새로운 증거 타입 추가 시 여러 곳 수정 필요
- 키워드 매핑 로직이 분산

### 개선 방안
```python
# src/utils/constants.py
EVIDENCE_TYPE_KEYWORDS = {
    "계약서": "계약서",
    "카톡": "대화내역",
    # ...
}

EVIDENCE_KEYWORDS_POSITIVE = [
    "증거", "계약서", "카톡", "이체", "내역", "대화", "송금", ...
]

EVIDENCE_KEYWORDS_NEGATIVE = [
    "없음", "없어", "아니", "no", "없다", "없습니다", "증거 없"
]
```

---

## 🔴 4. 증거 키워드 리스트 (Evidence Keywords)

### 위치
- `src/langgraph/nodes/fact_collection_node.py` (225-229줄)
- `src/langgraph/nodes/validation_node.py` (90, 94, 107줄)

### 하드코딩 내용
```python
evidence_keywords_positive = [
    "증거", "계약서", "카톡", "이체", "내역", "대화", "송금", 
    "대화내역", "송금내역", "계좌이체", "문서", "사진", "영상", 
    "녹음", "증빙", "자료"
]

evidence_keywords_negative = [
    "없음", "없어", "아니", "no", "없다", "없습니다", "증거 없"
]

simple_positive_keywords = ["네", "있어", "있어요", "예", "그래", "yes"]
```

### 문제점
- 여러 파일에 중복 정의
- 키워드 추가/수정 시 여러 곳 수정 필요

### 개선 방안
```python
# src/utils/constants.py 또는 config/keywords.py
EVIDENCE_KEYWORDS = {
    "positive": [...],
    "negative": [...],
    "simple_positive": [...]
}
```

---

## 🔴 5. 당사자 타입 (Party Type)

### 위치
- `src/langgraph/nodes/fact_collection_node.py` (195-203줄, 384-388줄)
- `src/langgraph/nodes/validation_node.py` (144-146줄)
- `src/db/models/case_party.py` (15줄 - CheckConstraint)

### 하드코딩 내용
```python
if party_type not in ["개인", "법인"]:
    party_type = "개인"  # 기본값
```

### 문제점
- 당사자 타입 검증 로직이 여러 곳에 분산
- DB 제약조건과 코드 로직이 중복

### 개선 방안
```python
# src/utils/constants.py
VALID_PARTY_TYPES = ["개인", "법인"]
DEFAULT_PARTY_TYPE = "개인"
```

---

## 🔴 6. 세션 상태 (Session Status)

### 위치
- `src/services/session_manager.py` (46줄)
- `src/langgraph/nodes/init_node.py` (140줄)
- `src/langgraph/nodes/completed_node.py` (37줄)
- `src/db/models/chat_session.py` (14줄 - CheckConstraint)

### 하드코딩 내용
```python
status="ACTIVE"
status="COMPLETED"
status="ABORTED"
```

### 문제점
- 상태 문자열이 여러 곳에 하드코딩
- 오타 위험

### 개선 방안
```python
# src/utils/constants.py 또는 enum 사용
class SessionStatus:
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
```

---

## 🔴 7. 매직 넘버 (Magic Numbers)

### 위치 및 값

#### 문자열 길이 제한
- `user_input[:50]` - 여러 파일 (로그 출력용)
- `user_input[:500]` - fact_collection_node.py (371줄)
- `user_input[:255]` - fact_collection_node.py (449줄)
- `user_input.strip()[:50]` - fact_collection_node.py (333줄)
- `summary_text[:200]` - summary_node.py (137줄)

#### 금액 관련
- `amount >= 1000` - validation_node.py (82줄), fact_collection_node.py
  - 1000원 이상만 금액으로 간주

#### GPT API 토큰 제한
- `max_tokens=50` - entity_extractor.py (102, 186줄)
- `max_tokens=100` - case_classification_node.py (86줄)
- `max_tokens=200` - entity_extractor.py (231, 288줄), keyword_extractor.py (39줄)
- `max_tokens=500` - summarizer.py (323줄), fact_emotion_splitter.py (58줄)

#### 기타
- `completion_rate` 범위: 0~100 (여러 파일)
- `order=999` - init_node.py (55줄, 기본값)

### 문제점
- 의미가 불명확한 숫자
- 변경 시 여러 곳 수정 필요
- 문서화 부족

### 개선 방안
```python
# src/utils/constants.py
class Limits:
    # 문자열 길이
    LOG_PREVIEW_LENGTH = 50
    DESCRIPTION_MAX_LENGTH = 500
    EVIDENCE_TYPE_MAX_LENGTH = 50
    SUMMARY_PREVIEW_LENGTH = 200
    
    # 금액
    MIN_AMOUNT_THRESHOLD = 1000  # 원
    
    # GPT API
    MAX_TOKENS_DATE_EXTRACTION = 50
    MAX_TOKENS_CLASSIFICATION = 100
    MAX_TOKENS_ENTITY_EXTRACTION = 200
    MAX_TOKENS_SUMMARY = 500
    
    # 완성도
    COMPLETION_RATE_MIN = 0
    COMPLETION_RATE_MAX = 100
```

---

## 🔴 8. 질문 텍스트 (Question Messages)

### 위치
- `src/langgraph/nodes/re_question_node.py` (60-64줄, 78-82줄)
- `src/langgraph/nodes/fact_collection_node.py` (516-539줄)

### 하드코딩 내용
```python
question_messages = {
    "incident_date": "사건이 발생한 날짜를 알려주세요.",
    "counterparty": "계약 상대방은 누구인가요?",
    "amount": "문제가 된 금액은 얼마인가요?",
    "evidence": "계약서나 관련 증거를 가지고 계신가요?",
    "evidence_type": "어떤 증거를 가지고 계신가요? (예: 계약서, 카톡 대화내역, 송금내역, 사진, 영상 등)"
}
```

### 문제점
- 질문 텍스트가 코드에 하드코딩
- 다국어 지원 어려움
- RAG K2 문서에서 가져와야 하는데 하드코딩

### 개선 방안
```python
# RAG K2 문서에서 동적으로 로드하거나
# config/questions.py 또는 YAML 파일로 관리
QUESTIONS = {
    "incident_date": "사건이 발생한 날짜를 알려주세요.",
    # ...
}
```

---

## 🔴 9. 폴백 키워드 (Fallback Keywords)

### 위치
- `src/langgraph/nodes/case_classification_node.py` (111-119줄)

### 하드코딩 내용
```python
if any(kw in user_input for kw in ["돈", "빌려", "대여금", "계약", "미지급"]):
    main_case_type = "CIVIL"
    sub_case_type = "CIVIL_CONTRACT"
elif any(kw in user_input for kw in ["사기", "절도", "폭행", "성범죄"]):
    main_case_type = "CRIMINAL"
    sub_case_type = "CRIMINAL_FRAUD"
else:
    main_case_type = "CIVIL"  # 기본값
    sub_case_type = "CIVIL_CONTRACT"
```

### 문제점
- 폴백 로직이 하드코딩
- 키워드 기반 분류가 제한적

### 개선 방안
```python
# config/fallback_keywords.py
FALLBACK_KEYWORDS = {
    "CIVIL": ["돈", "빌려", "대여금", "계약", "미지급"],
    "CRIMINAL": ["사기", "절도", "폭행", "성범죄"]
}
```

---

## 🔴 10. 우선순위 순서 (Priority Order)

### 위치
- `src/services/missing_field_manager.py` (68-69줄)

### 하드코딩 내용
```python
# 우선순위: incident_date > amount > counterparty > evidence
priority_order = ["incident_date", "amount", "counterparty", "evidence"]
```

### 문제점
- 우선순위가 하드코딩
- 사건 유형별로 우선순위가 다를 수 있음

### 개선 방안
```python
# config/priority.py
FIELD_PRIORITY_BY_CASE_TYPE = {
    "CIVIL": ["incident_date", "amount", "counterparty", "evidence"],
    "CRIMINAL": ["incident_date", "counterparty", "amount", "evidence"],
    # ...
}
```

---

## 🔴 11. 필드 매핑 (Field Mapping)

### 위치
- `src/langgraph/nodes/fact_collection_node.py` (56-60줄)

### 하드코딩 내용
```python
field_mapping = {
    "incident_date": ["date"],
    "counterparty": ["party"],
    "amount": ["amount"],
    "evidence": []  # evidence는 엔티티 추출 불필요
}
```

### 문제점
- 필드와 엔티티 타입 매핑이 하드코딩

### 개선 방안
```python
# src/utils/constants.py
FIELD_ENTITY_MAPPING = {
    "incident_date": ["date"],
    "counterparty": ["party"],
    "amount": ["amount"],
    "evidence": []
}
```

---

## 🔴 12. 입력 타입 매핑 (Input Type Mapping)

### 위치
- `src/langgraph/nodes/re_question_node.py` (78-82줄)

### 하드코딩 내용
```python
input_type_mapping = {
    "incident_date": "date",
    "counterparty": "text",
    "amount": "number",
    "evidence": "boolean",
    "evidence_type": "text"
}
```

### 문제점
- 필드별 입력 타입이 하드코딩

### 개선 방안
```python
# src/utils/constants.py
FIELD_INPUT_TYPE_MAPPING = {
    "incident_date": "date",
    "counterparty": "text",
    "amount": "number",
    "evidence": "boolean",
    "evidence_type": "text"
}
```

---

## 🔴 13. 한글 숫자 매핑 (Korean Number Mapping)

### 위치
- `src/services/entity_extractor.py` (132-136줄)

### 하드코딩 내용
```python
korean_numbers = {
    '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
    '육': 6, '칠': 7, '팔': 8, '구': 9,
    '십': 10, '백': 100, '천': 1000, '만': 10000,
    '억': 100000000, '조': 1000000000000
}
```

### 문제점
- 한글 숫자 변환 로직이 하드코딩
- 확장 시 수정 필요

### 개선 방안
```python
# src/utils/korean_numbers.py
KOREAN_NUMBER_MAPPING = {
    # ...
}
```

---

## 🔴 14. 사건 단계 (Case Stage)

### 위치
- `src/langgraph/nodes/case_classification_node.py` (152줄)
- `src/db/models/case_master.py` (21줄)

### 하드코딩 내용
```python
case_stage="상담전"
```

### 문제점
- 사건 단계가 하드코딩
- 다른 단계 추가 시 수정 필요

### 개선 방안
```python
# src/utils/constants.py
class CaseStage:
    BEFORE_CONSULTATION = "상담전"
    IN_CONSULTATION = "상담중"
    # ...
```

---

## 🔴 15. DB 필드 길이 제한

### 위치
- 여러 DB 모델 파일

### 하드코딩 내용
```python
Column(String(50))  # session_id
Column(String(255))  # file_name, party_description
Column(String(500))  # file_path
```

### 문제점
- 필드 길이가 하드코딩
- 변경 시 마이그레이션 필요

### 개선 방안
```python
# src/db/constants.py
class FieldLength:
    SESSION_ID = 50
    FILE_NAME = 255
    FILE_PATH = 500
    # ...
```

---

## 📊 하드코딩 통계

### 카테고리별 개수
- **매핑 딕셔너리**: 8개
- **키워드 리스트**: 5개
- **매직 넘버**: 15개 이상
- **질문 텍스트**: 5개
- **상태/타입 상수**: 4개

### 중복도가 높은 항목
1. **증거 타입 키워드 매핑**: 3곳에 중복
2. **필수 필드 목록**: 4곳에 중복
3. **사건 유형 매핑**: 3곳에 중복

---

## 🎯 개선 우선순위

### 높음 (High Priority)
1. ✅ 증거 타입 키워드 매핑 (3곳 중복)
2. ✅ 필수 필드 목록 (4곳 중복)
3. ✅ 사건 유형 매핑 (3곳 중복)
4. ✅ 증거 키워드 리스트 (2곳 중복)

### 중간 (Medium Priority)
5. ✅ 매직 넘버 상수화
6. ✅ 질문 텍스트 외부화
7. ✅ 당사자 타입 검증 로직 통합

### 낮음 (Low Priority)
8. ✅ 폴백 키워드
9. ✅ 우선순위 순서
10. ✅ DB 필드 길이

---

## 💡 권장 개선 방안

### 1. 상수 파일 생성
```python
# src/utils/constants.py
# 모든 하드코딩된 상수들을 한 곳에 모음
```

### 2. 설정 파일 활용
```python
# config/case_types.yaml
# config/keywords.yaml
# config/questions.yaml
```

### 3. RAG 문서 활용
- 필수 필드 목록은 RAG K2 문서에서 동적으로 로드
- 질문 텍스트는 RAG K2 문서에서 가져오기

### 4. Enum 클래스 활용
```python
# Python Enum을 사용하여 타입 안정성 확보
from enum import Enum

class CaseType(Enum):
    CIVIL = "CIVIL"
    CRIMINAL = "CRIMINAL"
    # ...
```

---

## 📝 체크리스트

- [ ] 증거 타입 키워드 매핑 통합
- [ ] 필수 필드 목록 상수화
- [ ] 사건 유형 매핑 통합
- [ ] 증거 키워드 리스트 상수화
- [ ] 매직 넘버 상수화
- [ ] 질문 텍스트 외부화
- [ ] 당사자 타입 검증 로직 통합
- [ ] 세션 상태 Enum 생성
- [ ] 폴백 키워드 설정 파일화
- [ ] 우선순위 순서 설정 파일화

---

**작성 일시**: 2025-12-30  
**분석 대상**: `info_scrap/ver2/legal-chatbot-system/` 전체 코드베이스

