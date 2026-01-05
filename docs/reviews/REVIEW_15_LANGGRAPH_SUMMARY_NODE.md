# LangGraph SUMMARY 노드 검토 보고서

## 검토 대상
- 파일: `src/langgraph/nodes/summary_node.py`
- 검토 일자: 2024년
- 검토 범위: 요약 생성, K4 포맷 활용, DB 저장, 상태 전이

---

## ✅ 정상 동작 부분

### 1. Context 취합 (Lines 34-67)
```python
# 사용자 입력 텍스트 수집 (DB의 CaseFact에서 source_text 수집)
user_inputs = []
with db_manager.get_db_session() as db_session:
    case = db_session.query(CaseMaster).filter(...).first()
    if case:
        case_facts = db_session.query(CaseFact).filter(...).all()
        for fact in case_facts:
            if fact.source_text:
                user_inputs.append(fact.source_text)
```
- ✅ DB에서 사용자 입력 수집
- ✅ Context 구성

### 2. RAG K4 포맷 조회 (Lines 69-122)
```python
rag_results = rag_searcher.search(
    query="요약 포맷",
    knowledge_type="K4",
    main_case_type=main_case_type_en,
    sub_case_type=sub_case_type,
    top_k=1
)
```
- ✅ K4 문서 검색
- ✅ 예외 처리

### 3. K4 문서 파싱 (Lines 107-119)
```python
k4_doc = RAGDocumentParser.parse_k4_document(k4_data)
format_template = {
    "sections": k4_doc.sections,
    "target": k4_doc.target,
    "main_case_type": main_case_type_en,
    "sub_case_type": sub_case_type
}
```
- ✅ K4 문서 파싱
- ✅ 포맷 템플릿 구성

### 4. 요약 생성 (Lines 124-132)
```python
summary_result = summarizer.generate_final_summary(
    context=context,
    format_template=format_template
)
```
- ✅ Summarizer 서비스 활용
- ✅ 로깅

### 5. DB 저장 (Lines 134-158)
```python
with db_manager.get_db_session() as db_session:
    # 기존 요약 삭제
    db_session.query(CaseSummary).filter(...).delete()
    # 새 요약 저장
    summary = CaseSummary(...)
    db_session.add(summary)
    db_session.commit()
```
- ✅ CaseSummary 저장
- ✅ 기존 요약 삭제 후 새로 추가

### 6. **LangGraph 흐름 준수** (Lines 166-172) ✅
```python
# graph.py에서 이미 SUMMARY → COMPLETED 엣지가 정의되어 있으므로
# next_state만 반환하면 LangGraph가 자동으로 COMPLETED 노드로 전이함
return {
    **state,
    "next_state": "COMPLETED"
}
```
- ✅ **직접 노드 호출하지 않음**
- ✅ **next_state를 사용하여 그래프 흐름 준수**
- ✅ **VALIDATION 노드와 대조적으로 올바른 구현**

### 7. 실행 시간 측정 (Line 17)
```python
@log_execution_time(logger)
def summary_node(state: StateContext) -> Dict[str, Any]:
```
- ✅ 데코레이터로 실행 시간 측정

---

## ⚠️ 발견된 문제점

### 1. 중복된 DB 세션 (Lines 37, 135)
**영향도**: 중간  
**문제**: 
- DB 세션을 두 번 열고 닫음
- 트랜잭션 분리로 인한 일관성 문제 가능

**현재 코드**:
```python
# 첫 번째 DB 세션 (Lines 37-50)
with db_manager.get_db_session() as db_session:
    # CaseFact 조회
    case_facts = db_session.query(CaseFact).filter(...).all()

# 두 번째 DB 세션 (Lines 135-158)
with db_manager.get_db_session() as db_session:
    # CaseSummary 저장
    db_session.commit()
```

**권장 수정**: 단일 DB 세션으로 통합
```python
with db_manager.get_db_session() as db_session:
    try:
        case = db_session.query(CaseMaster).filter(...).first()
        
        if case:
            # CaseFact 조회
            from src.db.models.case_fact import CaseFact
            case_facts = db_session.query(CaseFact).filter(...).all()
            
            for fact in case_facts:
                if fact.source_text:
                    user_inputs.append(fact.source_text)
            
            # ... 요약 생성 ...
            
            # CaseSummary 저장
            db_session.query(CaseSummary).filter(...).delete()
            summary = CaseSummary(...)
            db_session.add(summary)
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"[{session_id}] DB 저장 실패: {str(e)}")
        raise
```

