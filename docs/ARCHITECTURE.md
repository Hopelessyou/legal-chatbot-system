# 시스템 아키텍처 문서

## 전체 구조

```
[프론트엔드/채널]
        ↓
   [REST API]
        ↓
[FastAPI 서버]
        ↓
    ┌───┴───┐
    │       │
[LangGraph] [RAG]
    │       │
    ├───┬───┘
    │   │
  [GPT API]
    │
[PostgreSQL]
```

## 핵심 컴포넌트

### 1. API 레이어 (`src/api/`)
- FastAPI 기반 REST API 서버
- 5개 엔드포인트 제공
- 요청/응답 검증 및 에러 처리

### 2. LangGraph 레이어 (`src/langgraph/`)
- 상태 머신 기반 대화 흐름 제어
- 7개 Node로 구성된 그래프
- Conditional Edge를 통한 분기 처리

### 3. RAG 레이어 (`src/rag/`)
- 벡터 DB 기반 지식 검색
- K1~K4 문서 관리
- 메타데이터 필터링 검색

### 4. GPT API 레이어 (`src/services/`)
- 자연어 해석 및 엔티티 추출
- 사실/감정 분리
- 요약 생성

### 5. 데이터베이스 레이어 (`src/db/`)
- PostgreSQL 기반 구조화 데이터 저장
- 10개 테이블로 구성
- ORM 모델 및 관계 정의

## 데이터 흐름

### 상담 시작 플로우
1. 클라이언트 → POST /chat/start
2. API → SessionManager.create_session()
3. API → init_node() 실행
4. DB → chat_session 생성
5. API → 응답 반환

### 메시지 처리 플로우
1. 클라이언트 → POST /chat/message
2. API → 세션 상태 로드
3. API → run_graph_step() 실행
4. LangGraph → 현재 State에 해당하는 Node 실행
5. Node → GPT API 호출 (필요시)
6. Node → RAG 검색 (필요시)
7. Node → DB 저장
8. Node → State 업데이트
9. API → 응답 반환

## State 전이 흐름

```
INIT
  ↓
CASE_CLASSIFICATION
  ↓
FACT_COLLECTION
  ↓
VALIDATION
  ├─→ (누락 필드 있음) → RE_QUESTION → FACT_COLLECTION (Loop)
  └─→ (모든 필드 충족) → SUMMARY
                          ↓
                       COMPLETED
```

## 주요 설계 원칙

1. **LangGraph는 흐름 제어, GPT는 해석 도구**
   - 모든 판단과 분기는 LangGraph가 담당
   - GPT는 자연어 해석만 수행

2. **RAG는 GPT의 판단 범위를 제한**
   - 내부 기준 문서만 참조
   - 질문 및 요약 표준화

3. **DB는 법률 사건 데이터 웨어하우스**
   - 사실 단위 저장
   - 감정과 사실 분리

4. **API는 상태 머신을 1 Step씩 실행**
   - 각 요청마다 1 Node만 실행
   - 상태 기반 정보 수집

