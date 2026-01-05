# 성능 검토 보고서

## 검토 대상
- 전체 시스템 성능
- 검토 일자: 2024년
- 검토 범위: DB 쿼리 최적화, 캐싱 전략, API 응답 시간, GPT 호출 최적화

---

## ✅ 정상 동작 부분

### 1. 병렬 처리
- ✅ `fact_collection_node`에서 `ThreadPoolExecutor` 사용
- ✅ 엔티티 추출, 사실/감정 분리, RAG 검색을 병렬 처리
- ✅ GPT 호출 병렬화로 응답 시간 단축

### 2. 데이터베이스 인덱스
- ✅ 주요 컬럼에 인덱스 추가됨 (이전 검토에서 확인)
- ✅ 복합 인덱스 사용 (예: `idx_missing_unresolved`)
- ✅ 연결 풀 설정 (`pool_size=5`, `max_overflow=10`)

### 3. 캐싱
- ✅ 질문 템플릿 캐싱: `question_loader`에서 `_questions_cache` 사용
- ✅ Embedding 모델 싱글톤: 한 번만 로드하여 재사용

### 4. API 응답 시간 측정
- ✅ 미들웨어에서 응답 시간 측정 및 헤더 추가
- ✅ `X-Process-Time` 헤더로 모니터링 가능

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: N+1 쿼리 문제

**문제**: `load_session_state()`에서 여러 개별 쿼리를 순차적으로 실행합니다.

**영향도**: 중간  
**위험성**: 
- 세션 상태 로드 시 4-5개의 개별 쿼리 실행
- 대량 세션 처리 시 성능 저하

**현재 상황**:
```python
# load_session_state()에서:
1. ChatSession 조회
2. CaseMaster 조회
3. CaseFact 조회 (all())
4. CaseParty 조회
5. CaseEvidence 조회
```

**수정 권장**: 
```python
# SQLAlchemy의 joinedload 또는 selectinload 사용
from sqlalchemy.orm import joinedload, selectinload

session = db_session.query(ChatSession).options(
    joinedload(ChatSession.case).joinedload(CaseMaster.facts),
    joinedload(ChatSession.case).joinedload(CaseMaster.parties),
    joinedload(ChatSession.case).joinedload(CaseMaster.evidences)
).filter(
    ChatSession.session_id == session_id
).first()
```

---

### 2. 🟡 **중간**: GPT 호출 캐싱 부재

**문제**: 동일한 입력에 대한 GPT 호출 결과가 캐싱되지 않습니다.

**영향도**: 중간  
**위험성**: 
- 동일한 질문에 대한 반복 호출로 비용 증가
- 응답 시간 지연

**현재 상황**:
- GPT 호출마다 API 요청 발생
- 캐싱 메커니즘 없음

**수정 권장**: 
```python
# 간단한 인메모리 캐시 (개발용)
from functools import lru_cache
import hashlib

def _get_cache_key(messages: List[Dict], temperature: float) -> str:
    """캐시 키 생성"""
    content = str(messages) + str(temperature)
    return hashlib.md5(content.encode()).hexdigest()

# 또는 Redis 사용 (프로덕션)
# from redis import Redis
# redis_client = Redis(...)
```

---

### 3. 🟢 **낮음**: RAG 검색 결과 캐싱 부재

**문제**: 동일한 쿼리에 대한 RAG 검색 결과가 캐싱되지 않습니다.

**영향도**: 낮음  
**위험성**: 
- 동일한 쿼리 반복 검색으로 임베딩 계산 반복
- 검색 시간 지연

**현재 상황**:
- RAG 검색마다 벡터 DB 쿼리 및 임베딩 계산
- 캐싱 메커니즘 없음

**수정 권장**: 
```python
# RAG 검색 결과 캐싱
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_rag_search(query: str, knowledge_type: str, case_type: str):
    """RAG 검색 결과 캐싱"""
    return rag_searcher.search(query, ...)
```

---

### 4. 🟢 **낮음**: DB 쿼리 최적화 여지

**문제**: 일부 쿼리에서 불필요한 데이터 로드가 발생할 수 있습니다.

