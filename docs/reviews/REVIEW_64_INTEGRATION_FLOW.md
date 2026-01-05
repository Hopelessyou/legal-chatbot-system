# 통합 플로우 검토 보고서

## 검토 대상
- 전체 시스템 통합 플로우
- 검토 일자: 2024년
- 검토 범위: API → LangGraph → Services → DB 흐름, 에러 전파, 트랜잭션 관리

---

## ✅ 정상 동작 부분

### 1. 요청 처리 플로우
- ✅ 명확한 레이어 분리: API → LangGraph → Services → DB
- ✅ 세션 관리: 세션 생성, 상태 로드, 상태 저장이 일관되게 처리됨
- ✅ LangGraph 실행: `run_graph_step()`을 통한 단계별 실행

### 2. 에러 처리 구조
- ✅ 커스텀 예외 클래스 사용: `SessionNotFoundError`, `InvalidInputError` 등
- ✅ API 레이어에서 예외를 HTTPException으로 변환
- ✅ 로깅: 에러 발생 시 상세 로그 기록

### 3. 트랜잭션 관리
- ✅ 컨텍스트 매니저 사용: `get_db_session()`으로 자동 commit/rollback
- ✅ 일부 엔드포인트에서 단일 DB 세션 사용으로 트랜잭션 일관성 확보

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 노드 내부 DB 세션 관리 불일치

**문제**: LangGraph 노드들이 각각 독립적으로 DB 세션을 생성하고 있어, 여러 노드가 실행될 때 트랜잭션 일관성이 보장되지 않을 수 있습니다.

**영향도**: 중간  
**위험성**: 
- 여러 노드가 실행되는 경우 (예: `/chat/end`에서 SUMMARY → COMPLETED), 각 노드가 독립적인 트랜잭션을 사용하면 부분 실패 시 데이터 불일치 가능
- `fact_collection_node`에서 여러 DB 작업을 수행하지만, 각각 독립적인 세션을 사용할 수 있음

**현재 상황**:
- `/chat/end` 엔드포인트에서는 단일 DB 세션을 사용하여 트랜잭션 일관성 확보 (✅)
- 하지만 일반적인 `/chat/message` 플로우에서는 각 노드가 독립적으로 DB 세션을 생성

**수정 권장**: 
1. LangGraph 노드에 DB 세션을 파라미터로 전달하는 방식 고려
2. 또는 노드 실행 전에 DB 세션을 생성하고 모든 노드에 전달

---

### 2. 🟡 **중간**: 에러 전파 시 트랜잭션 롤백 보장 부족

**문제**: 노드 내부에서 예외가 발생했을 때, 이미 커밋된 DB 작업이 롤백되지 않을 수 있습니다.

**영향도**: 중간  
**위험성**: 
- 노드 A에서 DB 작업 후 커밋
- 노드 B에서 예외 발생
- 노드 A의 변경사항은 이미 커밋되어 롤백 불가

**현재 상황**:
- `get_db_session()` 컨텍스트 매니저는 예외 발생 시 자동 롤백
- 하지만 노드 내부에서 개별적으로 DB 세션을 생성하는 경우, 상위 레이어의 롤백이 적용되지 않음

**수정 권장**: 
1. 노드 실행 전에 DB 세션을 생성하고 모든 노드에 전달
2. 노드 실행 중 예외 발생 시 전체 트랜잭션 롤백

---

### 3. 🟢 **낮음**: 비동기 처리와 동기 DB 작업 혼재

**문제**: FastAPI 엔드포인트는 `async`이지만, LangGraph 노드와 DB 작업은 동기적으로 실행됩니다.

**영향도**: 낮음  
**위험성**: 
- 비동기 엔드포인트에서 동기 작업을 실행하면 블로킹 발생
- 동시 요청 처리 성능 저하 가능

**현재 상황**:
- `async def process_message()` 내부에서 `run_graph_step()` (동기) 호출
- `save_session_state()` (동기) 호출

**수정 권장**: 
1. `run_in_executor()`를 사용하여 동기 작업을 비동기로 실행 (선택적)
2. 또는 전체 플로우를 동기로 유지 (현재 방식 유지 가능)

---

### 4. 🟢 **낮음**: 에러 처리 일관성 부족

**문제**: 노드마다 에러 처리 방식이 다릅니다. 일부는 예외를 그대로 전파하고, 일부는 로깅 후 계속 진행합니다.

**영향도**: 낮음  
**위험성**: 
- 에러 처리 일관성 부족으로 디버깅 어려움
- 사용자에게 전달되는 에러 메시지가 일관되지 않을 수 있음

**현재 상황**:
- `init_node`: 예외 발생 시 로깅 후 빈 상태 반환
- `case_classification_node`: 예외 발생 시 폴백 처리
- `fact_collection_node`: 예외 발생 시 로깅 후 계속 진행

**수정 권장**: 
1. 노드별 에러 처리 전략 문서화
2. 공통 에러 처리 유틸리티 함수 생성 (선택적)

---

### 5. 🟢 **낮음**: 트랜잭션 범위 명확성 부족

**문제**: 어떤 작업이 하나의 트랜잭션으로 묶여야 하는지 명확하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
1. 트랜잭션 범위를 명확히 문서화
2. 예: "하나의 사용자 메시지 처리 = 하나의 트랜잭션"

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 2개 (노드 내부 DB 세션 관리 불일치, 에러 전파 시 트랜잭션 롤백 보장 부족)
- 🟢 **낮음**: 3개 (비동기/동기 혼재, 에러 처리 일관성, 트랜잭션 범위 명확성)

