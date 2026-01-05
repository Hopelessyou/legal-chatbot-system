# 문서 인덱스

이 문서는 프로젝트의 모든 문서에 대한 빠른 참조 가이드입니다.

## 📚 문서 구조

### 루트 문서
프로젝트 루트에 있는 주요 문서:
- `README.md` - 프로젝트 개요 및 시작 가이드
- `CHANGELOG.md` - 변경 이력
- `SETUP.md` - 설치 및 설정 가이드

### 📁 docs/ 디렉토리

#### 📂 reviews/ - 컴포넌트별 상세 리뷰 (75개)
각 컴포넌트에 대한 상세한 코드 리뷰 문서입니다.

**API 레이어** (REVIEW_01 ~ REVIEW_06)
- API 메인, 인증, 미들웨어, 에러 핸들러, 라우터

**LangGraph 레이어** (REVIEW_07 ~ REVIEW_17)
- 상태 관리, 그래프, 엣지, 각 노드별 리뷰

**RAG 레이어** (REVIEW_18 ~ REVIEW_24)
- 스키마, 파서, 청커, 임베딩, 벡터 DB, 검색기, 파이프라인

**서비스 레이어** (REVIEW_25 ~ REVIEW_35)
- GPT 클라이언트, 엔티티 추출기, 키워드 추출기, 요약기 등

**데이터베이스 레이어** (REVIEW_36 ~ REVIEW_49)
- DB 연결, 베이스 모델, 각 테이블 모델

**유틸리티 레이어** (REVIEW_50 ~ REVIEW_56)
- 로거, 예외 처리, 상수, 헬퍼 함수 등

**설정 레이어** (REVIEW_57 ~ REVIEW_62)
- 설정, 폴백 키워드, 우선순위, 질문 템플릿, 로깅, 프롬프트

**기타** (REVIEW_63 ~ REVIEW_75)
- 타입, 통합 플로우, 보안, 성능, 에러 처리, 테스트, Docker, 의존성, 문서화, 코드 품질, 유지보수성

#### 📂 reports/ - 종합 분석 및 개선 리포트 (10개)
프로젝트의 종합 분석 및 개선 리포트입니다.

**종합 리포트**
- `CODE_REVIEW_REPORT.md` - 전체 코드 리뷰 종합 리포트
- `COMPREHENSIVE_REVIEW_REPORT.md` - 모든 리뷰를 통합한 종합 리포트
- `NODE_REVIEW_REPORT.md` - LangGraph 노드 전체 점검 리포트

**분석 리포트**
- `CODE_ANALYSIS.md` - 코드 분석 리포트
- `HARDCODED_ISSUES.md` - 하드코딩된 이슈 목록
- `SECURITY_REVIEW.md` - 보안 리뷰 리포트

**개선 리포트**
- `FINAL_IMPROVEMENT_REPORT.md` - 최종 개선 리포트
- `IMPROVEMENT_SUMMARY.md` - 개선 사항 요약
- `FINAL_SUMMARY.md` - 최종 요약

#### 📄 사용 가이드 문서
- `API.md` - API 사용 가이드
- `ARCHITECTURE.md` - 아키텍처 문서
- `CHAT_USAGE.md` - 채팅 사용 가이드
- `DATABASE_SETUP.md` - 데이터베이스 설정 가이드
- `EXCEL_TO_YAML.md` - Excel to YAML 변환 가이드
- `LANGGRAPH.md` - LangGraph 가이드
- `LANGGRAPH_FLOW.md` - LangGraph 플로우 문서
- `RAG.md` - RAG 시스템 가이드
- `PROGRESS.md` - 프로젝트 진행 상황
- `NEXT_STEPS.md` - 다음 단계 계획

## 🔍 빠른 검색

### 특정 컴포넌트 리뷰 찾기
1. 컴포넌트의 카테고리를 확인 (API, LangGraph, RAG, Service, DB, Utils, Config)
2. `docs/reviews/` 폴더에서 해당 REVIEW_*.md 파일 찾기
3. 예: API 메인 → `docs/reviews/REVIEW_01_API_MAIN.md`

### 종합 리포트 찾기
- 전체 코드 리뷰: `docs/reports/CODE_REVIEW_REPORT.md`
- 통합 리뷰: `docs/reports/COMPREHENSIVE_REVIEW_REPORT.md`
- 노드 점검: `docs/reports/NODE_REVIEW_REPORT.md`

### 사용 가이드 찾기
- API 사용: `docs/API.md`
- 아키텍처: `docs/ARCHITECTURE.md`
- 데이터베이스 설정: `docs/DATABASE_SETUP.md`

## 📊 문서 통계

- **리뷰 문서**: 75개
- **리포트 문서**: 10개
- **사용 가이드**: 10개
- **총 문서 수**: 약 95개

## 📝 문서 업데이트

문서는 프로젝트 진행에 따라 지속적으로 업데이트됩니다.
최신 정보는 각 문서의 마지막 수정 일자를 확인하세요.

