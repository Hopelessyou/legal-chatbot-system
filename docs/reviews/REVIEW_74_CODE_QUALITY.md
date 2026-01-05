# 코드 품질 검토 보고서

## 개요

본 문서는 전체 코드베이스의 코드 품질을 검토한 결과를 정리합니다. 코드 스타일, 네이밍 규칙, 함수 길이, 복잡도, 중복 코드 등을 포함합니다.

**검토 일시**: 2025-01-XX  
**검토 범위**: `src/` 디렉토리 내 모든 Python 파일

---

## 1. 코드 스타일 검토

### 1.1 코드 포맷팅 도구 설정

#### ✅ 정상: Black 설정 존재

**위치**: `pyproject.toml`
```toml
[tool.black]
line-length = 100
target-version = ['py310', 'py311']
include = '\.pyi?$'
```

**평가**: 
- Black 포맷터 설정이 적절함
- 라인 길이 100자로 설정 (일반적인 88자보다 넓지만 허용 가능)
- Python 3.10, 3.11 타겟 버전 명시

#### ✅ 정상: Flake8 설정 존재

**위치**: `pyproject.toml` (optional-dependencies에 포함)
```toml
"flake8>=6.0.0",
```

**평가**: 
- Flake8 린터가 개발 의존성에 포함됨
- 실제 설정 파일(`.flake8` 또는 `setup.cfg`)은 없지만, 기본 설정 사용 가능

#### ✅ 정상: Mypy 타입 체크 설정 존재

**위치**: `pyproject.toml`
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

**평가**: 
- Mypy 설정이 적절함
- `disallow_untyped_defs = false`로 설정되어 있어 점진적 타입 체크 가능

### 1.2 코드 스타일 일관성

#### ✅ 대부분의 코드가 일관된 스타일 사용

**확인 사항**:
- 들여쓰기: 4칸 스페이스 (일관적)
- 따옴표: 대부분 작은따옴표 사용 (일관적)
- 줄 길이: 대부분 100자 이내
- 공백: 연산자 주변 공백 일관적

#### ⚠️ 일부 파일에서 스타일 불일치 가능성

**문제점**:
- 모든 파일이 Black으로 포맷팅되었는지 확인 필요
- 일부 긴 줄(100자 초과) 존재 가능

**수정 권장**:
1. 모든 파일에 Black 포맷터 적용:
   ```bash
   black src/
   ```
2. CI/CD 파이프라인에 Black 체크 추가

---

## 2. 네이밍 규칙 검토

### 2.1 변수 네이밍

#### ✅ 대부분의 변수가 PEP 8 규칙 준수

**확인 사항**:
- 함수/변수: `snake_case` 사용 (일관적)
- 클래스: `PascalCase` 사용 (일관적)
- 상수: `UPPER_SNAKE_CASE` 사용 (일관적)
- 비공개 변수: `_leading_underscore` 사용 (일관적)

**예시**:
```python
# ✅ 좋은 예
session_id = "abc123"
ChatSession = ...
MAX_RETRIES = 3
_private_method = ...

# ❌ 나쁜 예 (발견되지 않음)
SessionId = "abc123"  # PascalCase 변수
maxRetries = 3  # camelCase 변수
```

### 2.2 함수/클래스 네이밍

#### ✅ 대부분의 함수/클래스가 명확한 이름 사용

**확인 사항**:
- 함수명이 동사로 시작 (일관적)
- 클래스명이 명사로 시작 (일관적)
- 이름이 기능을 명확히 설명 (일관적)

**예시**:
```python
# ✅ 좋은 예
def extract_date(text: str) -> Optional[str]:
    ...

def calculate_completion_rate(state: StateContext) -> int:
    ...

class EntityExtractor:
    ...

# ⚠️ 개선 가능
def fact_collection_node(state: StateContext) -> Dict[str, Any]:
    # "node"는 명사이지만, 함수는 동사로 시작하는 것이 일반적
    # 하지만 LangGraph 노드 함수는 관례적으로 이렇게 명명됨
```

### 2.3 네이밍 개선 권장 사항

#### 🟡 중간: 일부 함수명이 너무 길거나 모호함

**문제점**:
- 일부 함수명이 너무 길어 가독성 저하 가능
- 일부 함수명이 기능을 명확히 설명하지 않음

**수정 권장**:
1. 함수명을 더 간결하고 명확하게 개선
2. 일관된 네이밍 패턴 적용

---

## 3. 함수 길이 검토

### 3.1 긴 함수 분석

