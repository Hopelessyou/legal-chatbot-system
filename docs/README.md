# 문서 디렉토리

이 디렉토리에는 프로젝트의 모든 문서가 체계적으로 정리되어 있습니다.

## 디렉토리 구조

```
docs/
├── README.md                    # 이 파일
├── reviews/                     # 컴포넌트별 상세 리뷰 문서
│   ├── README.md               # 리뷰 문서 가이드
│   └── REVIEW_*.md             # 각 컴포넌트별 리뷰 문서 (75개)
├── reports/                     # 종합 분석 및 개선 리포트
│   ├── README.md               # 리포트 문서 가이드
│   ├── CODE_REVIEW_REPORT.md   # 전체 코드 리뷰 종합 리포트
│   ├── COMPREHENSIVE_REVIEW_REPORT.md  # 통합 리뷰 리포트
│   ├── NODE_REVIEW_REPORT.md   # 노드 전체 점검 리포트
│   └── ...                     # 기타 리포트 문서
├── API.md                       # API 사용 가이드
├── ARCHITECTURE.md              # 아키텍처 문서
├── CHAT_USAGE.md                # 채팅 사용 가이드
├── DATABASE_SETUP.md            # 데이터베이스 설정 가이드
├── EXCEL_TO_YAML.md             # Excel to YAML 변환 가이드
├── LANGGRAPH.md                  # LangGraph 가이드
├── LANGGRAPH_FLOW.md             # LangGraph 플로우 문서
├── RAG.md                        # RAG 시스템 가이드
├── PROGRESS.md                   # 프로젝트 진행 상황
└── NEXT_STEPS.md                 # 다음 단계 계획
```

## 문서 유형

### 1. 리뷰 문서 (`reviews/`)
각 컴포넌트에 대한 상세한 코드 리뷰 문서입니다.
- API 레이어 (REVIEW_01 ~ REVIEW_06)
- LangGraph 레이어 (REVIEW_07 ~ REVIEW_17)
- RAG 레이어 (REVIEW_18 ~ REVIEW_24)
- 서비스 레이어 (REVIEW_25 ~ REVIEW_35)
- 데이터베이스 레이어 (REVIEW_36 ~ REVIEW_49)
- 유틸리티 레이어 (REVIEW_50 ~ REVIEW_56)
- 설정 레이어 (REVIEW_57 ~ REVIEW_62)
- 기타 (REVIEW_63 ~ REVIEW_75)

### 2. 리포트 문서 (`reports/`)
프로젝트의 종합 분석 및 개선 리포트입니다.
- 종합 리포트: 전체 코드 리뷰, 통합 리뷰, 노드 점검 리포트
- 분석 리포트: 코드 분석, 하드코딩 이슈, 보안 리뷰
- 개선 리포트: 최종 개선 리포트, 개선 사항 요약

### 3. 사용 가이드 문서
프로젝트 사용 및 개발을 위한 가이드 문서입니다.
- API 사용법
- 아키텍처 설명
- 데이터베이스 설정
- RAG 시스템 사용법
- LangGraph 플로우 설명

## 빠른 시작

1. **프로젝트 개요**: 루트의 `README.md` 참고
2. **설치 및 설정**: 루트의 `SETUP.md` 참고
3. **아키텍처 이해**: `ARCHITECTURE.md` 참고
4. **코드 리뷰**: `reviews/README.md` 참고
5. **개선 사항**: `reports/README.md` 참고

## 문서 업데이트

문서는 프로젝트 진행에 따라 지속적으로 업데이트됩니다.
최신 정보는 각 문서의 마지막 수정 일자를 확인하세요.

