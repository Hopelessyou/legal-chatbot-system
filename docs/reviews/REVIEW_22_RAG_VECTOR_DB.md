# RAG Vector DB 검토 보고서

## 검토 대상
- 파일: `src/rag/vector_db.py`
- 검토 일자: 2024년
- 검토 범위: ChromaDB 연결, 문서 추가/검색, 컬렉션 관리, 메타데이터 필터링

---

## ✅ 정상 동작 부분

### 1. ChromaDB 초기화 (Lines 22-44)
```python
def _initialize(self):
    if settings.vector_db_type == "chroma":
        db_path = Path(settings.vector_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
```
- ✅ PersistentClient 사용으로 데이터 영속성 보장
- ✅ 디렉토리 자동 생성
- ✅ 설정 옵션 명시

### 2. 컬렉션 관리 (Lines 46-127)
- ✅ `get_or_create_collection`: 컬렉션 획득/생성
- ✅ `get_collection`: 컬렉션 획득
- ✅ `delete_collection`: 컬렉션 삭제
- ✅ `list_collections`: 컬렉션 목록 조회
- ✅ 컬렉션 캐싱 (`self.collections`)

### 3. 헬스체크 (Lines 129-142)
```python
def health_check(self) -> bool:
    try:
        self.client.heartbeat()
        return True
    except Exception as e:
        logger.error(f"벡터 DB 연결 상태 확인 실패: {str(e)}")
        return False
```
- ✅ 연결 상태 확인 메서드 제공

### 4. 전역 인스턴스 (Line 146)
```python
vector_db_manager = VectorDBManager()
```
- ✅ 싱글톤 패턴으로 인스턴스 재사용

---

## ⚠️ 발견된 문제점

### 1. 문서 추가/검색 메서드 없음
**영향도**: 높음  
**문제**: 
- `VectorDBManager`에 문서 추가(`add_documents`) 및 검색(`search`) 메서드가 없음
- 실제 사용은 `pipeline.py`와 `searcher.py`에서 직접 `collection.add()`와 `collection.query()` 호출
- 추상화 레벨이 낮아 유지보수 어려움

**현재 코드**: 문서 추가/검색 메서드 없음

**권장 수정**:
```python
def add_documents(
    self,
    collection_name: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    """문서 추가"""
    collection = self.get_or_create_collection(collection_name)
    
    # 메타데이터 정리 (ChromaDB는 리스트를 허용하지 않음)
    if metadatas:
        cleaned_metadatas = []
        for metadata in metadatas:
            cleaned = self._clean_metadata(metadata)
            cleaned_metadatas.append(cleaned)
    else:
        cleaned_metadatas = None
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=cleaned_metadatas
    )
    logger.debug(f"문서 추가 완료: {collection_name}, {len(ids)}개")

def search(
    self,
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None,
    where_document: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """문서 검색"""
    collection = self.get_collection(collection_name)
    if not collection:
        raise ValueError(f"컬렉션을 찾을 수 없습니다: {collection_name}")
    
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where,
        where_document=where_document
    )
    return results

@staticmethod
def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """ChromaDB 메타데이터 정리 (리스트 제거)"""
    cleaned = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            # 리스트를 문자열로 변환
            cleaned[key] = str(value)
        elif isinstance(value, (dict, bool)):
            # dict와 bool도 문자열로 변환
            cleaned[key] = str(value)
        else:
            cleaned[key] = value
    return cleaned
```

### 2. 메타데이터 정리 로직 없음
**영향도**: 중간  
**문제**: 
- ChromaDB는 메타데이터에서 리스트, dict, bool 타입을 허용하지 않음
- 현재 `pipeline.py`에서 `_clean_metadata`를 별도로 구현
- 중복 코드 및 일관성 부족

**권장 수정**: `VectorDBManager`에 `_clean_metadata` 메서드 추가

### 3. 에러 처리 개선 필요
**영향도**: 중간  
**문제**: 
- 일부 메서드에서 예외 발생 시 `raise`만 함
- 사용자 친화적인 에러 메시지 부족
- 재시도 로직 없음

**현재 코드**:
```python
except Exception as e:
    logger.error(f"컬렉션 생성 실패: {name} - {str(e)}")
    raise
```

**권장 수정**:
```python
except chromadb.errors.InvalidCollectionException as e:
    logger.error(f"유효하지 않은 컬렉션: {name} - {str(e)}")
    raise ValueError(f"컬렉션 생성 실패: {name}") from e
except Exception as e:
    logger.error(f"컬렉션 생성 실패: {name} - {str(e)}", exc_info=True)
    raise
```

### 4. 컬렉션 캐싱 동기화 문제
**영향도**: 낮음  
**문제**: 
- `get_collection`에서 컬렉션을 찾으면 캐시에 추가하지만
- 외부에서 컬렉션을 삭제하거나 수정하면 캐시가 동기화되지 않음

**권장 수정**: 캐시 무효화 메서드 추가
```python
def invalidate_collection_cache(self, name: Optional[str] = None):
    """컬렉션 캐시 무효화"""
    if name:
        if name in self.collections:
            del self.collections[name]
    else:
        self.collections.clear()
```

