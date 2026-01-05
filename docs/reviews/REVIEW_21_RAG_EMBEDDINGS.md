# RAG Embeddings 검토 보고서

## 검토 대상
- 파일: `src/rag/embeddings.py`
- 검토 일자: 2024년
- 검토 범위: 임베딩 생성, 캐싱, 벡터 변환

---

## ✅ 정상 동작 부분

### 1. 다중 모델 지원 (Lines 27-59)
```python
class EmbeddingModel:
    def _initialize(self):
        if "text-embedding" in self.model_name.lower() or "openai" in self.model_name.lower():
            # OpenAI Embeddings
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model_type = "openai"
        else:
            # Sentence Transformers
            self.model = SentenceTransformer(self.model_name)
            self.model_type = "sentence_transformers"
```
- ✅ OpenAI Embeddings와 Sentence Transformers 모두 지원
- ✅ 모델 이름에 따른 자동 분기
- ✅ Import 에러 처리

### 2. 배치 처리 지원 (Lines 61-97)
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    ...
    embeddings = self.model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True
    )
```
- ✅ 단일 텍스트와 리스트 모두 처리
- ✅ 배치 크기 설정 가능
- ✅ NumPy 배열 반환

### 3. 쿼리 전용 메서드 (Lines 99-109)
```python
def encode_query(self, query: str) -> np.ndarray:
    """쿼리 텍스트를 벡터로 변환"""
    return self.encode(query)[0]
```
- ✅ 쿼리용 편의 메서드 제공

### 4. 전역 인스턴스 (Line 113)
```python
embedding_model = EmbeddingModel()
```
- ✅ 싱글톤 패턴으로 모델 재사용
- ✅ 메모리 효율적

---

## ⚠️ 발견된 문제점

### 1. 캐싱 메커니즘 없음
**영향도**: 높음  
**문제**: 
- 동일한 텍스트에 대해 매번 임베딩 재생성
- OpenAI API 호출 비용 증가
- Sentence Transformers도 불필요한 재계산

**현재 코드**: 캐싱 없음

**권장 수정**:
```python
from functools import lru_cache
import hashlib
import json

