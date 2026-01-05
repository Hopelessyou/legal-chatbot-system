# RAG 데이터 검토 보고서

## 개요

본 문서는 `data/rag/` 디렉토리의 RAG 문서 구조, YAML 형식, 메타데이터, 데이터 품질을 검토한 결과를 정리합니다.

**검토 일시**: 2025-01-XX  
**검토 범위**: `data/rag/` 디렉토리 내 모든 YAML 파일

---

## 1. 디렉토리 구조 분석

### 1.1 현재 디렉토리 구조

```
data/rag/
├── K0_intake/
│   └── intake_messages.yaml
├── K1_case_type/
│   ├── admin/ (5개 파일)
│   ├── civil/ (8개 파일)
│   ├── criminal/ (8개 파일)
│   └── family/ (4개 파일)
├── K2_required_fields/
│   ├── admin/ (13개 파일)
│   ├── civil/ (40개 파일)
│   ├── criminal/ (29개 파일)
│   └── family/ (15개 파일)
├── K3_risk_rules/
│   ├── admin/ (13개 파일)
│   ├── civil/ (40개 파일)
│   ├── criminal/ (29개 파일)
│   └── family/ (15개 파일)
├── K4_output_format/
│   ├── k4_counselor_summary.yaml
│   ├── k4_crm_summary.yaml
│   ├── k4_internal_brief.yaml
│   └── k4_lawyer_summary.yaml
├── common/
│   └── facts/ (97개 파일)
├── k1/ (소문자, 2개 파일)
├── k2/ (소문자, 1개 파일)
├── k3/ (소문자, 1개 파일)
└── k4/ (소문자, 1개 파일)
```

### 1.2 디렉토리 구조 문제점

#### 🔴 중요: 대소문자 불일치

**문제점**:
- 대문자 디렉토리: `K0_intake/`, `K1_case_type/`, `K2_required_fields/`, `K3_risk_rules/`, `K4_output_format/`
- 소문자 디렉토리: `k1/`, `k2/`, `k3/`, `k4/`
- 두 가지 구조가 혼재되어 있음

**영향도**: 높음  
**위험성**: 
- 인덱싱 시 일부 파일이 누락될 수 있음
- 디렉토리 구조가 일관되지 않아 유지보수 어려움
- 파일 탐색 시 혼란 가능성

**수정 권장**:
1. 소문자 디렉토리 (`k1/`, `k2/`, `k3/`, `k4/`)의 파일들을 대문자 디렉토리로 이동
2. 또는 소문자 디렉토리 삭제 (중복 파일인 경우)
3. 디렉토리 명명 규칙 통일:
   - `K0_intake/` (K0)
   - `K1_case_type/` (K1)
   - `K2_required_fields/` (K2)
   - `K3_risk_rules/` (K3)
   - `K4_output_format/` (K4)
   - `common/facts/` (FACT)

---

## 2. YAML 파일 형식 검토

### 2.1 파일 통계

- **총 파일 수**: 약 326개 YAML 파일
- **K0**: 1개
- **K1**: 약 25개 (대문자 디렉토리) + 2개 (소문자 디렉토리)
- **K2**: 약 97개 (대문자 디렉토리) + 1개 (소문자 디렉토리)
- **K3**: 약 97개 (대문자 디렉토리) + 1개 (소문자 디렉토리)
- **K4**: 4개 (대문자 디렉토리) + 1개 (소문자 디렉토리)
- **FACT**: 97개

### 2.2 YAML 형식 일관성

#### ✅ 잘 구성된 파일

1. **K0_intake/intake_messages.yaml**
   - 메타데이터 구조 일관적
   - `doc_id`, `knowledge_type`, `node_scope`, `version` 필수 필드 포함
   - `messages` 배열 구조 명확

2. **K1_case_type/civil/civil_contract_classification.yaml**
   - 메타데이터 구조 일관적
   - `level1`, `level2_code`, `level2_name` 필드 포함
   - `scenarios` 배열 구조 명확
   - `typical_keywords`, `typical_expressions` 포함

3. **K2_required_fields/civil/contract_nonpayment_required.yaml**
   - 메타데이터 구조 일관적
   - `required_fields` 배열 구조 명확
   - `questions` 배열에 `order`, `field`, `question`, `answer_type`, `required` 필드 포함

4. **K3_risk_rules/civil/contract_nonpayment_risk.yaml**
   - 메타데이터 구조 일관적
   - `rules` 배열에 `rule_code`, `trigger_facts`, `risk_level`, `risk_tag`, `description`, `action_hint` 포함

