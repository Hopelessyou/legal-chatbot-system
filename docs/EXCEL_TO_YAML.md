# 엑셀 → YAML 변환 가이드

## 개요

엑셀 파일에서 RAG용 YAML 파일을 자동 생성하는 스크립트입니다.

**핵심 원칙**: 내용을 판단하지 않고 그대로 변환만 합니다. 모든 규칙은 엑셀에 정의되어 있습니다.

## 폴더 구조

```
project/
 ├─ excel/                          # 엑셀 파일 위치
 │   └─ knowledge_base.xlsx         # 단일 엑셀 파일 (여러 시트 포함)
 │       ├─ 시트: K0_Intake                 # 초기 인입 질문/디스클레이머/긴급체크
 │       ├─ 시트: K1_Classification         # LEVEL2/LEVEL3 분류 기준
 │       ├─ 시트: K2_Questions               # 질문 및 필수 필드 정의
 │       ├─ 시트: LEVEL4_FACT_Pattern        # 사실 패턴 정의
 │       ├─ 시트: K3_Risk_Rules              # 리스크 규칙 정의
 │       └─ 시트: K4_Output_Format           # 출력 포맷 정의
 │
 ├─ data/rag/                        # 생성된 YAML 파일 위치
 │   ├─ K0_intake/
 │   │   └─ intake_messages.yaml
 │   ├─ K1_case_type/
 │   │   └─ {level1}/
 │   │       └─ {level2_code}_classification.yaml
 │   ├─ K2_required_fields/
 │   │   └─ {level1}/
 │   │       └─ {scenario}_required.yaml
 │   ├─ K3_risk_rules/
 │   │   └─ {level1}/
 │   │       └─ {scenario}_risk.yaml
 │   ├─ K4_output_format/
 │   │   └─ {format_id}.yaml
 │   └─ common/facts/
 │       └─ {scenario}_facts.yaml
 │
 └─ scripts/
     ├─ utils.py                     # 공통 유틸 함수
     ├─ generate_k0_yaml.py          # K0 Intake 시트 → YAML
     ├─ generate_k1_yaml.py          # K1 Classification 시트 → YAML
     ├─ generate_k2_yaml.py          # K2 질문 시트 → YAML
     ├─ generate_fact_yaml.py        # LEVEL4 FACT 시트 → YAML
     ├─ generate_k3_yaml.py          # K3 리스크 규칙 시트 → YAML
     ├─ generate_k4_yaml.py          # K4 출력 포맷 시트 → YAML
     └─ generate_all_yaml.py         # 통합 실행 스크립트
```

## 엑셀 파일 구조

**단일 엑셀 파일**: `excel/knowledge_base.xlsx`

이 파일에는 다음 시트들이 포함되어야 합니다:

### 시트: K0_Intake

**역할**: 초기 인입 단계에서 사용할 질문, 디스클레이머, 긴급 상황 체크

**필수 컬럼**:
- `STEP_CODE`: 단계 코드 (예: START_MESSAGE, DISCLAIMER, EMERGENCY_CHECK)
- `MESSAGE_ORDER`: 메시지 순서 (정수)
- `MESSAGE_TEXT`: 메시지 텍스트
- `ANSWER_TYPE`: 답변 타입 (none / boolean / choice / string)
- `NEXT_ACTION`: 다음 액션 (CLASSIFY / EMERGENCY_STOP / ASK_MORE)

**선택 컬럼**:
- `DISAMBIGUATION_OPTIONS`: 확인 질문 선택지 (쉼표로 구분)

**예시**:
- START_MESSAGE: "상황을 3~5줄로 적어주세요..."
- DISCLAIMER: "본 시스템은 법률 자문이 아닙니다..."
- EMERGENCY_CHECK: "신체 위협/긴급 상황인가요? (예/아니오)"

### 시트: K1_Classification

**역할**: 사용자의 첫 자유서술을 보고 LEVEL2/LEVEL3를 분류하는 기준

**필수 컬럼**:
- `LEVEL1`: 대분류 (예: CIVIL, CRIMINAL)
- `LEVEL2_CODE`: 중분류 코드 (예: CIVIL_CONTRACT, CRIMINAL_FRAUD)
- `LEVEL2_NAME`: 중분류 이름
- `LEVEL3_SCENARIO_CODE`: 시나리오 코드 (예: CONTRACT_NONPAYMENT)
- `LEVEL3_SCENARIO_NAME`: 시나리오 이름

