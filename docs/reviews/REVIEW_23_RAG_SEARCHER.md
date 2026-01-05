# RAG Searcher 검토 보고서

## 검토 대상
- 파일: `src/rag/searcher.py`
- 검토 일자: 2024년
- 검토 범위: 검색 로직, 쿼리 변환, 결과 정렬, 필터링

---

## ✅ 정상 동작 부분

### 1. 검색 메서드 구조 (Lines 27-117)
```python
def search(
    self,
    query: str,
    top_k: int = 5,
    knowledge_type: Optional[str] = None,
    main_case_type: Optional[str] = None,
    sub_case_type: Optional[str] = None,
    node_scope: Optional[str] = None,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
```
- ✅ 다양한 필터 옵션 제공
- ✅ 최소 점수 필터링
- ✅ 결과 포맷팅 및 정렬

### 2. 편의 메서드 (Lines 119-189)
- ✅ `search_by_knowledge_type`: 지식 타입별 검색
- ✅ `search_by_case_type`: 사건 유형별 검색
- ✅ `search_by_node_scope`: Node 범위별 검색

### 3. 메타데이터 필터 구성 (Lines 56-76)
```python
where_conditions = []
if knowledge_type:
    where_conditions.append({"knowledge_type": knowledge_type})
...
where = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0] if where_conditions else None
```
- ✅ ChromaDB 필터 형식에 맞게 구성
- ✅ 단일 조건과 다중 조건 처리

### 4. 점수 계산 및 정렬 (Lines 95-109)
```python
score = 1.0 - distance if distance is not None else 0.0
if score >= min_score:
    formatted_results.append({...})
formatted_results.sort(key=lambda x: x["score"], reverse=True)
```
- ✅ distance를 score로 변환
- ✅ 최소 점수 필터링
- ✅ 점수 순 정렬

### 5. 전역 인스턴스 (Line 193)
```python
rag_searcher = RAGSearcher()
```
- ✅ 싱글톤 패턴으로 인스턴스 재사용

---

## ⚠️ 발견된 문제점

### 1. node_scope 필터 미구현 (Lines 64-68)
**영향도**: 중간  
**문제**: 
- `node_scope` 파라미터가 있지만 실제로 필터링하지 않음
- 주석에 "일단 제외"라고만 표시
- ChromaDB는 배열 필드 직접 매칭이 어렵다는 제약

**현재 코드**:
```python
if node_scope:
    # node_scope는 리스트이므로 $in 사용 또는 각 요소 확인
    # ChromaDB는 배열 필드에 대해 직접 매칭이 어려우므로 일단 제외
    # 필요시 메타데이터에 별도 필드로 저장하는 것을 권장
    pass
```

**권장 수정**:
```python
if node_scope:
    # node_scope는 메타데이터에 문자열로 저장되어 있으므로 문자열 매칭
    # 예: "['CASE_CLASSIFICATION', 'FACT_COLLECTION']" 형태
    # 또는 별도 필드로 저장 (예: has_case_classification: true)
    where_conditions.append({"node_scope": {"$contains": node_scope}})
    # 또는 메타데이터 구조 변경하여 각 노드를 별도 필드로 저장
```

또는 메타데이터 구조 변경:
```python
# chunker.py에서 메타데이터 저장 시
metadata = {
    ...
    "has_init": "INIT" in doc.metadata.node_scope,
    "has_case_classification": "CASE_CLASSIFICATION" in doc.metadata.node_scope,
    ...
}
```

### 2. 빈 쿼리 처리 없음 (Line 54)
**영향도**: 중간  
**문제**: 
- 빈 문자열이나 None 쿼리에 대한 검증 없음
- `embedding_model.encode_query("")` 호출 시 불필요한 임베딩 생성

**권장 수정**:
```python
def search(self, query: str, ...):
    if not query or not query.strip():
        logger.warning("빈 쿼리로 검색 시도")
        return []
    
    query = query.strip()
    ...
```

### 3. 결과 인덱싱 안전성 부족 (Lines 88-93)
**영역도**: 중간  
**문제**: 
- `results["ids"][0][i]` 접근 시 인덱스 범위 체크 없음
- `results["ids"]`가 빈 리스트이거나 구조가 다를 경우 IndexError 발생 가능

**현재 코드**:
```python
if results["ids"] and len(results["ids"][0]) > 0:
    for i in range(len(results["ids"][0])):
        doc_id = results["ids"][0][i]
        distance = results["distances"][0][i] if results["distances"] else None
```

**권장 수정**:
```python
if results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
    ids = results["ids"][0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    
    for i in range(len(ids)):
        doc_id = ids[i]
        distance = distances[i] if i < len(distances) else None
        metadata = metadatas[i] if i < len(metadatas) else {}
        document = documents[i] if i < len(documents) else ""
        ...
```

### 4. 컬렉션 None 체크 없음 (Line 79)
**영역도**: 중간  
**문제**: 
- `self.collection`이 None일 경우 AttributeError 발생 가능
- 초기화 실패 시에도 검색 시도 가능

**권장 수정**:
```python
def search(self, ...):
    if self.collection is None:
        raise RuntimeError("RAG 컬렉션이 초기화되지 않았습니다.")
    ...
```

### 5. 에러 처리 개선 필요 (Lines 115-117)
**영역도**: 낮음  
**문제**: 
- 모든 예외를 동일하게 처리
- 구체적인 에러 타입별 처리 없음

