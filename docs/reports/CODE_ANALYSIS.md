# 법률 상담문의 수집 챗봇 시스템 - 코드 분석 보고서

## 📋 프로젝트 개요

**프로젝트명**: RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템  
**목적**: 법률 상담 요청자의 자연어 입력을 구조화된 데이터로 변환하는 대화형 AI 시스템  
**중요 사항**: 법률 자문을 제공하지 않으며, 변호사/상담사 상담 이전 단계에서 정보 수집과 정리를 담당

---

## 🏗️ 시스템 아키텍처

### 전체 구조
```
[프론트엔드/채널] → [REST API] → [FastAPI 서버]
                                    ↓
                            ┌───────┴───────┐
                            │               │
                        [LangGraph]      [RAG]
                            │               │
                            └───────┬───────┘
                                    │
                                [GPT API]
                                    │
                            [PostgreSQL/MySQL]
```

### 핵심 기술 스택
- **백엔드 프레임워크**: FastAPI (Python 3.10+)
- **대화 흐름 제어**: LangGraph
- **AI 모델**: OpenAI GPT-4 Turbo, Embedding 모델
- **벡터 DB**: ChromaDB
- **관계형 DB**: MySQL/PostgreSQL (SQLAlchemy ORM)
- **문서 관리**: YAML 기반 RAG 문서

---

## 📁 프로젝트 구조 분석

### 1. API 레이어 (`src/api/`)

#### 주요 파일
- **`main.py`**: FastAPI 애플리케이션 진입점
  - CORS, 미들웨어, 에러 핸들러 설정
  - 헬스 체크 엔드포인트
  - 정적 파일 서빙

- **`routers/chat.py`**: 채팅 관련 API 엔드포인트
  - `POST /chat/start`: 상담 세션 시작
  - `POST /chat/message`: 사용자 메시지 처리 (핵심)
  - `POST /chat/end`: 상담 종료
  - `GET /chat/status`: 현재 상담 상태 조회
  - `GET /chat/result`: 최종 상담 결과 조회
  - `GET /chat/detail`: 세션 상세 정보 (관리자용)
  - `GET /chat/list`: 세션 목록 조회
  - `POST /chat/upload`: 파일 업로드
  - `GET /chat/files`: 세션 파일 목록
  - `GET /chat/file/{file_id}/download`: 파일 다운로드

#### 특징
- 상태 머신을 1 Step씩 실행하는 설계
- 각 요청마다 LangGraph의 단일 Node만 실행
- 세션 상태는 DB에 영구 저장

---

### 2. LangGraph 레이어 (`src/langgraph/`)

#### State 정의 (`state.py`)
```python
StateContext = {
    session_id: str
    current_state: str  # INIT, CASE_CLASSIFICATION, FACT_COLLECTION, ...
    case_type: Optional[str]
    sub_case_type: Optional[str]
    facts: Dict[str, Any]  # incident_date, counterparty, amount, evidence
    emotion: List[Dict[str, Any]]
    completion_rate: int
    last_user_input: str
    missing_fields: List[str]
    bot_message: Optional[str]
    expected_input: Optional[Dict[str, Any]]
}
```

#### 그래프 구조 (`graph.py`)
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

#### 주요 Node 구현

1. **`init_node.py`**: 초기화 노드
   - 세션 초기화 및 환영 메시지

2. **`case_classification_node.py`**: 사건 유형 분류
   - 키워드 추출
   - RAG K1 문서 검색
   - GPT API로 최종 분류
   - 민사/형사/가사/행정 분류

3. **`fact_collection_node.py`**: 사실 수집 (핵심 노드)
   - 병렬 처리: 엔티티 추출, 사실/감정 분리, RAG 검색
   - 조건부 엔티티 추출 (expected_input 기반)
   - 날짜, 금액, 당사자, 증거 추출
   - DB에 CaseFact, CaseParty, CaseEvidence 저장
   - 완성도(completion_rate) 계산
   - 다음 질문 생성

