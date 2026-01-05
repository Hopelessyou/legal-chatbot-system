# RAG Chunker 검토 보고서

## 검토 대상
- 파일: `src/rag/chunker.py`
- 검토 일자: 2024년
- 검토 범위: 문서 청킹 전략, 청크 크기, 오버랩 처리

---

## ✅ 정상 동작 부분

### 1. Chunk 클래스 구조 (Lines 11-32)
```python
class Chunk:
    """Chunk 데이터 클래스"""
    def __init__(self, chunk_id: str, content: str, metadata: Dict[str, Any], chunk_index: int = 0):
        ...
    def to_dict(self) -> Dict[str, Any]:
        ...
```
- ✅ 명확한 데이터 구조
- ✅ 딕셔너리 변환 메서드 제공
- ✅ 메타데이터 포함

### 2. 문서 타입별 청킹 전략
- ✅ **K1**: 시나리오별로 개별 Chunk 생성 (의미 단위 분리)
- ✅ **K2**: 필수 필드와 질문을 하나의 Chunk로 생성
- ✅ **K3**: 리스크 규칙을 그룹화하여 Chunk 생성 (4개씩)
- ✅ **K4**: 포맷 전체를 하나의 Chunk로 생성
- ✅ **FACT**: 사실 패턴 전체를 하나의 Chunk로 생성
- ✅ **K0**: 메시지별로 개별 Chunk 생성

### 3. 자동 청킹 메서드 (Lines 441-465)
```python
@staticmethod
def chunk_document(doc: Any) -> List[Chunk]:
    """문서 타입에 따라 자동 Chunking"""
    if isinstance(doc, dict) and doc.get("knowledge_type") == "K0":
        return RAGChunker.chunk_k0_document(doc)
    elif isinstance(doc, K1Document):
        return RAGChunker.chunk_k1_document(doc)
    ...
```
- ✅ 타입에 따른 자동 분기
- ✅ 명확한 에러 메시지

### 4. 메타데이터 보존
- ✅ 모든 Chunk에 원본 문서 메타데이터 포함
- ✅ 문서 타입별 특정 필드 보존 (level1, level2, scenario 등)

---

## ⚠️ 발견된 문제점

### 1. chunk_size 하드코딩 (Line 208)
**영향도**: 중간  
**문제**: 
- K3 문서 청킹 시 `chunk_size = 4`로 하드코딩
- 설정 변경이 어려움
- 문서 타입별로 다른 청크 크기가 필요할 수 있음

**현재 코드**:
```python
chunk_size = 4
rules = doc.rules

for i in range(0, len(rules), chunk_size):
    group = rules[i:i + chunk_size]
```

**권장 수정**:
```python
# 설정 파일이나 클래스 변수로 관리
class RAGChunker:
    DEFAULT_CHUNK_SIZE = 4
    CHUNK_SIZE_BY_TYPE = {
        "K3": 4,
        # 다른 타입도 필요시 추가
    }
    
    @staticmethod
    def chunk_k3_document(doc: K3Document, chunk_size: Optional[int] = None) -> List[Chunk]:
        chunk_size = chunk_size or RAGChunker.CHUNK_SIZE_BY_TYPE.get("K3", RAGChunker.DEFAULT_CHUNK_SIZE)
        ...
```

### 2. 빈 문서 처리 부족
**영향도**: 중간  
**문제**: 
- `doc.scenarios`, `doc.questions`, `doc.rules` 등이 빈 리스트일 경우 빈 Chunk 생성
- 빈 Chunk는 검색에 도움이 되지 않음

**현재 코드**:
```python
for idx, scenario in enumerate(doc.scenarios):
    # scenarios가 빈 리스트면 chunks가 빈 리스트 반환
```

**권장 수정**:
```python
if not doc.scenarios:
    logger.warning(f"K1 문서에 시나리오가 없습니다: {doc.metadata.doc_id}")
    return []  # 또는 최소한의 Chunk 생성
```

### 3. Content 길이 제한 없음
**영향도**: 중간  
**문제**: 
- K2, K4, FACT 문서는 전체를 하나의 Chunk로 생성
- 질문이나 섹션이 많으면 매우 긴 Content 생성
- 임베딩 모델의 토큰 제한 초과 가능 (일반적으로 512~8192 토큰)

**현재 코드**:
```python
# K2: 모든 질문을 하나의 Chunk로
content = "\n".join(content_parts)  # 길이 제한 없음
```

**권장 수정**:
```python
MAX_CHUNK_LENGTH = 4000  # 토큰 기준으로 약 3000자 정도

def _split_long_content(content: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    """긴 Content를 여러 Chunk로 분할"""
    if len(content) <= max_length:
        return [content]
    
    # 문장 단위로 분할
    sentences = content.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) > max_length and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length += len(sentence) + 1
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks
```

### 4. chunk_id 중복 가능성
**영향도**: 낮음  
**문제**: 
- K1에서 `f"{doc.metadata.doc_id}-{scenario_code}-chunk-{idx}"` 사용
- scenario_code가 중복되거나 None일 경우 중복 가능

**현재 코드**:
```python
chunk_id=f"{doc.metadata.doc_id}-{scenario_code}-chunk-{idx}"
```

**권장 수정**:
```python
scenario_code = scenario.get("scenario_code", f"scenario_{idx}")
chunk_id = f"{doc.metadata.doc_id}-{scenario_code}-chunk-{idx}"
# 또는 UUID 사용
```

### 5. None 값 처리 불일치
**영역도**: 낮음  
**문제**: 
- 일부 메서드에서 `or ""` 사용 (Line 52-54)
- 일부 메서드에서 `if doc.level1:` 체크 (Line 137)
- 일관성 부족

