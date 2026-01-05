# RAG Schema 검토 보고서

## 검토 대상
- 파일: `src/rag/schema.py`
- 검토 일자: 2024년
- 검토 범위: 문서 메타데이터 스키마, K1~K4 문서 구조, Pydantic 모델

---

## ✅ 정상 동작 부분

### 1. Pydantic 모델 구조 (Lines 9-93)
```python
class RAGDocumentMetadata(BaseModel):
    """RAG 문서 메타데이터 스키마"""
    doc_id: str = Field(..., description="문서 고유 ID")
    knowledge_type: Literal["K0", "K1", "K2", "K3", "K4", "FACT"] = Field(..., description="지식 타입")
    ...
```
- ✅ Pydantic BaseModel 사용으로 타입 검증 및 직렬화 지원
- ✅ Field를 사용한 필드 설명 및 기본값 설정
- ✅ Literal 타입으로 knowledge_type 제한
- ✅ Optional 타입으로 선택적 필드 명시

### 2. 문서 타입별 스키마 정의
- ✅ **K1Document**: 사건 유형 기준 문서 구조
- ✅ **K2Document**: 필수 정보·질문 기준 문서 구조
- ✅ **K3Document**: 법률 판단 보조 기준 문서 구조
- ✅ **K4Document**: 출력·요약 포맷 기준 문서 구조
- ✅ **FACTDocument**: 사실 패턴 기준 문서 구조

### 3. 필드 검증 (Lines 19-46)
```python
@field_validator('doc_id')
@classmethod
def validate_doc_id(cls, v: str, info) -> str:
    """doc_id 형식 검증"""
    if hasattr(info, 'data') and 'knowledge_type' in info.data:
        kt = info.data['knowledge_type']
        if not v.startswith(kt):
            raise ValueError(f"doc_id는 {kt}로 시작해야 합니다")
    return v
```
- ✅ doc_id가 knowledge_type으로 시작하는지 검증
- ✅ node_scope가 유효한 노드 목록인지 검증

### 4. 메타데이터 공통화
- ✅ 모든 문서 타입이 `RAGDocumentMetadata`를 공통으로 사용
- ✅ 일관된 메타데이터 구조

---

## ⚠️ 발견된 문제점

### 1. K0 문서 스키마 없음
**영향도**: 중간  
**문제**: 
- `RAGDocumentMetadata`에 `knowledge_type: Literal["K0", "K1", "K2", "K3", "K4", "FACT"]`로 K0가 포함되어 있음
- 하지만 `K0Document` 클래스가 정의되지 않음
- `parser.py`에서 K0는 `return data`로 딕셔너리 그대로 반환 (Line 226)

**현재 코드**:
```python
# schema.py에 K0Document 클래스 없음
# parser.py
if knowledge_type == "K0":
    # K0는 간단한 구조이므로 그대로 반환
    return data
```

**권장 수정**:
```python
class K0Document(BaseModel):
    """K0 문서 구조 (초기 인테이크 메시지 기준)"""
    metadata: RAGDocumentMetadata
    messages: List[dict] = Field(..., description="인테이크 메시지 목록")
    # 또는 다른 K0 특정 필드들
```

### 2. Pydantic v2 field_validator 호환성 문제 (Lines 21-28)
**영향도**: 중간  
**문제**: 
- `field_validator`에서 `info.data`로 다른 필드에 접근하는 방식이 Pydantic v2에서 변경될 수 있음
- `info` 객체의 구조가 Pydantic 버전에 따라 다를 수 있음

**현재 코드**:
```python
@field_validator('doc_id')
@classmethod
def validate_doc_id(cls, v: str, info) -> str:
    if hasattr(info, 'data') and 'knowledge_type' in info.data:
        kt = info.data['knowledge_type']
        if not v.startswith(kt):
            raise ValueError(f"doc_id는 {kt}로 시작해야 합니다")
    return v
```

