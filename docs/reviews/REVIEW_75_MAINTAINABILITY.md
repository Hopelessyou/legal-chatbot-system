# 유지보수성 검토 보고서

## 개요

본 문서는 전체 코드베이스의 유지보수성을 검토한 결과를 정리합니다. 모듈화, 의존성 관리, 확장성, 리팩토링 필요 영역 등을 포함합니다.

**검토 일시**: 2025-01-XX  
**검토 범위**: 전체 코드베이스 구조 및 아키텍처

---

## 1. 모듈화 검토

### 1.1 디렉토리 구조

#### ✅ 잘 구성된 모듈 구조

**현재 구조**:
```
src/
├── api/              # API 레이어
│   ├── routers/     # 라우터 모듈
│   ├── middleware.py
│   ├── auth.py
│   └── error_handler.py
├── langgraph/        # LangGraph 레이어
│   ├── nodes/       # 노드 모듈
│   ├── edges/       # 엣지 모듈
│   ├── graph.py
│   └── state.py
├── rag/              # RAG 레이어
│   ├── parser.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_db.py
│   ├── searcher.py
│   └── pipeline.py
├── services/         # 서비스 레이어
│   ├── gpt_client.py
│   ├── entity_extractor.py
│   ├── fact_emotion_splitter.py
│   ├── summarizer.py
│   └── session_manager.py
├── db/               # 데이터베이스 레이어
│   ├── models/      # 모델 모듈
│   ├── connection.py
│   └── base.py
├── utils/            # 유틸리티 모듈
│   ├── logger.py
│   ├── helpers.py
│   ├── constants.py
│   └── exceptions.py
└── types.py          # 타입 정의
```

**평가**:
- 레이어별로 명확히 분리됨
- 각 모듈의 책임이 명확함
- 디렉토리 구조가 직관적임

### 1.2 모듈 간 결합도

#### ✅ 낮은 결합도 (Loose Coupling)

**확인 사항**:
- API 레이어는 LangGraph와 Services에 의존
- LangGraph는 Services와 RAG에 의존
- Services는 독립적으로 동작 가능
- DB 레이어는 독립적

**의존성 방향**:
```
API → LangGraph → Services → DB
  ↓      ↓          ↓
  └──────┴──────────┘
         ↓
       RAG
```

**평가**: 의존성 방향이 명확하고 순환 의존성이 없음

#### ⚠️ 일부 모듈 간 강한 결합

**문제점**:
- `fact_collection_node.py`가 많은 서비스에 직접 의존
- 일부 노드가 DB 모델에 직접 의존

**예시**:
```python
# fact_collection_node.py
from src.services.entity_extractor import entity_extractor
from src.services.fact_emotion_splitter import fact_emotion_splitter
from src.rag.searcher import rag_searcher
from src.db.models.case_fact import CaseFact
from src.db.models.case_emotion import CaseEmotion
# ... 많은 의존성
```

**수정 권장**:
1. 의존성 주입(Dependency Injection) 패턴 적용
2. 인터페이스/추상 클래스 도입
3. 서비스 레이어를 통한 간접 의존

---

## 2. 의존성 관리 검토

### 2.1 순환 의존성 (Circular Dependencies)

#### ✅ 순환 의존성 없음

**확인 사항**:
- 모듈 간 순환 import 없음
- 의존성 그래프가 DAG(Directed Acyclic Graph) 구조

**평가**: 순환 의존성 문제 없음

### 2.2 전역 상태 관리

#### 🟡 중간: 전역 싱글톤 패턴 사용

**문제점**:
- 일부 서비스가 전역 인스턴스로 관리됨
- 테스트 시 모킹 어려움

**예시**:
```python
# services/entity_extractor.py
entity_extractor = EntityExtractor()

# services/fact_emotion_splitter.py
fact_emotion_splitter = FactEmotionSplitter()

# rag/searcher.py
rag_searcher = RAGSearcher()
```

**수정 권장**:
1. FastAPI의 `Depends`를 활용한 의존성 주입
2. 팩토리 패턴 적용
3. 테스트 가능한 구조로 개선

### 2.3 외부 의존성 관리

#### ✅ 잘 관리됨

**확인 사항**:
- `requirements.txt`에 의존성 명시
- `pyproject.toml`에 프로젝트 메타데이터 포함
- 버전 고정으로 안정성 확보

**평가**: 외부 의존성이 잘 관리됨

---

## 3. 확장성 검토

### 3.1 새로운 기능 추가 용이성

#### ✅ 확장 가능한 구조

**확인 사항**:
- 새로운 노드 추가 용이 (LangGraph)
- 새로운 서비스 추가 용이 (Services 레이어)
- 새로운 API 엔드포인트 추가 용이 (Routers)

**예시**:
```python
# 새로운 노드 추가
# langgraph/nodes/new_node.py
def new_node(state: StateContext) -> Dict[str, Any]:
    ...

# graph.py에 등록
graph.add_node("NEW_NODE", new_node)
```

**평가**: 확장 가능한 구조

#### 🟡 중간: 하드코딩된 값들

