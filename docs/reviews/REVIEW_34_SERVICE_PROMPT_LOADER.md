# Service Prompt Loader 검토 보고서

## 검토 대상
- 파일: `src/services/prompt_loader.py`
- 검토 일자: 2024년
- 검토 범위: 프롬프트 파일 로드, 템플릿 관리

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-12)
- ✅ `PromptLoader` 클래스 구조 명확
- ✅ 초기화 시 프롬프트 디렉토리 경로 설정

### 2. 프롬프트 디렉토리 초기화 (Lines 14-27)
- ✅ `__init__()`: 프롬프트 디렉토리 경로 설정 로직 적절
- ✅ 기본 경로 자동 탐지 (`current_file.parent.parent / "prompts"`)
- ✅ 로깅 구현됨

### 3. 프롬프트 로드 (Lines 29-59)
- ✅ `load_prompt()`: 프롬프트 파일 로드 로직 적절
- ✅ 파일 존재 여부 확인 (`prompt_path.exists()`)
- ✅ UTF-8 인코딩 사용
- ✅ 에러 처리 및 로깅 구현됨
- ✅ `None` 반환으로 안전하게 처리

### 4. 프롬프트 파일명 결정 (Lines 61-119)
- ✅ `get_summary_prompt_name()`: 케이스 타입에 따른 프롬프트 파일명 결정 로직 구현
- ✅ 한글 및 영문 코드 모두 지원
- ✅ 폴백 로직 구현 ("기타" → "default")

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중요한 문제**: `get_summary_prompt_name`에서 `main_case_type` 변환 누락 (Line 111)

**문제**: `main_case_type`이 한글("민사", "형사" 등)일 수 있지만, `prompt_mapping`의 키는 영문 코드("CIVIL", "CRIMINAL" 등)만 있습니다. 한글 `main_case_type`이 들어오면 매핑에 실패하여 항상 "default"를 반환합니다.

```python
# 케이스 타입별 매핑 (한글 및 영문 코드 모두 지원)
prompt_mapping = {
    "FAMILY": {  # ❌ 영문 코드만 있음
        "이혼": "family_divorce",
        ...
    },
    "CIVIL": {  # ❌ 영문 코드만 있음
        ...
    },
    ...
}

# 세부 사건 유형별 프롬프트 선택
if main_case_type in prompt_mapping:  # ❌ 한글 "민사"는 매핑에 없음
    ...
```

**영향도**: 중간  
**수정 필요**: `main_case_type`을 영문 코드로 변환하는 로직 추가

**수정 예시**:
```python
from src.utils.constants import CASE_TYPE_MAPPING

def get_summary_prompt_name(
    self,
    main_case_type: str,
    sub_case_type: str
) -> str:
    # main_case_type 변환 (한글 → 영문)
    main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type) if main_case_type else None
    
    # 케이스 타입별 매핑
    prompt_mapping = {
        "FAMILY": {
            ...
        },
        ...
    }
    
    # 세부 사건 유형별 프롬프트 선택
    if main_case_type_en and main_case_type_en in prompt_mapping:
        if sub_case_type and sub_case_type in prompt_mapping[main_case_type_en]:
            return prompt_mapping[main_case_type_en][sub_case_type]
        else:
            return prompt_mapping[main_case_type_en].get("기타", "default")
    
    # 주 사건 유형이 매핑에 없으면 기본값
    return "default"
```

---

### 2. 🟡 **중요한 문제**: `get_summary_prompt_name`에서 `sub_case_type` 변환 누락 (Line 112)

**문제**: `sub_case_type`도 한글일 수 있지만, 매핑의 키는 한글과 영문 코드가 혼재되어 있습니다. 일관성 확인 필요.

**영향도**: 낮음-중간  
**수정 권장**: `sub_case_type` 변환 로직 추가 또는 문서화

---

### 3. 🟢 **낮음**: 프롬프트 파일 캐싱 없음

**문제**: `load_prompt()`는 매번 파일을 읽습니다. 동일한 프롬프트를 여러 번 로드할 때 성능 저하가 발생할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 프롬프트 파일 캐싱 추가 (선택적)

**수정 예시**:
```python
class PromptLoader:
    def __init__(self, prompts_dir: Optional[Path] = None):
        ...
        self._cache: Dict[str, str] = {}  # 캐시 추가
    
    def load_prompt(
        self,
        template_name: str,
        sub_dir: str = "summary"
    ) -> Optional[str]:
        cache_key = f"{sub_dir}/{template_name}"
        
        # 캐시 확인
        if cache_key in self._cache:
            logger.debug(f"프롬프트 캐시에서 로드: {template_name}")
            return self._cache[cache_key]
        
        try:
            prompt_path = self.prompts_dir / sub_dir / f"{template_name}.txt"
            
            if not prompt_path.exists():
                logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
                return None
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 캐시에 저장
            self._cache[cache_key] = content
            
            logger.debug(f"프롬프트 로드 완료: {template_name}")
            return content
        
        except Exception as e:
            logger.error(f"프롬프트 로드 실패: {template_name} - {str(e)}")
            return None
```

---

### 4. 🟢 **낮음**: 프롬프트 디렉토리 존재 여부 확인 없음

**문제**: `__init__()`에서 `prompts_dir` 경로를 설정하지만, 디렉토리가 실제로 존재하는지 확인하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 디렉토리 존재 여부 확인 및 경고 로그

