# Service Keyword Extractor 검토 보고서

## 검토 대상
- 파일: `src/services/keyword_extractor.py`
- 검토 일자: 2024년
- 검토 범위: 키워드 추출, 의미적 특징 추출, GPT 호출

---

## ✅ 정상 동작 부분

### 1. 폴백 메커니즘 (Lines 98-107)
```python
except Exception as e:
    logger.error(f"의미적 특징 추출 실패: {str(e)}")
    # 폴백: 기본 키워드만 추출
    keywords = self.extract_keywords(text, max_keywords=5)
    return {
        "domain": None,
        "keywords": keywords,
        "main_issue": None,
        "related_concepts": []
    }
```
- ✅ 에러 발생 시 폴백 제공
- ✅ 부분적 결과라도 반환

### 2. JSON 파싱 견고성 (Lines 83-90)
```python
from src.utils.helpers import parse_json_from_text
result = parse_json_from_text(content, default={
    "domain": None,
    "keywords": [],
    "main_issue": None,
    "related_concepts": []
})
```
- ✅ 견고한 JSON 파싱 유틸리티 사용
- ✅ 기본값 제공

### 3. 키워드 개수 제한 (Line 46)
```python
return keywords[:max_keywords]
```
- ✅ 최대 개수 제한 준수

### 4. 에러 처리 (각 메서드)
```python
except Exception as e:
    logger.error(f"키워드 추출 실패: {str(e)}")
    return []
```
- ✅ 모든 메서드에서 예외 처리
- ✅ 기본값 반환

### 5. 실제 사용 확인
- ✅ `case_classification_node`에서 `extract_semantic_features` 사용
- ✅ 실제로 활용되고 있음

---

## ⚠️ 발견된 문제점

### 1. 프롬프트 로더 미사용
**영향도**: 중간  
**문제**: 
- 프롬프트가 하드코딩되어 있음
- `entity_extractor`와 달리 `prompt_loader`를 사용하지 않음
- 프롬프트 수정 시 코드 변경 필요

**현재 코드**:
```python
prompt = f"""다음 텍스트에서 법률 사건 분류에 중요한 핵심 키워드를 추출하세요..."""
```

**권장 수정**:
```python
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    try:
        from src.services.prompt_loader import prompt_loader
        prompt_template = prompt_loader.load_prompt("keyword", sub_dir="classification")
        if prompt_template:
            prompt = prompt_template.format(text=text, max_keywords=max_keywords)
        else:
            prompt = f"""다음 텍스트에서 법률 사건 분류에 중요한 핵심 키워드를 추출하세요..."""
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
        prompt = f"""다음 텍스트에서 법률 사건 분류에 중요한 핵심 키워드를 추출하세요..."""
    ...
```

### 2. 키워드 분리 로직 단순함
**영향도**: 낮음  
**문제**: 
- 쉼표로만 분리
- 다른 구분자(세미콜론, 줄바꿈 등) 미지원
- 빈 키워드 제거 없음

**현재 코드**:
```python
keywords_str = response["content"].strip()
keywords = [kw.strip() for kw in keywords_str.split(",")]
```

**권장 수정**:
```python
keywords_str = response["content"].strip()
# 여러 구분자 지원
keywords = []
for separator in [",", ";", "\n", "|"]:
    if separator in keywords_str:
        keywords = [kw.strip() for kw in keywords_str.split(separator)]
        break
else:
    # 구분자가 없으면 공백으로 분리
    keywords = [kw.strip() for kw in keywords_str.split()]

# 빈 키워드 제거
keywords = [kw for kw in keywords if kw]
```

### 3. 빈 텍스트 처리 없음
**영향도**: 낮음  
**문제**: 
- 빈 문자열이나 None 입력 시 처리 없음
- 불필요한 GPT 호출 발생 가능

**권장 수정**:
```python
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    if not text or not text.strip():
        logger.warning("빈 텍스트로 키워드 추출 시도")
        return []
    ...
```

### 4. 폴백에서 재귀 호출 위험
**영향도**: 낮음  
**문제**: 
- `extract_semantic_features` 실패 시 `extract_keywords` 호출
- `extract_keywords`도 실패하면 예외 발생 가능