class EmbeddingModel:
    def __init__(self):
        self.model = None
        self.model_name = settings.embedding_model
        self._cache = {}  # 또는 Redis, DB 등
        self._initialize()
    
    def _get_cache_key(self, text: str) -> str:
        """텍스트의 캐시 키 생성"""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32, use_cache: bool = True) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        
        # 캐시 확인
        if use_cache:
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for idx, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    cached_embeddings.append((idx, self._cache[cache_key]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(idx)
            
            # 캐시된 것과 새로 생성한 것 병합
            if uncached_texts:
                new_embeddings = self._encode_uncached(uncached_texts, batch_size)
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    cache_key = self._get_cache_key(uncached_texts[uncached_indices.index(idx)])
                    self._cache[cache_key] = embedding
                    cached_embeddings.append((idx, embedding))
            
            # 인덱스 순서대로 정렬
            cached_embeddings.sort(key=lambda x: x[0])
            return np.array([emb for _, emb in cached_embeddings])
        else:
            return self._encode_uncached(texts, batch_size)
```

### 2. OpenAI API 에러 처리 부족
**영향도**: 중간  
**문제**: 
- Rate limit, Timeout 등 구체적인 에러 처리 없음
- 재시도 로직 없음

**현재 코드**:
```python
try:
    response = self.client.embeddings.create(
        model=self.model_name,
        input=texts
    )
    embeddings = [item.embedding for item in response.data]
    return np.array(embeddings)
except Exception as e:
    logger.error(f"Embedding 생성 실패: {str(e)}")
    raise
```

**권장 수정**:
```python
from openai import RateLimitError, APIError
import time

def encode(self, texts: Union[str, List[str]], batch_size: int = 32, max_retries: int = 3) -> np.ndarray:
    ...
    if self.model_type == "openai":
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
                return np.array(embeddings)
            except RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limit 도달, {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
            except APIError as e:
                logger.error(f"OpenAI API 오류: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)
            except Exception as e:
                logger.error(f"Embedding 생성 실패: {str(e)}")
                raise
```

### 3. 빈 텍스트 처리 없음
**영향도**: 중간  
**문제**: 
- 빈 문자열이나 None에 대한 처리 없음
- OpenAI API는 빈 문자열을 허용하지 않을 수 있음

**권장 수정**:
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    
    # 빈 텍스트 필터링
    valid_texts = []
    valid_indices = []
    for idx, text in enumerate(texts):
        if text and isinstance(text, str) and text.strip():
            valid_texts.append(text.strip())
            valid_indices.append(idx)
        else:
            logger.warning(f"빈 텍스트 건너뜀: 인덱스 {idx}")
    
    if not valid_texts:
        raise ValueError("유효한 텍스트가 없습니다.")
    
    # 임베딩 생성
    embeddings = self._encode_uncached(valid_texts, batch_size)
    
    # 원본 인덱스에 맞춰 결과 재배열 (빈 텍스트는 0 벡터)
    result = np.zeros((len(texts), embeddings.shape[1]))
    for i, idx in enumerate(valid_indices):
        result[idx] = embeddings[i]
    
    return result
```

### 4. 모델 타입 체크 없음 (Line 76)
**영향도**: 중간  
**문제**: 
- `self.model_type`이 초기화되지 않았을 경우 AttributeError 발생 가능

**현재 코드**:
```python
if self.model_type == "openai":
    ...
```

**권장 수정**:
```python
if not hasattr(self, 'model_type'):
    raise RuntimeError("Embedding 모델이 초기화되지 않았습니다.")

if self.model_type == "openai":
    ...
```

### 5. 전역 인스턴스 초기화 시점
**영향도**: 낮음  
**문제**: 
- 모듈 임포트 시 즉시 초기화 (Line 113)
- 설정이 없거나 잘못된 경우 애플리케이션 시작 실패

**현재 코드**:
```python
embedding_model = EmbeddingModel()  # 모듈 임포트 시 즉시 실행
```

**권장 수정**: Lazy initialization
```python
_embedding_model_instance = None

def get_embedding_model() -> EmbeddingModel:
    """Embedding 모델 싱글톤 인스턴스 반환 (Lazy initialization)"""
    global _embedding_model_instance
    if _embedding_model_instance is None:
        _embedding_model_instance = EmbeddingModel()
    return _embedding_model_instance

# 하위 호환성을 위한 별칭
embedding_model = property(lambda self: get_embedding_model())
```

### 6. 배치 크기 검증 없음
**영향도**: 낮음  
**문제**: 
- `batch_size`가 0 이하이거나 너무 큰 값에 대한 검증 없음
- OpenAI API는 배치 크기 제한이 있을 수 있음

**권장 수정**:
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if batch_size <= 0:
        raise ValueError(f"batch_size는 1 이상이어야 합니다: {batch_size}")
    
    # OpenAI API 배치 크기 제한
    if self.model_type == "openai" and batch_size > 2048:
        logger.warning(f"OpenAI API 배치 크기 제한으로 2048로 조정: {batch_size}")
        batch_size = 2048
    ...
```

### 7. 텍스트 길이 제한 없음
**영향도**: 낮음  
**문제**: 
- OpenAI Embeddings API는 입력 텍스트 길이 제한이 있음 (일반적으로 8192 토큰)
- 제한 초과 시 에러 발생

**권장 수정**:
```python
MAX_TEXT_LENGTH = 8000  # 토큰 기준으로 약 6000자

def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    
    # 텍스트 길이 검증 및 자르기
    if self.model_type == "openai":
        texts = [text[:MAX_TEXT_LENGTH] if len(text) > MAX_TEXT_LENGTH else text for text in texts]
    ...
```

### 8. NumPy 배열 차원 불일치 가능성
**영향도**: 낮음  
**문제**: 
- 단일 텍스트 입력 시 `[0]` 인덱싱으로 1차원 배열 반환
- 리스트 입력 시 2차원 배열 반환
- 일관성 부족

**현재 코드**:
```python
def encode_query(self, query: str) -> np.ndarray:
    return self.encode(query)[0]  # 1차원 배열
```

**권장 수정**: 항상 2차원 배열 반환 후 필요시 squeeze
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    ...
    # 항상 2차원 배열 반환
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    return embeddings

def encode_query(self, query: str) -> np.ndarray:
    result = self.encode(query)
    return result[0] if result.ndim == 2 else result
```

### 9. 로깅 개선 필요
**영역도**: 낮음  
**문제**: 
- 임베딩 생성 성공 시 로깅 없음
- 배치 처리 진행 상황 로깅 없음

**권장 수정**:
```python
logger.debug(f"임베딩 생성: {len(texts)}개 텍스트, 배치 크기: {batch_size}")
```

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 배치 크기 최적화
- GPU 사용 여부 확인 (Sentence Transformers)
- 비동기 처리 (OpenAI API)

### 2. 모니터링
- 임베딩 생성 시간 측정
- API 호출 횟수 및 비용 추적
- 캐시 히트율

### 3. 모델 버전 관리
- 모델 버전 변경 시 캐시 무효화
- 여러 모델 동시 지원

---

## 📊 종합 평가

### 강점
1. ✅ OpenAI와 Sentence Transformers 모두 지원
2. ✅ 배치 처리 지원
3. ✅ 전역 인스턴스로 모델 재사용
4. ✅ 쿼리 전용 메서드 제공

### 개선 필요
1. 🔴 **높음**: 캐싱 메커니즘 추가
2. 🟡 **중간**: OpenAI API 에러 처리 및 재시도
3. 🟡 **중간**: 빈 텍스트 처리
4. 🟡 **중간**: 모델 타입 체크
5. 🟢 **낮음**: Lazy initialization
6. 🟢 **낮음**: 배치 크기 검증
7. 🟢 **낮음**: 텍스트 길이 제한
8. 🟢 **낮음**: NumPy 배열 차원 일관성
9. 🟢 **낮음**: 로깅 개선

### 우선순위
- **높음**: 캐싱 메커니즘 추가
- **중간**: OpenAI API 에러 처리, 빈 텍스트 처리, 모델 타입 체크
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 캐싱 메커니즘 추가
```python
class EmbeddingModel:
    def __init__(self):
        self.model = None
        self.model_name = settings.embedding_model
        self._cache = {}
        self._cache_size_limit = 10000  # 캐시 크기 제한
        self._initialize()
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32, use_cache: bool = True) -> np.ndarray:
        # 캐시 확인 및 생성 로직
        ...
```

### 수정 2: OpenAI API 에러 처리
```python
from openai import RateLimitError, APIError
import time

def encode(self, texts: Union[str, List[str]], batch_size: int = 32, max_retries: int = 3) -> np.ndarray:
    if self.model_type == "openai":
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(...)
                ...
            except RateLimitError as e:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit, {wait_time}초 대기...")
                time.sleep(wait_time)
            except APIError as e:
                logger.error(f"OpenAI API 오류: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)
```

### 수정 3: 빈 텍스트 처리
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    
    # 빈 텍스트 필터링
    valid_texts = [text.strip() for text in texts if text and isinstance(text, str) and text.strip()]
    if not valid_texts:
        raise ValueError("유효한 텍스트가 없습니다.")
    ...
```

### 수정 4: 모델 타입 체크
```python
def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
    if not hasattr(self, 'model_type'):
        raise RuntimeError("Embedding 모델이 초기화되지 않았습니다.")
    ...
```

---

## ✅ 검토 완료

**검토 항목**: `review_21_rag_embeddings`  
**상태**: 완료  
**다음 항목**: `review_22_rag_vector_db`

