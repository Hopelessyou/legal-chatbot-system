# 변경 이력

## [0.1.0] - 2025-01-XX

### 추가됨
- 프로젝트 기본 구조 및 디렉토리 생성
- Phase 1: 프로젝트 환경 설정 및 인프라 구축
  - 공통 유틸리티 모듈 (예외 처리, 응답 포맷, 헬퍼 함수, 로거)
  - 환경 변수 관리
  - 로깅 시스템
  
- Phase 2: 데이터베이스 설계 및 구현
  - 10개 테이블 DDL 작성
  - SQLAlchemy ORM 모델 정의
  - DB 연결 모듈
  - Alembic 마이그레이션 설정
  
- Phase 3: RAG 시스템 구축
  - RAG 문서 구조 설계 (K1~K4)
  - 메타데이터 스키마 및 파서
  - ChromaDB 벡터 DB 설정
  - Embedding 모델 관리
  - Chunking 전략 구현
  - RAG 검색 모듈
  - 인덱싱 파이프라인
  
- Phase 4: GPT API 연동 모듈 개발
  - GPT API 클라이언트 (재시도 로직 포함)
  - 엔티티 추출 함수 (날짜, 금액, 인물, 행위)
  - 사실/감정 분리 함수
  - 키워드/의미 추출 함수
  - 요약 생성 함수
  - GPT API 호출 로깅
  - 프롬프트 빌더
  
- Phase 5: LangGraph 상태 머신 구현
  - State Context 구조 정의
  - 7개 Node 구현 (INIT, CASE_CLASSIFICATION, FACT_COLLECTION, VALIDATION, RE_QUESTION, SUMMARY, COMPLETED)
  - Conditional Edge 구현
  - LangGraph 그래프 구성
  - State 전이 로깅
  
- Phase 6-8: 통합 및 연동
  - API 라우터 실제 구현
  - 세션 관리 서비스
  - 완성도 계산 모듈
  - 누락 필드 관리 모듈
  - 에러 핸들링 및 미들웨어
  - 통합 테스트 코드

### 문서화
- README.md
- SETUP.md (설치 및 실행 가이드)
- API.md (API 명세서)
- ARCHITECTURE.md (시스템 아키텍처)
- LANGGRAPH.md (LangGraph 구조 설명)
- RAG.md (RAG 문서 구조 설명)
- PROGRESS.md (개발 진행 상황)

### 테스트
- 단위 테스트 (utils, exceptions, response)
- 통합 테스트 (chat flow, langgraph nodes, rag search)