#### 🔴 중요: `fact_collection_node` 함수가 매우 김

**위치**: `src/langgraph/nodes/fact_collection_node.py:39-430`
**길이**: 약 390줄

**문제점**:
- 함수가 너무 길어 가독성 저하
- 단일 책임 원칙(SRP) 위반 가능
- 테스트 및 디버깅 어려움

**구조 분석**:
1. 엔티티 추출 (병렬 처리)
2. Facts 업데이트 (날짜, 금액, 당사자, 증거 등)
3. 감정 정보 저장
4. DB 저장 (case_fact, case_party, case_emotion, case_evidence)
5. 완성도 계산
6. 다음 질문 생성

**수정 권장**:
1. 함수를 여러 개의 작은 함수로 분리:
   ```python
   def fact_collection_node(state: StateContext) -> Dict[str, Any]:
       """FACT_COLLECTION Node 실행"""
       # 1. 엔티티 추출
       entities, fact_emotion, rag_results = _extract_entities_and_emotions(state)
       
       # 2. Facts 업데이트
       facts = _update_facts(state, entities, fact_emotion)
       
       # 3. DB 저장
       _save_to_database(state, facts, fact_emotion)
       
       # 4. 완성도 계산 및 다음 질문 생성
       completion_rate = _calculate_completion_rate(state, rag_results)
       next_question = _generate_next_question(state, rag_results)
       
       return {
           **state,
           "facts": facts,
           "completion_rate": completion_rate,
           "bot_message": next_question["message"],
           "expected_input": next_question["expected_input"],
           "next_state": "VALIDATION"
       }
   
   def _extract_entities_and_emotions(state: StateContext) -> Tuple[Dict, Dict, List]:
       """엔티티 및 감정 추출 (병렬 처리)"""
       ...
   
   def _update_facts(state: StateContext, entities: Dict, fact_emotion: Dict) -> Dict:
       """Facts 업데이트"""
       ...
   
   def _save_to_database(state: StateContext, facts: Dict, fact_emotion: Dict) -> None:
       """DB 저장"""
       ...
   ```

#### 🟡 중간: 일부 엔드포인트 함수가 김

**위치**: `src/api/routers/chat.py`
- `end_chat`: 약 50줄
- `upload_file`: 약 100줄
- `get_session_detail`: 약 150줄

**문제점**:
- 일부 엔드포인트 함수가 길어 가독성 저하
- 비즈니스 로직이 엔드포인트에 직접 포함됨

**수정 권장**:
1. 비즈니스 로직을 서비스 레이어로 분리
2. 엔드포인트는 요청/응답 처리만 담당

---

## 4. 복잡도 검토

### 4.1 순환 복잡도 (Cyclomatic Complexity)

#### 🔴 중요: `fact_collection_node` 함수의 복잡도가 높음

**문제점**:
- 다수의 중첩된 `if-elif-else` 문
- 다수의 조건부 분기
- 순환 복잡도가 15 이상으로 추정됨 (권장: 10 이하)

**예시**:
```python
# 복잡한 조건부 분기
if expected_input and isinstance(expected_input, dict):
    expected_field = expected_input.get("field")
    
    if expected_field == "incident_date":
        # 날짜 필드 처리
        ...
    elif expected_field == "counterparty":
        # 당사자 필드 처리
        ...
    elif expected_field == "amount":
        # 금액 필드 처리
        ...
    elif expected_field == "evidence":
        # 증거 필드 처리
        ...
else:
    # 모든 필드 추출 시도
    ...
```

**수정 권장**:
1. 전략 패턴(Strategy Pattern) 적용:
   ```python
   class FieldExtractor:
       def extract(self, state: StateContext, entities: Dict, user_input: str) -> Dict:
           raise NotImplementedError
   
   class DateFieldExtractor(FieldExtractor):
       def extract(self, state: StateContext, entities: Dict, user_input: str) -> Dict:
           ...
   
   class CounterpartyFieldExtractor(FieldExtractor):
       def extract(self, state: StateContext, entities: Dict, user_input: str) -> Dict:
           ...
   
   # 사용
   extractors = {
       "incident_date": DateFieldExtractor(),
       "counterparty": CounterpartyFieldExtractor(),
       "amount": AmountFieldExtractor(),
       "evidence": EvidenceFieldExtractor(),
   }
   
   if expected_field in extractors:
       facts.update(extractors[expected_field].extract(state, entities, user_input))
   ```

#### 🟡 중간: 일부 함수의 복잡도가 중간 수준

