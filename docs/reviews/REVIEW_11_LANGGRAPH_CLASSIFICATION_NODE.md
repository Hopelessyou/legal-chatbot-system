# LangGraph CASE_CLASSIFICATION 노드 검토 보고서

## 검토 대상
- 파일: `src/langgraph/nodes/case_classification_node.py`
- 검토 일자: 2024년
- 검토 범위: 사건 분류 로직, RAG 검색, GPT 호출, 폴백 처리

---

## ✅ 정상 동작 부분

### 1. 키워드 및 의미 추출 (Lines 50-52)
```python
semantic_features = keyword_extractor.extract_semantic_features(user_input)
keywords = semantic_features.get("keywords", [])
```
- ✅ 키워드 추출을 통한 검색 쿼리 생성
- ✅ 의미적 특징 추출 활용

### 2. RAG K1 검색 (Lines 54-60)
```python
rag_results = rag_searcher.search_by_knowledge_type(
    query=query,
    knowledge_type="K1",
    top_k=3
)
```
- ✅ K1 문서 타입으로 사건 유형 분류 기준 검색
- ✅ top_k=3으로 여러 결과 검색

### 3. RAG 결과 활용 (Lines 66-71)
```python
if rag_results:
    best_match = rag_results[0]
    metadata = best_match.get("metadata", {})
    main_case_type = metadata.get("main_case_type")
    sub_case_type = metadata.get("sub_case_type")
```
- ✅ 가장 유사도 높은 결과 사용
- ✅ 메타데이터에서 사건 유형 추출

### 4. 폴백 메커니즘 (Lines 140-143)
```python
except Exception as e:
    logger.error(f"GPT 분류 실패: {str(e)}")
    # 폴백: 키워드 기반 간단한 분류
    main_case_type, sub_case_type = get_fallback_case_type(user_input)
```
- ✅ GPT 실패 시 키워드 기반 폴백
- ✅ 에러 로깅

### 5. DB 저장 (Lines 152-179)
```python
with db_manager.get_db_session() as db_session:
    case = db_session.query(CaseMaster).filter(...).first()
    if not case:
        case = CaseMaster(...)
        db_session.add(case)
    else:
        case.main_case_type = main_case_type_en
        case.sub_case_type = sub_case_type
    db_session.commit()
```
- ✅ CaseMaster 생성/업데이트
- ✅ 세션 상태 업데이트
- ✅ DB 세션 관리 적절

### 6. 실행 시간 측정 (Line 25)
```python
@log_execution_time(logger)
def case_classification_node(state: StateContext) -> Dict[str, Any]:
```
- ✅ 데코레이터로 실행 시간 측정

### 7. 사용자 입력 검증 (Lines 42-48)
```python
if not user_input:
    logger.warning("사용자 입력이 없습니다.")
    return {
        **state,
        "bot_message": "사건과 관련된 내용을 알려주세요.",
        "next_state": "CASE_CLASSIFICATION"
    }
```
- ✅ 입력 없을 때 적절한 응답

---

## ⚠️ 발견된 문제점

### 1. RAG 결과를 GPT 프롬프트에 포함하지 않음 (Lines 73-143)
**영향도**: 높음  
**문제**: 
- RAG 결과가 있어도 GPT 프롬프트에 포함하지 않음
- RAG 결과를 참고하라는 주석이 있지만 실제로는 활용하지 않음
- RAG 결과가 없을 때만 GPT를 호출하는 구조

**현재 로직**:
```python
if rag_results:
    # RAG 결과 사용
    main_case_type = metadata.get("main_case_type")
    sub_case_type = metadata.get("sub_case_type")

# GPT API로 최종 분류 (RAG 결과를 참고)
if not main_case_type:
    # GPT 호출
```

**권장 수정**:
```python
# RAG 결과를 GPT 프롬프트에 포함
rag_context = ""
if rag_results:
    best_match = rag_results[0]
    metadata = best_match.get("metadata", {})
    rag_main_case_type = metadata.get("main_case_type")
    rag_sub_case_type = metadata.get("sub_case_type")
    
    # RAG 결과를 컨텍스트로 포함
    rag_context = f"""
참고할 수 있는 유사 사건 유형:
- 주요 유형: {rag_main_case_type}
- 세부 유형: {rag_sub_case_type}
- 유사도: {best_match.get('score', 0):.2f}
"""

# GPT API로 최종 분류 (RAG 결과를 참고)
classification_prompt = f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
{rag_context}
...
"""
```