**선택 컬럼**:
- `KEYWORDS`: 키워드 (쉼표로 구분, 예: "중고거래, 번개장터, 입금, 미배송")
- `TYPICAL_EXPRESSIONS`: 전형적 표현 (쉼표로 구분)
- `DISAMBIGUATION_QUESTION`: 애매할 때 확인 질문
- `DISAMBIGUATION_OPTIONS`: 확인 질문 선택지 (쉼표로 구분)

**예시**:
- CRIMINAL_FRAUD / FRAUD_ONLINE: 키워드 = "중고거래, 번개장터, 당근, 입금, 미배송, 연락두절..."
- CIVIL_CONTRACT / CONTRACT_NONPAYMENT: 키워드 = "계약, 대금, 잔금, 지급, 미지급..."

### 시트: K2_Questions

필수 컬럼:
- `LEVEL1`: 대분류 (예: CIVIL)
- `LEVEL2_CODE`: 중분류 코드 (예: CIVIL_CONTRACT)
- `LEVEL3_SCENARIO_CODE`: 시나리오 코드 (예: CONTRACT_NONPAYMENT)
- `QUESTION_ORDER`: 질문 순서 (정수)
- `FIELD_KEY`: 필드 키 (예: incident_date)
- `QUESTION_TEXT`: 질문 텍스트
- `ANSWER_TYPE`: 답변 타입 (예: date, string, integer)
- `REQUIRED`: 필수 여부 (boolean)

### 시트: LEVEL4_FACT_Pattern

필수 컬럼:
- `LEVEL1`: 대분류
- `LEVEL2_CODE`: 중분류 코드
- `LEVEL3_SCENARIO_CODE`: 시나리오 코드
- `FACT_CODE`: 사실 코드
- `FACT_NAME`: 사실 이름
- `DESCRIPTION`: 설명
- `CRITICAL`: 중요 여부 (boolean)
- `RELATED_FIELD`: 관련 필드

### 시트: K3_Risk_Rules

필수 컬럼:
- `LEVEL1`: 대분류
- `LEVEL2_CODE`: 중분류 코드
- `LEVEL3_SCENARIO_CODE`: 시나리오 코드
- `RISK_RULE_CODE`: 리스크 규칙 코드
- `TRIGGER_FACT_CODES`: 트리거 사실 코드 (쉼표로 구분)
- `RISK_LEVEL`: 리스크 레벨
- `RISK_TAG`: 리스크 태그
- `DESCRIPTION`: 설명
- `ACTION_HINT`: 액션 힌트

### 시트: K4_Output_Format

필수 컬럼:
- `FORMAT_ID`: 포맷 ID
- `TARGET_USER`: 대상 사용자
- `SECTION_ORDER`: 섹션 순서 (정수)
- `SECTION_KEY`: 섹션 키
- `SECTION_TITLE`: 섹션 제목
- `CONTENT_RULE`: 내용 규칙
- `SOURCE_DATA`: 소스 데이터
- `STYLE_RULE`: 스타일 규칙

## 사용 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- `pandas>=2.0.0`
- `openpyxl>=3.1.0`
- `pyyaml>=6.0.0`

### 2. 엑셀 파일 준비

`excel/` 폴더에 `knowledge_base.xlsx` 파일을 배치하고, 다음 시트들을 포함시킵니다:
- `K0_Intake` (초기 인입 질문)
- `K1_Classification` (분류 기준)
- `K2_Questions` (질문 및 필수 필드)
- `LEVEL4_FACT_Pattern` (사실 패턴)
- `K3_Risk_Rules` (리스크 규칙)
- `K4_Output_Format` (출력 포맷)

### 3. 스크립트 실행

#### 개별 실행

```bash
# K0 Intake 시트 → YAML
python scripts/generate_k0_yaml.py

# K1 Classification 시트 → YAML
python scripts/generate_k1_yaml.py

# K2 질문 시트 → YAML
python scripts/generate_k2_yaml.py

# LEVEL4 FACT 시트 → YAML
python scripts/generate_fact_yaml.py

# K3 리스크 규칙 시트 → YAML
python scripts/generate_k3_yaml.py

# K4 출력 포맷 시트 → YAML
python scripts/generate_k4_yaml.py
```

#### 통합 실행 (권장)

```bash
python scripts/generate_all_yaml.py
```

모든 시트를 한 번에 변환합니다.

## 생성되는 YAML 파일 예시

### K0 YAML 예시