**현재 코드**:
```python
# K1
level1 = doc.level1 or ""
# K2
if doc.level1:
    content_parts.append(f"LEVEL1: {doc.level1}")
```

**권장 수정**: 일관된 처리 방식 사용

### 6. 에러 처리 부족
**영역도**: 낮음  
**문제**: 
- 딕셔너리 접근 시 KeyError 가능
- `.get()` 사용하지만 예외 처리 없음

**권장 수정**:
```python
try:
    scenario_code = scenario.get("scenario_code", "")
    ...
except (KeyError, AttributeError, TypeError) as e:
    logger.error(f"시나리오 파싱 실패: {scenario} - {str(e)}")
    continue  # 또는 기본값 사용
```

### 7. K3 청킹에서 오버랩 없음
**영역도**: 낮음  
**문제**: 
- K3에서 규칙을 4개씩 그룹화하지만 오버랩 없음
- 경계에 있는 규칙이 분리될 수 있음

**현재 코드**:
```python
for i in range(0, len(rules), chunk_size):
    group = rules[i:i + chunk_size]  # 오버랩 없음
```

**권장 수정**: 필요 시 오버랩 추가
```python
overlap = 1  # 1개 규칙 오버랩
for i in range(0, len(rules), chunk_size - overlap):
    group = rules[i:i + chunk_size]
```

### 8. Content 포맷팅 일관성
**영역도**: 낮음  
**문제**: 
- 각 메서드에서 Content 포맷이 약간씩 다름
- 일관된 포맷이 검색 성능에 도움

**권장 수정**: 공통 포맷팅 유틸리티 함수

### 9. 빈 Content 체크 없음
**영역도**: 낮음  
**문제**: 
- Content가 빈 문자열일 경우에도 Chunk 생성
- 빈 Chunk는 검색에 도움이 되지 않음

**권장 수정**:
```python
content = "\n".join(content_parts)
if not content.strip():
    logger.warning(f"빈 Content Chunk 생성 건너뜀: {chunk_id}")
    continue
```

---

## 🔍 추가 검토 사항

### 1. 청킹 전략 최적화
- 문서 타입별 최적 청크 크기 실험
- 검색 성능과의 관계 분석

### 2. 메타데이터 최적화
- 검색에 유용한 메타데이터만 포함
- 불필요한 메타데이터 제거로 저장 공간 절약

### 3. 청킹 성능
- 대용량 문서 처리 시 성능
- 메모리 사용량 최적화

---

## 📊 종합 평가

### 강점
1. ✅ 문서 타입별 적절한 청킹 전략
2. ✅ 명확한 Chunk 데이터 구조
3. ✅ 메타데이터 보존
4. ✅ 자동 청킹 메서드

### 개선 필요
1. 🟡 **중간**: chunk_size 하드코딩
2. 🟡 **중간**: 빈 문서 처리
3. 🟡 **중간**: Content 길이 제한
4. 🟢 **낮음**: chunk_id 중복 가능성
5. 🟢 **낮음**: None 값 처리 불일치
6. 🟢 **낮음**: 에러 처리 부족
7. 🟢 **낮음**: K3 오버랩 없음
8. 🟢 **낮음**: Content 포맷팅 일관성
9. 🟢 **낮음**: 빈 Content 체크

### 우선순위
- **중간**: chunk_size 설정화, 빈 문서 처리, Content 길이 제한
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: chunk_size 설정화
```python
class RAGChunker:
    DEFAULT_CHUNK_SIZE = 4
    CHUNK_SIZE_BY_TYPE = {
        "K3": 4,
    }
    
    @staticmethod
    def chunk_k3_document(doc: K3Document, chunk_size: Optional[int] = None) -> List[Chunk]:
        chunk_size = chunk_size or RAGChunker.CHUNK_SIZE_BY_TYPE.get("K3", RAGChunker.DEFAULT_CHUNK_SIZE)
        ...
```

### 수정 2: 빈 문서 처리
```python
@staticmethod
def chunk_k1_document(doc: K1Document) -> List[Chunk]:
    if not doc.scenarios:
        logger.warning(f"K1 문서에 시나리오가 없습니다: {doc.metadata.doc_id}")
        return []
    ...
```

### 수정 3: Content 길이 제한
```python
MAX_CHUNK_LENGTH = 4000  # 문자 기준

@staticmethod
def chunk_k2_document(doc: K2Document) -> List[Chunk]:
    ...
    content = "\n".join(content_parts)
    
    if len(content) > MAX_CHUNK_LENGTH:
        # 여러 Chunk로 분할
        return RAGChunker._split_long_content(content, MAX_CHUNK_LENGTH, doc.metadata)
    
    chunk = Chunk(...)
    ...
```

### 수정 4: 에러 처리 강화
```python
@staticmethod
def chunk_k1_document(doc: K1Document) -> List[Chunk]:
    chunks = []
    
    for idx, scenario in enumerate(doc.scenarios):
        try:
            scenario_code = scenario.get("scenario_code", f"scenario_{idx}")
            ...
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"시나리오 파싱 실패: {scenario} - {str(e)}")
            continue
    ...
```

### 수정 5: 빈 Content 체크
```python
content = "\n".join(content_parts)
if not content.strip():
    logger.warning(f"빈 Content Chunk 생성 건너뜀")
    continue

chunk = Chunk(...)
```

---

## ✅ 검토 완료

**검토 항목**: `review_20_rag_chunker`  
**상태**: 완료  
**다음 항목**: `review_21_rag_embeddings`