### 2. 중복된 프롬프트 코드 (Lines 83-96, 99-112)
**영향도**: 중간  
**문제**: 
- 기본 프롬프트가 두 곳에 중복 정의됨
- 유지보수 어려움

**권장 수정**:
```python
def _get_classification_prompt(user_input: str, rag_context: str = "") -> str:
    """분류 프롬프트 생성"""
    try:
        from src.services.prompt_loader import prompt_loader
        prompt_template = prompt_loader.load_prompt("case_classification", sub_dir="classification")
        if prompt_template:
            return prompt_template.format(user_input=user_input, rag_context=rag_context)
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
    
    # 기본 프롬프트
    return f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
{rag_context}
가능한 분류:
- 민사: 계약, 불법행위, 대여금, 손해배상
- 형사: 사기, 성범죄, 폭행
- 가사: 이혼, 상속
- 행정: 행정처분, 세무

텍스트: {user_input}

JSON 형식으로 반환:
{{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}}"""
```

### 3. JSON 파싱 로직 복잡 및 에러 처리 부족 (Lines 121-139)
**영향도**: 중간  
**문제**: 
- 정규식으로 JSON 추출하는 로직이 복잡함
- JSON 파싱 실패 시 상세한 에러 정보 없음
- 마크다운 코드 블록 처리 로직이 복잡

**현재 코드**:
```python
content = response["content"].strip()
json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
if json_match:
    content = json_match.group(1)
else:
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)

classification = json.loads(content)
```

**권장 수정**:
```python
from src.utils.helpers import parse_json_from_text

try:
    content = response["content"].strip()
    classification = parse_json_from_text(content)
    
    if not classification:
        raise ValueError("JSON 파싱 결과가 None입니다.")
    
    main_case_type = classification.get("main_case_type")
    sub_case_type = classification.get("sub_case_type")
    
    if not main_case_type:
        raise ValueError("main_case_type이 없습니다.")
        
except (json.JSONDecodeError, ValueError) as e:
    logger.error(f"JSON 파싱 실패: {str(e)}, 원본 응답: {content[:200]}")
    # 폴백 처리
    main_case_type, sub_case_type = get_fallback_case_type(user_input)
```

### 4. 사용되지 않는 Import (Lines 12-13)
**영향도**: 낮음  
**문제**: 
- `DEFAULT_CASE_TYPE`, `DEFAULT_SUB_CASE_TYPE`를 import하지만 사용하지 않음

**수정**:
```python
from src.utils.constants import (
    CASE_TYPE_MAPPING,
    # DEFAULT_CASE_TYPE,  # 사용되지 않음
    # DEFAULT_SUB_CASE_TYPE,  # 사용되지 않음
    CaseStage,
    Limits
)
```

### 5. 에러 발생 시 raise만 함 (Lines 204-206)
**영역도**: 중간  
**문제**: 
- 예외 발생 시 raise만 하고 사용자에게 친화적인 응답 없음
- 애플리케이션 중단 가능

**현재 코드**:
```python
except Exception as e:
    logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}")
    raise
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리
    main_case_type, sub_case_type = get_fallback_case_type(user_input or "")
    main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type) if main_case_type else None
    
    return {
        **state,
        "case_type": main_case_type_en,
        "sub_case_type": sub_case_type,
        "bot_message": "사건과 관련된 구체적인 내용을 알려주세요.",
        "expected_input": {
            "type": "text",
            "field": "fact_description"
        },
        "next_state": "FACT_COLLECTION"
    }
```

### 6. RAG 결과가 있을 때 GPT를 호출하지 않음
**영향도**: 중간  
**문제**: 
- RAG 결과가 있으면 GPT를 호출하지 않음
- RAG 결과의 정확도를 GPT로 검증/보완할 수 없음

