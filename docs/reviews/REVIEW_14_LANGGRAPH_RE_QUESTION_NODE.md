# LangGraph RE_QUESTION 노드 검토 보고서

## 검토 대상
- 파일: `src/langgraph/nodes/re_question_node.py`
- 검토 일자: 2024년
- 검토 범위: 질문 생성, RAG 템플릿 활용, 우선순위 처리

---

## ✅ 정상 동작 부분

### 1. 누락 필드 검증 (Lines 34-39)
```python
if not missing_fields:
    logger.warning(f"[{session_id}] 누락 필드가 없습니다.")
    return {
        **state,
        "next_state": "SUMMARY"
    }
```
- ✅ 누락 필드 없을 때 적절한 처리

### 2. 우선순위 기반 필드 선택 (Lines 41-48)
```python
next_field = get_next_missing_field(missing_fields, case_type)
if not next_field:
    logger.warning(f"[{session_id}] 다음 질문할 필드를 찾을 수 없습니다.")
    return {
        **state,
        "next_state": "SUMMARY"
    }
```
- ✅ 우선순위 기반으로 다음 질문할 필드 선택
- ✅ 필드 선택 실패 시 적절한 처리

### 3. RAG 검색 및 예외 처리 (Lines 53-65)
```python
try:
    rag_results = rag_searcher.search(...)
    logger.debug(f"[{session_id}] RAG 검색 완료: {len(rag_results)}개 결과")
except Exception as e:
    logger.warning(f"[{session_id}] RAG 검색 실패 (계속 진행): {str(e)}")
    rag_results = []
```
- ✅ RAG 검색 예외 처리
- ✅ 검색 실패 시에도 계속 진행

### 4. RAG 결과에서 질문 추출 (Lines 71-110)
```python
if rag_results:
    # RAG 결과에서 질문 템플릿 추출 시도
    question_templates = k2_data.get("question_templates", {})
    if question_templates and isinstance(question_templates, dict):
        if next_field in question_templates:
            question = question_templates[next_field]
```
- ✅ RAG 결과에서 질문 템플릿 추출
- ✅ 여러 형식 지원 (question_templates, questions 리스트)

### 5. 폴백 메커니즘 (Lines 112-114)
```python
# RAG 결과가 없거나 추출 실패 시 YAML 파일에서 로드
if not question:
    question = get_question_message(next_field, case_type)
```
- ✅ RAG 실패 시 YAML 파일에서 질문 로드

### 6. State 업데이트 (Lines 116-121)
```python
state["bot_message"] = question
state["expected_input"] = {
    "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
    "field": next_field
}
```
- ✅ bot_message 및 expected_input 설정

### 7. 실행 시간 측정 (Line 15)
```python
@log_execution_time(logger)
def re_question_node(state: StateContext) -> Dict[str, Any]:
```
- ✅ 데코레이터로 실행 시간 측정

---

## ⚠️ 발견된 문제점

### 1. import 위치 (Lines 74-75)
**영향도**: 낮음  
**문제**: 
- `RAGDocumentParser`, `yaml`을 함수 내부에서 import
- 파일 상단에서 import하는 것이 일반적

**현재 코드**:
```python
if rag_results:
    try:
        from src.rag.parser import RAGDocumentParser
        import yaml
```

**권장 수정**:
```python
"""
RE_QUESTION Node 구현
"""
import yaml
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.rag.parser import RAGDocumentParser
# ... 나머지 imports ...
```

### 2. 사용되지 않는 Import (Line 74)
**영향도**: 낮음  
**문제**: 
- `RAGDocumentParser`를 import하지만 사용하지 않음

**수정**: 제거하거나 실제로 사용

### 3. YAML 파싱 에러 처리 부족 (Lines 83-86)
**영향도**: 낮음  
**문제**: 
- `yaml.safe_load`에서 예외 발생 시 빈 except 블록
- 에러 정보 손실

**현재 코드**:
```python
try:
    k2_data = yaml.safe_load(content)
except:
    k2_data = metadata
```

**권장 수정**:
```python
try:
    k2_data = yaml.safe_load(content)
    if not k2_data:
        k2_data = metadata
except yaml.YAMLError as e:
    logger.warning(f"[{session_id}] YAML 파싱 실패: {str(e)}, metadata 사용")
    k2_data = metadata
except Exception as e:
    logger.warning(f"[{session_id}] 예상치 못한 파싱 오류: {str(e)}, metadata 사용")
    k2_data = metadata
```

### 4. 에러 발생 시 raise만 함 (Lines 130-132)
**영향도**: 중간  
**문제**: 
- 예외 발생 시 raise만 하고 사용자에게 친화적인 응답 없음
- 애플리케이션 중단 가능

**현재 코드**:
```python
except Exception as e:
    logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}")
    raise
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리: 기본 질문 사용
    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        next_field = missing_fields[0]  # 첫 번째 누락 필드 사용
        question = get_question_message(next_field, state.get("case_type"))
        
        return {
            **state,
            "bot_message": question,
            "expected_input": {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            },
            "next_state": "FACT_COLLECTION"
        }
    else:
        return {
            **state,
            "next_state": "SUMMARY"
        }
```

### 5. 로깅에서 exc_info 누락 (Line 131)
**영역도**: 낮음  
**문제**: 
- 예외 발생 시 `exc_info=True` 없이 로깅
- 스택 트레이스 정보 부족

**수정**:
```python
except Exception as e:
    logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}", exc_info=True)
```

