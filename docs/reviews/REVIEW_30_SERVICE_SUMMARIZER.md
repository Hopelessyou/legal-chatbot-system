# Service Summarizer 검토 보고서

## 검토 대상
- 파일: `src/services/summarizer.py`
- 검토 일자: 2024년
- 검토 범위: 요약 생성, 프롬프트 템플릿, K4 포맷 활용, GPT 호출

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 12-16)
```python
class Summarizer:
    """요약 생성 클래스"""
    
    def __init__(self):
        self.gpt_client = gpt_client
```
- ✅ 클래스 구조 명확
- ✅ GPT 클라이언트 의존성 주입 적절

### 2. 중간 요약 생성 (Lines 18-55)
```python
def generate_intermediate_summary(self, facts: Dict[str, Any]) -> str:
```
- ✅ 사실 정보를 텍스트로 변환하는 로직 적절
- ✅ GPT API 호출 및 에러 처리 구현됨
- ✅ 반환 타입 명확

### 3. 최종 요약 생성 - Context 처리 (Lines 57-115)
- ✅ Context에서 필요한 정보 추출 로직 적절
- ✅ K4 포맷 템플릿 활용
- ✅ 케이스 타입별 가이드 생성 (`_get_case_specific_guide`)
- ✅ 사용자 입력 섹션 구성 로직 복잡하지만 기능적

### 4. 프롬프트 템플릿 로딩 (Lines 119-157)
- ✅ `prompt_loader`를 통한 템플릿 로딩
- ✅ 폴백 메커니즘 (템플릿 없을 때 기본 프롬프트 사용)
- ✅ 변수 치환 에러 처리 (`KeyError` 캐치)

### 5. JSON 파싱 (Lines 166-187)
- ✅ `parse_json_from_text` 유틸리티 사용
- ✅ 파싱 실패 시 빈 딕셔너리 반환
- ✅ 구조화된 결과 반환 (`summary_text`, `structured_data`)

### 6. 케이스별 가이드 (Lines 250-290)
- ✅ 케이스 타입별 중요 정보 가이드 하드코딩
- ✅ 폴백 로직 (기본 가이드 제공)

---

## ⚠️ 발견된 문제점

### 1. 🟥 **치명적 버그**: `convert_to_legal_language` 메서드 들여쓰기 오류 (Line 292)

**문제**: `convert_to_legal_language` 메서드가 클래스 밖에 정의되어 있습니다. 들여쓰기가 잘못되어 `_get_case_specific_guide` 함수 내부에 정의된 것처럼 보이지만, 실제로는 독립 함수로 정의되어 있습니다. 그러나 `self`를 사용하고 있어 호출 시 `NameError`가 발생합니다.

```python
def _get_case_specific_guide(main_case_type: str, sub_case_type: str) -> str:
    # ... (함수 내용)
    return main_guide
    
    def convert_to_legal_language(self, text: str) -> str:  # ❌ 잘못된 들여쓰기
        # self를 사용하지만 클래스 밖에 정의됨
```

**영향도**: 높음  
**수정 필요**: `convert_to_legal_language` 메서드를 클래스 내부로 이동 (올바른 들여쓰기)

**수정 예시**:
```python
class Summarizer:
    # ... (다른 메서드들)
    
    def convert_to_legal_language(self, text: str) -> str:
        """
        일상 언어를 법률 언어로 변환
        
        Args:
            text: 일상 언어 텍스트
        
        Returns:
            법률 언어로 변환된 텍스트
        """
        prompt = f"""다음 텍스트를 법률 용어를 사용하여 정확하고 전문적으로 변환하세요.
의미는 유지하되 법률 용어를 사용하세요.

텍스트: {text}

법률 언어:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            legal_text = response["content"].strip()
            logger.debug("법률 언어 변환 완료")
            return legal_text
        
        except Exception as e:
            logger.error(f"법률 언어 변환 실패: {str(e)}")
            return text
```

---

### 2. 🟡 **중요한 문제**: `case_type` 추출 로직 불일치 (Line 73)

**문제**: `context.get('case_type', '')`를 사용하지만, 실제로 `summary_node.py`에서는 `case_type`과 `sub_case_type`을 별도로 전달합니다 (Lines 61-62). `context`에 `case_type` 키가 없을 수 있습니다.