**권장 수정**:
```python
@field_validator('doc_id')
@classmethod
def validate_doc_id(cls, v: str, info) -> str:
    """doc_id 형식 검증"""
    # Pydantic v2에서는 ValidationInfo를 사용
    if hasattr(info, 'data'):
        kt = info.data.get('knowledge_type')
    else:
        # Pydantic v1 호환성
        return v
    
    if kt and not v.startswith(kt):
        raise ValueError(f"doc_id는 {kt}로 시작해야 합니다")
    return v
```

또는 `model_validator`를 사용하여 전체 모델 검증:
```python
from pydantic import model_validator

@model_validator(mode='after')
def validate_doc_id_format(self):
    """doc_id가 knowledge_type으로 시작하는지 검증"""
    if not self.doc_id.startswith(self.knowledge_type):
        raise ValueError(f"doc_id는 {self.knowledge_type}로 시작해야 합니다")
    return self
```

### 3. List[dict] 타입 검증 부족
**영향도**: 낮음  
**문제**: 
- `scenarios`, `questions`, `rules`, `sections`, `facts` 등이 `List[dict]`로 정의됨
- 딕셔너리 내부 구조에 대한 검증이 없음
- 런타임에 잘못된 구조로 인한 오류 가능

**현재 코드**:
```python
scenarios: List[dict] = Field(..., description="시나리오 목록")
questions: List[dict] = Field(..., description="질문 목록")
rules: List[dict] = Field(..., description="리스크 규칙 목록")
sections: List[dict] = Field(..., description="섹션 목록")
facts: List[dict] = Field(..., description="사실 패턴 목록")
```

**권장 수정**: 중첩된 Pydantic 모델 정의
```python
class Scenario(BaseModel):
    scenario_code: str
    scenario_name: str
    keywords: List[str]
    typical_expressions: Optional[List[str]] = None
    disambiguation_question: Optional[str] = None
    disambiguation_options: Optional[str] = None

class K1Document(BaseModel):
    metadata: RAGDocumentMetadata
    scenarios: List[Scenario] = Field(..., description="시나리오 목록")
    ...
```

### 4. node_scope 하드코딩 (Lines 34-42)
**영향도**: 낮음  
**문제**: 
- `valid_nodes` 리스트가 하드코딩됨
- 노드가 추가/변경될 때 수정 필요

**현재 코드**:
```python
valid_nodes = [
    "INIT",
    "CASE_CLASSIFICATION",
    "FACT_COLLECTION",
    "VALIDATION",
    "RE_QUESTION",
    "SUMMARY",
    "COMPLETED"
]
```

**권장 수정**: 상수로 분리
```python
from src.utils.constants import VALID_LANGGRAPH_NODES

@field_validator('node_scope')
@classmethod
def validate_node_scope(cls, v: List[str]) -> List[str]:
    """node_scope 유효성 검증"""
    for node in v:
        if node not in VALID_LANGGRAPH_NODES:
            raise ValueError(f"유효하지 않은 Node: {node}")
    return v
```

### 5. datetime.utcnow() 사용 (Line 17)
**영향도**: 낮음  
**문제**: 
- `datetime.utcnow()`는 Python 3.12+에서 deprecated
- `datetime.now(timezone.utc)` 사용 권장

**현재 코드**:
```python
last_updated: datetime = Field(default_factory=datetime.utcnow, description="마지막 업데이트 시간")
```

**권장 수정**:
```python
from datetime import datetime, timezone

last_updated: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    description="마지막 업데이트 시간"
)
```

### 6. K1Document에 typical_keywords 필드 누락
**영향도**: 낮음  
**문제**: 
- `parser.py` Line 111에서 `typical_keywords`를 사용하지만
- `schema.py` Line 56에는 `typical_keywords` 필드가 없음 (Line 57에 `typical_expressions`만 있음)

**현재 코드**:
```python
# schema.py Line 56
typical_expressions: Optional[List[str]] = Field(None, description="전체 대표 표현")
# typical_keywords 필드 없음

# parser.py Line 111
typical_keywords=data.get("typical_keywords"),
```