### 6. RAG 결과 파싱 로직 복잡 (Lines 71-110)
**영역도**: 낮음  
**문제**: 
- RAG 결과 파싱 로직이 복잡하고 중첩된 try-except
- 가독성 저하

**권장 개선**: 공통 함수로 추출
```python
def _extract_question_from_rag(rag_results: list, next_field: str, session_id: str) -> Optional[str]:
    """RAG 결과에서 질문 추출"""
    if not rag_results:
        return None
    
    try:
        import yaml
        result = rag_results[0]
        content = result.get("content", "")
        metadata = result.get("metadata", {})
        
        # content 파싱
        if isinstance(content, str):
            try:
                k2_data = yaml.safe_load(content)
            except yaml.YAMLError:
                k2_data = metadata
        else:
            k2_data = content if content else metadata
        
        # question_templates에서 찾기
        question_templates = k2_data.get("question_templates", {})
        if question_templates and isinstance(question_templates, dict):
            if next_field in question_templates:
                logger.info(f"[{session_id}] RAG에서 질문 템플릿 추출: {next_field}")
                return question_templates[next_field]
        
        # questions 리스트에서 찾기
        questions = k2_data.get("questions", [])
        if questions:
            for q in questions:
                if isinstance(q, dict) and q.get("field") == next_field:
                    question_text = q.get("question_text") or q.get("text")
                    if question_text:
                        logger.info(f"[{session_id}] RAG에서 질문 추출: {next_field}")
                        return question_text
        
        return None
    except Exception as e:
        logger.warning(f"[{session_id}] RAG 결과에서 질문 추출 실패: {str(e)}")
        return None
```

### 7. question이 None일 수 있음 (Line 114)
**영역도**: 낮음  
**문제**: 
- `get_question_message`가 None을 반환할 수 있음
- None 체크 없음

**권장 수정**:
```python
# RAG 결과가 없거나 추출 실패 시 YAML 파일에서 로드
if not question:
    question = get_question_message(next_field, case_type)
    if not question:
        logger.warning(f"[{session_id}] 질문을 찾을 수 없습니다: field={next_field}, case_type={case_type}")
        question = f"{next_field}에 대한 정보를 알려주세요."  # 기본 질문
```

---

## 🔍 추가 검토 사항

### 1. 질문 템플릿 캐싱
- 현재: 매번 RAG 검색 및 파싱
- 권장: 질문 템플릿 캐싱

### 2. 질문 개인화
- 현재: 템플릿만 사용
- 권장: 사용자 컨텍스트를 반영한 질문 생성

### 3. 질문 우선순위 동적 조정
- 현재: 고정된 우선순위
- 권장: 사용자 응답 패턴에 따른 동적 조정

---

## 📊 종합 평가

### 강점
1. ✅ 우선순위 기반 필드 선택
2. ✅ RAG 결과 활용
3. ✅ 폴백 메커니즘
4. ✅ 예외 처리 (RAG 검색)
5. ✅ 실행 시간 측정

### 개선 필요
1. 🟡 **중간**: 에러 처리 개선 (raise 대신 폴백)
2. 🟢 **낮음**: import 위치 정리
3. 🟢 **낮음**: 사용되지 않는 import 제거
4. 🟢 **낮음**: YAML 파싱 에러 처리 개선
5. 🟢 **낮음**: 로깅 개선
6. 🟢 **낮음**: RAG 결과 파싱 로직 개선
7. 🟢 **낮음**: question None 체크

### 우선순위
- **중간**: 에러 처리 개선
- **낮음**: import 정리, 로깅 개선, 파싱 로직 개선

---

## 📝 권장 수정 사항

### 수정 1: Import 정리
```python
"""
RE_QUESTION Node 구현
"""
import yaml
from typing import Dict, Any, Optional
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import FIELD_INPUT_TYPE_MAPPING
from src.utils.question_loader import get_question_message
from src.services.missing_field_manager import get_next_missing_field
```

### 수정 2: RAG 결과 파싱 함수 추출
```python
def _extract_question_from_rag(rag_results: list, next_field: str, session_id: str) -> Optional[str]:
    """RAG 결과에서 질문 추출"""
    # ... 위의 개선된 코드 ...
```

### 수정 3: 에러 처리 개선
```python
except Exception as e:
    logger.error(f"RE_QUESTION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리
    missing_fields = state.get("missing_fields", [])
    if missing_fields:
        next_field = missing_fields[0]
        question = get_question_message(next_field, state.get("case_type")) or f"{next_field}에 대한 정보를 알려주세요."
        
        return {
            **state,
            "bot_message": question,
            "expected_input": {
                "type": FIELD_INPUT_TYPE_MAPPING.get(next_field, "text"),
                "field": next_field
            },
            "next_state": "FACT_COLLECTION"
        }
    else:
        return {
            **state,
            "next_state": "SUMMARY"
        }
```

### 수정 4: question None 체크
```python
# RAG 결과가 없거나 추출 실패 시 YAML 파일에서 로드
if not question:
    question = get_question_message(next_field, case_type)
    if not question:
        logger.warning(f"[{session_id}] 질문을 찾을 수 없습니다: field={next_field}, case_type={case_type}")
        question = f"{next_field}에 대한 정보를 알려주세요."
```

---

## ✅ 검토 완료

**검토 항목**: `review_14_langgraph_re_question_node`  
**상태**: 완료  
**다음 항목**: `review_15_langgraph_summary_node`

