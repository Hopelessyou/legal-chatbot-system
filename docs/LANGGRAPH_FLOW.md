# LangGraph 흐름 가이드

## 개요

LangGraph는 법률 상담 챗봇의 대화 흐름을 제어하는 핵심 엔진입니다. 사용자의 자유로운 입력을 받아 구조화된 상담 데이터로 변환하는 과정을 단계별로 관리합니다.

**핵심 원칙**:
- GPT는 해석 도구일 뿐, 판단은 하지 않음
- 모든 기준은 RAG 문서(K0~K4)에 정의
- LangGraph가 분기, 반복, 검증을 담당

## 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 세션 시작                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  INIT Node                                                    │
│  - 세션 생성                                                  │
│  - K0_Intake 참조 (START_MESSAGE, DISCLAIMER)                │
│  - 긴급 상황 체크 (EMERGENCY_CHECK)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  CASE_CLASSIFICATION Node                                     │
│  - 사용자 첫 입력 분석                                        │
│  - K1_Classification 참조 (키워드/표현 매칭)                  │
│  - LEVEL2/LEVEL3 분류                                         │
│  - 애매하면 DISAMBIGUATION_QUESTION 사용                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  FACT_COLLECTION Node                                        │
│  - 엔티티 추출 (날짜, 금액, 인물, 행위)                      │
│  - 사실/감정 분리                                            │
│  - K2_Questions 참조 (필수 필드 및 질문 템플릿)              │
│  - DB 저장 (case_fact, case_emotion)                         │
│  - Completion Rate 계산                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  VALIDATION Node                                             │
│  - K2_Questions에서 필수 필드 목록 조회                      │
│  - 누락 필드 확인                                             │
│  - LEVEL4_FACT_Pattern 참조 (중요 사실 체크)                 │
└───────┬───────────────────────────────────────┬─────────────┘
        │                                       │
        │ (missing_fields 있음)                 │ (모든 필드 충족)
        ↓                                       ↓
┌───────────────────────────┐    ┌──────────────────────────────┐
│  RE_QUESTION Node         │    │  SUMMARY Node                │
│  - 누락 필드 우선순위 결정 │    │  - K4_Output_Format 참조     │
│  - K2 질문 템플릿 사용      │    │  - GPT 요약 생성             │
│  - 재질문 생성             │    │  - case_summary 저장         │
└───────┬───────────────────┘    └───────┬──────────────────────┘
        │                                  │
        │ (Loop)                            │
        └──────────→ FACT_COLLECTION ←─────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  COMPLETED Node                                              │
│  - K3_Risk_Rules 참조 (리스크 태그)                           │
│  - 세션 종료 처리                                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
                    세션 종료
```

## 단계별 상세 설명

### 1. INIT Node (초기화)

**역할**: 상담 세션 초기화 및 초기 메시지 출력

**RAG 참조**: `K0_Intake`

**처리 과정**:
1. 세션 ID 생성 및 DB 저장
2. K0_Intake YAML에서 메시지 순서대로 읽기:
   - `START_MESSAGE`: "상황을 3~5줄로 적어주세요..."
   - `DISCLAIMER`: "본 시스템은 법률 자문이 아닙니다..."
   - `EMERGENCY_CHECK`: "신체 위협/긴급 상황인가요?"
3. 긴급 상황이면 `EMERGENCY_STOP` → 세션 종료
4. 정상이면 `CLASSIFY` → 다음 단계로

**출력**:
- `bot_message`: K0의 START_MESSAGE
- `next_state`: `CASE_CLASSIFICATION`

**예시**:
```yaml
# K0_Intake YAML
messages:
  - step_code: START_MESSAGE
    order: 1
    message_text: "상황을 3~5줄로 적어주세요..."
    answer_type: string
    next_action: CLASSIFY