**현재 로직**:
```python
if rag_results:
    # RAG 결과 사용
    main_case_type = metadata.get("main_case_type")
    sub_case_type = metadata.get("sub_case_type")

# GPT API로 최종 분류 (RAG 결과를 참고)
if not main_case_type:  # RAG 결과가 없을 때만 GPT 호출
    # GPT 호출
```

**권장 개선**:
```python
# RAG 결과가 있어도 GPT로 검증/보완
rag_suggestion = None
if rag_results:
    best_match = rag_results[0]
    metadata = best_match.get("metadata", {})
    rag_suggestion = {
        "main_case_type": metadata.get("main_case_type"),
        "sub_case_type": metadata.get("sub_case_type"),
        "score": best_match.get("score", 0)
    }

# GPT API로 최종 분류 (RAG 결과를 참고)
# RAG 결과가 있어도 GPT로 최종 결정
try:
    rag_context = ""
    if rag_suggestion:
        rag_context = f"""
참고할 수 있는 유사 사건 유형:
- 주요 유형: {rag_suggestion['main_case_type']}
- 세부 유형: {rag_suggestion['sub_case_type']}
- 유사도: {rag_suggestion['score']:.2f}
"""
    
    classification_prompt = _get_classification_prompt(user_input, rag_context)
    response = gpt_client.chat_completion(...)
    classification = parse_json_from_text(response["content"])
    
    main_case_type = classification.get("main_case_type")
    sub_case_type = classification.get("sub_case_type")
    
except Exception as e:
    logger.error(f"GPT 분류 실패: {str(e)}")
    # 폴백: RAG 결과 또는 키워드 기반
    if rag_suggestion:
        main_case_type = rag_suggestion["main_case_type"]
        sub_case_type = rag_suggestion["sub_case_type"]
    else:
        main_case_type, sub_case_type = get_fallback_case_type(user_input)
```

### 7. CaseMaster import 중복 (Line 19, 160)
**영역도**: 낮음  
**문제**: 
- `CaseMaster`를 파일 상단과 함수 내부에서 import

**수정**:
```python
# 파일 상단에서만 import
from src.db.models.case_master import CaseMaster
```

### 8. 로깅에서 exc_info 누락 (Line 205)
**영역도**: 낮음  
**문제**: 
- 예외 발생 시 `exc_info=True` 없이 로깅
- 스택 트레이스 정보 부족

**수정**:
```python
except Exception as e:
    logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}", exc_info=True)
```

### 9. 하드코딩된 분류 목록 (Lines 85-88, 101-104)
**영역도**: 낮음  
**문제**: 
- 분류 목록이 프롬프트에 하드코딩됨
- 변경 시 여러 곳 수정 필요

**권장 개선**: 설정 파일 또는 상수로 관리

---

## 🔍 추가 검토 사항

### 1. RAG 결과 신뢰도 임계값
- 현재: RAG 결과가 있으면 무조건 사용
- 권장: 유사도 점수가 임계값 이상일 때만 사용

### 2. GPT 응답 검증
- 현재: JSON 파싱만 수행
- 권장: 필수 필드 검증, 유효한 case_type인지 확인

### 3. 분류 결과 캐싱
- 현재: 매번 GPT 호출
- 권장: 유사한 입력에 대해 캐싱

### 4. 다중 RAG 결과 활용
- 현재: 첫 번째 결과만 사용
- 권장: 상위 3개 결과를 모두 GPT에 제공

---

## 📊 종합 평가

### 강점
1. ✅ 키워드 추출 및 RAG 검색 활용
2. ✅ 폴백 메커니즘 구현
3. ✅ DB 저장 및 상태 관리
4. ✅ 실행 시간 측정
5. ✅ 사용자 입력 검증

### 개선 필요
1. 🔴 **높음**: RAG 결과를 GPT 프롬프트에 포함
2. 🟡 **중간**: 중복 프롬프트 코드 제거
3. 🟡 **중간**: JSON 파싱 로직 개선
4. 🟡 **중간**: 에러 처리 개선 (raise 대신 폴백)
5. 🟡 **중간**: RAG 결과가 있어도 GPT 호출
6. 🟢 **낮음**: 사용되지 않는 import 제거
7. 🟢 **낮음**: import 중복 제거
8. 🟢 **낮음**: exc_info 추가

