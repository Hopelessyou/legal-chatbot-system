# RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템

## 프로젝트 개요

본 프로젝트는 법률 상담 요청자의 자유로운 자연어 입력을 기반으로, 사건을 '법률적으로 판단 가능한 구조화 데이터'로 변환하는 대화형 AI 상담문의 수집 시스템입니다.

**중요**: 본 시스템은 법률 자문을 제공하지 않으며, 변호사·상담사 상담 이전 단계에서 정보 수집과 정리를 담당합니다.

## 핵심 기술

- **LangGraph**: 대화 흐름 제어 및 상태 관리
- **GPT API**: 자연어 해석 및 엔티티 추출
- **RAG**: 내부 기준 문서 참조 및 질문 표준화
- **FastAPI**: REST API 서버
- **PostgreSQL**: 구조화된 상담 데이터 저장

## 프로젝트 구조

```
ver1/
├── src/
│   ├── api/              # API 엔드포인트
│   ├── langgraph/        # LangGraph 노드 및 그래프
│   ├── rag/              # RAG 검색 및 문서 관리
│   ├── db/               # DB 모델 및 연결
│   ├── services/         # 비즈니스 로직 서비스
│   ├── models/           # Pydantic 모델
│   └── utils/            # 공통 유틸리티
├── config/               # 설정 파일
├── data/                 # 데이터 파일
│   └── rag/             # RAG 문서
├── tests/                # 테스트
├── scripts/              # 유틸리티 스크립트
├── migrations/           # DB 마이그레이션
└── docs/                 # 문서화
```

## 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하고 필요한 값들을 설정하세요.

```bash
cp .env.example .env
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 데이터베이스 생성
createdb legal_chatbot_db

# 마이그레이션 실행
alembic upgrade head
```

### 4. RAG 문서 인덱싱

```bash
python scripts/index_rag_documents.py
```

### 5. 서버 실행

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## API 엔드포인트

- `POST /chat/start` - 상담 세션 시작
- `POST /chat/message` - 사용자 메시지 처리
- `POST /chat/end` - 상담 종료
- `GET /chat/status` - 현재 상담 상태 조회
- `GET /chat/result` - 최종 상담 결과 조회

API 문서는 서버 실행 후 `http://localhost:8000/docs`에서 확인할 수 있습니다.

## 개발 원칙

1. **LangGraph는 흐름 제어, GPT는 해석 도구**
   - GPT API는 판단이 아닌 해석만 수행
   - 분기 및 반복은 LangGraph가 담당

2. **RAG는 GPT의 판단 범위를 제한**
   - 내부 기준 문서만 참조
   - 질문 및 요약 표준화

3. **DB는 법률 사건 데이터 웨어하우스**
   - 사실 단위 저장
   - 감정과 사실 분리

4. **API는 상태 머신을 1 Step씩 실행**
   - 단순 챗봇 응답이 아님
   - 상태 기반 정보 수집 시스템

## 개발 일정

- Phase 1-2: 환경 설정, DB 설계 및 구현 (1주)
- Phase 3-4: RAG 구축, GPT API 연동 (1주)
- Phase 5: LangGraph 구현 (핵심) (1-2주)
- Phase 6-7: API 서버 개발, 세션 관리 (1주)
- Phase 8: 통합 및 연동 (1주)
- Phase 9: 테스트 및 검증 (1주)
- Phase 10-11: 문서화, 최적화, 안정화 (1주)

**총 예상 기간: 6-8주**

## 라이선스

[라이선스 정보]

