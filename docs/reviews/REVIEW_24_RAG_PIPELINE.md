# RAG Pipeline 검토 보고서

## 검토 대상
- 파일: `src/rag/pipeline.py`
- 검토 일자: 2024년
- 검토 범위: 문서 인덱싱 파이프라인, 배치 처리

---

## ✅ 정상 동작 부분

### 1. 파이프라인 구조 (Lines 16-30)
```python
class RAGIndexingPipeline:
    def __init__(self, collection_name: str = "rag_documents"):
        self.collection_name = collection_name
        self.collection = None
        self.parser = RAGDocumentParser()
        self.chunker = RAGChunker()
        self._initialize_collection()
```
- ✅ 명확한 파이프라인 구조
- ✅ Parser, Chunker, VectorDB 분리
- ✅ 컬렉션 초기화

### 2. 메타데이터 정리 (Lines 32-63)
```python
@staticmethod
def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """ChromaDB 호환을 위해 metadata 정리"""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        elif isinstance(value, list):
            cleaned[key] = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            cleaned[key] = json.dumps(value, ensure_ascii=False)
        ...
```
- ✅ ChromaDB 호환성 처리
- ✅ None 값 제거
- ✅ 리스트/딕셔너리 변환

### 3. 단일 문서 인덱싱 (Lines 65-122)
```python
def index_document(self, file_path: Path) -> int:
    # 1. 파싱
    doc = self.parser.parse_document(file_path)
    # 2. 청킹
    chunks = self.chunker.chunk_document(doc)
    # 3. 임베딩 생성
    # 4. 벡터 DB 저장
```
- ✅ 명확한 단계별 처리
- ✅ 에러 처리 및 로깅

### 4. 디렉토리 인덱싱 (Lines 124-161)
```python
def index_directory(self, directory: Path, recursive: bool = True) -> int:
    # 파일 검색
    # 각 파일 인덱싱
    # 에러 발생 시 계속 진행
```
- ✅ 재귀적 검색 지원
- ✅ 개별 파일 실패 시에도 계속 진행
- ✅ 총 Chunk 개수 반환

### 5. 컬렉션 초기화 (Lines 163-171)
```python
def clear_collection(self):
    """컬렉션 초기화"""
    vector_db_manager.delete_collection(self.collection_name)
    self._initialize_collection()
```
- ✅ 컬렉션 초기화 메서드 제공

---

## ⚠️ 발견된 문제점

### 1. 배치 처리 없음
**영향도**: 높음  
**문제**: 
- 각 Chunk마다 개별적으로 임베딩 생성 (Line 93)
- 대량 문서 처리 시 비효율적
- OpenAI API 호출 비용 증가

**현재 코드**:
```python
for chunk in chunks:
    embedding_result = embedding_model.encode(chunk.content)
    embedding = embedding_result[0].tolist()
    ...
```

**권장 수정**:
```python
# 모든 Chunk의 Content를 한 번에 임베딩 생성
chunk_contents = [chunk.content for chunk in chunks]
embeddings_batch = embedding_model.encode(chunk_contents, batch_size=32)

for i, chunk in enumerate(chunks):
    if embeddings_batch.ndim == 2:
        embedding = embeddings_batch[i].tolist()
    else:
        embedding = embeddings_batch.tolist()
    ...
```

### 2. 중복 인덱싱 방지 없음
**영향도**: 중간  
**문제**: 
- 동일한 문서를 다시 인덱싱하면 중복 Chunk 생성
- `chunk_id` 중복 체크 없음

**권장 수정**:
```python
def index_document(self, file_path: Path, overwrite: bool = False) -> int:
    # 기존 Chunk 확인
    if not overwrite:
        existing_ids = self._get_existing_chunk_ids(file_path)
        if existing_ids:
            logger.warning(f"문서가 이미 인덱싱되어 있습니다: {file_path}")
            return len(existing_ids)
    ...
```

### 3. 빈 Chunk 처리 없음
**영역도**: 중간  
**문제**: 
- 빈 Content를 가진 Chunk도 인덱싱
- 불필요한 임베딩 생성 및 저장

**현재 코드**:
```python
for chunk in chunks:
    embedding_result = embedding_model.encode(chunk.content)
    # 빈 Content 체크 없음
```

**권장 수정**:
```python
for chunk in chunks:
    if not chunk.content or not chunk.content.strip():
        logger.warning(f"빈 Content Chunk 건너뜀: {chunk.chunk_id}")
        continue
    ...
```

### 4. 컬렉션 None 체크 없음 (Line 110)
**영역도**: 중간  
**문제**: 
- `self.collection`이 None일 경우 AttributeError 발생 가능

**권장 수정**:
```python
def index_document(self, file_path: Path) -> int:
    if self.collection is None:
        raise RuntimeError("RAG 컬렉션이 초기화되지 않았습니다.")
    ...
```

### 5. 파일 경로 검증 없음 (Line 65)
**영역도**: 낮음  
**문제**: 
- 파일 존재 여부, 파일 타입 확인 없음

**권장 수정**:
```python
def index_document(self, file_path: Path) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"파일이 아닙니다: {file_path}")
    ...
```

### 6. 진행 상황 추적 없음
**영역도**: 낮음  
**문제**: 
- 대량 파일 인덱싱 시 진행 상황 확인 불가
- 사용자 피드백 어려움

**권장 수정**:
```python
def index_directory(self, directory: Path, recursive: bool = True, progress_callback: Optional[Callable] = None) -> int:
    total_files = len(files)
    for idx, file_path in enumerate(files):
        if progress_callback:
            progress_callback(idx + 1, total_files, file_path)
        ...
```