**문제점**:
- 일부 함수에 중첩된 조건문이 많음
- 일부 함수에 긴 `if-elif-else` 체인이 있음

**수정 권장**:
1. 조건문을 함수로 분리
2. Early return 패턴 적용
3. 가드 클로즈(Guard Clauses) 사용

---

## 5. 중복 코드 검토

### 5.1 발견된 중복 코드

#### 🟡 중간: 증거 추출 로직 중복

**위치**: 
- `src/langgraph/nodes/fact_collection_node.py:214-295` (evidence 필드 추출)
- `src/langgraph/nodes/fact_collection_node.py:269-295` (evidence_type 필드 추출)

**문제점**:
- 증거 키워드 매칭 로직이 여러 곳에서 반복됨
- 정규식 패턴 생성 로직이 중복됨

**예시**:
```python
# 중복된 패턴
for keyword in EVIDENCE_KEYWORDS_POSITIVE:
    pattern = r'\b' + re.escape(keyword) + r'\b'
    if re.search(pattern, user_input_lower):
        ...

# 다른 곳에서도 동일한 패턴
for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
    pattern = r'\b' + re.escape(keyword) + r'\b'
    if re.search(pattern, user_input_lower):
        ...
```

**수정 권장**:
1. 키워드 매칭 로직을 헬퍼 함수로 분리:
   ```python
   def match_keyword_in_text(text: str, keywords: List[str]) -> bool:
       """텍스트에서 키워드 매칭"""
       text_lower = text.lower()
       for keyword in keywords:
           pattern = r'\b' + re.escape(keyword) + r'\b'
           if re.search(pattern, text_lower):
               return True
       return False
   
   def extract_evidence_type_from_text(text: str) -> Optional[str]:
       """텍스트에서 증거 타입 추출"""
       text_lower = text.lower()
       for keyword, evidence_type_value in EVIDENCE_TYPE_KEYWORDS.items():
           pattern = r'\b' + re.escape(keyword) + r'\b'
           if re.search(pattern, text_lower):
               return evidence_type_value
       return None
   ```

#### 🟡 중간: 날짜 추출 로직 중복

**위치**:
- `src/langgraph/nodes/fact_collection_node.py:119-132` (날짜 추출)
- `src/langgraph/nodes/fact_collection_node.py:170-182` (날짜 추출)
- `src/langgraph/nodes/fact_collection_node.py:303-307` (날짜 재추출)

**문제점**:
- 날짜 추출 로직이 여러 곳에서 반복됨
- `entity_extractor.extract_date()` 호출이 중복됨

**수정 권장**:
1. 날짜 추출 로직을 한 곳으로 통합
2. 헬퍼 함수로 분리

#### 🟢 낮음: DB 세션 관리 패턴 중복

**위치**: 여러 파일
- `src/api/routers/chat.py`
- `src/services/session_manager.py`
- `src/langgraph/nodes/fact_collection_node.py`

**문제점**:
- `with db_manager.get_db_session() as db_session:` 패턴이 반복됨
- 하지만 이는 일반적인 패턴이므로 큰 문제는 아님

**수정 권장**:
1. DB 세션 관리는 현재 패턴 유지 (일관성 있음)
2. 필요시 컨텍스트 매니저로 래핑

---

## 6. 타입 힌트 검토

### 6.1 타입 힌트 사용 현황

#### ✅ 대부분의 함수에 타입 힌트 존재

**확인 사항**:
- 함수 매개변수: 대부분 타입 힌트 포함
- 함수 반환값: 대부분 타입 힌트 포함
- 클래스 속성: 일부 타입 힌트 포함

**예시**:
```python
# ✅ 좋은 예
def extract_date(self, text: str) -> Optional[str]:
    ...

def get_session(self, session_id: str) -> Optional[ChatSession]:
    ...

# ⚠️ 개선 가능
async def start_chat(request: ChatStartRequest, _: str = Depends(verify_api_key)):
    # 반환 타입 힌트 없음
    ...
```

#### 🟡 중간: 일부 함수에 타입 힌트 누락

**문제점**:
- 일부 엔드포인트 함수에 반환 타입 힌트 없음
- 일부 내부 함수에 타입 힌트 누락

**수정 권장**:
1. 모든 함수에 타입 힌트 추가
2. Mypy로 타입 체크 실행:
   ```bash
   mypy src/
   ```

---

## 7. 주석 및 문서화 검토

### 7.1 Docstring 사용 현황

#### ✅ 대부분의 클래스/함수에 Docstring 존재