### 우선순위별 수정 권장
1. 🟡 **중간**: 노드에 DB 세션 전달 방식 개선 (권장)
2. 🟡 **중간**: 에러 전파 시 트랜잭션 롤백 보장 (권장)
3. 🟢 **낮음**: 비동기 처리 개선 (선택적)
4. 🟢 **낮음**: 에러 처리 일관성 개선 (선택적)
5. 🟢 **낮음**: 트랜잭션 범위 문서화 (선택적)

---

## 🔧 수정 제안

### 수정 1: 노드에 DB 세션 전달

#### `src/langgraph/graph.py` 수정
```python
def run_graph_step(state: StateContext, db_session: Optional[Session] = None) -> StateContext:
    """
    LangGraph 1 step 실행
    
    Args:
        state: 현재 State Context
        db_session: DB 세션 (None이면 노드 내부에서 생성)
    
    Returns:
        업데이트된 State Context
    """
    # DB 세션이 제공되지 않으면 생성
    if db_session is None:
        with db_manager.get_db_session() as session:
            return _run_graph_step_internal(state, session)
    else:
        return _run_graph_step_internal(state, db_session)

def _run_graph_step_internal(state: StateContext, db_session: Session) -> StateContext:
    """내부 실행 함수 (DB 세션 전달)"""
    # ... 기존 로직 ...
```

#### 노드 시그니처 변경
```python
def fact_collection_node(
    state: StateContext, 
    db_session: Optional[Session] = None
) -> Dict[str, Any]:
    """FACT_COLLECTION Node 실행"""
    if db_session is None:
        with db_manager.get_db_session() as session:
            return _fact_collection_internal(state, session)
    else:
        return _fact_collection_internal(state, db_session)
```

---

### 수정 2: API 레이어에서 단일 트랜잭션 보장

#### `src/api/routers/chat.py` 수정
```python
@router.post("/message")
async def process_message(request: ChatMessageRequest, _: str = Depends(verify_api_key)):
    """사용자 메시지 처리"""
    try:
        # ... 세션 검증 ...
        
        # 단일 DB 세션으로 전체 플로우 실행
        with db_manager.get_db_session() as db_session:
            # LangGraph 실행 (DB 세션 전달)
            result = run_graph_step(state, db_session=db_session)
            
            # 상태 저장 (같은 세션 사용)
            save_session_state(request.session_id, result, db_session=db_session)
            
            # 응답 반환 (컨텍스트 매니저 종료 시 자동 커밋)
            return success_response({...})
    
    except Exception as e:
        # 예외 발생 시 자동 롤백 (컨텍스트 매니저)
        logger.error(f"메시지 처리 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
```

---

### 수정 3: 에러 처리 일관성 개선 (선택적)

#### 공통 에러 처리 유틸리티 생성
```python
# src/utils/node_error_handler.py
from typing import Callable, Any, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)

def handle_node_error(
    node_name: str,
    state: Dict[str, Any],
    error: Exception,
    fallback_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    노드 에러 처리 공통 함수
    
    Args:
        node_name: 노드 이름
        state: 현재 상태
        error: 발생한 예외
        fallback_state: 폴백 상태 (None이면 현재 상태 유지)
    
    Returns:
        업데이트된 상태
    """
    logger.error(f"[{node_name}] 노드 실행 실패: {str(error)}", exc_info=True)
    
    if fallback_state:
        return {
            **state,
            **fallback_state,
            "error": str(error)
        }
    
    return {
        **state,
        "error": str(error)
    }
```

---

## 📋 현재 플로우 다이어그램

### 메시지 처리 플로우
```
1. API: POST /chat/message
   ↓
2. API: 세션 검증 및 상태 로드
   ↓
3. API: state["last_user_input"] 업데이트
   ↓
4. API: run_graph_step(state) 호출
   ↓
5. LangGraph: 현재 State에 해당하는 Node 실행
   ├─ INIT → init_node()
   ├─ CASE_CLASSIFICATION → case_classification_node()
   ├─ FACT_COLLECTION → fact_collection_node()
   │   ├─ 엔티티 추출 (EntityExtractor)
   │   ├─ 사실/감정 분리 (FactEmotionSplitter)
   │   ├─ RAG 검색 (RAGSearcher)
   │   └─ DB 저장 (각 서비스가 독립적으로 DB 세션 생성)
   ├─ VALIDATION → validation_node()
   ├─ RE_QUESTION → re_question_node()
   ├─ SUMMARY → summary_node()
   └─ COMPLETED → completed_node()
   ↓
6. API: save_session_state() (독립적인 DB 세션)
   ↓
7. API: 응답 반환
```

### 트랜잭션 범위
- 현재: 각 노드와 `save_session_state()`가 독립적인 트랜잭션 사용
- 권장: 하나의 사용자 메시지 처리 = 하나의 트랜잭션

---

## ✅ 결론

전체 시스템 통합 플로우는 전반적으로 잘 구성되어 있지만, **트랜잭션 관리**와 **에러 전파** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: 노드에 DB 세션 전달 방식 개선 (권장)
2. 🟡 **중간**: 에러 전파 시 트랜잭션 롤백 보장 (권장)
3. 🟢 **낮음**: 비동기 처리 개선 (선택적)
4. 🟢 **낮음**: 에러 처리 일관성 개선 (선택적)
5. 🟢 **낮음**: 트랜잭션 범위 문서화 (선택적)

**참고**: 현재 구조는 기능적으로 문제가 없지만, 데이터 일관성을 위해 트랜잭션 관리 개선을 권장합니다.

