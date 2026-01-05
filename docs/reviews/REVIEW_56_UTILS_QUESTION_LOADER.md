# Utils Question Loader 검토 보고서

## 검토 대상
- 파일: `src/utils/question_loader.py`
- 관련 파일: `config/questions.yaml`
- 검토 일자: 2024년
- 검토 범위: 질문 템플릿 로드, YAML 파싱

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-11)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 모두 포함
- ✅ 로거 설정

### 2. 캐싱 메커니즘 (Lines 13-14, 24-27)
- ✅ 전역 캐시 변수 `_questions_cache` 사용
- ✅ 캐시 히트 시 즉시 반환

### 3. YAML 로딩 (Lines 17-48)
- ✅ `load_questions_from_yaml()` 함수 구현
- ✅ 파일 존재 여부 확인
- ✅ 예외 처리 및 폴백 메커니즘
- ✅ UTF-8 인코딩 명시

### 4. 질문 메시지 조회 (Lines 51-82)
- ✅ 사건 유형별 질문 우선순위 처리
- ✅ 기본 질문 → constants.py → 폴백 순서
- ✅ 명확한 폴백 메시지

### 5. 캐시 재로드 (Lines 85-89)
- ✅ `reload_questions()` 함수로 캐시 초기화

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 타입 힌팅 불완전

**문제**: `_questions_cache`와 `load_questions_from_yaml()`의 반환 타입이 `Optional[Dict]`와 `Dict`로만 정의되어 있습니다. 더 구체적인 타입을 사용할 수 있습니다.

**영향도**: 중간  
**수정 권장**: 타입 힌팅 개선

**수정 예시**:
```python
from typing import Dict, Optional, Any

# 질문 텍스트 캐시
_questions_cache: Optional[Dict[str, Any]] = None

def load_questions_from_yaml() -> Dict[str, Any]:
    """
    YAML 파일에서 질문 텍스트 로드
    
    Returns:
        질문 텍스트 딕셔너리
    """
    # ...
```

---

### 2. 🟢 **낮음**: YAML 파싱 예외 처리 범위가 넓음

**문제**: `load_questions_from_yaml()` 함수에서 `except Exception as e:`로 모든 예외를 잡고 있습니다. 더 구체적인 예외 처리(`yaml.YAMLError`, `IOError` 등)를 사용하는 것이 좋습니다.

**영향도**: 낮음  
**수정 권장**: 구체적인 예외 처리

**수정 예시**:
```python
import yaml
from yaml import YAMLError

def load_questions_from_yaml() -> Dict[str, Any]:
    """
    YAML 파일에서 질문 텍스트 로드
    
    Returns:
        질문 텍스트 딕셔너리
    """
    global _questions_cache
    
    if _questions_cache is not None:
        return _questions_cache
    
    try:
        # config 디렉토리 경로
        config_dir = Path(__file__).parent.parent.parent / "config"
        questions_file = config_dir / "questions.yaml"
        
        if not questions_file.exists():
            logger.warning(f"질문 파일이 없습니다: {questions_file}, 기본값 사용")
            _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
            return _questions_cache
        
        with open(questions_file, "r", encoding="utf-8") as f:
            _questions_cache = yaml.safe_load(f)
        
        logger.info("질문 텍스트 YAML 파일 로드 완료")
        return _questions_cache
    
    except YAMLError as e:
        logger.error(f"YAML 파싱 오류: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except IOError as e:
        logger.error(f"파일 읽기 오류: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except Exception as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
```

---

### 3. 🟢 **낮음**: YAML 파일 구조 검증 부재

**문제**: `yaml.safe_load()`로 로드한 데이터의 구조가 예상과 다를 수 있습니다. `questions` 키가 없거나, `case_types` 구조가 잘못되었을 때를 대비한 검증이 없습니다.

**영향도**: 낮음  
**수정 권장**: YAML 구조 검증 추가 (선택적)

**수정 예시**:
```python
def load_questions_from_yaml() -> Dict[str, Any]:
    """
    YAML 파일에서 질문 텍스트 로드
    
    Returns:
        질문 텍스트 딕셔너리
    """
    global _questions_cache
    
    if _questions_cache is not None:
        return _questions_cache
    
    try:
        # config 디렉토리 경로
        config_dir = Path(__file__).parent.parent.parent / "config"
        questions_file = config_dir / "questions.yaml"
        
        if not questions_file.exists():
            logger.warning(f"질문 파일이 없습니다: {questions_file}, 기본값 사용")
            _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
            return _questions_cache
        
        with open(questions_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # 구조 검증
        if not isinstance(data, dict):
            raise ValueError("YAML 파일이 딕셔너리 형식이 아닙니다.")
        
        if "questions" not in data:
            logger.warning("YAML 파일에 'questions' 키가 없습니다. 기본 구조로 변환합니다.")
            data = {"questions": data}
        
        if not isinstance(data["questions"], dict):
            raise ValueError("'questions' 키의 값이 딕셔너리 형식이 아닙니다.")
        
        _questions_cache = data
        logger.info("질문 텍스트 YAML 파일 로드 완료")
        return _questions_cache
    
    except YAMLError as e:
        logger.error(f"YAML 파싱 오류: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except (IOError, ValueError) as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except Exception as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
```

---

### 4. 🟢 **낮음**: `reload_questions()` 함수의 반환값

**문제**: `reload_questions()` 함수가 반환값이 없습니다. 테스트나 디버깅 시 유용할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재도 충분히 유용함)

---

### 5. 🟢 **낮음**: `get_question_message()`의 `case_type` 대소문자 처리