**권장 수정**:
```python
except ValueError as e:
    logger.error(f"검색 파라미터 오류: {str(e)}")
    raise
except Exception as e:
    logger.error(f"RAG 검색 실패: {str(e)}", exc_info=True)
    raise
```

### 6. top_k 검증 없음 (Line 30)
**영역도**: 낮음  
**문제**: 
- `top_k`가 0 이하이거나 너무 큰 값에 대한 검증 없음

**권장 수정**:
```python
def search(self, query: str, top_k: int = 5, ...):
    if top_k <= 0:
        raise ValueError(f"top_k는 1 이상이어야 합니다: {top_k}")
    if top_k > 100:
        logger.warning(f"top_k가 너무 큽니다: {top_k}, 100으로 제한")
        top_k = 100
    ...
```

### 7. min_score 검증 없음 (Line 35)
**영역도**: 낮음  
**문제**: 
- `min_score`가 0.0~1.0 범위를 벗어날 수 있음

**권장 수정**:
```python
def search(self, ..., min_score: float = 0.0):
    if not 0.0 <= min_score <= 1.0:
        raise ValueError(f"min_score는 0.0~1.0 범위여야 합니다: {min_score}")
    ...
```

### 8. 로깅 레벨 개선
**영역도**: 낮음  
**문제**: 
- 검색 성공 시 `debug` 레벨로만 로깅
- 중요한 검색은 `info` 레벨이 적절

**권장 수정**:
```python
logger.info(f"검색 완료: 쿼리='{query[:50]}...', 결과={len(formatted_results)}개, 필터={where}")
```

### 9. 검색 결과 캐싱 없음
**영역도**: 낮음  
**문제**: 
- 동일한 쿼리와 필터에 대해 매번 검색 수행
- 성능 최적화 기회 상실

**권장 수정**: 쿼리 캐싱 메커니즘 추가 (선택적)

### 10. 검색 결과 제한 없음
**영역도**: 낮음  
**문제**: 
- `top_k`만으로 제한하지만, 실제 반환되는 결과 수에 대한 제한 없음
- 대량 결과 반환 시 메모리 문제 가능

---

## 🔍 추가 검토 사항

### 1. 검색 성능
- 쿼리 최적화
- 인덱싱 전략
- 배치 검색 지원

### 2. 검색 품질
- 유사도 임계값 튜닝
- 결과 다양성
- 관련성 점수 개선

### 3. 하이브리드 검색
- 키워드 검색과 벡터 검색 결합
- BM25 등 전통적 검색 알고리즘 활용

---

## 📊 종합 평가

### 강점
1. ✅ 다양한 필터 옵션 제공
2. ✅ 편의 메서드 제공
3. ✅ 결과 포맷팅 및 정렬
4. ✅ 점수 계산 및 필터링

### 개선 필요
1. 🟡 **중간**: node_scope 필터 구현
2. 🟡 **중간**: 빈 쿼리 처리
3. 🟡 **중간**: 결과 인덱싱 안전성
4. 🟡 **중간**: 컬렉션 None 체크
5. 🟢 **낮음**: 에러 처리 개선
6. 🟢 **낮음**: 파라미터 검증 (top_k, min_score)
7. 🟢 **낮음**: 로깅 레벨 개선
8. 🟢 **낮음**: 검색 결과 캐싱

### 우선순위
- **중간**: node_scope 필터 구현, 빈 쿼리 처리, 결과 인덱싱 안전성, 컬렉션 None 체크
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 빈 쿼리 처리
```python
def search(self, query: str, ...):
    if not query or not query.strip():
        logger.warning("빈 쿼리로 검색 시도")
        return []
    
    query = query.strip()
    ...
```

### 수정 2: 결과 인덱싱 안전성
```python
if results.get("ids") and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
    ids = results["ids"][0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    
    for i in range(len(ids)):
        doc_id = ids[i]
        distance = distances[i] if i < len(distances) else None
        metadata = metadatas[i] if i < len(metadatas) else {}
        document = documents[i] if i < len(documents) else ""
        ...
```

### 수정 3: 컬렉션 None 체크
```python
def search(self, ...):
    if self.collection is None:
        raise RuntimeError("RAG 컬렉션이 초기화되지 않았습니다.")
    ...
```

### 수정 4: 파라미터 검증
```python
def search(self, query: str, top_k: int = 5, ..., min_score: float = 0.0, ...):
    if not query or not query.strip():
        logger.warning("빈 쿼리로 검색 시도")
        return []
    
    if top_k <= 0:
        raise ValueError(f"top_k는 1 이상이어야 합니다: {top_k}")
    if top_k > 100:
        logger.warning(f"top_k가 너무 큽니다: {top_k}, 100으로 제한")
        top_k = 100
    
    if not 0.0 <= min_score <= 1.0:
        raise ValueError(f"min_score는 0.0~1.0 범위여야 합니다: {min_score}")
    ...
```

### 수정 5: node_scope 필터 구현
```python
# chunker.py에서 메타데이터 저장 시 각 노드를 별도 필드로 저장
# 또는 검색 시 문자열 매칭 사용

if node_scope:
    # 메타데이터에 node_scope가 문자열로 저장되어 있다고 가정
    # 예: "['CASE_CLASSIFICATION', 'FACT_COLLECTION']"
    where_conditions.append({"node_scope": {"$contains": node_scope}})
```

---

## ✅ 검토 완료

**검토 항목**: `review_23_rag_searcher`  
**상태**: 완료  
**다음 항목**: `review_24_rag_pipeline`