### 2. import 위치 (Lines 43, 74, 89-90)
**영역도**: 낮음  
**문제**: 
- `CaseFact`, `CASE_TYPE_MAPPING`, `RAGDocumentParser`, `yaml`을 함수 내부에서 import
- 파일 상단에서 import하는 것이 일반적

**현재 코드**:
```python
if case:
    from src.db.models.case_fact import CaseFact
    # ...
from src.utils.constants import CASE_TYPE_MAPPING
# ...
from src.rag.parser import RAGDocumentParser
import yaml
```

**권장 수정**:
```python
"""
SUMMARY Node 구현
"""
import json
import yaml
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.summarizer import summarizer
from src.rag.searcher import rag_searcher
from src.rag.parser import RAGDocumentParser
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import CASE_TYPE_MAPPING
from src.db.connection import db_manager
from src.db.models.case_summary import CaseSummary
from src.db.models.case_master import CaseMaster
from src.db.models.case_fact import CaseFact
```

### 3. YAML 파싱 에러 처리 부족 (Lines 99-103)
**영역도**: 낮음  
**문제**: 
- `yaml.safe_load`에서 예외 발생 시 빈 except 블록
- 에러 정보 손실

**현재 코드**:
```python
try:
    k4_data = yaml.safe_load(content)
except:
    # YAML 파싱 실패 시 metadata에서 정보 추출
    k4_data = metadata
```

**권장 수정**:
```python
try:
    k4_data = yaml.safe_load(content)
    if not k4_data:
        k4_data = metadata
except yaml.YAMLError as e:
    logger.warning(f"[{session_id}] YAML 파싱 실패: {str(e)}, metadata 사용")
    k4_data = metadata
except Exception as e:
    logger.warning(f"[{session_id}] 예상치 못한 파싱 오류: {str(e)}, metadata 사용")
    k4_data = metadata
```

### 4. 에러 발생 시 raise만 함 (Lines 174-176)
**영역도**: 중간  
**문제**: 
- 예외 발생 시 raise만 하고 사용자에게 친화적인 응답 없음
- 애플리케이션 중단 가능

**현재 코드**:
```python
except Exception as e:
    logger.error(f"SUMMARY Node 실행 실패: {str(e)}")
    raise
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"SUMMARY Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리: 기본 메시지 반환
    return {
        **state,
        "bot_message": "요약 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
        "expected_input": None,
        "next_state": "COMPLETED"
    }
```

### 5. 로깅에서 exc_info 누락 (Line 175)
**영역도**: 낮음  
**문제**: 
- 예외 발생 시 `exc_info=True` 없이 로깅
- 스택 트레이스 정보 부족

**수정**:
```python
except Exception as e:
    logger.error(f"SUMMARY Node 실행 실패: {str(e)}", exc_info=True)
```

### 6. summary_result 검증 없음 (Lines 147-150)
**영역도**: 낮음  
**문제**: 
- `summary_result`에서 필수 필드 존재 여부 확인 없음
- KeyError 가능

**권장 수정**:
```python
# summary_result 검증
if not summary_result or "summary_text" not in summary_result:
    logger.error(f"[{session_id}] 요약 생성 실패: summary_result가 유효하지 않음")
    raise ValueError("요약 생성 결과가 유효하지 않습니다.")

summary = CaseSummary(
    case_id=case.case_id,
    summary_text=summary_result.get("summary_text", ""),
    structured_json=summary_result.get("structured_data"),
    risk_level=None,
    ai_version="gpt-4-turbo-preview"
)
```

### 7. bot_message 하드코딩 (Line 161)
**영역도**: 낮음  
**문제**: 
- bot_message가 하드코딩됨
- 요약 완료 메시지가 더 적절할 수 있음

**권장 개선**: 요약 내용의 일부를 포함하거나 더 구체적인 메시지

---

## 🔍 추가 검토 사항