5. **K4_output_format/k4_counselor_summary.yaml**
   - 메타데이터 구조 일관적
   - `target` 필드 포함
   - `sections` 배열 구조 명확

6. **common/facts/contract_nonpayment_facts.yaml**
   - 메타데이터 구조 일관적
   - `facts` 배열에 `fact_code`, `name`, `description`, `critical`, `related_field` 포함

#### ⚠️ 형식 불일치 가능성

**문제점**:
- 소문자 디렉토리 (`k1/`, `k2/`, `k3/`, `k4/`)의 파일들이 대문자 디렉토리와 다른 형식을 사용할 수 있음

**확인 필요**:
- `k1/k1_civil_contract.yaml` 파일은 `main_case_type`, `sub_case_type` 필드를 사용 (대문자 디렉토리는 `level1`, `level2_code` 사용)
- `k2/k2_civil_contract.yaml` 파일은 `main_case_type`, `sub_case_type` 필드를 사용 (대문자 디렉토리는 `level1`, `level2` 사용)

**수정 권장**:
1. 모든 파일의 메타데이터 필드명 통일:
   - `level1` (또는 `main_case_type`)
   - `level2_code` (또는 `sub_case_type`)
   - `scenario` (시나리오 코드)
2. Pydantic 스키마와 일치하도록 필드명 통일

---

## 3. 메타데이터 검토

### 3.1 필수 메타데이터 필드

모든 RAG 문서는 다음 메타데이터를 포함해야 합니다:

| 필드 | 필수 여부 | 설명 | 예시 |
|-----|---------|------|------|
| `doc_id` | 필수 | 문서 고유 ID | `K1-CIVIL-CIVIL_CONTRACT` |
| `knowledge_type` | 필수 | 지식 타입 | `K1`, `K2`, `K3`, `K4`, `FACT` |
| `node_scope` | 선택 | 사용 가능한 LangGraph Node 목록 | `["CASE_CLASSIFICATION"]` |
| `version` | 선택 | 문서 버전 | `v1.0` |
| `last_updated` | 선택 | 마지막 업데이트 시간 | `2025-01-01T00:00:00Z` |

### 3.2 지식 타입별 추가 메타데이터

#### K1 문서
- `level1`: 주 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
- `level2_code`: 세부 사건 유형 코드 (CIVIL_CONTRACT 등)
- `level2_name`: 세부 사건 유형 이름 (계약 등)
- `scenarios`: 시나리오 목록

#### K2 문서
- `level1`: 주 사건 유형
- `level2`: 세부 사건 유형
- `scenario`: 시나리오 코드
- `required_fields`: 필수 필드 목록
- `questions`: 질문 목록

#### K3 문서
- `level1`: 주 사건 유형
- `level2`: 세부 사건 유형
- `scenario`: 시나리오 코드
- `rules`: 리스크 규칙 목록

#### K4 문서
- `target`: 대상 (COUNSELOR, LAWYER, CRM, INTERNAL)
- `sections`: 섹션 목록

#### FACT 문서
- `level1`: 주 사건 유형
- `level2`: 세부 사건 유형
- `scenario`: 시나리오 코드
- `facts`: 사실 패턴 목록

### 3.3 메타데이터 일관성 문제

#### 🟡 중요: 필드명 불일치

**문제점**:
- 일부 파일은 `main_case_type`, `sub_case_type` 사용
- 일부 파일은 `level1`, `level2_code`, `level2_name` 사용
- 일부 파일은 `level1`, `level2` 사용

**영향도**: 중간  
**위험성**: 
- Pydantic 스키마 검증 실패 가능성
- 검색 필터링 시 필드명 불일치로 인한 오류

**수정 권장**:
1. 모든 파일의 메타데이터 필드명을 Pydantic 스키마와 일치시키기
2. `main_case_type` → `level1` (또는 스키마에 `main_case_type` 추가)
3. `sub_case_type` → `level2_code` (또는 스키마에 `sub_case_type` 추가)

---

## 4. 데이터 품질 검토

### 4.1 YAML 문법 검증

#### ✅ 대부분의 파일이 유효한 YAML 형식

**확인 사항**:
- YAML 문법 오류 없음
- 인코딩: UTF-8
- 들여쓰기 일관적

### 4.2 필수 필드 누락 가능성

#### 🟡 중요: 일부 파일에 필수 필드 누락 가능