### 우선순위
- **높음**: RAG 결과를 GPT 프롬프트에 포함
- **중간**: 중복 코드 제거, JSON 파싱 개선, 에러 처리 개선
- **낮음**: import 정리, 로깅 개선

---

## 📝 권장 수정 사항

### 수정 1: RAG 결과를 GPT 프롬프트에 포함
```python
# RAG 결과 수집
rag_context = ""
rag_suggestion = None
if rag_results:
    best_match = rag_results[0]
    metadata = best_match.get("metadata", {})
    rag_suggestion = {
        "main_case_type": metadata.get("main_case_type"),
        "sub_case_type": metadata.get("sub_case_type"),
        "score": best_match.get("score", 0)
    }
    
    rag_context = f"""
참고할 수 있는 유사 사건 유형:
- 주요 유형: {rag_suggestion['main_case_type']}
- 세부 유형: {rag_suggestion['sub_case_type']}
- 유사도: {rag_suggestion['score']:.2f}
"""

# GPT API로 최종 분류 (RAG 결과를 참고)
classification_prompt = _get_classification_prompt(user_input, rag_context)
```

### 수정 2: 중복 프롬프트 코드 제거
```python
def _get_classification_prompt(user_input: str, rag_context: str = "") -> str:
    """분류 프롬프트 생성"""
    try:
        from src.services.prompt_loader import prompt_loader
        prompt_template = prompt_loader.load_prompt("case_classification", sub_dir="classification")
        if prompt_template:
            return prompt_template.format(user_input=user_input, rag_context=rag_context)
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
    
    # 기본 프롬프트
    return f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
{rag_context}
가능한 분류:
- 민사: 계약, 불법행위, 대여금, 손해배상
- 형사: 사기, 성범죄, 폭행
- 가사: 이혼, 상속
- 행정: 행정처분, 세무

텍스트: {user_input}

JSON 형식으로 반환:
{{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}}"""
```

### 수정 3: JSON 파싱 개선
```python
from src.utils.helpers import parse_json_from_text

try:
    content = response["content"].strip()
    classification = parse_json_from_text(content)
    
    if not classification:
        raise ValueError("JSON 파싱 결과가 None입니다.")
    
    main_case_type = classification.get("main_case_type")
    sub_case_type = classification.get("sub_case_type")
    
    if not main_case_type:
        raise ValueError("main_case_type이 없습니다.")
        
except (json.JSONDecodeError, ValueError) as e:
    logger.error(f"JSON 파싱 실패: {str(e)}, 원본 응답: {content[:200]}")
    # 폴백 처리
    if rag_suggestion:
        main_case_type = rag_suggestion["main_case_type"]
        sub_case_type = rag_suggestion["sub_case_type"]
    else:
        main_case_type, sub_case_type = get_fallback_case_type(user_input)
```

### 수정 4: 에러 처리 개선
```python
except Exception as e:
    logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}", exc_info=True)
    # 폴백 처리
    main_case_type, sub_case_type = get_fallback_case_type(user_input or "")
    main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type) if main_case_type else None
    
    return {
        **state,
        "case_type": main_case_type_en,
        "sub_case_type": sub_case_type,
        "bot_message": "사건과 관련된 구체적인 내용을 알려주세요.",
        "expected_input": {
            "type": "text",
            "field": "fact_description"
        },
        "next_state": "FACT_COLLECTION"
    }
```

### 수정 5: Import 정리
```python
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.keyword_extractor import keyword_extractor
from src.services.gpt_client import gpt_client
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import (
    CASE_TYPE_MAPPING,
    CaseStage,
    Limits
)
from config.fallback_keywords import get_fallback_case_type
from src.db.connection import db_manager
from src.db.models.case_master import CaseMaster
from src.db.models.chat_session import ChatSession
```

---

## ✅ 검토 완료

**검토 항목**: `review_11_langgraph_classification_node`  
**상태**: 완료  
**다음 항목**: `review_12_langgraph_fact_collection_node`