```python
# summarizer.py Line 73
main_case_type = context.get('case_type', '')  # ❌ 'case_type' 키가 없을 수 있음

# summary_node.py Lines 61-62
context = {
    "case_type": state.get("case_type"),  # ✅ 전달됨
    "sub_case_type": state.get("sub_case_type"),
    # ...
}
```

**영향도**: 중간  
**수정 필요**: `context`에서 `case_type`과 `sub_case_type`을 별도로 추출하도록 수정

**수정 예시**:
```python
# Context 정보 정리
main_case_type = context.get('case_type', '') or context.get('main_case_type', '')
sub_case_type = context.get('sub_case_type', '')
case_type = f"{main_case_type} / {sub_case_type}" if sub_case_type else main_case_type
```

---

### 3. 🟡 **중요한 문제**: 프롬프트 템플릿 변수 타입 변환 (Lines 131-139)

**문제**: `prompt_variables`에 `facts` (딕셔너리)와 `emotions` (리스트)를 그대로 전달합니다. 프롬프트 템플릿에서 `.format(**prompt_variables)`를 사용할 때, 딕셔너리나 리스트가 문자열로 자동 변환되지 않으면 `TypeError`가 발생할 수 있습니다.

```python
prompt_variables = {
    "case_type": case_type,
    "facts": facts,  # ❌ 딕셔너리 - 문자열 변환 필요
    "emotions": emotions,  # ❌ 리스트 - 문자열 변환 필요
    # ...
}
```

**영향도**: 중간  
**수정 필요**: `facts`와 `emotions`를 문자열로 변환하거나, 템플릿에서 적절히 처리

**수정 예시**:
```python
# facts를 문자열로 변환
facts_text = "\n".join([
    f"- {key}: {value}"
    for key, value in facts.items()
    if value is not None
]) if facts else "없음"

# emotions를 문자열로 변환
emotions_text = ", ".join(emotions) if emotions else "없음"

prompt_variables = {
    "case_type": case_type,
    "facts": facts_text,  # ✅ 문자열
    "emotions": emotions_text,  # ✅ 문자열
    # ...
}
```

---

### 4. 🟢 **낮음**: `generate_intermediate_summary` 에러 처리 (Lines 53-55)

**문제**: 에러 발생 시 빈 문자열(`""`)을 반환합니다. 호출자가 에러를 감지하기 어렵고, 빈 요약과 실제 에러를 구분할 수 없습니다.

**영향도**: 낮음  
**수정 권장**: 예외를 재발생시키거나, `Optional[str]`을 반환하고 `None`을 에러 표시로 사용

**수정 예시**:
```python
except Exception as e:
    logger.error(f"중간 요약 생성 실패: {str(e)}")
    raise  # 또는 return None
```

---

### 5. 🟢 **낮음**: JSON 파싱 실패 시 폴백 (Lines 169-172)

**문제**: `parse_json_from_text`가 `None`을 반환하면 빈 딕셔너리를 사용합니다. 더 나은 폴백 전략이 필요할 수 있습니다 (예: 텍스트에서 부분 정보 추출).

**영향도**: 낮음  
**수정 권장**: JSON 파싱 실패 시 텍스트에서 구조화된 정보를 추출하거나, 사용자에게 알림

---

### 6. 🟢 **낮음**: 하드코딩된 프롬프트 (Lines 34-40, 222-247)

**문제**: `generate_intermediate_summary`와 `_build_default_prompt`에서 프롬프트가 하드코딩되어 있습니다. `prompt_loader`를 사용하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 프롬프트를 파일로 분리하여 관리

---

### 7. 🟢 **낮음**: `user_inputs` 타입 불일치 (Line 79)

**문제**: `context.get('user_inputs', '')`는 문자열을 기대하지만, `summary_node.py`에서는 문자열로 전달합니다 (Line 58). 타입 힌트가 없어 혼동 가능.

**영향도**: 낮음  
**수정 권장**: 타입 힌트 추가 또는 명확한 문서화

---

### 8. 🟢 **낮음**: `date_context_note` 로직 복잡성 (Lines 100-106)

**문제**: 사기 케이스에서 날짜 맥락을 확인하는 로직이 복잡하고 하드코딩되어 있습니다. 다른 케이스 타입에도 유사한 로직이 필요할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 케이스별 맥락 확인 로직을 별도 함수로 분리하거나 설정 파일로 관리