### 7. 에러 복구 전략 없음
**영역도**: 낮음  
**문제**: 
- 일부 Chunk 인덱싱 실패 시 전체 롤백 없음
- 부분 실패 처리 전략 없음

**권장 수정**: 트랜잭션 또는 체크포인트 메커니즘

### 8. 임베딩 생성 실패 처리 부족
**영역도**: 낮음  
**문제**: 
- 임베딩 생성 실패 시 전체 문서 인덱싱 실패
- 개별 Chunk 실패 시에도 계속 진행하는 옵션 없음

**권장 수정**:
```python
for chunk in chunks:
    try:
        embedding_result = embedding_model.encode(chunk.content)
        ...
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {chunk.chunk_id} - {str(e)}")
        if skip_on_error:
            continue
        else:
            raise
```

### 9. 메타데이터 정리 로직 중복
**영역도**: 낮음  
**문제**: 
- `_clean_metadata`가 `VectorDBManager`에도 필요할 수 있음
- 중복 코드 가능성

**권장 수정**: 공통 유틸리티로 분리

### 10. 로깅 개선 필요
**영역도**: 낮음  
**문제**: 
- 인덱싱 성능 메트릭 로깅 없음
- 처리 시간, 처리량 등 정보 부족

**권장 수정**:
```python
import time

def index_document(self, file_path: Path) -> int:
    start_time = time.time()
    ...
    elapsed_time = time.time() - start_time
    logger.info(f"인덱싱 완료: {file_path.name} ({len(chunks)}개 Chunk, {elapsed_time:.2f}초)")
    ...
```

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 배치 크기 최적화
- 병렬 처리 (멀티프로세싱)
- 메모리 사용량 최적화

### 2. 모니터링
- 인덱싱 진행률
- 성능 메트릭
- 에러율 추적

### 3. 재인덱싱 전략
- 증분 인덱싱
- 변경 감지
- 버전 관리

---

## 📊 종합 평가

### 강점
1. ✅ 명확한 파이프라인 구조
2. ✅ 메타데이터 정리 로직
3. ✅ 디렉토리 인덱싱 지원
4. ✅ 에러 발생 시 계속 진행

### 개선 필요
1. 🔴 **높음**: 배치 처리 추가
2. 🟡 **중간**: 중복 인덱싱 방지
3. 🟡 **중간**: 빈 Chunk 처리
4. 🟡 **중간**: 컬렉션 None 체크
5. 🟢 **낮음**: 파일 경로 검증
6. 🟢 **낮음**: 진행 상황 추적
7. 🟢 **낮음**: 에러 복구 전략
8. 🟢 **낮음**: 임베딩 생성 실패 처리
9. 🟢 **낮음**: 메타데이터 정리 로직 중복 해결
10. 🟢 **낮음**: 로깅 개선

### 우선순위
- **높음**: 배치 처리 추가
- **중간**: 중복 인덱싱 방지, 빈 Chunk 처리, 컬렉션 None 체크
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 배치 처리 추가
```python
def index_document(self, file_path: Path) -> int:
    ...
    chunks = self.chunker.chunk_document(doc)
    
    if not chunks:
        logger.warning(f"Chunk가 생성되지 않았습니다: {file_path.name}")
        return 0
    
    # 배치로 임베딩 생성
    chunk_contents = [chunk.content for chunk in chunks]
    embeddings_batch = embedding_model.encode(chunk_contents, batch_size=32)
    
    chunk_ids = []
    chunk_contents_list = []
    chunk_embeddings = []
    chunk_metadatas = []
    
    for i, chunk in enumerate(chunks):
        if not chunk.content or not chunk.content.strip():
            logger.warning(f"빈 Content Chunk 건너뜀: {chunk.chunk_id}")
            continue
        
        if embeddings_batch.ndim == 2:
            embedding = embeddings_batch[i].tolist()
        else:
            embedding = embeddings_batch.tolist()
        
        cleaned_metadata = RAGIndexingPipeline._clean_metadata(chunk.metadata)
        
        chunk_ids.append(chunk.chunk_id)
        chunk_contents_list.append(chunk.content)
        chunk_embeddings.append(embedding)
        chunk_metadatas.append(cleaned_metadata)
    
    # 벡터 DB에 저장
    if chunk_ids:
        self.collection.add(
            ids=chunk_ids,
            embeddings=chunk_embeddings,
            documents=chunk_contents_list,
            metadatas=chunk_metadatas
        )
    ...
```

### 수정 2: 빈 Chunk 처리
```python
for chunk in chunks:
    if not chunk.content or not chunk.content.strip():
        logger.warning(f"빈 Content Chunk 건너뜀: {chunk.chunk_id}")
        continue
    ...
```

### 수정 3: 컬렉션 None 체크
```python
def index_document(self, file_path: Path) -> int:
    if self.collection is None:
        raise RuntimeError("RAG 컬렉션이 초기화되지 않았습니다.")
    ...
```

### 수정 4: 파일 경로 검증
```python
def index_document(self, file_path: Path) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"파일이 아닙니다: {file_path}")
    ...
```

### 수정 5: 진행 상황 추적
```python
def index_directory(self, directory: Path, recursive: bool = True, progress_callback: Optional[Callable] = None) -> int:
    ...
    for idx, file_path in enumerate(files):
        if progress_callback:
            progress_callback(idx + 1, len(files), file_path)
        try:
            chunks_count = self.index_document(file_path)
            total_chunks += chunks_count
        except Exception as e:
            logger.error(f"파일 인덱싱 실패: {file_path} - {str(e)}")
            continue
    ...
```

---

## ✅ 검토 완료

**검토 항목**: `review_24_rag_pipeline`  
**상태**: 완료  
**다음 항목**: `review_25_service_gpt_client`

