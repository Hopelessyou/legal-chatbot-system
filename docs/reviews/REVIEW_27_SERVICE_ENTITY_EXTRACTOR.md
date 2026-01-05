# Service Entity Extractor 검토 보고서

## 검토 대상
- 파일: `src/services/entity_extractor.py`
- 검토 일자: 2024년
- 검토 범위: 날짜/금액/당사자/행위 추출, 패턴 매칭, GPT 호출, 프롬프트 관리

---

## ✅ 정상 동작 부분

### 1. 하이브리드 추출 전략 (Lines 349-400)
```python
def extract_all_entities(self, text: str, fields: Optional[List[str]] = None):
    # 1. 먼저 로컬 패턴 매칭 시도 (GPT 호출 없이)
    # 2. 패턴 매칭으로 추출되지 않은 필드만 GPT로 통합 추출
```
- ✅ 패턴 매칭 우선, GPT는 필요한 경우만 호출
- ✅ 비용 최적화
- ✅ 성능 최적화

### 2. 날짜 패턴 매칭 다양성 (Lines 52-90)
```python
relative_patterns = {
    r'작년\s*(\d+)월\s*(\d+)일?': ...,
    r'올해\s*(\d+)월\s*(\d+)일?': ...,
    ...
}
absolute_patterns = [
    r'(\d{4})[년\.\-\/](\d{1,2})[월\.\-\/](\d{1,2})일?',
    ...
]
```
- ✅ 다양한 날짜 형식 지원
- ✅ 상대적/절대적 날짜 모두 처리

### 3. 날짜 유효성 검증 (Lines 86-90, 132-136)
```python
try:
    date = datetime(year, month, day)
    return date.strftime("%Y-%m-%d")
except ValueError:
    continue
```
- ✅ 잘못된 날짜 처리
- ✅ GPT 응답 날짜 형식 검증

### 4. 에러 처리 (각 메서드)
```python
except Exception as e:
    logger.error(f"날짜 추출 실패: {str(e)}")
    return None
```
- ✅ 모든 메서드에서 예외 처리
- ✅ 기본값 반환

### 5. JSON 파싱 견고성 (Lines 271-273, 336-338, 462-464)
```python
from src.utils.helpers import parse_json_from_text
result = parse_json_from_text(content, default={})
return result if result is not None else {}
```
- ✅ 견고한 JSON 파싱 유틸리티 사용
- ✅ 기본값 제공

---

## ⚠️ 발견된 문제점

### 1. 프롬프트 로드가 사용되지 않음 (Lines 30-49, 228-261, 295-326)
**영향도**: 중간  
**문제**: 
- `extract_date`에서 프롬프트를 로드하지만, 실제로는 패턴 매칭을 먼저 시도하고 GPT는 패턴 매칭 실패 시에만 호출됨
- `_extract_date_with_gpt`에서는 프롬프트를 다시 생성하여 로드한 프롬프트가 사용되지 않음
- `extract_party`와 `extract_action`에서는 프롬프트를 로드하지만, `extract_all_entities`의 통합 추출에서는 사용되지 않음

**현재 코드**:
```python
def extract_date(self, text: str):
    # 프롬프트 로드
    prompt_template = prompt_loader.load_prompt("date", ...)
    ...
    # 패턴 매칭 시도
    ...
    # GPT 호출 (프롬프트 재생성)
    return self._extract_date_with_gpt(text)

def _extract_date_with_gpt(self, text: str):
    prompt = f"""다음 텍스트에서 날짜를 추출..."""  # 프롬프트 재생성
```

**권장 수정**:
```python
def extract_date(self, text: str):
    # 프롬프트 로드 (나중에 사용)
    prompt_template = self._load_date_prompt()
    ...
    # 패턴 매칭 시도
    ...
    # GPT 호출 (로드한 프롬프트 사용)
    return self._extract_date_with_gpt(text, prompt_template)

def _extract_date_with_gpt(self, text: str, prompt_template: Optional[str] = None):
    if prompt_template:
        prompt = prompt_template.format(text=text)
    else:
        prompt = f"""다음 텍스트에서 날짜를 추출..."""
    ...
```

### 2. 중복된 프롬프트 템플릿 코드
**영향도**: 낮음  
**문제**: 
- `extract_date`, `extract_party`, `extract_action`에서 프롬프트 로드 실패 시 기본 프롬프트가 중복됨
- 유지보수 어려움

**권장 수정**:
```python
def _get_default_prompt(self, prompt_type: str, text: str) -> str:
    """기본 프롬프트 반환"""
    prompts = {
        "date": f"""다음 텍스트에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환하세요...""",
        "party": f"""다음 텍스트에서 계약 상대방 또는 관련 인물 정보를 추출하세요...""",
        "action": f"""다음 텍스트에서 핵심 행위나 사건 내용을 추출하세요..."""
    }
    return prompts.get(prompt_type, "")
```