**현재 코드**:
```python
except Exception as e:
    logger.error(f"의미적 특징 추출 실패: {str(e)}")
    # 폴백: 기본 키워드만 추출
    keywords = self.extract_keywords(text, max_keywords=5)  # 이것도 실패할 수 있음
```

**권장 수정**:
```python
except Exception as e:
    logger.error(f"의미적 특징 추출 실패: {str(e)}")
    # 폴백: 기본 키워드만 추출
    try:
        keywords = self.extract_keywords(text, max_keywords=5)
    except Exception as fallback_error:
        logger.error(f"폴백 키워드 추출도 실패: {str(fallback_error)}")
        keywords = []
    return {
        "domain": None,
        "keywords": keywords,
        "main_issue": None,
        "related_concepts": []
    }
```

### 5. 파라미터 검증 없음
**영향도**: 낮음  
**문제**: 
- `max_keywords`가 음수이거나 0일 수 있음
- `text`가 None일 수 있음

**권장 수정**:
```python
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    if not text:
        raise ValueError("text는 필수입니다.")
    if max_keywords <= 0:
        raise ValueError(f"max_keywords는 1 이상이어야 합니다: {max_keywords}")
    ...
```

### 6. JSON 파싱 실패 시 예외 발생
**영향도**: 낮음  
**문제**: 
- `extract_semantic_features`에서 JSON 파싱 실패 시 `ValueError` 발생
- 기본값이 제공되었지만 예외가 발생하면 폴백으로 넘어감

**현재 코드**:
```python
if result is None:
    raise ValueError("JSON 파싱 실패")
```

**권장 수정**:
```python
if result is None:
    logger.warning("JSON 파싱 실패, 기본값 사용")
    result = {
        "domain": None,
        "keywords": [],
        "main_issue": None,
        "related_concepts": []
    }
```

또는 예외를 발생시키지 않고 기본값 사용:
```python
result = parse_json_from_text(content, default={
    "domain": None,
    "keywords": [],
    "main_issue": None,
    "related_concepts": []
})

if result is None:
    result = {
        "domain": None,
        "keywords": [],
        "main_issue": None,
        "related_concepts": []
    }
# 예외 발생하지 않음
```

### 7. 키워드 중복 제거 없음
**영향도**: 낮음  
**문제**: 
- 동일한 키워드가 여러 번 반환될 수 있음
- 대소문자 구분 없이 중복 제거 필요할 수 있음

**권장 수정**:
```python
keywords = [kw.strip() for kw in keywords_str.split(",")]
# 빈 키워드 제거 및 중복 제거
keywords = list(dict.fromkeys([kw for kw in keywords if kw]))  # 순서 유지
return keywords[:max_keywords]
```

### 8. 로깅 개선 필요
**영향도**: 낮음  
**문제**: 
- 성공 시 로깅이 `debug` 레벨만
- 추출된 키워드 내용 로깅 없음

**권장 수정**:
```python
logger.info(f"키워드 추출 완료: {len(keywords)}개 - {keywords[:5]}")  # 처음 5개만
```

### 9. `extract_semantic_features`에서 `domain` 검증 없음
**영향도**: 낮음  
**문제**: 
- `domain`이 예상된 값(민사/형사/가사/행정/기타)인지 검증 없음
- 잘못된 값이 반환될 수 있음

**권장 수정**:
```python
VALID_DOMAINS = ["민사", "형사", "가사", "행정", "기타"]

domain = result.get("domain")
if domain and domain not in VALID_DOMAINS:
    logger.warning(f"유효하지 않은 domain 값: {domain}, '기타'로 설정")
    result["domain"] = "기타"
```

### 10. 프롬프트에 컨텍스트 부족
**영향도**: 낮음  
**문제**: 
- `extract_keywords` 프롬프트가 단순함
- 법률 사건 분류에 필요한 구체적 가이드라인 없음

**권장 수정**:
```python
prompt = f"""다음 텍스트에서 법률 사건 분류에 중요한 핵심 키워드를 추출하세요.

주의사항:
- 법률 용어, 사건 유형, 관련 법률, 행위 등을 우선 추출
- 일반적인 단어는 제외
- 최대 {max_keywords}개까지 추출

텍스트: {text}

키워드:"""
```

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 키워드 추출 결과 캐싱
- 짧은 텍스트에 대한 빠른 경로