```

---

### 2. CASE_CLASSIFICATION Node (사건 분류)

**역할**: 사용자의 첫 입력을 분석하여 사건 유형 분류

**RAG 참조**: `K1_Classification`

**처리 과정**:
1. 사용자 입력 텍스트 수신
2. GPT API로 키워드/의미 추출
3. K1_Classification YAML에서 매칭:
   - `KEYWORDS` 리스트와 비교
   - `TYPICAL_EXPRESSIONS`와 유사도 계산
4. LEVEL2/LEVEL3 추정
5. 애매한 경우:
   - `DISAMBIGUATION_QUESTION` 사용
   - `DISAMBIGUATION_OPTIONS` 제시
   - 사용자 선택 대기
6. 확정되면 DB에 case_master 저장

**출력**:
- `case_type`: LEVEL1 (예: CIVIL)
- `sub_case_type`: LEVEL2_CODE (예: CIVIL_CONTRACT)
- `scenario`: LEVEL3_SCENARIO_CODE (예: CONTRACT_NONPAYMENT)
- `next_state`: `FACT_COLLECTION`

**예시**:
```yaml
# K1_Classification YAML
level1: CIVIL
level2_code: CIVIL_CONTRACT
typical_keywords:
  - 계약
  - 대금
  - 미지급
scenarios:
  - scenario_code: CONTRACT_NONPAYMENT
    keywords: ["계약", "대금", "미지급"]
    disambiguation_question: "계약서가 있으신가요?"
    disambiguation_options: ["있음", "없음"]
```

---

### 3. FACT_COLLECTION Node (사실 수집)

**역할**: 사건의 핵심 사실 정보 수집

**RAG 참조**: `K2_Questions`

**처리 과정**:
1. 사용자 입력에서 엔티티 추출:
   - 날짜 (incident_date)
   - 금액 (amount)
   - 인물 (counterparty)
   - 행위 (action)
2. 사실과 감정 분리 (GPT API)
3. K2_Questions YAML 조회:
   - 현재 시나리오의 `required_fields` 확인
   - `questions` 리스트에서 다음 질문 선택
4. 수집된 사실을 DB에 저장:
   - `case_fact` 테이블
   - `case_emotion` 테이블
5. Completion Rate 재계산:
   - `(수집된 필수 필드 수 / 전체 필수 필드 수) * 100`

**출력**:
- `facts`: 수집된 사실 딕셔너리
- `completion_rate`: 완성도 (0~100)
- `bot_message`: 다음 질문
- `next_state`: `VALIDATION`

**예시**:
```yaml
# K2_Questions YAML
scenario: CONTRACT_NONPAYMENT
required_fields:
  - incident_date
  - counterparty
  - amount
questions:
  - order: 1
    field: incident_date
    question: "계약 또는 문제가 발생한 시점은 언제인가요?"
    answer_type: date
    required: true
```

---

### 4. VALIDATION Node (검증)

**역할**: 필수 정보 충족 여부 확인

**RAG 참조**: `K2_Questions`, `LEVEL4_FACT_Pattern`

**처리 과정**:
1. K2_Questions에서 `required_fields` 목록 조회
2. 현재 수집된 `facts`와 비교
3. 누락 필드 산출:
   ```python
   missing_fields = required_fields - collected_fields
   ```
4. LEVEL4_FACT_Pattern 참조:
   - `CRITICAL=True`인 사실이 누락되었는지 확인
5. 분기 결정:
   - `missing_fields` 있음 → `RE_QUESTION`
   - 모든 필드 충족 → `SUMMARY`

**출력**:
- `missing_fields`: 누락된 필수 필드 리스트
- `next_state`: `RE_QUESTION` 또는 `SUMMARY`

**조건부 분기**:
```python
def route_after_validation(state):
    if len(state["missing_fields"]) > 0:
        return "RE_QUESTION"
    else:
        return "SUMMARY"