### 3. 한글 숫자 패턴 매칭 미사용 (Lines 173-178)
**영향도**: 낮음  
**문제**: 
- 한글 숫자 패턴을 찾았지만 실제로는 GPT로 넘어감
- 간단한 한글 숫자(일, 이, 삼 등)는 로컬에서 처리 가능

**현재 코드**:
```python
korean_pattern = r'([일이삼사오육칠팔구]+)\s*(천|만|억|조)?\s*원'
match = re.search(korean_pattern, text)
if match:
    # 간단한 한글 숫자 변환 (복잡한 경우 GPT 사용)
    return self._extract_amount_with_gpt(text)  # 항상 GPT 호출
```

**권장 수정**:
```python
if match:
    korean_number = match.group(1)
    unit = match.group(2) if len(match.groups()) >= 2 else None
    
    # 간단한 한글 숫자 변환 시도
    number = self._convert_korean_number(korean_number)
    if number is not None:
        if unit:
            multiplier = KOREAN_NUMBER_MAPPING.get(unit, 1)
            return int(number * multiplier)
        return int(number)
    
    # 변환 실패 시 GPT 사용
    return self._extract_amount_with_gpt(text)
```

### 4. `extract_date`에서 프롬프트 로드 위치 문제
**영향도**: 낮음  
**문제**: 
- 프롬프트를 로드하지만 패턴 매칭이 성공하면 사용되지 않음
- 불필요한 프롬프트 로드

**권장 수정**:
```python
def extract_date(self, text: str):
    # 패턴 매칭 먼저 시도
    ...
    # 패턴 매칭 실패 시에만 프롬프트 로드
    prompt_template = self._load_date_prompt()
    return self._extract_date_with_gpt(text, prompt_template)
```

### 5. 날짜 형식 검증 부족
**영향도**: 낮음  
**문제**: 
- GPT 응답에서 날짜 형식 검증은 있지만, 패턴 매칭 결과는 검증 없음
- `_get_relative_date`에서 잘못된 날짜 처리하지만, 절대 날짜 패턴 매칭에서는 `ValueError`만 처리

**권장 수정**:
```python
# 절대적 날짜 매칭
for pattern in absolute_patterns:
    match = re.search(pattern, text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3)) if len(match.groups()) >= 3 else 1
        
        # 날짜 범위 검증
        if not (1 <= month <= 12):
            continue
        if not (1 <= day <= 31):
            continue
        if year < 1900 or year > 2100:  # 합리적인 범위
            continue
        
        try:
            date = datetime(year, month, day)
            return date.strftime("%Y-%m-%d")
        except ValueError:
            continue
```

### 6. 금액 추출에서 숫자만 추출하는 로직 (Lines 207-210)
**영향도**: 낮음  
**문제**: 
- `re.findall(r'\d+', amount_str)`로 첫 번째 숫자만 사용
- "5000만원" 같은 경우 "5000"만 추출되어 단위 정보 손실

**현재 코드**:
```python
numbers = re.findall(r'\d+', amount_str)
if numbers:
    return int(numbers[0])
```

**권장 수정**:
```python
# 숫자와 단위를 함께 추출
amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(만|억|조)?', amount_str)
if amount_match:
    number = float(amount_match.group(1))
    unit = amount_match.group(2)
    if unit:
        multiplier = KOREAN_NUMBER_MAPPING.get(unit, 1)
        return int(number * multiplier)
    return int(number)

# 단순 숫자만 있는 경우
numbers = re.findall(r'\d+', amount_str)
if numbers:
    return int(numbers[0])
```

### 7. `extract_all_entities`에서 중복 추출 가능성
**영향도**: 낮음  
**문제**: 
- `extract_date`를 호출하면 내부에서 패턴 매칭 실패 시 GPT 호출
- 그 후 `_extract_entities_with_gpt`에서 다시 날짜 추출 시도
- 중복 GPT 호출 가능

**현재 코드**:
```python
date = self.extract_date(text)  # 내부에서 GPT 호출 가능
if date:
    result["date"] = date
...
if not result.get("date"):
    missing_fields.append("date")
...
gpt_result = self._extract_entities_with_gpt(text, missing_fields)  # 다시 GPT 호출
```