**문제점**:
- 일부 설정값이 하드코딩됨
- 새로운 사건 유형 추가 시 코드 수정 필요

**수정 권장**:
1. 설정 파일로 외부화
2. 플러그인 시스템 도입
3. 동적 로딩 지원

### 3.2 성능 확장성

#### ✅ 확장 가능한 구조

**확인 사항**:
- 비동기 처리 지원 (FastAPI)
- 병렬 처리 지원 (ThreadPoolExecutor)
- DB 연결 풀링 지원

**평가**: 성능 확장 가능

#### 🟡 중간: 캐싱 전략 부족

**문제점**:
- RAG 검색 결과 캐싱 없음
- GPT API 응답 캐싱 없음
- 임베딩 캐싱은 있으나 완전하지 않음

**수정 권장**:
1. Redis 등 캐시 시스템 도입
2. 응답 캐싱 전략 수립
3. 캐시 무효화 전략 수립

---

## 4. 리팩토링 필요 영역

### 4.1 즉시 리팩토링 필요 (높은 우선순위)

#### 🔴 중요: `fact_collection_node` 함수 리팩토링

**위치**: `src/langgraph/nodes/fact_collection_node.py:39-430`
**길이**: 약 390줄

**문제점**:
- 함수가 너무 길어 가독성 저하
- 단일 책임 원칙(SRP) 위반
- 테스트 및 디버깅 어려움
- 순환 복잡도가 높음

**리팩토링 방안**:
1. 함수를 여러 개의 작은 함수로 분리
2. 전략 패턴(Strategy Pattern) 적용
3. 서비스 레이어로 비즈니스 로직 이동

**예시**:
```python
# 리팩토링 후
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    """FACT_COLLECTION Node 실행"""
    # 1. 엔티티 추출
    entities, fact_emotion, rag_results = _extract_entities_and_emotions(state)
    
    # 2. Facts 업데이트
    facts = _update_facts(state, entities, fact_emotion)
    
    # 3. DB 저장
    _save_to_database(state, facts, fact_emotion)
    
    # 4. 완성도 계산 및 다음 질문 생성
    completion_rate = _calculate_completion_rate(state, rag_results)
    next_question = _generate_next_question(state, rag_results)
    
    return {
        **state,
        "facts": facts,
        "completion_rate": completion_rate,
        "bot_message": next_question["message"],
        "expected_input": next_question["expected_input"],
        "next_state": "VALIDATION"
    }
```

#### 🔴 중요: 중복 코드 제거

**위치**: 여러 파일
- 증거 추출 로직 중복
- 날짜 추출 로직 중복
- 키워드 매칭 로직 중복

**리팩토링 방안**:
1. 공통 로직을 헬퍼 함수로 분리
2. 서비스 레이어로 이동
3. 재사용 가능한 유틸리티 모듈 생성

### 4.2 단기 리팩토링 필요 (중간 우선순위)

#### 🟡 중간: 의존성 주입 패턴 적용

**문제점**:
- 전역 싱글톤 패턴 사용
- 테스트 시 모킹 어려움

**리팩토링 방안**:
1. FastAPI의 `Depends` 활용
2. 팩토리 패턴 적용
3. 인터페이스/추상 클래스 도입

**예시**:
```python
# api/dependencies.py
@lru_cache()
def get_entity_extractor() -> EntityExtractor:
    """EntityExtractor 인스턴스 반환 (싱글톤)"""
    return EntityExtractor()

# langgraph/nodes/fact_collection_node.py
def fact_collection_node(
    state: StateContext,
    entity_extractor: EntityExtractor = Depends(get_entity_extractor)
) -> Dict[str, Any]:
    ...
```

#### 🟡 중간: 설정 외부화

**문제점**:
- 일부 설정값이 하드코딩됨
- 환경별 설정 관리 어려움

**리팩토링 방안**:
1. 모든 설정값을 `config/settings.py`로 이동
2. 환경변수 기반 설정 관리
3. 설정 검증 로직 추가

### 4.3 장기 리팩토링 필요 (낮은 우선순위)

#### 🟢 낮음: 아키텍처 개선

**문제점**:
- 일부 레이어 간 경계가 모호함
- 도메인 로직이 여러 레이어에 분산됨

**리팩토링 방안**:
1. 도메인 주도 설계(DDD) 적용
2. 레이어 경계 명확화
3. 도메인 서비스 도입

---

## 5. 테스트 가능성 검토

### 5.1 단위 테스트 가능성

#### 🟡 중간: 테스트 가능하나 개선 필요

**문제점**:
- 전역 싱글톤 패턴으로 모킹 어려움
- DB 의존성으로 테스트 복잡도 증가
- 외부 API(GPT) 의존성

**개선 방안**:
1. 의존성 주입 패턴 적용
2. 인터페이스/추상 클래스 도입
3. 모킹 전략 수립

### 5.2 통합 테스트 가능성

#### ✅ 통합 테스트 가능

**확인 사항**:
- FastAPI 테스트 클라이언트 사용 가능
- DB 테스트 데이터베이스 사용 가능
- 모킹 라이브러리 사용 가능