```yaml
doc_id: K0-INTAKE-001
knowledge_type: K0
node_scope:
  - INIT
  - INTAKE
version: v1.0
messages:
  - step_code: START_MESSAGE
    order: 1
    message_text: 상황을 3~5줄로 적어주세요...
    answer_type: string
    next_action: CLASSIFY
  - step_code: DISCLAIMER
    order: 2
    message_text: 본 시스템은 법률 자문이 아닙니다...
    answer_type: none
    next_action: CLASSIFY
  - step_code: EMERGENCY_CHECK
    order: 3
    message_text: 신체 위협/긴급 상황인가요?
    answer_type: boolean
    next_action: EMERGENCY_STOP
    options:
      - 예
      - 아니오
```

### K1 YAML 예시

```yaml
doc_id: K1-CIVIL-CIVIL_CONTRACT
knowledge_type: K1
level1: CIVIL
level2_code: CIVIL_CONTRACT
level2_name: 계약
node_scope:
  - CASE_CLASSIFICATION
version: v1.0
typical_keywords:
  - 계약
  - 대금
  - 잔금
  - 지급
  - 미지급
scenarios:
  - scenario_code: CONTRACT_NONPAYMENT
    scenario_name: 계약금 미지급
    keywords:
      - 계약
      - 대금
      - 미지급
    disambiguation_question: 계약서가 있으신가요?
    disambiguation_options:
      - 있음
      - 없음
```

### K2 YAML 예시

```yaml
doc_id: K2-CONTRACT_NONPAYMENT
knowledge_type: K2
level1: CIVIL
level2: CIVIL_CONTRACT
scenario: CONTRACT_NONPAYMENT
required_fields:
  - incident_date
  - counterparty
  - amount
questions:
  - order: 1
    field: incident_date
    question: 계약 또는 문제가 발생한 시점은 언제인가요?
    answer_type: date
    required: true
  - order: 2
    field: counterparty
    question: 계약 상대방은 누구인가요?
    answer_type: string
    required: true
```

### K3 YAML 예시

```yaml
doc_id: K3-CONTRACT_NONPAYMENT
knowledge_type: K3
level1: CIVIL
level2: CIVIL_CONTRACT
scenario: CONTRACT_NONPAYMENT
rules:
  - rule_code: RULE_001
    trigger_facts:
      - FACT_001
      - FACT_002
    risk_level: high
    risk_tag: 소멸시효_의심
    description: 사건 발생 시점으로 보아 시효 문제 검토 필요
    action_hint: 변호사 상담 권장
```

### K4 YAML 예시

```yaml
doc_id: FORMAT_001
knowledge_type: K4
target: 변호사
sections:
  - order: 1
    key: case_type
    title: 사건 유형
    content_rule: "{main_case_type} / {sub_case_type}"
    source: classification_result
    style: 객관적 사실 중심
```

## 장점

1. **엑셀 수정 = 시스템 즉시 반영**: 엑셀 파일만 수정하면 YAML이 자동으로 업데이트됩니다.
2. **GPT 프롬프트 하드코딩 없음**: 모든 규칙이 문서화되어 있습니다.
3. **기준 완전 문서화**: 엑셀 파일이 단일 소스 오브 트루스입니다.
4. **완전 분리**: RAG, LangGraph, DB가 완전히 분리되어 있습니다.
5. **확장성**: 규모가 커져도 구조가 무너지지 않습니다.

## 주의사항

- 엑셀 파일명은 `knowledge_base.xlsx`여야 합니다.
- 각 시트의 컬럼명이 정확해야 합니다.
- 필수 컬럼이 없으면 오류가 발생합니다.
- 엑셀 파일을 수정한 후에는 반드시 스크립트를 다시 실행해야 합니다.
- 생성된 YAML 파일은 `data/rag/` 폴더에 저장됩니다.

## 문제 해결

### 엑셀 파일을 찾을 수 없습니다

- `excel/` 폴더에 `knowledge_base.xlsx` 파일이 있는지 확인하세요.
- 파일명이 정확한지 확인하세요.

### 시트를 찾을 수 없습니다

- 엑셀 파일에 필요한 시트가 모두 있는지 확인하세요.
- 시트 이름이 정확한지 확인하세요 (대소문자 구분).
- 스크립트 실행 시 사용 가능한 시트 목록이 출력됩니다.

### 필수 컬럼이 없습니다

- 엑셀 파일의 컬럼명을 확인하세요.
- 대소문자를 정확히 맞춰야 합니다.

### 인코딩 오류

- 엑셀 파일이 UTF-8로 저장되어 있는지 확인하세요.
- 한글이 포함된 경우 특히 주의하세요.

