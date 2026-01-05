# LangGraph 노드 에러 처리 전략

## 원칙

모든 LangGraph 노드는 다음 에러 처리 전략을 따릅니다:

### 1. 치명적 에러 (Critical Errors)
- **전략**: 예외를 raise하여 상위 레벨로 전파
- **사용 사례**:
  - DB 연결 실패
  - 필수 의존성 누락
  - 상태 불일치 (예: session_id 없음)
  - 잘못된 상태 전이

### 2. 복구 가능한 에러 (Recoverable Errors)
- **전략**: 기본값 반환 및 로깅 후 계속 진행
- **사용 사례**:
  - RAG 검색 실패 (기본값 사용)
  - GPT API 일시적 실패 (재시도 또는 기본값)
  - 선택적 데이터 파싱 실패

### 3. 노드별 에러 처리

#### INIT Node
- **전략**: 복구 가능한 에러로 처리
- **이유**: 초기화 실패 시에도 기본 메시지로 사용자와 상호작용 가능해야 함
- **구현**: 기본 메시지 반환

#### CASE_CLASSIFICATION Node
- **전략**: 치명적 에러로 처리
- **이유**: 사건 분류는 핵심 기능이며 실패 시 다음 단계 진행 불가
- **구현**: 예외 raise

#### FACT_COLLECTION Node
- **전략**: 치명적 에러로 처리
- **이유**: 사실 수집은 핵심 기능
- **구현**: 예외 raise

#### VALIDATION Node
- **전략**: 치명적 에러로 처리
- **이유**: 검증 실패 시 잘못된 데이터로 진행될 수 있음
- **구현**: 예외 raise

#### RE_QUESTION Node
- **전략**: 치명적 에러로 처리
- **이유**: 질문 생성 실패 시 사용자 상호작용 불가
- **구현**: 예외 raise

#### SUMMARY Node
- **전략**: 치명적 에러로 처리
- **이유**: 요약 생성은 최종 단계의 핵심 기능
- **구현**: 예외 raise

#### COMPLETED Node
- **전략**: 치명적 에러로 처리
- **이유**: 완료 처리 실패 시 세션 상태 불일치
- **구현**: 예외 raise

## 에러 로깅

모든 에러는 다음 형식으로 로깅합니다:

```python
logger.error(f"[{session_id}] {NodeName} Node 실행 실패: {str(e)}", exc_info=True)
```

- `session_id`: 세션 식별자 (가능한 경우)
- `NodeName`: 노드 이름
- `exc_info=True`: 스택 트레이스 포함

## 예외 타입

- `ValueError`: 잘못된 입력값
- `RuntimeError`: 런타임 오류 (DB 연결 실패 등)
- `KeyError`: 필수 키 누락
- `Exception`: 기타 예외 (최후의 수단)