4. **`validation_node.py`**: 검증 노드
   - 필수 필드 충족 여부 확인
   - 누락 필드 식별

5. **`re_question_node.py`**: 재질문 노드
   - 누락 필드에 대한 질문 생성

6. **`summary_node.py`**: 요약 노드
   - 최종 상담 내용 요약
   - 구조화된 데이터 생성

7. **`completed_node.py`**: 완료 노드
   - 세션 종료 처리

---

### 3. RAG 레이어 (`src/rag/`)

#### 주요 컴포넌트
- **`searcher.py`**: RAG 검색 엔진
  - 벡터 유사도 검색
  - 메타데이터 필터링 (knowledge_type, case_type, sub_case_type)
  - ChromaDB 기반

- **`vector_db.py`**: 벡터 DB 관리
  - ChromaDB 컬렉션 관리
  - 임베딩 저장 및 검색

- **`embeddings.py`**: 임베딩 모델
  - OpenAI Embedding API 또는 Sentence Transformers

- **`parser.py`**: YAML 문서 파싱
- **`chunker.py`**: 텍스트 청킹
- **`pipeline.py`**: RAG 파이프라인

#### RAG 문서 구조 (`data/rag/`)
- **K0_intake/**: 초기 상담 메시지
- **K1_case_type/**: 사건 유형 분류 기준
  - admin/, civil/, criminal/, family/
- **K2_required_fields/**: 필수 필드 정의
- **K3_risk_rules/**: 위험도 판단 규칙
- **K4_output_format/**: 출력 형식 정의
- **common/facts/**: 공통 사실 패턴 (97개 YAML 파일)

---

### 4. 서비스 레이어 (`src/services/`)

#### 주요 서비스

1. **`entity_extractor.py`**: 엔티티 추출
   - 날짜 추출 (패턴 매칭 + GPT)
   - 금액 추출 (한글 숫자 지원)
   - 당사자 추출 (GPT)
   - 행위 추출 (GPT)
   - 통합 엔티티 추출 (조건부 필드 추출 지원)

2. **`fact_emotion_splitter.py`**: 사실/감정 분리
   - 사용자 입력에서 사실과 감정 분리
   - GPT API 활용

3. **`gpt_client.py`**: GPT API 클라이언트
   - OpenAI API 래퍼
   - 에러 처리 및 재시도 로직

4. **`session_manager.py`**: 세션 관리
   - 세션 생성/조회
   - 상태 로드/저장
   - 만료 세션 정리

5. **`missing_field_manager.py`**: 누락 필드 관리
6. **`completion_calculator.py`**: 완성도 계산
7. **`summarizer.py`**: 요약 생성
8. **`prompt_builder.py`**: 프롬프트 빌더
9. **`prompt_loader.py`**: 프롬프트 로더

---

### 5. 데이터베이스 레이어 (`src/db/`)

#### 주요 모델 (`models/`)

1. **`chat_session.py`**: 채팅 세션
   - session_id, channel, status, current_state, completion_rate

2. **`case_master.py`**: 사건 마스터
   - case_id, main_case_type, sub_case_type, case_stage, urgency_level

3. **`case_fact.py`**: 사실 정보
   - fact_type, incident_date, amount, description

4. **`case_party.py`**: 당사자 정보
   - party_role, party_type, party_description

5. **`case_evidence.py`**: 증거 정보
   - evidence_type, description, available

6. **`case_emotion.py`**: 감정 정보
   - emotion_type, intensity, source_text

7. **`case_missing_field.py`**: 누락 필드
8. **`case_summary.py`**: 요약 정보
9. **`chat_file.py`**: 업로드 파일
10. **`ai_process_log.py`**: AI 처리 로그

#### 관계 구조
```
ChatSession (1) ── (1) CaseMaster
                      │
                      ├── (N) CaseFact
                      ├── (N) CaseParty
                      ├── (N) CaseEvidence
                      ├── (N) CaseEmotion
                      ├── (N) CaseMissingField
                      └── (1) CaseSummary
```

---

### 6. 설정 및 유틸리티

#### 설정 (`config/settings.py`)
- Pydantic Settings 기반
- 환경 변수 로드 (.env)
- 데이터베이스, OpenAI, 벡터 DB, API 설정

#### 유틸리티 (`src/utils/`)
- **`logger.py`**: 구조화된 로깅
- **`exceptions.py`**: 커스텀 예외
- **`response.py`**: API 응답 포맷
- **`helpers.py`**: 헬퍼 함수

---

## 🔄 데이터 흐름 분석

### 상담 시작 플로우
1. 클라이언트 → `POST /chat/start`
2. `SessionManager.create_session()` → 세션 생성
3. `create_initial_context()` → 초기 State 생성
4. `run_graph_step()` → INIT Node 실행
5. DB에 `chat_session` 저장
6. 응답 반환

### 메시지 처리 플로우 (핵심)
1. 클라이언트 → `POST /chat/message`
2. 세션 상태 로드 (`load_session_state()`)
3. `state["last_user_input"]` 업데이트
4. `run_graph_step(state)` 실행
5. 현재 State에 해당하는 Node 실행:
   - **CASE_CLASSIFICATION**: 사건 유형 분류
   - **FACT_COLLECTION**: 사실 수집 (가장 복잡)
   - **VALIDATION**: 검증
   - **RE_QUESTION**: 재질문
   - **SUMMARY**: 요약
6. Node 내부 처리:
   - GPT API 호출 (엔티티 추출, 분류 등)
   - RAG 검색 (K1, K2 문서)
   - DB 저장 (CaseFact, CaseParty 등)
   - State 업데이트
7. `save_session_state()` → 상태 저장
8. 응답 반환

### FACT_COLLECTION Node 상세 흐름
```
사용자 입력
  ↓
병렬 처리:
  ├─ 엔티티 추출 (조건부)
  ├─ 사실/감정 분리
  └─ RAG K2 검색
  ↓
Facts 업데이트:
  ├─ incident_date (날짜)
  ├─ counterparty (당사자)
  ├─ amount (금액)
  └─ evidence (증거)
  ↓
DB 저장:
  ├─ CaseFact
  ├─ CaseParty
  ├─ CaseEvidence
  └─ CaseEmotion
  ↓
완성도 계산
  ↓
다음 질문 생성
  ↓
State 업데이트
```

---

## 🎯 핵심 설계 원칙

### 1. LangGraph는 흐름 제어, GPT는 해석 도구
- **LangGraph**: 모든 판단과 분기 담당
- **GPT API**: 자연어 해석만 수행 (엔티티 추출, 분류)

### 2. RAG는 GPT의 판단 범위를 제한
- 내부 기준 문서(K1~K4)만 참조
- 질문 및 요약 표준화
- 메타데이터 필터링으로 정확도 향상

### 3. DB는 법률 사건 데이터 웨어하우스
- 사실 단위 저장 (CaseFact)
- 감정과 사실 분리 (CaseEmotion vs CaseFact)
- 구조화된 데이터 저장

### 4. API는 상태 머신을 1 Step씩 실행
- 단순 챗봇 응답이 아님
- 각 요청마다 1 Node만 실행
- 상태 기반 정보 수집 시스템

---

## 🔍 코드 품질 분석

### 강점
1. **명확한 아키텍처**: 레이어 분리가 잘 되어 있음
2. **상태 관리**: LangGraph 기반 체계적인 상태 관리
3. **에러 처리**: 커스텀 예외 및 에러 핸들러 구현
4. **로깅**: 구조화된 로깅 시스템
5. **확장성**: RAG 문서 기반으로 쉽게 확장 가능
6. **병렬 처리**: FACT_COLLECTION에서 병렬 처리로 성능 최적화

### 개선 가능한 부분
1. **하드코딩된 값**: 일부 매직 넘버/문자열 존재
2. **에러 복구**: GPT API 실패 시 폴백 로직 개선 가능
3. **테스트 커버리지**: 테스트 코드 보강 필요
4. **문서화**: 일부 함수의 docstring 보강 필요
5. **타입 힌팅**: 일부 함수의 타입 힌팅 보완 필요

---

## 📊 의존성 분석

### 주요 의존성 (`requirements.txt`)
- **FastAPI**: 웹 프레임워크
- **LangGraph/LangChain**: 대화 흐름 제어
- **OpenAI**: GPT API
- **SQLAlchemy**: ORM
- **ChromaDB**: 벡터 DB
- **Sentence Transformers**: 임베딩 모델
- **Pydantic**: 데이터 검증
- **Alembic**: DB 마이그레이션

### 외부 서비스 의존성
- **OpenAI API**: 필수 (GPT 모델, Embedding)
- **MySQL/PostgreSQL**: 필수 (데이터 저장)
- **ChromaDB**: 필수 (벡터 검색)

---

## 🚀 실행 및 배포

### 로컬 실행
1. 가상환경 생성 및 활성화
2. `pip install -r requirements.txt`
3. `.env` 파일 설정 (env.example 참고)
4. DB 생성 및 마이그레이션 (`alembic upgrade head`)
5. RAG 문서 인덱싱 (`python scripts/index_rag_documents.py`)
6. 서버 실행 (`uvicorn src.api.main:app --reload`)

### Docker 배포
- `Dockerfile` 및 `docker-compose.yml` 제공

---

## 📝 주요 기능 요약

### 구현된 기능
✅ 세션 관리 (생성, 조회, 종료)  
✅ 사건 유형 자동 분류  
✅ 사실 정보 수집 (날짜, 금액, 당사자, 증거)  
✅ 감정 정보 분리 및 저장  
✅ 완성도 계산  
✅ 누락 필드 자동 감지 및 재질문  
✅ 최종 요약 생성  
✅ 파일 업로드/다운로드  
✅ 세션 상태 조회 및 관리  

### 미구현/개선 필요
⚠️ 실시간 채팅 (현재는 요청-응답 방식)  
⚠️ 다중 채널 지원 강화  
⚠️ 관리자 대시보드 (HTML 파일은 있으나 API 연동 필요)  
⚠️ 성능 모니터링 및 메트릭 수집  

---

## 🎓 학습 포인트

1. **LangGraph 활용**: 상태 머신 기반 대화 흐름 제어
2. **RAG 구현**: 벡터 검색과 메타데이터 필터링
3. **엔티티 추출**: 패턴 매칭 + GPT API 하이브리드 접근
4. **병렬 처리**: ThreadPoolExecutor를 활용한 성능 최적화
5. **조건부 처리**: expected_input 기반 조건부 엔티티 추출
6. **DB 설계**: 법률 사건 데이터의 구조화된 저장

---

## 📌 결론

이 프로젝트는 **RAG + LangGraph 기반의 법률 상담문의 수집 시스템**으로, 잘 구조화된 아키텍처와 명확한 책임 분리를 가지고 있습니다. 

**핵심 강점**:
- LangGraph를 활용한 체계적인 상태 관리
- RAG를 통한 표준화된 질문 및 분류
- GPT API와 패턴 매칭의 하이브리드 접근
- 확장 가능한 문서 기반 지식 관리

**활용 가능성**:
- 법률 상담 외 다른 도메인으로 확장 가능
- RAG 문서만 교체하면 다른 분야에 적용 가능
- LangGraph 구조는 다양한 대화형 시스템에 재사용 가능

---

**분석 일시**: 2025-12-30  
**분석 대상**: `info_scrap/ver2/legal-chatbot-system/` 전체 코드베이스