**영향도**: 낮음  
**위험성**: 
- 전체 컬럼 로드로 메모리 사용량 증가
- 네트워크 트래픽 증가

**현재 상황**:
- `query().all()` 또는 `query().first()`로 전체 객체 로드
- 필요한 컬럼만 선택하는 최적화 없음

**수정 권장**: 
```python
# 필요한 컬럼만 선택
from sqlalchemy import select

result = db_session.execute(
    select(CaseFact.incident_date, CaseFact.amount)
    .where(CaseFact.case_id == case_id)
    .order_by(CaseFact.created_at.desc())
).first()
```

---

### 5. 🟢 **낮음**: 프롬프트 템플릿 캐싱

**문제**: `prompt_loader`는 파일에서 매번 읽지만, `prompt_builder`는 초기화 시 한 번만 로드합니다.

**영향도**: 낮음  
**현재 상황**:
- `prompt_loader.load_prompt()`: 매번 파일 읽기
- `prompt_builder._load_templates()`: 초기화 시 한 번만 로드

**수정 권장**: 
- `prompt_loader`도 메모리 캐싱 추가 (선택적)

---

### 6. 🟢 **낮음**: API 응답 시간 최적화

**문제**: 비동기 엔드포인트에서 동기 작업을 실행하여 블로킹 발생 가능.

**영향도**: 낮음  
**위험성**: 
- 동시 요청 처리 성능 저하
- 이벤트 루프 블로킹

**현재 상황**:
- `async def process_message()` 내부에서 `run_graph_step()` (동기) 호출
- `save_session_state()` (동기) 호출

**수정 권장**: 
```python
# 동기 작업을 비동기로 실행
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def process_message(...):
    # 동기 작업을 스레드 풀에서 실행
    result = await asyncio.get_event_loop().run_in_executor(
        executor,
        run_graph_step,
        state
    )
```

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 2개 (N+1 쿼리 문제, GPT 호출 캐싱 부재)
- 🟢 **낮음**: 4개 (RAG 검색 캐싱, DB 쿼리 최적화, 프롬프트 캐싱, API 응답 시간)

### 우선순위별 수정 권장
1. 🟡 **중간**: N+1 쿼리 문제 해결 (권장)
2. 🟡 **중간**: GPT 호출 캐싱 추가 (권장)
3. 🟢 **낮음**: RAG 검색 결과 캐싱 (선택적)
4. 🟢 **낮음**: DB 쿼리 최적화 (선택적)
5. 🟢 **낮음**: 프롬프트 템플릿 캐싱 개선 (선택적)
6. 🟢 **낮음**: API 응답 시간 최적화 (선택적)

---

## 🔧 수정 제안

### 수정 1: N+1 쿼리 문제 해결

#### `src/services/session_manager.py` 수정
```python
from sqlalchemy.orm import joinedload, selectinload

@staticmethod
def load_session_state(session_id: str) -> Optional[StateContext]:
    """세션 상태 로드 (최적화)"""
    try:
        with db_manager.get_db_session() as db_session:
            # Eager Loading으로 N+1 문제 해결
            session = db_session.query(ChatSession).options(
                joinedload(ChatSession.case).selectinload(CaseMaster.facts),
                joinedload(ChatSession.case).selectinload(CaseMaster.parties),
                joinedload(ChatSession.case).selectinload(CaseMaster.evidences)
            ).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                return None
            
            # ... 기존 로직 ...
```

---

### 수정 2: GPT 호출 캐싱 추가

#### `src/services/gpt_client.py` 수정
```python
from functools import lru_cache
import hashlib
import json

class GPTClient:
    def __init__(self, ...):
        # ... 기존 초기화 ...
        self._cache = {}  # 간단한 인메모리 캐시
    
    def _get_cache_key(self, messages: List[Dict], temperature: float) -> str:
        """캐시 키 생성"""
        cache_data = {
            "messages": messages,
            "temperature": temperature,
            "model": self.model
        }
        content = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def chat_completion(self, messages, temperature=0.7, max_tokens=None, use_cache=True, **kwargs):
        """Chat Completion API 호출 (캐싱 지원)"""
        if use_cache:
            cache_key = self._get_cache_key(messages, temperature)
            if cache_key in self._cache:
                logger.debug("GPT 호출 캐시 히트")
                return self._cache[cache_key]
        
        # API 호출
        result = self._retry_with_backoff(...)
        
        if use_cache:
            self._cache[cache_key] = result
            # 캐시 크기 제한 (최대 100개)
            if len(self._cache) > 100:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
        
        return result
```