**수정 예시**:
```python
def __init__(self, prompts_dir: Optional[Path] = None):
    if prompts_dir is None:
        current_file = Path(__file__)
        prompts_dir = current_file.parent.parent / "prompts"
    
    self.prompts_dir = prompts_dir
    
    # 디렉토리 존재 여부 확인
    if not self.prompts_dir.exists():
        logger.warning(f"프롬프트 디렉토리가 존재하지 않습니다: {self.prompts_dir}")
    else:
        logger.debug(f"프롬프트 디렉토리: {self.prompts_dir}")
```

---

### 5. 🟢 **낮음**: `get_summary_prompt_name`에서 `main_case_type`이 `None`일 때 처리

**문제**: `main_case_type`이 `None`이거나 빈 문자열일 때 `prompt_mapping`에 접근하지 않지만, 명시적인 처리가 없습니다.

**영향도**: 낮음  
**수정 권장**: `None` 또는 빈 문자열 체크 추가

**수정 예시**:
```python
def get_summary_prompt_name(
    self,
    main_case_type: str,
    sub_case_type: str
) -> str:
    # main_case_type이 None이거나 빈 문자열인 경우
    if not main_case_type:
        return "default"
    
    # main_case_type 변환 (한글 → 영문)
    main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type)
    
    # 케이스 타입별 매핑
    prompt_mapping = {
        ...
    }
    
    # 세부 사건 유형별 프롬프트 선택
    if main_case_type_en in prompt_mapping:
        ...
    
    return "default"
```

---

### 6. 🟢 **낮음**: `load_prompt`에서 파일 읽기 실패 시 상세 에러 정보 부족

**문제**: `except Exception as e:`에서 `str(e)`만 로깅하지만, 파일 경로 정보가 없어 디버깅이 어려울 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 파일 경로 정보 포함

**수정 예시**:
```python
except Exception as e:
    logger.error(f"프롬프트 로드 실패: {template_name} (경로: {prompt_path}) - {str(e)}")
    return None
```

---

### 7. 🟢 **낮음**: 전역 인스턴스 사용 (Line 123)

**문제**: 전역 인스턴스 `prompt_loader`를 사용하면 테스트나 다중 인스턴스 사용이 어려울 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 싱글톤 패턴 또는 팩토리 함수 사용 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중요한 문제**: 2개 (`main_case_type` 변환 누락, `sub_case_type` 변환 누락)
- 🟢 **낮음**: 5개 (캐싱, 디렉토리 확인, None 처리, 에러 정보, 전역 인스턴스)

### 우선순위별 수정 권장
1. 🟡 **중요**: `get_summary_prompt_name`에서 `main_case_type` 변환 로직 추가
2. 🟡 **중요**: `get_summary_prompt_name`에서 `sub_case_type` 변환 로직 추가 또는 문서화
3. 🟢 **낮음**: 프롬프트 디렉토리 존재 여부 확인, `None` 처리 개선, 에러 정보 개선

---

## 🔧 수정 제안

### 수정 1: `get_summary_prompt_name`에서 `main_case_type` 변환 추가

```python
from src.utils.constants import CASE_TYPE_MAPPING

def get_summary_prompt_name(
    self,
    main_case_type: str,
    sub_case_type: str
) -> str:
    # main_case_type이 None이거나 빈 문자열인 경우
    if not main_case_type:
        return "default"
    
    # main_case_type 변환 (한글 → 영문)
    main_case_type_en = CASE_TYPE_MAPPING.get(main_case_type, main_case_type)
    
    # 케이스 타입별 매핑
    prompt_mapping = {
        "FAMILY": {
            "이혼": "family_divorce",
            "FAMILY_DIVORCE": "family_divorce",
            "상속": "family_inheritance",
            "FAMILY_INHERITANCE": "family_inheritance",
            "기타": "family_default"
        },
        ...
    }
    
    # 세부 사건 유형별 프롬프트 선택
    if main_case_type_en in prompt_mapping:
        if sub_case_type and sub_case_type in prompt_mapping[main_case_type_en]:
            return prompt_mapping[main_case_type_en][sub_case_type]
        else:
            return prompt_mapping[main_case_type_en].get("기타", "default")
    
    # 주 사건 유형이 매핑에 없으면 기본값
    return "default"
```

### 수정 2: 프롬프트 디렉토리 존재 여부 확인

```python
def __init__(self, prompts_dir: Optional[Path] = None):
    if prompts_dir is None:
        current_file = Path(__file__)
        prompts_dir = current_file.parent.parent / "prompts"
    
    self.prompts_dir = prompts_dir
    
    # 디렉토리 존재 여부 확인
    if not self.prompts_dir.exists():
        logger.warning(f"프롬프트 디렉토리가 존재하지 않습니다: {self.prompts_dir}")
    else:
        logger.debug(f"프롬프트 디렉토리: {self.prompts_dir}")
```

### 수정 3: 에러 정보 개선

```python
except Exception as e:
    logger.error(f"프롬프트 로드 실패: {template_name} (경로: {prompt_path}) - {str(e)}")
    return None
```

---

## ✅ 결론

`PromptLoader` 클래스는 전반적으로 잘 구현되어 있으나, **`get_summary_prompt_name`에서 `main_case_type` 변환 로직**이 누락되어 한글 케이스 타입이 제대로 처리되지 않을 수 있습니다. 또한 프롬프트 디렉토리 존재 여부 확인, `None` 처리 개선 등 소소한 개선 사항이 있습니다.

**우선순위**:
1. 🟡 **중요**: `get_summary_prompt_name`에서 `main_case_type` 변환 로직 추가
2. 🟡 **중요**: `get_summary_prompt_name`에서 `sub_case_type` 변환 로직 추가 또는 문서화
3. 🟢 **낮음**: 프롬프트 디렉토리 존재 여부 확인, `None` 처리 개선, 에러 정보 개선