**확인 사항**:
- 클래스: 대부분 Docstring 포함
- 공개 함수: 대부분 Docstring 포함
- 비공개 함수: 일부 Docstring 포함

**예시**:
```python
# ✅ 좋은 예
def extract_date(self, text: str) -> Optional[str]:
    """
    날짜 추출
    
    Args:
        text: 입력 텍스트
    
    Returns:
        추출된 날짜 문자열 (YYYY-MM-DD 형식) 또는 None
    """
    ...
```

#### 🟡 중간: Docstring 형식 불일치

**문제점**:
- 일부 Docstring이 Google 스타일
- 일부 Docstring이 간단한 설명만 포함
- 일부 Docstring에 `Args`, `Returns` 섹션 누락

**수정 권장**:
1. Google 스타일 Docstring 표준화
2. 모든 공개 함수에 `Args`, `Returns` 섹션 추가

---

## 8. 코드 품질 개선 권장 사항

### 8.1 즉시 개선 (높은 우선순위)

1. **`fact_collection_node` 함수 리팩토링**
   - 함수를 여러 개의 작은 함수로 분리
   - 단일 책임 원칙(SRP) 적용
   - 순환 복잡도 감소

2. **중복 코드 제거**
   - 증거 추출 로직 통합
   - 날짜 추출 로직 통합
   - 키워드 매칭 로직 헬퍼 함수로 분리

3. **타입 힌트 추가**
   - 모든 함수에 타입 힌트 추가
   - Mypy로 타입 체크 실행

### 8.2 단기 개선 (중간 우선순위)

4. **Docstring 표준화**
   - Google 스타일 Docstring 적용
   - 모든 공개 함수에 `Args`, `Returns` 섹션 추가

5. **코드 포맷팅 자동화**
   - Black 포맷터 적용
   - CI/CD 파이프라인에 Black 체크 추가

6. **복잡도 감소**
   - 전략 패턴 적용
   - Early return 패턴 적용
   - 가드 클로즈 사용

### 8.3 장기 개선 (낮은 우선순위)

7. **코드 리뷰 프로세스**
   - 코드 리뷰 체크리스트 작성
   - 자동화된 코드 품질 체크 통합

8. **테스트 커버리지 향상**
   - 단위 테스트 작성
   - 통합 테스트 작성

---

## 9. 검토 요약

### 9.1 코드 품질 현황

- **코드 스타일**: 대부분 일관적, Black 설정 존재
- **네이밍 규칙**: PEP 8 준수, 대부분 명확함
- **함수 길이**: 일부 함수가 너무 김 (특히 `fact_collection_node`)
- **복잡도**: 일부 함수의 복잡도가 높음
- **중복 코드**: 일부 중복 코드 존재
- **타입 힌트**: 대부분 존재, 일부 누락
- **문서화**: 대부분 Docstring 존재, 형식 불일치

### 9.2 발견된 문제

- 🔴 **높음**: `fact_collection_node` 함수가 너무 김 (390줄)
- 🔴 **높음**: `fact_collection_node` 함수의 복잡도가 높음
- 🟡 **중간**: 증거 추출 로직 중복
- 🟡 **중간**: 날짜 추출 로직 중복
- 🟡 **중간**: 일부 함수에 타입 힌트 누락
- 🟡 **중간**: Docstring 형식 불일치

### 9.3 우선순위별 수정 권장

1. 🔴 **높음**: `fact_collection_node` 함수 리팩토링 (즉시)
2. 🔴 **높음**: 중복 코드 제거 (즉시)
3. 🟡 **중간**: 타입 힌트 추가 (단기)
4. 🟡 **중간**: Docstring 표준화 (단기)
5. 🟢 **낮음**: 코드 포맷팅 자동화 (장기)

---

## 10. 결론

코드 품질은 전반적으로 양호하지만, **`fact_collection_node` 함수의 길이와 복잡도** 문제를 해결하면 코드 품질이 크게 향상될 것입니다. 또한 **중복 코드 제거**와 **타입 힌트 보완**도 중요한 개선 사항입니다.

**우선순위**:
1. 🔴 **높음**: `fact_collection_node` 함수 리팩토링 (즉시)
2. 🔴 **높음**: 중복 코드 제거 (즉시)
3. 🟡 **중간**: 타입 힌트 추가 (단기)

**참고**: 
- 코드 스타일 도구(Black, Flake8, Mypy) 설정이 잘 되어 있음
- 네이밍 규칙이 일관적으로 적용됨
- 대부분의 함수에 Docstring이 존재함