### 5. 클라이언트 None 체크 없음
**영향도**: 중간  
**문제**: 
- `self.client`가 None일 경우 AttributeError 발생 가능
- 초기화 실패 시에도 메서드 호출 가능

**권장 수정**:
```python
def get_or_create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> chromadb.Collection:
    if self.client is None:
        raise RuntimeError("벡터 DB 클라이언트가 초기화되지 않았습니다.")
    ...
```

### 6. close() 메서드 없음
**영향도**: 낮음  
**문제**: 
- 리소스 정리 메서드 없음
- 애플리케이션 종료 시 명시적 정리 불가

**권장 수정**:
```python
def close(self):
    """벡터 DB 연결 종료"""
    if self.client:
        # ChromaDB PersistentClient는 명시적 close가 필요 없을 수 있음
        # 하지만 리소스 정리를 위해 메서드 제공
        self.collections.clear()
        logger.info("벡터 DB 연결 종료")
```

### 7. 컬렉션 존재 여부 확인 메서드 없음
**영역도**: 낮음  
**문제**: 
- 컬렉션이 존재하는지 확인하는 메서드 없음
- `get_collection`이 None을 반환하지만 명시적 체크 메서드가 더 명확

**권장 수정**:
```python
def collection_exists(self, name: str) -> bool:
    """컬렉션 존재 여부 확인"""
    if name in self.collections:
        return True
    
    try:
        self.client.get_collection(name)
        return True
    except Exception:
        return False
```

### 8. 배치 작업 지원 없음
**영역도**: 낮음  
**문제**: 
- 대량 문서 추가 시 배치 처리 메서드 없음
- 성능 최적화 기회 상실

**권장 수정**: 배치 크기 파라미터 추가

### 9. 트랜잭션 지원 없음
**영역도**: 낮음  
**문제**: 
- 여러 문서 추가 시 원자성 보장 불가
- 일부 실패 시 롤백 불가

**참고**: ChromaDB는 트랜잭션을 지원하지 않으므로 이는 제한사항

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 배치 크기 최적화
- 인덱싱 전략
- 메모리 사용량

### 2. 백업 및 복구
- 데이터 백업 전략
- 복구 메커니즘

### 3. 모니터링
- 컬렉션 크기 추적
- 검색 성능 모니터링

---

## 📊 종합 평가

### 강점
1. ✅ ChromaDB PersistentClient 사용
2. ✅ 컬렉션 관리 메서드 제공
3. ✅ 헬스체크 메서드 제공
4. ✅ 컬렉션 캐싱

### 개선 필요
1. 🔴 **높음**: 문서 추가/검색 메서드 추가
2. 🟡 **중간**: 메타데이터 정리 로직 통합
3. 🟡 **중간**: 에러 처리 개선
4. 🟡 **중간**: 클라이언트 None 체크
5. 🟢 **낮음**: 컬렉션 캐싱 동기화
6. 🟢 **낮음**: close() 메서드 추가
7. 🟢 **낮음**: 컬렉션 존재 여부 확인 메서드
8. 🟢 **낮음**: 배치 작업 지원

### 우선순위
- **높음**: 문서 추가/검색 메서드 추가
- **중간**: 메타데이터 정리 로직 통합, 에러 처리 개선, 클라이언트 None 체크
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 문서 추가/검색 메서드 추가
```python
def add_documents(
    self,
    collection_name: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None
):
    """문서 추가"""
    if self.client is None:
        raise RuntimeError("벡터 DB 클라이언트가 초기화되지 않았습니다.")
    
    collection = self.get_or_create_collection(collection_name)
    
    # 메타데이터 정리
    if metadatas:
        cleaned_metadatas = [self._clean_metadata(m) for m in metadatas]
    else:
        cleaned_metadatas = None
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=cleaned_metadatas
    )
    logger.debug(f"문서 추가 완료: {collection_name}, {len(ids)}개")

def search(
    self,
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None,
    where_document: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """문서 검색"""
    if self.client is None:
        raise RuntimeError("벡터 DB 클라이언트가 초기화되지 않았습니다.")
    
    collection = self.get_collection(collection_name)
    if not collection:
        raise ValueError(f"컬렉션을 찾을 수 없습니다: {collection_name}")
    
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where,
        where_document=where_document
    )
    return results

@staticmethod
def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """ChromaDB 메타데이터 정리"""
    cleaned = {}
    for key, value in metadata.items():
        if isinstance(value, (list, dict, bool)):
            cleaned[key] = str(value)
        else:
            cleaned[key] = value
    return cleaned
```

### 수정 2: 클라이언트 None 체크
```python
def get_or_create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> chromadb.Collection:
    if self.client is None:
        raise RuntimeError("벡터 DB 클라이언트가 초기화되지 않았습니다.")
    ...
```

### 수정 3: close() 메서드 추가
```python
def close(self):
    """벡터 DB 연결 종료"""
    if self.client:
        self.collections.clear()
        logger.info("벡터 DB 연결 종료")
```

---

## ✅ 검토 완료

**검토 항목**: `review_22_rag_vector_db`  
**상태**: 완료  
**다음 항목**: `review_23_rag_searcher`