### 2. 정확도 개선
- 키워드 중요도 점수
- 동의어 처리

### 3. 테스트 커버리지
- 다양한 텍스트 형식 테스트
- 엣지 케이스 테스트

---

## 📊 종합 평가

### 강점
1. ✅ 폴백 메커니즘
2. ✅ JSON 파싱 견고성
3. ✅ 키워드 개수 제한
4. ✅ 에러 처리
5. ✅ 실제 사용 확인

### 개선 필요
1. 🟡 **중간**: 프롬프트 로더 미사용
2. 🟢 **낮음**: 키워드 분리 로직 단순함
3. 🟢 **낮음**: 빈 텍스트 처리 없음
4. 🟢 **낮음**: 폴백에서 재귀 호출 위험
5. 🟢 **낮음**: 파라미터 검증 없음
6. 🟢 **낮음**: JSON 파싱 실패 시 예외 발생
7. 🟢 **낮음**: 키워드 중복 제거 없음
8. 🟢 **낮음**: 로깅 개선 필요
9. 🟢 **낮음**: `domain` 검증 없음
10. 🟢 **낮음**: 프롬프트에 컨텍스트 부족

### 우선순위
- **중간**: 프롬프트 로더 사용
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: 프롬프트 로더 사용
```python
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    if not text or not text.strip():
        return []
    
    try:
        from src.services.prompt_loader import prompt_loader
        prompt_template = prompt_loader.load_prompt("keyword", sub_dir="classification")
        if prompt_template:
            prompt = prompt_template.format(text=text, max_keywords=max_keywords)
        else:
            prompt = self._get_default_keyword_prompt(text, max_keywords)
    except Exception as prompt_error:
        logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
        prompt = self._get_default_keyword_prompt(text, max_keywords)
    ...
```

### 수정 2: 키워드 분리 로직 개선
```python
keywords_str = response["content"].strip()
# 여러 구분자 지원
keywords = []
for separator in [",", ";", "\n", "|"]:
    if separator in keywords_str:
        keywords = [kw.strip() for kw in keywords_str.split(separator)]
        break
else:
    # 구분자가 없으면 공백으로 분리
    keywords = [kw.strip() for kw in keywords_str.split()]

# 빈 키워드 제거 및 중복 제거
keywords = list(dict.fromkeys([kw for kw in keywords if kw]))
return keywords[:max_keywords]
```

### 수정 3: 파라미터 검증 추가
```python
def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
    if not text or not text.strip():
        logger.warning("빈 텍스트로 키워드 추출 시도")
        return []
    if max_keywords <= 0:
        raise ValueError(f"max_keywords는 1 이상이어야 합니다: {max_keywords}")
    ...
```

### 수정 4: 폴백 안전성 개선
```python
except Exception as e:
    logger.error(f"의미적 특징 추출 실패: {str(e)}")
    # 폴백: 기본 키워드만 추출
    try:
        keywords = self.extract_keywords(text, max_keywords=5)
    except Exception as fallback_error:
        logger.error(f"폴백 키워드 추출도 실패: {str(fallback_error)}")
        keywords = []
    return {
        "domain": None,
        "keywords": keywords,
        "main_issue": None,
        "related_concepts": []
    }
```

### 수정 5: JSON 파싱 실패 처리 개선
```python
result = parse_json_from_text(content, default={
    "domain": None,
    "keywords": [],
    "main_issue": None,
    "related_concepts": []
})

if result is None:
    logger.warning("JSON 파싱 실패, 기본값 사용")
    result = {
        "domain": None,
        "keywords": [],
        "main_issue": None,
        "related_concepts": []
    }

# domain 검증
VALID_DOMAINS = ["민사", "형사", "가사", "행정", "기타"]
domain = result.get("domain")
if domain and domain not in VALID_DOMAINS:
    logger.warning(f"유효하지 않은 domain 값: {domain}, '기타'로 설정")
    result["domain"] = "기타"
```

---

## ✅ 검토 완료

**검토 항목**: `review_28_service_keyword_extractor`  
**상태**: 완료  
**다음 항목**: `review_29_service_fact_emotion_splitter`