**확인 필요**:
- 모든 파일에 `doc_id` 필드 존재 여부
- 모든 파일에 `knowledge_type` 필드 존재 여부
- `doc_id`가 `knowledge_type`으로 시작하는지 확인

**수정 권장**:
1. YAML 파일 검증 스크립트 작성:
   ```python
   def validate_rag_document(file_path: Path) -> bool:
       """RAG 문서 검증"""
       data = yaml.safe_load(file_path)
       
       # 필수 필드 확인
       required_fields = ["doc_id", "knowledge_type"]
       for field in required_fields:
           if field not in data:
               logger.error(f"필수 필드 누락: {field} in {file_path}")
               return False
       
       # doc_id 형식 확인
       if not data["doc_id"].startswith(data["knowledge_type"]):
           logger.error(f"doc_id 형식 오류: {data['doc_id']} in {file_path}")
           return False
       
       return True
   ```

### 4.3 데이터 일관성

#### ✅ 대부분의 데이터가 일관적

**확인 사항**:
- 시나리오 코드 일관성 (K1, K2, K3, FACT 간 매칭)
- 필드명 일관성 (K2의 `required_fields`와 FACT의 `related_field` 매칭)
- 질문 템플릿 일관성

#### 🟡 중요: 시나리오 코드 매칭 확인 필요

**확인 필요**:
- K1의 `scenario_code`와 K2의 `scenario` 매칭
- K2의 `scenario`와 K3의 `scenario` 매칭
- K2의 `scenario`와 FACT의 `scenario` 매칭

**수정 권장**:
1. 시나리오 코드 매칭 검증 스크립트 작성
2. 누락된 시나리오 파일 확인

---

## 5. 파일 구조 및 명명 규칙

### 5.1 파일명 규칙

#### ✅ 대부분의 파일이 일관된 명명 규칙 사용

**현재 명명 규칙**:
- K1: `{level1}_{level2_code}_classification.yaml` (예: `civil_contract_classification.yaml`)
- K2: `{scenario}_required.yaml` (예: `contract_nonpayment_required.yaml`)
- K3: `{scenario}_risk.yaml` (예: `contract_nonpayment_risk.yaml`)
- K4: `k4_{target}_summary.yaml` (예: `k4_counselor_summary.yaml`)
- FACT: `{scenario}_facts.yaml` (예: `contract_nonpayment_facts.yaml`)

#### ⚠️ 일부 파일명 불일치

**문제점**:
- 소문자 디렉토리의 파일명: `k1_civil_contract.yaml`, `k2_civil_contract.yaml` 등
- 대문자 디렉토리의 파일명과 다른 형식

**수정 권장**:
1. 모든 파일명을 통일된 규칙으로 변경
2. 또는 소문자 디렉토리 파일을 대문자 디렉토리로 이동 후 삭제

---

## 6. 데이터 검증 권장 사항

### 6.1 자동 검증 스크립트

#### 권장: `scripts/validate_rag_documents.py` 생성

```python
"""
RAG 문서 검증 스크립트
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any
from src.rag.schema import RAGDocumentMetadata

def validate_all_documents(rag_dir: Path) -> Dict[str, List[str]]:
    """
    모든 RAG 문서 검증
    
    Returns:
        {"errors": [...], "warnings": [...]}
    """
    errors = []
    warnings = []
    
    for yaml_file in rag_dir.rglob("*.yaml"):
        try:
            # YAML 파싱
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 필수 필드 확인
            if "doc_id" not in data:
                errors.append(f"{yaml_file}: doc_id 필수 필드 누락")
            
            if "knowledge_type" not in data:
                errors.append(f"{yaml_file}: knowledge_type 필수 필드 누락")
            
            # doc_id 형식 확인
            if "doc_id" in data and "knowledge_type" in data:
                if not data["doc_id"].startswith(data["knowledge_type"]):
                    errors.append(
                        f"{yaml_file}: doc_id ({data['doc_id']})가 "
                        f"knowledge_type ({data['knowledge_type']})로 시작하지 않음"
                    )
            
            # 메타데이터 스키마 검증
            try:
                metadata = RAGDocumentMetadata(**data)
            except Exception as e:
                errors.append(f"{yaml_file}: 메타데이터 검증 실패 - {str(e)}")
            
        except yaml.YAMLError as e:
            errors.append(f"{yaml_file}: YAML 파싱 오류 - {str(e)}")
        except Exception as e:
            errors.append(f"{yaml_file}: 검증 중 오류 - {str(e)}")
    
    return {"errors": errors, "warnings": warnings}
```