```

---

### 5. RE_QUESTION Node (재질문)

**역할**: 누락된 정보를 재질문

**RAG 참조**: `K2_Questions`

**처리 과정**:
1. `missing_fields`에서 우선순위 결정:
   - `CRITICAL=True`인 필드 우선
   - `QUESTION_ORDER`가 낮은 필드 우선
2. K2_Questions에서 해당 필드의 `question` 템플릿 조회
3. 질문 생성 및 출력
4. Loop: `FACT_COLLECTION`으로 돌아가서 사용자 응답 대기

**출력**:
- `bot_message`: 재질문 메시지
- `expected_input`: 기대하는 입력 타입
- `next_state`: `FACT_COLLECTION` (Loop)

**예시**:
```yaml
# K2_Questions에서
questions:
  - field: amount
    question: "문제가 된 금액은 얼마인가요?"
    answer_type: integer
    required: true
```

---

### 6. SUMMARY Node (요약 생성)

**역할**: 내부 전달용 구조화된 요약 생성

**RAG 참조**: `K4_Output_Format`

**처리 과정**:
1. K4_Output_Format YAML 조회:
   - `sections` 리스트 확인
   - `content_rule`, `style_rule` 적용
2. GPT API로 요약 생성:
   - 수집된 모든 `facts` 기반
   - K4 포맷에 맞춰 구조화
3. DB에 `case_summary` 저장
4. 리스크 태그 추가 (K3 참조)

**출력**:
- `summary`: 구조화된 요약 딕셔너리
- `risk_tags`: 리스크 태그 리스트
- `next_state`: `COMPLETED`

**예시**:
```yaml
# K4_Output_Format YAML
sections:
  - name: 사건 유형
    format: "{main_case_type} / {sub_case_type}"
  - name: 핵심 사실관계
    format: "날짜, 당사자, 행위, 결과를 포함한 사실 중심 서술"
```

---

### 7. COMPLETED Node (완료)

**역할**: 세션 종료 처리

**RAG 참조**: `K3_Risk_Rules`

**처리 과정**:
1. K3_Risk_Rules 참조:
   - `trigger_facts`와 수집된 사실 비교
   - 조건 만족 시 `risk_tag` 추가
2. 세션 상태를 `COMPLETED`로 업데이트
3. 종료 시간 기록
4. 최종 응답 반환

**출력**:
- `session_status`: `COMPLETED`
- `risk_tags`: 리스크 태그 리스트
- `next_state`: `END`

**예시**:
```yaml
# K3_Risk_Rules YAML
rules:
  - rule_code: RULE_001
    trigger_facts: ["FACT_001", "FACT_002"]
    risk_level: high
    risk_tag: 소멸시효_의심
```

---

## RAG 문서 매핑

| LangGraph Node | 참조 RAG 문서 | 용도 |
|---------------|--------------|------|
| **INIT** | K0_Intake | 초기 메시지, 디스클레이머, 긴급 체크 |
| **CASE_CLASSIFICATION** | K1_Classification | 사건 유형 분류 기준 (키워드, 표현, 확인 질문) |
| **FACT_COLLECTION** | K2_Questions | 필수 필드 목록, 질문 템플릿 |
| **VALIDATION** | K2_Questions, LEVEL4_FACT_Pattern | 필수 필드 검증, 중요 사실 체크 |
| **RE_QUESTION** | K2_Questions | 재질문 템플릿 |
| **SUMMARY** | K4_Output_Format | 요약 포맷, 스타일 규칙 |
| **COMPLETED** | K3_Risk_Rules | 리스크 태그, 주의사항 |

## State 전이 규칙

### 일반 Edge (순차 진행)
- `INIT` → `CASE_CLASSIFICATION`
- `CASE_CLASSIFICATION` → `FACT_COLLECTION`
- `FACT_COLLECTION` → `VALIDATION`
- `RE_QUESTION` → `FACT_COLLECTION` (Loop)
- `SUMMARY` → `COMPLETED`
- `COMPLETED` → `END`

### 조건부 Edge
- `VALIDATION` → `RE_QUESTION` (missing_fields 있음)
- `VALIDATION` → `SUMMARY` (모든 필드 충족)

### 예외 처리
- `INIT`에서 긴급 상황 감지 → `EMERGENCY_STOP` → 세션 종료

## 실행 방식

### 1 Step 실행 모델
각 API 요청마다 현재 State에 해당하는 Node만 실행:
1. `/chat/start` → INIT Node 실행
2. `/chat/message` → 현재 State의 Node 실행
3. State 업데이트 및 다음 State 결정
4. 응답 반환

### 예시 플로우

```
1. POST /chat/start
   → INIT Node 실행
   → K0_Intake 메시지 출력
   → State: CASE_CLASSIFICATION

