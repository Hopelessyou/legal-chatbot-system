# LangGraph INIT 노드 검토 보고서

## 검토 대상
- 파일: `src/langgraph/nodes/init_node.py`
- 검토 일자: 2024년
- 검토 범위: 초기화 로직, K0 메시지 로드, 세션 생성

---

## ✅ 정상 동작 부분

### 1. K0 메시지 로드 (Lines 18-41)
```python
def _load_k0_messages() -> Optional[Dict[str, Any]]:
    """K0 Intake YAML 파일 로드"""
    k0_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
    k0_data = RAGDocumentParser.load_yaml(k0_path)
    return k0_data
```
- ✅ YAML 파일 로드
- ✅ 파일 없을 때 None 반환
- ✅ 예외 처리

### 2. 초기 메시지 생성 (Lines 44-104)
```python
def _build_initial_message(k0_data: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """초기 메시지 생성"""
    # MESSAGE_ORDER 순서대로 메시지 결합
    messages = sorted(k0_data["messages"], key=lambda x: x.get("order", 999))
    # ...
```
- ✅ 메시지 순서 정렬
- ✅ next_action에 따른 필터링
- ✅ expected_input 설정
- ✅ 기본 메시지 폴백

### 3. 세션 생성 (Lines 126-152)
```python
with db_manager.get_db_session() as db_session:
    existing_session = db_session.query(ChatSession).filter(...).first()
    if not existing_session:
        new_session = ChatSession(...)
        db_session.add(new_session)
        db_session.commit()
```
- ✅ DB 세션 관리 적절
- ✅ 기존 세션 확인
- ✅ 새 세션 생성

### 4. 에러 처리 (Lines 170-182)
```python
except Exception as e:
    logger.error(f"INIT Node 실행 실패: {str(e)}", exc_info=True)
    # 에러가 발생해도 기본 메시지로 응답
    return {
        **state,
        "bot_message": "안녕하세요. 법률 상담을 도와드리겠습니다...",
        "next_state": "CASE_CLASSIFICATION"
    }
```
- ✅ 예외 발생 시에도 기본 메시지 반환
- ✅ 애플리케이션 중단 방지

### 5. 실행 시간 측정 (Line 107)
```python
@log_execution_time(logger)
def init_node(state: StateContext) -> Dict[str, Any]:
```
- ✅ 데코레이터로 실행 시간 측정

---

## ⚠️ 발견된 문제점

### 1. 경로 계산 복잡성 (Lines 27-29)
```python
current_file = Path(__file__)
project_root = current_file.parent.parent.parent.parent
k0_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
```
**영향도**: 중간  
**문제**: 
- `parent.parent.parent.parent`는 취약함
- 파일 구조 변경 시 깨질 수 있음
- 상대 경로 계산이 복잡

**권장 수정**:
```python
from pathlib import Path
from config.settings import settings

def _load_k0_messages() -> Optional[Dict[str, Any]]:
    """K0 Intake YAML 파일 로드"""
    try:
        # 설정에서 경로 가져오기 또는 상대 경로 사용
        # 방법 1: 설정 파일에서 경로 관리
        k0_path = Path(settings.rag_data_directory or "./data/rag") / "K0_intake" / "intake_messages.yaml"
        
        # 방법 2: 프로젝트 루트 찾기 (더 견고한 방법)
        current_file = Path(__file__)
        # src/langgraph/nodes/init_node.py에서 프로젝트 루트까지
        project_root = current_file.parent.parent.parent.parent
        k0_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
        
        # 방법 3: 절대 경로 또는 환경변수 사용
        # k0_path = Path(os.getenv("K0_MESSAGES_PATH", "./data/rag/K0_intake/intake_messages.yaml"))
        
        if not k0_path.exists():
            logger.warning(f"K0 YAML 파일을 찾을 수 없습니다: {k0_path}")
            return None
        
        k0_data = RAGDocumentParser.load_yaml(k0_path)
        logger.info(f"K0 메시지 로드 완료: {len(k0_data.get('messages', []))}개 메시지")
        return k0_data
    
    except Exception as e:
        logger.error(f"K0 YAML 로드 실패: {str(e)}", exc_info=True)
        return None
```

### 2. 사용되지 않는 변수 (Line 64)
```python
step_code = msg.get("step_code", "").upper()
```
**영향도**: 낮음  
**문제**: `step_code`를 읽지만 사용하지 않음  
**수정 필요**: 제거하거나 사용