**권장 수정**:
```python
def extract_all_entities(self, text: str, fields: Optional[List[str]] = None):
    result = {}
    
    # 패턴 매칭만 시도 (GPT 호출 없이)
    if fields is None or "date" in fields or "incident_date" in fields:
        date = self._extract_date_with_patterns(text)  # 패턴만
        if date:
            result["date"] = date
    
    if fields is None or "amount" in fields:
        amount = self._extract_amount_with_patterns(text)  # 패턴만
        if amount:
            result["amount"] = amount
    
    # 나머지는 통합 GPT 호출
    ...
```

### 8. 빈 텍스트 처리 없음
**영향도**: 낮음  
**문제**: 
- 빈 문자열이나 None 입력 시 처리 없음

**권장 수정**:
```python
def extract_date(self, text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    ...
```

### 9. 프롬프트 로드 임포트 위치
**영향도**: 낮음  
**문제**: 
- 각 메서드 내부에서 `from src.services.prompt_loader import prompt_loader` 임포트
- 파일 상단에서 임포트하는 것이 일반적

**권장 수정**:
```python
from src.services.prompt_loader import prompt_loader
...
```

### 10. 로깅 개선 필요
**영향도**: 낮음  
**문제**: 
- 성공 시 로깅 부족
- 디버깅 어려움

**권장 수정**:
```python
def extract_date(self, text: str):
    ...
    date = func(match)
    if isinstance(date, datetime):
        result = date.strftime("%Y-%m-%d")
        logger.debug(f"날짜 추출 성공 (패턴 매칭): {result}")
        return result
```

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 패턴 매칭 순서 최적화 (자주 사용되는 패턴 우선)
- 정규식 컴파일 캐싱

### 2. 정확도 개선
- 날짜 모호성 처리 (예: "3월"이 올해인지 작년인지)
- 금액 범위 검증 (합리적인 범위)

### 3. 테스트 커버리지
- 다양한 날짜/금액 형식 테스트
- 엣지 케이스 테스트

---

## 📊 종합 평가

### 강점
1. ✅ 하이브리드 추출 전략 (패턴 + GPT)
2. ✅ 다양한 날짜 형식 지원
3. ✅ 에러 처리
4. ✅ JSON 파싱 견고성
5. ✅ 비용 최적화 (필요한 경우만 GPT 호출)

### 개선 필요
1. 🟡 **중간**: 프롬프트 로드가 사용되지 않음
2. 🟢 **낮음**: 중복된 프롬프트 템플릿 코드
3. 🟢 **낮음**: 한글 숫자 패턴 매칭 미사용
4. 🟢 **낮음**: 프롬프트 로드 위치 문제
5. 🟢 **낮음**: 날짜 형식 검증 부족
6. 🟢 **낮음**: 금액 추출 로직 개선
7. 🟢 **낮음**: 중복 추출 가능성
8. 🟢 **낮음**: 빈 텍스트 처리
9. 🟢 **낮음**: 프롬프트 로드 임포트 위치
10. 🟢 **낮음**: 로깅 개선

### 우선순위
- **중간**: 프롬프트 로드 사용 문제
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 프롬프트 로드 사용 개선
```python
def extract_date(self, text: str) -> Optional[str]:
    # 패턴 매칭 먼저 시도
    ...
    # 패턴 매칭 실패 시에만 프롬프트 로드 및 GPT 호출
    prompt_template = self._load_date_prompt()
    return self._extract_date_with_gpt(text, prompt_template)

def _extract_date_with_gpt(self, text: str, prompt_template: Optional[str] = None):
    if prompt_template:
        prompt = prompt_template.format(text=text)
    else:
        prompt = f"""다음 텍스트에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환하세요..."""
    ...
```

### 수정 2: 패턴 매칭과 GPT 호출 분리
```python
def _extract_date_with_patterns(self, text: str) -> Optional[str]:
    """패턴 매칭만 수행 (GPT 호출 없음)"""
    ...

def extract_date(self, text: str) -> Optional[str]:
    # 패턴 매칭 시도
    date = self._extract_date_with_patterns(text)
    if date:
        return date
    
    # GPT 호출
    prompt_template = self._load_date_prompt()
    return self._extract_date_with_gpt(text, prompt_template)
```

### 수정 3: 한글 숫자 변환 추가
```python
def _convert_korean_number(self, korean: str) -> Optional[int]:
    """한글 숫자를 아라비아 숫자로 변환"""
    mapping = {
        "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5,
        "육": 6, "칠": 7, "팔": 8, "구": 9, "십": 10
    }
    # 간단한 변환 로직 (복잡한 경우 None 반환하여 GPT 사용)
    ...
```

### 수정 4: 파일 상단에 임포트 추가
```python
from src.services.prompt_loader import prompt_loader
...
```

---

## ✅ 검토 완료

**검토 항목**: `review_27_service_entity_extractor`  
**상태**: 완료  
**다음 항목**: `review_28_service_keyword_extractor`