**권장 수정**:
```python
class K1Document(BaseModel):
    """K1 문서 구조 (사건 유형 기준)"""
    metadata: RAGDocumentMetadata
    level1: Optional[str] = Field(None, description="LEVEL1 분류")
    level2_code: Optional[str] = Field(None, description="LEVEL2 코드")
    level2_name: Optional[str] = Field(None, description="LEVEL2 이름")
    scenarios: List[dict] = Field(..., description="시나리오 목록")
    typical_keywords: Optional[List[str]] = Field(None, description="전체 대표 키워드")
    typical_expressions: Optional[List[str]] = Field(None, description="전체 대표 표현")
```

### 7. 필드 설명 부족
**영향도**: 낮음  
**문제**: 
- 일부 필드의 description이 간단하거나 없음
- 예: `level1`, `level2`, `scenario` 등

**권장 수정**: 더 자세한 description 추가

---

## 🔍 추가 검토 사항

### 1. 스키마 버전 관리
- 현재: `version: str = Field(default="v1.0", ...)`
- 권장: 버전별 스키마 마이그레이션 전략

### 2. 스키마 확장성
- 새로운 knowledge_type 추가 시 스키마 확장 방법
- 하위 호환성 유지 전략

### 3. 실제 데이터와의 일치성
- 실제 YAML 파일 구조와 스키마 일치 여부 확인 필요
- 예: K1 문서의 `scenarios` 구조가 실제 데이터와 일치하는지

### 4. 검증 에러 메시지
- 검증 실패 시 사용자 친화적인 에러 메시지 제공

---

## 📊 종합 평가

### 강점
1. ✅ Pydantic 모델 사용으로 타입 안정성 확보
2. ✅ 필드 검증 로직 포함
3. ✅ 메타데이터 공통화
4. ✅ 문서 타입별 명확한 구조 정의

### 개선 필요
1. 🟡 **중간**: K0 문서 스키마 추가
2. 🟡 **중간**: Pydantic v2 호환성 개선
3. 🟢 **낮음**: 중첩된 구조에 대한 타입 검증 강화
4. 🟢 **낮음**: 하드코딩된 상수 분리
5. 🟢 **낮음**: datetime.utcnow() 대체
6. 🟢 **낮음**: K1Document에 typical_keywords 필드 추가

### 우선순위
- **중간**: K0 문서 스키마 추가, Pydantic v2 호환성 개선
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: K0 문서 스키마 추가
```python
class K0Document(BaseModel):
    """K0 문서 구조 (초기 인테이크 메시지 기준)"""
    metadata: RAGDocumentMetadata
    messages: List[dict] = Field(..., description="인테이크 메시지 목록")
    # 또는 실제 K0 구조에 맞게 필드 정의
```

### 수정 2: Pydantic v2 호환성 개선
```python
from pydantic import model_validator

class RAGDocumentMetadata(BaseModel):
    ...
    
    @model_validator(mode='after')
    def validate_doc_id_format(self):
        """doc_id가 knowledge_type으로 시작하는지 검증"""
        if not self.doc_id.startswith(self.knowledge_type):
            raise ValueError(f"doc_id는 {self.knowledge_type}로 시작해야 합니다")
        return self
```

### 수정 3: K1Document에 typical_keywords 추가
```python
class K1Document(BaseModel):
    ...
    typical_keywords: Optional[List[str]] = Field(None, description="전체 대표 키워드")
    typical_expressions: Optional[List[str]] = Field(None, description="전체 대표 표현")
```

### 수정 4: datetime.utcnow() 대체
```python
from datetime import datetime, timezone

last_updated: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    description="마지막 업데이트 시간"
)
```

---

## ✅ 검토 완료

**검토 항목**: `review_18_rag_schema`  
**상태**: 완료  
**다음 항목**: `review_19_rag_parser`

