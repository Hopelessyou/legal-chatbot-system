# LangGraph 구조 설명 문서

## 개요

LangGraph는 본 시스템에서 대화의 흐름을 통제하는 핵심 엔진입니다. GPT API는 해석 도구이며, 판단·분기·반복은 LangGraph가 담당합니다.

## State 정의

### State 목록

| State 코드 | State 명 | 설명 |
|-----------|---------|------|
| INIT | 상담 시작 | 세션 생성 직후 상태 |
| CASE_CLASSIFICATION | 사건 유형 분류 | 사건 분야 판단 |
| FACT_COLLECTION | 사실관계 수집 | 핵심 정보 입력 단계 |
| VALIDATION | 정보 검증 | 필수 정보 충족 여부 확인 |
| RE_QUESTION | 재질문 | 누락 정보 보완 |
| SUMMARY | 요약 생성 | 내부 전달용 정리 |
| COMPLETED | 상담 종료 | 세션 종료 |

### State Context 구조

```python
{
    "session_id": "sess_abc123",
    "current_state": "FACT_COLLECTION",
    "case_type": "민사",
    "sub_case_type": "계약",
    "facts": {
        "incident_date": "2023-10-15",
        "location": None,
        "counterparty": "개인",
        "amount": 50000000,
        "evidence": True
    },
    "emotion": [
        {"type": "억울함", "intensity": 4}
    ],
    "completion_rate": 75,
    "last_user_input": "작년 10월에 계약을 했어요.",
    "missing_fields": [],
    "bot_message": "계약 상대방은 개인인가요, 법인인가요?",
    "expected_input": {
        "type": "choice",
        "field": "counterparty_type",
        "options": ["개인", "법인"]
    }
}
```

## Node 설명

### INIT Node
- **역할**: 상담 세션 초기화
- **입력**: 없음 (세션 생성 시 자동 실행)
- **처리**: Context 초기화, DB 세션 생성
- **출력**: 첫 질문 반환
- **다음 State**: CASE_CLASSIFICATION

### CASE_CLASSIFICATION Node
- **역할**: 사건 유형 분류
- **입력**: 사용자 입력 텍스트
- **처리**: 
  - 키워드/의미 추출 (GPT API)
  - RAG K1 조회
  - 사건 유형 결정
- **출력**: case_type, sub_case_type 설정
- **다음 State**: FACT_COLLECTION

### FACT_COLLECTION Node (핵심)
- **역할**: 사건 핵심 사실 수집
- **입력**: 사용자 입력 텍스트
- **처리**:
  - 엔티티 추출 (날짜, 금액, 인물, 행위)
  - 사실/감정 분리
  - RAG K2 조회 (필수 필드 및 질문 템플릿)
  - DB 저장 (case_fact, case_emotion)
  - Completion Rate 재계산
- **출력**: 다음 질문 생성
- **다음 State**: VALIDATION

### VALIDATION Node
- **역할**: 필수 정보 충족 여부 판단
- **입력**: 수집된 facts
- **처리**:
  - RAG K2에서 필수 필드 목록 조회
  - 누락 필드 산출
  - 분기 조건 생성
- **출력**: missing_fields 리스트
- **다음 State**: RE_QUESTION 또는 SUMMARY (조건부)

### RE_QUESTION Node
- **역할**: 누락 정보 재질문
- **입력**: missing_fields 리스트
- **처리**:
  - 우선순위 기반 필드 선택
  - RAG K2 질문 템플릿 활용
  - 질문 생성
- **출력**: 재질문 메시지
- **다음 State**: FACT_COLLECTION (Loop)

### SUMMARY Node
- **역할**: 내부 전달용 요약 생성
- **입력**: 전체 Context
- **처리**:
  - RAG K4 포맷 기준 조회
  - GPT API 요약 생성
  - case_summary 저장
- **출력**: 구조화된 요약
- **다음 State**: COMPLETED