**문제**: `get_question_message()` 함수에서 `case_type`을 그대로 사용하는데, 대소문자가 일치하지 않으면 매칭이 실패할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `case_type`을 대문자로 정규화 (선택적)

**수정 예시**:
```python
def get_question_message(field: str, case_type: Optional[str] = None) -> str:
    """
    필드에 대한 질문 메시지 가져오기
    
    Args:
        field: 필드 키 (incident_date, counterparty, amount, evidence 등)
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        질문 메시지 문자열
    """
    questions_data = load_questions_from_yaml()
    questions = questions_data.get("questions", {})
    
    # 1. 사건 유형별 질문 확인
    if case_type:
        case_type_upper = case_type.upper()  # 대문자로 정규화
        case_questions = questions.get("case_types", {}).get(case_type_upper, {})
        if field in case_questions:
            return case_questions[field]
    
    # 2. 기본 질문 확인
    default_questions = questions.get("default", {})
    if field in default_questions:
        return default_questions[field]
    
    # 3. constants.py의 기본값 확인
    if field in QUESTION_MESSAGES:
        return QUESTION_MESSAGES[field]
    
    # 4. 폴백
    logger.warning(f"질문 메시지를 찾을 수 없습니다: field={field}, case_type={case_type}")
    return f"{field}에 대한 정보를 알려주세요."
```

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 1개 (타입 힌팅 불완전)
- 🟢 **낮음**: 4개 (예외 처리 범위, YAML 구조 검증, reload 반환값, case_type 대소문자)

### 우선순위별 수정 권장
1. 🟡 **중간**: 타입 힌팅 개선
2. 🟢 **낮음**: YAML 파싱 예외 처리 개선
3. 🟢 **낮음**: case_type 대소문자 정규화 (선택적)
4. 🟢 **낮음**: YAML 구조 검증 추가 (선택적)
5. 🟢 **낮음**: reload_questions() 반환값 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: 타입 힌팅 개선 및 예외 처리 개선

```python
"""
질문 텍스트 로더 모듈
YAML 파일에서 질문 텍스트를 로드하고 관리
"""
import yaml
from yaml import YAMLError
from pathlib import Path
from typing import Dict, Optional, Any
from src.utils.logger import get_logger
from src.utils.constants import QUESTION_MESSAGES

logger = get_logger(__name__)

# 질문 텍스트 캐시
_questions_cache: Optional[Dict[str, Any]] = None


def load_questions_from_yaml() -> Dict[str, Any]:
    """
    YAML 파일에서 질문 텍스트 로드
    
    Returns:
        질문 텍스트 딕셔너리
    """
    global _questions_cache
    
    if _questions_cache is not None:
        return _questions_cache
    
    try:
        # config 디렉토리 경로
        config_dir = Path(__file__).parent.parent.parent / "config"
        questions_file = config_dir / "questions.yaml"
        
        if not questions_file.exists():
            logger.warning(f"질문 파일이 없습니다: {questions_file}, 기본값 사용")
            _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
            return _questions_cache
        
        with open(questions_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # 구조 검증
        if not isinstance(data, dict):
            raise ValueError("YAML 파일이 딕셔너리 형식이 아닙니다.")
        
        if "questions" not in data:
            logger.warning("YAML 파일에 'questions' 키가 없습니다. 기본 구조로 변환합니다.")
            data = {"questions": data}
        
        if not isinstance(data["questions"], dict):
            raise ValueError("'questions' 키의 값이 딕셔너리 형식이 아닙니다.")
        
        _questions_cache = data
        logger.info("질문 텍스트 YAML 파일 로드 완료")
        return _questions_cache
    
    except YAMLError as e:
        logger.error(f"YAML 파싱 오류: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except (IOError, ValueError) as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except Exception as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache


def get_question_message(field: str, case_type: Optional[str] = None) -> str:
    """
    필드에 대한 질문 메시지 가져오기
    
    Args:
        field: 필드 키 (incident_date, counterparty, amount, evidence 등)
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        질문 메시지 문자열
    """
    questions_data = load_questions_from_yaml()
    questions = questions_data.get("questions", {})
    
    # 1. 사건 유형별 질문 확인
    if case_type:
        case_type_upper = case_type.upper()  # 대문자로 정규화
        case_questions = questions.get("case_types", {}).get(case_type_upper, {})
        if field in case_questions:
            return case_questions[field]
    
    # 2. 기본 질문 확인
    default_questions = questions.get("default", {})
    if field in default_questions:
        return default_questions[field]
    
    # 3. constants.py의 기본값 확인
    if field in QUESTION_MESSAGES:
        return QUESTION_MESSAGES[field]
    
    # 4. 폴백
    logger.warning(f"질문 메시지를 찾을 수 없습니다: field={field}, case_type={case_type}")
    return f"{field}에 대한 정보를 알려주세요."


def reload_questions() -> Dict[str, Any]:
    """
    질문 텍스트 캐시 재로드 (테스트 또는 동적 업데이트용)
    
    Returns:
        재로드된 질문 텍스트 딕셔너리
    """
    global _questions_cache
    _questions_cache = None
    return load_questions_from_yaml()
```

---

## ✅ 결론

`utils/question_loader.py` 모듈은 전반적으로 잘 구현되어 있습니다. **타입 힌팅 개선**과 **예외 처리 개선**을 권장합니다.

**우선순위**:
1. 🟡 **중간**: 타입 힌팅 개선
2. 🟢 **낮음**: YAML 파싱 예외 처리 개선
3. 🟢 **낮음**: case_type 대소문자 정규화 (선택적)
4. 🟢 **낮음**: YAML 구조 검증 추가 (선택적)
5. 🟢 **낮음**: reload_questions() 반환값 추가 (선택적)