### 3. K0 파일 경로 하드코딩 (Line 29)
```python
k0_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
```
**영향도**: 낮음  
**문제**: 
- 파일명이 하드코딩됨
- 다른 파일명 사용 불가

**권장 개선**: 설정 파일에서 관리

### 4. DB 오류 시 계속 진행 (Lines 150-152)
```python
except Exception as db_error:
    logger.error(f"DB 세션 생성 실패: {str(db_error)}")
    # DB 오류가 있어도 계속 진행 (세션은 메모리에 저장됨)
```
**영향도**: 낮음  
**현황**: 적절한 처리 (애플리케이션 중단 방지)  
**주의사항**: 
- DB 오류가 지속되면 세션 정보 손실 가능
- 모니터링 필요

### 5. 메시지 필터링 로직 복잡 (Lines 62-88)
```python
for msg in messages:
    next_action = msg.get("next_action", "").upper()
    # ...
    if next_action in ["STOP", "INTERNAL_ONLY"]:
        continue
    if next_action == "ROUTE_EMERGENCY":
        continue
    # ...
```
**영향도**: 낮음  
**현황**: 로직은 명확하지만, 필터링 조건이 여러 곳에 분산  
**권장 개선**: 필터링 조건을 상수로 분리

### 6. expected_input 중복 설정 (Lines 79-88, 92-96)
```python
if next_action in ["CLASSIFY", "CLASSIFY_TEXT", "CLASSIFY_MENU"]:
    expected_input = {...}  # 설정
# ...
if not expected_input:
    expected_input = {...}  # 기본값
```
**영향도**: 낮음  
**현황**: 적절한 폴백 로직  
**권장사항**: 현재 상태 유지

### 7. K0 데이터 캐싱 없음
**영향도**: 낮음  
**문제**: 
- 매번 파일을 읽음
- 성능 저하 가능

**권장 개선**:
```python
_k0_cache = None
_k0_cache_time = None

def _load_k0_messages() -> Optional[Dict[str, Any]]:
    """K0 Intake YAML 파일 로드 (캐싱)"""
    global _k0_cache, _k0_cache_time
    
    # 캐시가 있고 최근 1시간 이내면 재사용
    if _k0_cache and _k0_cache_time:
        from datetime import datetime, timedelta
        if datetime.now() - _k0_cache_time < timedelta(hours=1):
            return _k0_cache
    
    # 파일 로드
    # ... 기존 로직 ...
    
    # 캐시 저장
    _k0_cache = k0_data
    _k0_cache_time = datetime.now()
    return k0_data
```

### 8. 세션 ID 검증 없음 (Line 119)
```python
session_id = state.get("session_id")
```
**영향도**: 낮음  
**문제**: 
- session_id 형식 검증 없음
- 잘못된 형식의 ID 사용 가능

**권장 수정**:
```python
from src.services.session_manager import validate_session_id

session_id = state.get("session_id")
if session_id and not validate_session_id(session_id):
    logger.warning(f"유효하지 않은 세션 ID 형식: {session_id}")
    session_id = None  # 새로 생성
```

---

## 🔍 추가 검토 사항

### 1. K0 메시지 구조 검증
- 현재: 구조 검증 없음
- 권장: Pydantic 모델로 검증

### 2. 다국어 지원
- 현재: 한국어만 지원
- 권장: 다국어 메시지 로드

### 3. 채널별 초기 메시지
- 현재: 채널 구분 없음
- 권장: 채널별 다른 메시지

### 4. 사용자 컨텍스트
- 현재: user_hash만 저장
- 권장: 추가 사용자 정보 활용

---

## 📊 종합 평가

### 강점
1. ✅ K0 메시지 동적 로드
2. ✅ 메시지 순서 및 필터링 로직
3. ✅ DB 세션 생성 및 관리
4. ✅ 에러 발생 시 기본 메시지 반환
5. ✅ 실행 시간 측정

### 개선 필요
1. 🟡 **중간**: 경로 계산 개선
2. 🟡 **중간**: K0 데이터 캐싱
3. 🟢 **낮음**: 사용되지 않는 변수 제거
4. 🟢 **낮음**: 세션 ID 검증
5. 🟢 **낮음**: 필터링 조건 상수화

### 우선순위
- **중간**: 경로 계산 개선, K0 캐싱
- **낮음**: 변수 정리, 검증 추가

---

## 📝 권장 수정 사항