### COMPLETED Node
- **역할**: 세션 종료
- **입력**: 최종 State
- **처리**:
  - 세션 상태를 COMPLETED로 업데이트
  - 종료 시간 기록
- **출력**: 종료 응답
- **다음 State**: None (종료)

## Edge 및 분기 로직

### 일반 Edge
- INIT → CASE_CLASSIFICATION
- CASE_CLASSIFICATION → FACT_COLLECTION
- FACT_COLLECTION → VALIDATION
- RE_QUESTION → FACT_COLLECTION (Loop)
- SUMMARY → COMPLETED
- COMPLETED → END

### Conditional Edge
- VALIDATION → RE_QUESTION (missing_fields 존재 시)
- VALIDATION → SUMMARY (모든 필드 충족 시)

**조건 함수:**
```python
def route_after_validation(state):
    if len(state["missing_fields"]) > 0:
        return "RE_QUESTION"
    else:
        return "SUMMARY"
```

## State 전이 다이어그램

```
INIT
 ↓
CASE_CLASSIFICATION
 ↓
FACT_COLLECTION
 ↓
VALIDATION ── (missing_fields 있음) ──→ RE_QUESTION
     │                                        │
     │                                        │ (Loop)
     │                                        ↓
     └─── (모든 필드 충족) ───────────→ FACT_COLLECTION
              │
              ↓
          SUMMARY
              ↓
          COMPLETED
              ↓
            END
```

## LangGraph ↔ RAG 매핑

| LangGraph Node | 참조 RAG | 용도 |
|---------------|---------|------|
| INIT | K0_Intake | 초기 메시지, 디스클레이머, 긴급 체크 |
| CASE_CLASSIFICATION | K1_Classification | 사건 유형 분류 기준 (키워드, 표현, 확인 질문) |
| FACT_COLLECTION | K2_Questions | 필수 필드 목록, 질문 템플릿 |
| VALIDATION | K2_Questions, LEVEL4_FACT_Pattern | 필수 필드 검증, 중요 사실 체크 |
| RE_QUESTION | K2_Questions | 재질문 템플릿 |
| SUMMARY | K4_Output_Format | 요약 포맷, 스타일 규칙 |
| COMPLETED | K3_Risk_Rules | 리스크 태그, 주의사항 |

**자세한 흐름은 `LANGGRAPH_FLOW.md` 문서를 참고하세요.**

## LangGraph ↔ GPT API 매핑

| LangGraph Node | GPT API 사용 |
|---------------|-------------|
| CASE_CLASSIFICATION | 키워드/의미 추출 |
| FACT_COLLECTION | 엔티티 추출, 사실/감정 분리 |
| RE_QUESTION | 질문 자연화 (선택적) |
| SUMMARY | 요약 생성 |
| VALIDATION | 사용 금지 (순수 로직) |

## 실행 방식

### 1 Step 실행
- 각 API 요청마다 현재 State에 해당하는 Node만 실행
- Node 실행 후 State 업데이트
- 다음 State 결정 및 반환

### 예시 플로우
1. `/chat/start` → INIT Node 실행 → CASE_CLASSIFICATION으로 전이
2. `/chat/message` (CASE_CLASSIFICATION) → CASE_CLASSIFICATION Node 실행 → FACT_COLLECTION으로 전이
3. `/chat/message` (FACT_COLLECTION) → FACT_COLLECTION Node 실행 → VALIDATION으로 전이
4. `/chat/message` (VALIDATION) → VALIDATION Node 실행 → RE_QUESTION 또는 SUMMARY로 전이
5. 반복...

## 핵심 설계 원칙

1. **GPT는 판단하지 않는다**
   - GPT API는 해석만 수행 (엔티티 추출, 키워드 추출 등)
   - 분기 및 반복은 LangGraph가 담당

2. **RAG는 기준을 제공한다**
   - 내부 기준 문서만 참조
   - 질문 및 요약 표준화

3. **State는 명시적으로 관리된다**
   - 모든 State 전이는 로깅됨
   - State 변경은 Node 실행 결과로만 가능

