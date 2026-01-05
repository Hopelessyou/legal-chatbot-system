# Service Fact Emotion Splitter 검토 보고서

## 검토 대상
- 파일: `src/services/fact_emotion_splitter.py`
- 검토 일자: 2024년
- 검토 범위: 사실/감정 분리, GPT 호출, 프롬프트 관리

---

## ✅ 정상 동작 부분

### 1. 프롬프트 로더 사용 (Lines 28-32)
```python
from src.services.prompt_loader import prompt_loader
prompt_template = prompt_loader.load_prompt("split", sub_dir="fact_emotion")
if prompt_template:
    prompt = prompt_template.format(text=text)
```
- ✅ 프롬프트 로더 사용
- ✅ 기본 프롬프트 폴백 제공

### 2. JSON 파싱 견고성 (Lines 98-103)
```python
from src.utils.helpers import parse_json_from_text
result = parse_json_from_text(content, default={
    "facts": [],
    "emotions": []
})
```
- ✅ 견고한 JSON 파싱 유틸리티 사용
- ✅ 기본값 제공

### 3. 기본값 설정 (Lines 108-112)
```python
if "facts" not in result:
    result["facts"] = []
if "emotions" not in result:
    result["emotions"] = []
```
- ✅ 필수 키 존재 확인
- ✅ 기본값 설정

### 4. 에러 처리 (Lines 118-124)
```python
except Exception as e:
    logger.error(f"사실/감정 분리 실패: {str(e)}")
    return {
        "facts": [],
        "emotions": []
    }
```
- ✅ 예외 처리
- ✅ 기본값 반환

### 5. 실제 사용 확인
- ✅ `fact_collection_node`에서 사용
- ✅ 병렬 처리로 성능 최적화

### 6. 낮은 Temperature (Line 93)
```python
temperature=0.1,  # 더 낮은 temperature로 일관성 향상
```
- ✅ 일관성 향상을 위한 낮은 temperature

---

## ⚠️ 발견된 문제점

### 1. 중복된 프롬프트 템플릿 코드
**영향도**: 낮음  
**문제**: 
- 기본 프롬프트가 `try` 블록과 `except` 블록에서 중복됨
- 유지보수 어려움

**현재 코드**:
```python
try:
    prompt_template = prompt_loader.load_prompt(...)
    if prompt_template:
        prompt = prompt_template.format(text=text)
    else:
        prompt = f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요..."""
except Exception as prompt_error:
    prompt = f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요..."""
```

**권장 수정**:
```python
def _get_default_prompt(self, text: str) -> str:
    """기본 프롬프트 반환"""
    return f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요..."""

def split_fact_emotion(self, text: str):
    try:
        from src.services.prompt_loader import prompt_loader
        prompt_template = prompt_loader.load_prompt("split", sub_dir="fact_emotion")
        if prompt_template:
            prompt = prompt_template.format(text=text)
        else:
            prompt = self._get_default_prompt(text)
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
        prompt = self._get_default_prompt(text)
    ...
```

### 2. 빈 텍스트 처리 없음
**영향도**: 낮음  
**문제**: 
- 빈 문자열이나 None 입력 시 처리 없음
- 불필요한 GPT 호출 발생 가능

**권장 수정**:
```python
def split_fact_emotion(self, text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        logger.warning("빈 텍스트로 사실/감정 분리 시도")
        return {
            "facts": [],
            "emotions": []
        }
    ...
```

### 3. Facts/Emotions 구조 검증 없음
**영향도**: 중간  
**문제**: 
- `facts`와 `emotions`가 리스트인지 확인하지만, 내부 구조 검증 없음
- 각 항목이 예상된 키를 가지고 있는지 확인 없음

**현재 코드**:
```python
if "facts" not in result:
    result["facts"] = []
if "emotions" not in result:
    result["emotions"] = []
```

**권장 수정**:
```python
# facts 검증
if not isinstance(result.get("facts"), list):
    logger.warning("facts가 리스트가 아닙니다. 빈 리스트로 설정")
    result["facts"] = []
else:
    # 각 fact 항목 검증
    validated_facts = []
    for fact in result["facts"]:
        if isinstance(fact, dict) and "content" in fact:
            validated_facts.append(fact)
        else:
            logger.warning(f"유효하지 않은 fact 항목: {fact}")
    result["facts"] = validated_facts

# emotions 검증
if not isinstance(result.get("emotions"), list):
    logger.warning("emotions가 리스트가 아닙니다. 빈 리스트로 설정")
    result["emotions"] = []
else:
    # 각 emotion 항목 검증
    validated_emotions = []
    for emotion in result["emotions"]:
        if isinstance(emotion, dict) and "type" in emotion:
            # intensity 범위 검증
            if "intensity" in emotion:
                intensity = emotion["intensity"]
                if not isinstance(intensity, int) or not (1 <= intensity <= 5):
                    logger.warning(f"유효하지 않은 intensity 값: {intensity}, 제거")
                    emotion["intensity"] = None
            validated_emotions.append(emotion)
        else:
            logger.warning(f"유효하지 않은 emotion 항목: {emotion}")
    result["emotions"] = validated_emotions
```