### 수정 1: 경로 계산 개선
```python
from pathlib import Path
from config.settings import settings

def _get_k0_path() -> Path:
    """K0 파일 경로 획득"""
    # 설정에서 경로 가져오기
    if hasattr(settings, 'k0_messages_path') and settings.k0_messages_path:
        return Path(settings.k0_messages_path)
    
    # 기본 경로
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"

def _load_k0_messages() -> Optional[Dict[str, Any]]:
    """K0 Intake YAML 파일 로드"""
    try:
        k0_path = _get_k0_path()
        
        if not k0_path.exists():
            logger.warning(f"K0 YAML 파일을 찾을 수 없습니다: {k0_path}")
            return None
        
        k0_data = RAGDocumentParser.load_yaml(k0_path)
        logger.info(f"K0 메시지 로드 완료: {len(k0_data.get('messages', []))}개 메시지")
        return k0_data
    
    except Exception as e:
        logger.error(f"K0 YAML 로드 실패: {str(e)}", exc_info=True)
        return None
```

### 수정 2: K0 데이터 캐싱
```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

_k0_cache: Optional[Dict[str, Any]] = None
_k0_cache_time: Optional[datetime] = None
_K0_CACHE_TTL = timedelta(hours=1)

def _load_k0_messages(force_reload: bool = False) -> Optional[Dict[str, Any]]:
    """K0 Intake YAML 파일 로드 (캐싱)"""
    global _k0_cache, _k0_cache_time
    
    # 캐시 확인
    if not force_reload and _k0_cache and _k0_cache_time:
        if datetime.now() - _k0_cache_time < _K0_CACHE_TTL:
            logger.debug("K0 메시지 캐시 사용")
            return _k0_cache
    
    # 파일 로드
    try:
        k0_path = _get_k0_path()
        
        if not k0_path.exists():
            logger.warning(f"K0 YAML 파일을 찾을 수 없습니다: {k0_path}")
            return None
        
        k0_data = RAGDocumentParser.load_yaml(k0_path)
        
        # 캐시 저장
        _k0_cache = k0_data
        _k0_cache_time = datetime.now()
        
        logger.info(f"K0 메시지 로드 완료: {len(k0_data.get('messages', []))}개 메시지")
        return k0_data
    
    except Exception as e:
        logger.error(f"K0 YAML 로드 실패: {str(e)}", exc_info=True)
        return None
```

### 수정 3: 사용되지 않는 변수 제거
```python
for msg in messages:
    next_action = msg.get("next_action", "").upper()
    # step_code = msg.get("step_code", "").upper()  # 제거
    
    # ... 나머지 로직 ...
```

### 수정 4: 필터링 조건 상수화
```python
# 파일 상단에 상수 정의
EXCLUDED_NEXT_ACTIONS = ["STOP", "INTERNAL_ONLY", "ROUTE_EMERGENCY"]
CLASSIFY_ACTIONS = ["CLASSIFY", "CLASSIFY_TEXT", "CLASSIFY_MENU"]

def _build_initial_message(k0_data: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """초기 메시지 생성"""
    if k0_data and "messages" in k0_data:
        messages = sorted(k0_data["messages"], key=lambda x: x.get("order", 999))
        message_parts = []
        expected_input = None
        
        for msg in messages:
            next_action = msg.get("next_action", "").upper()
            
            # 제외할 액션 필터링
            if next_action in EXCLUDED_NEXT_ACTIONS:
                continue
            
            message_text = msg.get("message_text", "")
            if message_text:
                message_parts.append(message_text)
            
            # CLASSIFY 액션 처리
            if next_action in CLASSIFY_ACTIONS:
                answer_type = msg.get("answer_type", "string")
                expected_input = {
                    "type": answer_type,
                    "description": "사건 상황 설명" if answer_type == "string" else "선택"
                }
                if answer_type == "choice" and "options" in msg:
                    expected_input["options"] = msg["options"]
        
        # ... 나머지 로직 ...
```

### 수정 5: 세션 ID 검증
```python
from src.services.session_manager import validate_session_id

def init_node(state: StateContext) -> Dict[str, Any]:
    """INIT Node 실행"""
    try:
        session_id = state.get("session_id")
        
        # 세션 ID 검증
        if session_id and not validate_session_id(session_id):
            logger.warning(f"유효하지 않은 세션 ID 형식: {session_id}, 새로 생성")
            session_id = None
        
        # 세션 ID가 없으면 생성
        if not session_id:
            session_id = generate_session_id()
            state["session_id"] = session_id
        
        # ... 나머지 로직 ...
```

---

## ✅ 검토 완료

**검토 항목**: `review_10_langgraph_init_node`  
**상태**: 완료  
**다음 항목**: `review_11_langgraph_classification_node`