### 1. 요약 결과 검증
- 현재: 기본적인 검증만 수행
- 권장: 요약 텍스트 길이, 구조화 데이터 형식 검증

### 2. 요약 캐싱
- 현재: 매번 요약 생성
- 권장: 동일한 facts에 대한 요약 캐싱

### 3. 요약 품질 검증
- 현재: 품질 검증 없음
- 권장: 요약 품질 점수 계산

---

## 📊 종합 평가

### 강점
1. ✅ **LangGraph 흐름 준수** (직접 노드 호출하지 않음)
2. ✅ Context 취합
3. ✅ RAG K4 포맷 활용
4. ✅ 요약 생성 및 DB 저장
5. ✅ 실행 시간 측정

### 개선 필요
1. 🟡 **중간**: 중복된 DB 세션 통합
2. 🟡 **중간**: 에러 처리 개선
3. 🟢 **낮음**: import 위치 정리
4. 🟢 **낮음**: YAML 파싱 에러 처리 개선
5. 🟢 **낮음**: 로깅 개선
6. 🟢 **낮음**: summary_result 검증
7. 🟢 **낮음**: bot_message 개선

### 우선순위
- **중간**: DB 세션 통합, 에러 처리 개선
- **낮음**: import 정리, 로깅 개선, 검증 추가

---

## 📝 권장 수정 사항

### 수정 1: Import 정리
```python
"""
SUMMARY Node 구현
"""
import json
import yaml
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.summarizer import summarizer
from src.rag.searcher import rag_searcher
from src.rag.parser import RAGDocumentParser
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import CASE_TYPE_MAPPING
from src.db.connection import db_manager
from src.db.models.case_summary import CaseSummary
from src.db.models.case_master import CaseMaster
from src.db.models.case_fact import CaseFact
```

### 수정 2: DB 세션 통합
```python
# 단일 DB 세션으로 통합
with db_manager.get_db_session() as db_session:
    try:
        case = db_session.query(CaseMaster).filter(...).first()
        
        if case:
            # CaseFact 조회
            case_facts = db_session.query(CaseFact).filter(...).all()
            for fact in case_facts:
                if fact.source_text:
                    user_inputs.append(fact.source_text)
            
            # ... 요약 생성 ...
            
            # CaseSummary 저장
            db_session.query(CaseSummary).filter(...).delete()
            summary = CaseSummary(...)
            db_session.add(summary)
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"[{session_id}] DB 저장 실패: {str(e)}")
        raise
```

### 수정 3: YAML 파싱 에러 처리 개선
```python
try:
    k4_data = yaml.safe_load(content)
    if not k4_data:
        k4_data = metadata
except yaml.YAMLError as e:
    logger.warning(f"[{session_id}] YAML 파싱 실패: {str(e)}, metadata 사용")
    k4_data = metadata
except Exception as e:
    logger.warning(f"[{session_id}] 예상치 못한 파싱 오류: {str(e)}, metadata 사용")
    k4_data = metadata
```

### 수정 4: 에러 처리 개선
```python
except Exception as e:
    logger.error(f"SUMMARY Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리
    return {
        **state,
        "bot_message": "요약 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
        "expected_input": None,
        "next_state": "COMPLETED"
    }
```

### 수정 5: summary_result 검증
```python
# summary_result 검증
if not summary_result or "summary_text" not in summary_result:
    logger.error(f"[{session_id}] 요약 생성 실패: summary_result가 유효하지 않음")
    raise ValueError("요약 생성 결과가 유효하지 않습니다.")

summary = CaseSummary(
    case_id=case.case_id,
    summary_text=summary_result.get("summary_text", ""),
    structured_json=summary_result.get("structured_data"),
    risk_level=None,
    ai_version="gpt-4-turbo-preview"
)
```

---

## ✅ 검토 완료

**검토 항목**: `review_15_langgraph_summary_node`  
**상태**: 완료  
**다음 항목**: `review_16_langgraph_completed_node`

**특별 언급**: 
- **SUMMARY 노드는 LangGraph 흐름을 올바르게 준수합니다.** `next_state`를 사용하여 COMPLETED 노드로 전이하며, 직접 노드 호출을 하지 않습니다. 이는 VALIDATION 노드와 대조적이며, 다른 노드들도 이 패턴을 따라야 합니다.