### 4. Intensity 범위 검증 없음
**영향도**: 낮음  
**문제**: 
- 프롬프트에서 "intensity": 1-5라고 명시했지만 검증 없음
- 범위를 벗어난 값이 반환될 수 있음

**권장 수정**:
```python
# 위의 구조 검증 코드에 포함
if "intensity" in emotion:
    intensity = emotion["intensity"]
    if not isinstance(intensity, int) or not (1 <= intensity <= 5):
        logger.warning(f"유효하지 않은 intensity 값: {intensity}, 기본값 3으로 설정")
        emotion["intensity"] = 3
```

### 5. Fact Type 검증 없음
**영향도**: 낮음  
**문제**: 
- 프롬프트에서 "type": "날짜/금액/행위/기타"라고 명시했지만 검증 없음
- 예상되지 않은 타입이 반환될 수 있음

**권장 수정**:
```python
VALID_FACT_TYPES = ["날짜", "금액", "행위", "기타"]

for fact in result["facts"]:
    if "type" in fact:
        fact_type = fact["type"]
        if fact_type not in VALID_FACT_TYPES:
            logger.warning(f"유효하지 않은 fact type: {fact_type}, '기타'로 설정")
            fact["type"] = "기타"
```

### 6. Emotion Type 검증 없음
**영향도**: 낮음  
**문제**: 
- 프롬프트에서 "type": "억울함/불안/화남/기타"라고 명시했지만 검증 없음

**권장 수정**:
```python
VALID_EMOTION_TYPES = ["억울함", "불안", "화남", "기타"]

for emotion in result["emotions"]:
    if "type" in emotion:
        emotion_type = emotion["type"]
        if emotion_type not in VALID_EMOTION_TYPES:
            logger.warning(f"유효하지 않은 emotion type: {emotion_type}, '기타'로 설정")
            emotion["type"] = "기타"
```

### 7. 프롬프트 로드 임포트 위치
**영향도**: 낮음  
**문제**: 
- 메서드 내부에서 `from src.services.prompt_loader import prompt_loader` 임포트
- 파일 상단에서 임포트하는 것이 일반적

**권장 수정**:
```python
from src.services.prompt_loader import prompt_loader
...
```

### 8. 로깅 개선 필요
**영향도**: 낮음  
**문제**: 
- 성공 시 로깅이 `debug` 레벨만
- 추출된 사실/감정 내용 로깅 없음

**권장 수정**:
```python
logger.info(f"사실/감정 분리 완료: 사실 {len(result['facts'])}개, 감정 {len(result['emotions'])}개")
if result['facts']:
    logger.debug(f"추출된 사실: {[f.get('type', 'N/A') for f in result['facts']]}")
if result['emotions']:
    logger.debug(f"추출된 감정: {[e.get('type', 'N/A') for e in result['emotions']]}")
```

### 9. 빈 결과 처리 개선
**영향도**: 낮음  
**문제**: 
- 빈 텍스트나 사실/감정이 없는 경우에 대한 명시적 처리 없음

**권장 수정**:
```python
if not result.get("facts") and not result.get("emotions"):
    logger.warning("텍스트에서 사실이나 감정을 추출하지 못했습니다.")
```

### 10. 파라미터 검증 없음
**영향도**: 낮음  
**문제**: 
- `text`가 None이거나 잘못된 타입일 수 있음

**권장 수정**:
```python
def split_fact_emotion(self, text: str) -> Dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError(f"text는 문자열이어야 합니다: {type(text)}")
    if not text or not text.strip():
        logger.warning("빈 텍스트로 사실/감정 분리 시도")
        return {
            "facts": [],
            "emotions": []
        }
    ...
```

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 짧은 텍스트에 대한 빠른 경로
- 결과 캐싱

### 2. 정확도 개선
- 사실과 감정의 경계 모호성 처리
- 복합 감정 처리

### 3. 테스트 커버리지
- 다양한 텍스트 형식 테스트
- 엣지 케이스 테스트

---

## 📊 종합 평가