---

### 수정 3: RAG 검색 결과 캐싱 (선택적)

#### `src/rag/searcher.py` 수정
```python
from functools import lru_cache
import hashlib

class RAGSearcher:
    def __init__(self):
        # ... 기존 초기화 ...
        self._search_cache = {}
    
    def _get_cache_key(self, query: str, knowledge_type: str, case_type: str) -> str:
        """캐시 키 생성"""
        content = f"{query}:{knowledge_type}:{case_type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def search(self, query: str, top_k: int = 5, knowledge_type: str = "K1", 
               main_case_type: str = None, sub_case_type: str = None,
               node_scope: str = None, min_score: float = 0.0, use_cache: bool = True):
        """RAG 검색 (캐싱 지원)"""
        if use_cache:
            cache_key = self._get_cache_key(query, knowledge_type, main_case_type or "")
            if cache_key in self._search_cache:
                logger.debug("RAG 검색 캐시 히트")
                return self._search_cache[cache_key]
        
        # 검색 실행
        results = self._execute_search(...)
        
        if use_cache:
            self._search_cache[cache_key] = results
            # 캐시 크기 제한
            if len(self._search_cache) > 200:
                oldest_key = next(iter(self._search_cache))
                del self._search_cache[oldest_key]
        
        return results
```

---

### 수정 4: 프롬프트 로더 캐싱 개선 (선택적)

#### `src/services/prompt_loader.py` 수정
```python
class PromptLoader:
    def __init__(self, prompts_dir: Optional[Path] = None):
        # ... 기존 초기화 ...
        self._prompt_cache = {}  # 프롬프트 템플릿 캐시
    
    def load_prompt(self, template_name: str, sub_dir: str = "summary") -> Optional[str]:
        """프롬프트 템플릿 로드 (캐싱)"""
        cache_key = f"{sub_dir}/{template_name}"
        
        # 캐시 확인
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        # 파일에서 로드
        prompt_path = self.prompts_dir / sub_dir / f"{template_name}.txt"
        
        if not prompt_path.exists():
            logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
            return None
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 캐시에 저장
        self._prompt_cache[cache_key] = content
        
        logger.debug(f"프롬프트 로드 완료: {template_name}")
        return content
```

---

## 📈 성능 벤치마크 권장

### 측정 항목
1. **API 응답 시간**: 평균, P50, P95, P99
2. **DB 쿼리 시간**: 쿼리별 실행 시간
3. **GPT 호출 시간**: 평균 응답 시간
4. **RAG 검색 시간**: 평균 검색 시간
5. **동시 요청 처리**: 초당 요청 수 (RPS)

### 모니터링 도구
- APM (Application Performance Monitoring) 도구 사용 권장
- 예: New Relic, Datadog, Prometheus + Grafana

---

## ✅ 결론

전체 시스템 성능은 전반적으로 잘 구성되어 있지만, **N+1 쿼리 문제**와 **캐싱 전략** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: N+1 쿼리 문제 해결 (권장)
2. 🟡 **중간**: GPT 호출 캐싱 추가 (권장)
3. 🟢 **낮음**: RAG 검색 결과 캐싱 (선택적)
4. 🟢 **낮음**: DB 쿼리 최적화 (선택적)
5. 🟢 **낮음**: 프롬프트 템플릿 캐싱 개선 (선택적)
6. 🟢 **낮음**: API 응답 시간 최적화 (선택적)

**참고**: 
- 병렬 처리는 이미 잘 구현되어 있음
- 데이터베이스 인덱스는 적절히 설정됨
- 미들웨어에서 응답 시간 측정 및 모니터링 가능
- GPT 호출 비용 절감을 위해 캐싱 추가 권장

