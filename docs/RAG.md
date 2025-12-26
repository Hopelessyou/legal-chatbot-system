# RAG 문서 구조 설명

## 개요

RAG는 법률 지식을 학습시키기 위한 것이 아니라, GPT가 항상 '같은 기준'으로 질문하고 요약하도록 만드는 것이 목적입니다.

## RAG 구성

RAG는 4개의 독립 Knowledge Layer로 구성됩니다:

- **K1**: 사건 유형 기준 DB
- **K2**: 필수 정보·질문 기준 DB (가장 중요)
- **K3**: 법률 판단 보조 기준 DB
- **K4**: 출력·요약 포맷 기준 DB

## 문서 메타데이터 규격

모든 RAG 문서는 다음 메타데이터를 포함합니다:

```yaml
doc_id: K2-CIVIL-CONTRACT-REQ-001
knowledge_type: K2
main_case_type: 민사
sub_case_type: 계약
node_scope:
  - FACT_COLLECTION
  - VALIDATION
  - RE_QUESTION
version: v1.0
last_updated: 2025-01-01T00:00:00Z
```

## K1: 사건 유형 기준 DB

### 목적
사건을 법률적으로 분류하기 위한 기준 제공

### 문서 구조
```yaml
doc_id: K1-CIVIL-CONTRACT-001
knowledge_type: K1
main_case_type: 민사
sub_case_type: 계약
definition:
  - 계약 체결 또는 이행 과정에서 발생한 분쟁
typical_keywords:
  - 계약
  - 약정
  - 대금
exclusion_rules:
  - 사기 의도가 명확한 경우 형사 검토 필요
related_case_types:
  - 대여금
  - 손해배상
```

### 사용 위치
- CASE_CLASSIFICATION Node

## K2: 필수 정보·질문 기준 DB

### 목적
"무엇을 반드시 물어봐야 하는가"를 고정

### 문서 구조
```yaml
doc_id: K2-CIVIL-CONTRACT-REQ-001
knowledge_type: K2
main_case_type: 민사
sub_case_type: 계약
required_fields:
  - field: incident_date
    label: 사건 발생일
    required: true
  - field: counterparty
    label: 계약 상대방
    required: true
question_templates:
  incident_date: "계약 또는 문제가 발생한 시점을 알려주세요."
  counterparty: "계약 상대방은 누구인가요?"
```

### 사용 위치
- FACT_COLLECTION Node (필수 필드 조회)
- VALIDATION Node (필수 필드 검증)
- RE_QUESTION Node (질문 템플릿)

## K3: 법률 판단 보조 기준 DB

### 목적
상담 가능/불가·주의 사안 판단을 위한 기준 제공

### 문서 구조
```yaml
doc_id: K3-CIVIL-CONTRACT-RISK-001
knowledge_type: K3
main_case_type: 민사
sub_case_type: 계약
risk_checks:
  - condition: incident_date > 10년 경과
    flag: 소멸시효_의심
    message: "사건 발생 시점으로 보아 시효 문제 검토 필요"
non_advisory_notice:
  - 본 시스템은 법률 자문을 제공하지 않음
```

### 사용 위치
- COMPLETED Node (리스크 태그)

## K4: 출력·요약 포맷 기준 DB

### 목적
변호사·상담사에게 전달되는 결과를 항상 동일한 구조로 출력

### 문서 구조
```yaml
doc_id: K4-SUMMARY-FORMAT-001
knowledge_type: K4
output_format:
  title: 사건 요약
  sections:
    - 사건 유형
    - 핵심 사실관계
    - 금액 및 증거
style_rules:
  - 감정 표현 배제
  - 추측 표현 금지
```

### 사용 위치
- SUMMARY Node

## Chunking 전략

| 문서 타입 | Chunk 기준 |
|----------|-----------|
| K1 | 사건 유형 1개 = 1 Chunk |
| K2 | 사건 유형별 필수 질문 세트 |
| K3 | 리스크 기준 3~5개 단위 |
| K4 | 포맷 1개 = 1 Chunk |

## 검색 전략

### 메타데이터 필터링
검색 시 다음 필터를 사용하여 필요한 문서만 조회:

```python
{
    "knowledge_type": "K2",
    "main_case_type": "민사",
    "sub_case_type": "계약",
    "node_scope": "FACT_COLLECTION"
}
```

### 검색 흐름
1. 쿼리 텍스트를 Embedding으로 변환
2. 벡터 유사도 검색
3. 메타데이터 필터 적용
4. 유사도 점수 기반 랭킹
5. 상위 N개 결과 반환

## 인덱싱 프로세스

1. 문서 로드 (YAML/JSON)
2. 메타데이터 추출 및 검증
3. Chunking (타입별 전략 적용)
4. Embedding 생성
5. 벡터 DB에 저장 (메타데이터 포함)