2. POST /chat/message {"text": "작년 10월에 계약했는데 돈을 안 줬어요"}
   → CASE_CLASSIFICATION Node 실행
   → K1_Classification 참조하여 분류
   → State: FACT_COLLECTION

3. POST /chat/message {"text": "5000만원이요"}
   → FACT_COLLECTION Node 실행
   → K2_Questions 참조하여 질문
   → State: VALIDATION

4. VALIDATION Node 실행
   → missing_fields 확인
   → State: RE_QUESTION (필드 누락 시) 또는 SUMMARY (완료 시)

5. (Loop) RE_QUESTION → FACT_COLLECTION → VALIDATION
   → 모든 필드 수집될 때까지 반복

6. SUMMARY Node 실행
   → K4_Output_Format 참조하여 요약 생성
   → State: COMPLETED

7. COMPLETED Node 실행
   → K3_Risk_Rules 참조하여 리스크 태그 추가
   → 세션 종료
```

## 핵심 설계 원칙

### 1. GPT는 해석만 수행
- GPT API는 엔티티 추출, 키워드 추출, 요약 생성만 담당
- 판단, 분기, 검증은 LangGraph가 담당

### 2. RAG는 기준만 제공
- 모든 질문, 규칙, 포맷은 RAG 문서에 정의
- GPT 프롬프트 하드코딩 금지
- 엑셀 수정 = 시스템 즉시 반영

### 3. State는 명시적으로 관리
- 모든 State 전이는 로깅됨 (`chat_session_state_log`)
- State 변경은 Node 실행 결과로만 가능
- 예외 상황도 State로 관리

### 4. 완전 분리 구조
- RAG (기준 문서) ↔ LangGraph (흐름 제어) ↔ DB (데이터 저장)
- 각 레이어는 독립적으로 수정 가능
- 확장성과 유지보수성 보장

## 확장 가능성

### 새로운 시나리오 추가
1. 엑셀에 K1, K2, K3 시트에 행 추가
2. `python scripts/generate_all_yaml.py` 실행
3. 자동으로 YAML 생성 및 RAG 인덱싱
4. LangGraph 코드 수정 불필요

### 새로운 질문 추가
1. 엑셀 K2_Questions 시트에 행 추가
2. YAML 재생성
3. 다음 실행부터 자동 반영

### 새로운 리스크 규칙 추가
1. 엑셀 K3_Risk_Rules 시트에 행 추가
2. YAML 재생성
3. COMPLETED Node에서 자동 적용

## 문제 해결

### 분류가 애매한 경우
- K1_Classification의 `DISAMBIGUATION_QUESTION` 사용
- 사용자에게 선택지 제시
- 명확해질 때까지 반복 가능

### 필수 필드가 계속 누락되는 경우
- RE_QUESTION → FACT_COLLECTION Loop
- 최대 반복 횟수 제한 가능 (추가 구현 필요)
- 우선순위 기반 질문 순서 조정

### 긴급 상황 처리
- INIT Node에서 EMERGENCY_CHECK
- 긴급 상황 감지 시 즉시 세션 종료
- 적절한 안내 메시지 제공