### 6.2 시나리오 코드 매칭 검증

#### 권장: 시나리오 코드 일관성 검증

```python
def validate_scenario_matching(rag_dir: Path) -> Dict[str, List[str]]:
    """
    K1, K2, K3, FACT 간 시나리오 코드 매칭 검증
    """
    k1_scenarios = set()
    k2_scenarios = set()
    k3_scenarios = set()
    fact_scenarios = set()
    
    # K1 시나리오 수집
    for k1_file in (rag_dir / "K1_case_type").rglob("*.yaml"):
        # ...
    
    # K2 시나리오 수집
    for k2_file in (rag_dir / "K2_required_fields").rglob("*.yaml"):
        # ...
    
    # 매칭 확인
    missing_k2 = k1_scenarios - k2_scenarios
    missing_k3 = k1_scenarios - k3_scenarios
    missing_fact = k1_scenarios - fact_scenarios
    
    return {
        "missing_k2": list(missing_k2),
        "missing_k3": list(missing_k3),
        "missing_fact": list(missing_fact)
    }
```

---

## 7. 개선 권장 사항

### 7.1 즉시 개선 (높은 우선순위)

1. **디렉토리 구조 통일**
   - 소문자 디렉토리 (`k1/`, `k2/`, `k3/`, `k4/`) 제거 또는 대문자 디렉토리로 통합
   - 모든 파일을 대문자 디렉토리 구조로 이동

2. **메타데이터 필드명 통일**
   - 모든 파일의 메타데이터 필드명을 Pydantic 스키마와 일치시키기
   - `main_case_type` → `level1` 또는 스키마 수정
   - `sub_case_type` → `level2_code` 또는 스키마 수정

3. **파일 검증 스크립트 작성**
   - YAML 문법 검증
   - 필수 필드 확인
   - 메타데이터 스키마 검증
   - 시나리오 코드 매칭 검증

### 7.2 단기 개선 (중간 우선순위)

4. **문서화 개선**
   - 각 디렉토리의 README.md 추가
   - 파일명 규칙 문서화
   - 메타데이터 필드 설명 문서화

5. **데이터 품질 개선**
   - 누락된 시나리오 파일 추가
   - 질문 템플릿 일관성 개선
   - 필드명 일관성 개선

### 7.3 장기 개선 (낮은 우선순위)

6. **자동화 도구**
   - Excel → YAML 변환 스크립트 개선
   - 자동 검증 CI/CD 통합
   - 데이터 마이그레이션 스크립트

---

## 8. 검토 요약

### 8.1 데이터 현황

- **총 파일 수**: 약 326개 YAML 파일
- **디렉토리 구조**: 대부분 일관적, 일부 대소문자 불일치
- **YAML 형식**: 대부분 유효
- **메타데이터**: 대부분 일관적, 일부 필드명 불일치

### 8.2 발견된 문제

- 🔴 **높음**: 디렉토리 구조 대소문자 불일치 (2개)
- 🟡 **중간**: 메타데이터 필드명 불일치 (1개)
- 🟡 **중간**: 시나리오 코드 매칭 확인 필요 (1개)
- 🟢 **낮음**: 파일명 규칙 일부 불일치 (1개)

### 8.3 우선순위별 수정 권장

1. 🔴 **높음**: 디렉토리 구조 통일 (즉시)
2. 🟡 **중간**: 메타데이터 필드명 통일 (단기)
3. 🟡 **중간**: 파일 검증 스크립트 작성 (단기)
4. 🟢 **낮음**: 문서화 개선 (장기)

---

## 9. 결론

RAG 데이터는 전반적으로 잘 구성되어 있으며, 약 326개의 YAML 파일이 체계적으로 정리되어 있습니다. 다만, **디렉토리 구조의 대소문자 불일치**와 **메타데이터 필드명 불일치** 문제를 해결하면 데이터 품질이 크게 향상될 것입니다.

**우선순위**:
1. 🔴 **높음**: 디렉토리 구조 통일 (즉시)
2. 🟡 **중간**: 메타데이터 필드명 통일 (단기)
3. 🟡 **중간**: 파일 검증 스크립트 작성 (단기)

**참고**: 
- 대부분의 파일이 유효한 YAML 형식
- 메타데이터 구조가 잘 정의되어 있음
- 시나리오별로 체계적으로 분류되어 있음
- 파일 수가 많아 자동 검증 도구가 필요함

