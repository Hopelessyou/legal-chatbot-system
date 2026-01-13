# LangGraph 노드 테스트

## 개요
각 LangGraph 노드가 순차적으로 올바르게 작동하는지 테스트하는 스크립트입니다.

## 사용법

### 1. 순차 실행 테스트
모든 노드를 순서대로 실행하여 전체 플로우를 테스트합니다:

```powershell
python tests/test_nodes_sequential.py --mode sequential
```

### 2. 개별 노드 테스트
각 노드를 독립적으로 테스트합니다:

```powershell
python tests/test_nodes_sequential.py --mode individual
```

### 3. 둘 다 실행
순차 실행과 개별 테스트를 모두 실행합니다:

```powershell
python tests/test_nodes_sequential.py --mode both
```

또는 기본값으로:

```powershell
python tests/test_nodes_sequential.py
```

## 테스트되는 노드

1. **INIT** - 초기화 노드
   - 세션 생성 및 초기 메시지 표시
   - 사용자 입력에 따라 CASE_CLASSIFICATION으로 전이

2. **CASE_CLASSIFICATION** - 사건 분류 노드
   - 사건 유형 분류 (CRIMINAL, CIVIL 등)
   - 세부 사건 유형 분류
   - 1차 서술 분석 및 missing_fields 설정

3. **FACT_COLLECTION** - 사실 수집 노드
   - Q-A 쌍 저장
   - 다음 질문 생성
   - completion_rate 계산

4. **VALIDATION** - 검증 노드
   - conversation_history에서 facts 추출
   - 누락 필드 확인
   - RE_QUESTION 또는 SUMMARY로 전이 결정

5. **RE_QUESTION** - 추가 질문 노드
   - 누락 필드에 대한 질문 생성
   - asked_fields 추적하여 중복 질문 방지

6. **SUMMARY** - 요약 노드
   - 수집된 정보 기반 요약 생성
   - DB에 저장
   - COMPLETED로 전이

7. **COMPLETED** - 완료 노드
   - 세션 완료 처리

## 출력 예시

```
======================================================================
🧪 [INIT] 노드 테스트 시작
======================================================================
입력 State: current_state=INIT
✅ [INIT] 실행 완료
   현재 State: CASE_CLASSIFICATION
   다음 State: CASE_CLASSIFICATION

======================================================================
📍 [INIT] 실행 후 State 요약
======================================================================
  세션 ID: sess_xxxxx
  현재 State: CASE_CLASSIFICATION
  다음 State: CASE_CLASSIFICATION
  사건 유형: N/A / N/A
  완성도: 0%
  Bot 메시지: ...
  누락 필드: []
  ...
======================================================================
```

## 주의사항

1. **환경 변수 설정 필요**: 테스트 실행 전 `.env` 파일에 필요한 환경 변수가 설정되어 있어야 합니다.
   - `OPENAI_API_KEY`: GPT API 호출에 필요
   - `DATABASE_URL`: DB 연결에 필요 (일부 노드)

2. **DB 연결**: 일부 노드(INIT, VALIDATION, SUMMARY)는 DB 연결이 필요합니다.

3. **RAG 설정**: K0, K1, K2 등의 YAML 파일이 `data/rag/` 디렉토리에 있어야 합니다.

## 오류 해결

### ModuleNotFoundError
프로젝트 루트에서 실행하고 있는지 확인하세요:
```powershell
cd C:\Users\1gmla\OneDrive\Documents\coding\info_scrap\ver2\legal-chatbot-system
python tests/test_nodes_sequential.py
```

### 환경 변수 오류
`.env` 파일에 필요한 환경 변수가 설정되어 있는지 확인하세요.

### DB 연결 오류
데이터베이스가 실행 중인지 확인하세요.