**평가**: 통합 테스트 가능

---

## 6. 문서화 및 주석 검토

### 6.1 코드 문서화

#### ✅ 대부분의 코드가 문서화됨

**확인 사항**:
- 대부분의 클래스/함수에 Docstring 존재
- 모듈 레벨 문서화 존재
- 아키텍처 문서 존재

**평가**: 문서화가 잘 되어 있음

#### 🟡 중간: Docstring 형식 불일치

**문제점**:
- 일부 Docstring이 Google 스타일
- 일부 Docstring이 간단한 설명만 포함

**개선 방안**:
1. Google 스타일 Docstring 표준화
2. 모든 공개 함수에 `Args`, `Returns` 섹션 추가

---

## 7. 버전 관리 및 변경 이력

### 7.1 버전 관리

#### ✅ Git 사용 중

**확인 사항**:
- Git 저장소 존재
- 커밋 이력 관리

**평가**: 버전 관리가 잘 되어 있음

### 7.2 변경 이력 관리

#### 🟡 중간: 변경 이력 문서화 부족

**문제점**:
- CHANGELOG.md 없음
- 주요 변경 사항 추적 어려움

**개선 방안**:
1. CHANGELOG.md 생성
2. 버전별 변경 사항 기록
3. 릴리스 노트 작성

---

## 8. 유지보수성 개선 권장 사항

### 8.1 즉시 개선 (높은 우선순위)

1. **`fact_collection_node` 함수 리팩토링**
   - 함수를 여러 개의 작은 함수로 분리
   - 단일 책임 원칙(SRP) 적용
   - 순환 복잡도 감소

2. **중복 코드 제거**
   - 증거 추출 로직 통합
   - 날짜 추출 로직 통합
   - 키워드 매칭 로직 헬퍼 함수로 분리

3. **의존성 주입 패턴 적용**
   - FastAPI의 `Depends` 활용
   - 전역 싱글톤 패턴 제거
   - 테스트 가능한 구조로 개선

### 8.2 단기 개선 (중간 우선순위)

4. **설정 외부화**
   - 모든 설정값을 `config/settings.py`로 이동
   - 환경변수 기반 설정 관리
   - 설정 검증 로직 추가

5. **캐싱 전략 수립**
   - Redis 등 캐시 시스템 도입
   - 응답 캐싱 전략 수립
   - 캐시 무효화 전략 수립

6. **Docstring 표준화**
   - Google 스타일 Docstring 적용
   - 모든 공개 함수에 `Args`, `Returns` 섹션 추가

### 8.3 장기 개선 (낮은 우선순위)

7. **아키텍처 개선**
   - 도메인 주도 설계(DDD) 적용
   - 레이어 경계 명확화
   - 도메인 서비스 도입

8. **변경 이력 관리**
   - CHANGELOG.md 생성
   - 버전별 변경 사항 기록
   - 릴리스 노트 작성

---

## 9. 검토 요약

### 9.1 유지보수성 현황

- **모듈화**: 잘 구성됨, 레이어별 명확한 분리
- **의존성 관리**: 순환 의존성 없음, 일부 전역 상태 사용
- **확장성**: 확장 가능한 구조, 일부 하드코딩된 값
- **리팩토링 필요**: `fact_collection_node` 함수, 중복 코드
- **테스트 가능성**: 테스트 가능하나 개선 필요
- **문서화**: 대부분 문서화됨, 형식 불일치

### 9.2 발견된 문제

- 🔴 **높음**: `fact_collection_node` 함수가 너무 김 (390줄)
- 🔴 **높음**: 중복 코드 존재
- 🟡 **중간**: 전역 싱글톤 패턴 사용
- 🟡 **중간**: 일부 설정값 하드코딩
- 🟡 **중간**: Docstring 형식 불일치
- 🟢 **낮음**: 변경 이력 문서화 부족

### 9.3 우선순위별 수정 권장

1. 🔴 **높음**: `fact_collection_node` 함수 리팩토링 (즉시)
2. 🔴 **높음**: 중복 코드 제거 (즉시)
3. 🟡 **중간**: 의존성 주입 패턴 적용 (단기)
4. 🟡 **중간**: 설정 외부화 (단기)
5. 🟢 **낮음**: 아키텍처 개선 (장기)

---

## 10. 결론

유지보수성은 전반적으로 양호하지만, **`fact_collection_node` 함수의 리팩토링**과 **중복 코드 제거**가 가장 중요한 개선 사항입니다. 또한 **의존성 주입 패턴 적용**과 **설정 외부화**도 단기적으로 개선하면 유지보수성이 크게 향상될 것입니다.

**우선순위**:
1. 🔴 **높음**: `fact_collection_node` 함수 리팩토링 (즉시)
2. 🔴 **높음**: 중복 코드 제거 (즉시)
3. 🟡 **중간**: 의존성 주입 패턴 적용 (단기)

**참고**: 
- 모듈 구조가 잘 구성되어 있음
- 순환 의존성 문제 없음
- 확장 가능한 구조
- 대부분의 코드가 문서화됨