### 강점
1. ✅ 프롬프트 로더 사용
2. ✅ JSON 파싱 견고성
3. ✅ 기본값 설정
4. ✅ 에러 처리
5. ✅ 실제 사용 확인
6. ✅ 낮은 temperature로 일관성 향상

### 개선 필요
1. 🟡 **중간**: Facts/Emotions 구조 검증 없음
2. 🟢 **낮음**: 중복된 프롬프트 템플릿 코드
3. 🟢 **낮음**: 빈 텍스트 처리 없음
4. 🟢 **낮음**: Intensity 범위 검증 없음
5. 🟢 **낮음**: Fact Type 검증 없음
6. 🟢 **낮음**: Emotion Type 검증 없음
7. 🟢 **낮음**: 프롬프트 로드 임포트 위치
8. 🟢 **낮음**: 로깅 개선 필요
9. 🟢 **낮음**: 빈 결과 처리 개선
10. 🟢 **낮음**: 파라미터 검증 없음

### 우선순위
- **중간**: Facts/Emotions 구조 검증
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 구조 검증 추가
```python
def _validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
    """결과 구조 검증 및 정규화"""
    VALID_FACT_TYPES = ["날짜", "금액", "행위", "기타"]
    VALID_EMOTION_TYPES = ["억울함", "불안", "화남", "기타"]
    
    # facts 검증
    if not isinstance(result.get("facts"), list):
        logger.warning("facts가 리스트가 아닙니다. 빈 리스트로 설정")
        result["facts"] = []
    else:
        validated_facts = []
        for fact in result["facts"]:
            if isinstance(fact, dict) and "content" in fact:
                # type 검증
                if "type" in fact and fact["type"] not in VALID_FACT_TYPES:
                    logger.warning(f"유효하지 않은 fact type: {fact['type']}, '기타'로 설정")
                    fact["type"] = "기타"
                validated_facts.append(fact)
            else:
                logger.warning(f"유효하지 않은 fact 항목: {fact}")
        result["facts"] = validated_facts
    
    # emotions 검증
    if not isinstance(result.get("emotions"), list):
        logger.warning("emotions가 리스트가 아닙니다. 빈 리스트로 설정")
        result["emotions"] = []
    else:
        validated_emotions = []
        for emotion in result["emotions"]:
            if isinstance(emotion, dict) and "type" in emotion:
                # type 검증
                if emotion["type"] not in VALID_EMOTION_TYPES:
                    logger.warning(f"유효하지 않은 emotion type: {emotion['type']}, '기타'로 설정")
                    emotion["type"] = "기타"
                
                # intensity 검증
                if "intensity" in emotion:
                    intensity = emotion["intensity"]
                    if not isinstance(intensity, int) or not (1 <= intensity <= 5):
                        logger.warning(f"유효하지 않은 intensity 값: {intensity}, 기본값 3으로 설정")
                        emotion["intensity"] = 3
                
                validated_emotions.append(emotion)
            else:
                logger.warning(f"유효하지 않은 emotion 항목: {emotion}")
        result["emotions"] = validated_emotions
    
    return result

def split_fact_emotion(self, text: str) -> Dict[str, Any]:
    ...
    result = parse_json_from_text(content, default={
        "facts": [],
        "emotions": []
    })
    
    if result is None:
        result = {"facts": [], "emotions": []}
    
    # 기본값 설정
    if "facts" not in result:
        result["facts"] = []
    if "emotions" not in result:
        result["emotions"] = []
    
    # 구조 검증
    result = self._validate_result(result)
    ...
```

### 수정 2: 중복 코드 제거
```python
def _get_default_prompt(self, text: str) -> str:
    """기본 프롬프트 반환"""
    return f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요..."""

def split_fact_emotion(self, text: str):
    if not text or not text.strip():
        return {"facts": [], "emotions": []}
    
    try:
        prompt_template = prompt_loader.load_prompt("split", sub_dir="fact_emotion")
        if prompt_template:
            prompt = prompt_template.format(text=text)
        else:
            prompt = self._get_default_prompt(text)
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
        prompt = self._get_default_prompt(text)
    ...
```

### 수정 3: 파일 상단에 임포트 추가
```python
from src.services.prompt_loader import prompt_loader
...
```

### 수정 4: 파라미터 검증 추가
```python
def split_fact_emotion(self, text: str) -> Dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError(f"text는 문자열이어야 합니다: {type(text)}")
    if not text or not text.strip():
        logger.warning("빈 텍스트로 사실/감정 분리 시도")
        return {
            "facts": [],
            "emotions": []
        }
    ...
```

---

## ✅ 검토 완료

**검토 항목**: `review_29_service_fact_emotion_splitter`  
**상태**: 완료  
**다음 항목**: `review_30_service_summarizer`