---

### 9. 🟢 **낮음**: `sections_info` 생성 로직 (Line 117)

**문제**: 섹션 정보를 문자열로 변환하는 로직이 한 줄에 길게 작성되어 있습니다. 가독성이 떨어집니다.

**영향도**: 낮음  
**수정 권장**: 별도 함수로 분리

---

### 10. 🟢 **낮음**: `important_info_guide_first` 추출 (Line 129)

**문제**: 첫 줄만 추출하는 로직이 간단하지만, 더 복잡한 가이드의 경우 부족할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 가이드 요약 로직 개선

---

## 📊 검토 요약

### 발견된 문제
- 🟥 **치명적 버그**: 1개 (`convert_to_legal_language` 들여쓰기 오류)
- 🟡 **중요한 문제**: 2개 (`case_type` 추출, 프롬프트 변수 타입)
- 🟢 **낮음**: 7개 (에러 처리, 하드코딩, 타입 힌트 등)

### 우선순위별 수정 권장
1. 🟥 **즉시 수정**: `convert_to_legal_language` 메서드 들여쓰기 수정
2. 🟡 **중요**: `case_type` 추출 로직 수정
3. 🟡 **중요**: 프롬프트 템플릿 변수 타입 변환
4. 🟢 **낮음**: 에러 처리 개선, 하드코딩 제거, 타입 힌트 추가

---

## 🔧 수정 제안

### 수정 1: `convert_to_legal_language` 메서드 들여쓰기 수정

```python
class Summarizer:
    # ... (다른 메서드들)
    
    def convert_to_legal_language(self, text: str) -> str:
        """
        일상 언어를 법률 언어로 변환
        
        Args:
            text: 일상 언어 텍스트
        
        Returns:
            법률 언어로 변환된 텍스트
        """
        prompt = f"""다음 텍스트를 법률 용어를 사용하여 정확하고 전문적으로 변환하세요.
의미는 유지하되 법률 용어를 사용하세요.

텍스트: {text}

법률 언어:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            legal_text = response["content"].strip()
            logger.debug("법률 언어 변환 완료")
            return legal_text
        
        except Exception as e:
            logger.error(f"법률 언어 변환 실패: {str(e)}")
            return text


def _get_case_specific_guide(main_case_type: str, sub_case_type: str) -> str:
    # ... (함수 내용, convert_to_legal_language 제거)
    return main_guide
```

### 수정 2: `case_type` 추출 로직 개선

```python
# Context 정보 정리
main_case_type = context.get('case_type', '') or context.get('main_case_type', '')
sub_case_type = context.get('sub_case_type', '')
if main_case_type and sub_case_type:
    case_type = f"{main_case_type} / {sub_case_type}"
elif main_case_type:
    case_type = main_case_type
elif sub_case_type:
    case_type = sub_case_type
else:
    case_type = "미분류"
```

### 수정 3: 프롬프트 변수 타입 변환

```python
# facts를 문자열로 변환
facts_text = "\n".join([
    f"- {key}: {value}"
    for key, value in facts.items()
    if value is not None
]) if facts else "없음"

# emotions를 문자열로 변환
emotions_text = ", ".join(str(e) for e in emotions) if emotions else "없음"

prompt_variables = {
    "case_type": case_type,
    "facts": facts_text,
    "emotions": emotions_text,
    "completion_rate": completion_rate,
    "user_inputs_section": user_inputs_section,
    "sections_info": sections_info,
    "important_info_guide_first": important_info_guide_first
}
```

---

## ✅ 결론

`Summarizer` 클래스는 전반적으로 잘 구현되어 있으나, **들여쓰기 오류로 인한 치명적 버그**와 몇 가지 개선 사항이 있습니다. 특히 `convert_to_legal_language` 메서드는 현재 호출할 수 없는 상태이므로 즉시 수정이 필요합니다.

**우선순위**:
1. 🟥 **즉시**: `convert_to_legal_language` 들여쓰기 수정
2. 🟡 **중요**: `case_type` 추출 및 프롬프트 변수 타입 변환
3. 🟢 **낮음**: 에러 처리 개선, 하드코딩 제거, 타입 힌트 추가

