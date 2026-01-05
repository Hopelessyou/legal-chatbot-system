# GPT 기반 자유 대화 방식 설계안

## 목차

1. [현재 시스템의 문제점](#현재-시스템의-문제점)
2. [새로운 접근 방식](#새로운-접근-방식-gpt-기반-자유-대화)
3. [설계 개요](#설계-개요)
4. [상세 설계](#상세-설계)
5. [구현 전략](#구현-전략)
6. [추천 모델 및 선택 가이드](#추천-모델-및-선택-가이드)
7. [기술적 세부사항](#기술적-세부사항)
8. [비교 분석](#비교-분석)
9. [고려사항 및 해결 방안](#고려사항-및-해결-방안)
10. [구현 단계](#구현-단계)
11. [예시 시나리오](#예시-시나리오)
12. [마이그레이션 전략](#마이그레이션-전략)

---

## 현재 시스템의 문제점

### 1. 복잡한 상태 관리
- 각 필드별로 질문하고 답변을 기다리는 방식
- FACT_COLLECTION → VALIDATION → RE_QUESTION 루프
- `asked_fields`, `missing_fields` 등 복잡한 상태 추적

### 2. 사용자 경험 저하
- "어제", "모름" 같은 답변이 처리되지 않아 반복 질문
- 사용자가 원하는 정보를 자유롭게 제공하기 어려움
- 대화 흐름이 부자연스러움

### 3. 유지보수 어려움
- 필드별 추출 로직이 분산되어 있음
- 새로운 필드 추가 시 여러 곳 수정 필요
- 키워드 기반 추출의 한계

---

## 새로운 접근 방식: GPT 기반 자유 대화

### 핵심 아이디어

**"사용자가 자유롭게 이야기하고, GPT가 필요한 정보를 지능적으로 추출"**

### 기본 원칙

1. **자유로운 대화**: 사용자가 원하는 순서로 정보 제공
2. **지능적 분석**: GPT가 대화 내용을 분석하여 구조화된 정보 추출
3. **자연스러운 질문**: 누락된 정보가 있으면 자연스럽게 추가 질문
4. **점진적 수집**: 대화가 진행되면서 정보가 점진적으로 채워짐

---

## 설계 개요

### 1. 대화 흐름

```
사용자 입력
    ↓
GPT 분석 (대화 컨텍스트 + 현재까지 수집된 정보)
    ↓
정보 추출 및 업데이트
    ↓
누락 정보 확인
    ↓
자연스러운 추가 질문 (필요시)
    ↓
다음 사용자 입력 대기
```

### 2. 핵심 컴포넌트

#### A. 대화 컨텍스트 관리
```python
class ConversationContext:
    """대화 컨텍스트 관리"""
    - 전체 대화 히스토리
    - 현재까지 추출된 정보 (structured_facts)
    - 누락된 필수 정보 목록
    - 대화 단계 (초기/수집중/완료)
```

#### B. GPT 기반 정보 추출기
```python
class GPTInformationExtractor:
    """GPT를 사용한 정보 추출"""
    
    def extract_information(
        conversation_history: List[Message],
        current_facts: Dict,
        required_fields: List[str]
    ) -> ExtractionResult:
        """
        대화 내용을 분석하여 정보 추출
        
        Returns:
            - extracted_facts: 새로 추출된 정보
            - updated_facts: 업데이트된 전체 정보
            - missing_fields: 여전히 누락된 필드
            - confidence_scores: 각 필드의 신뢰도
        """
```

#### C. 자연스러운 질문 생성기
```python
class NaturalQuestionGenerator:
    """자연스러운 추가 질문 생성"""
    
    def generate_question(
        missing_fields: List[str],
        conversation_context: ConversationContext,
        case_type: str
    ) -> Optional[str]:
        """
        누락된 정보에 대해 자연스러운 질문 생성
        
        - 여러 필드를 한 번에 물어볼 수 있음
        - 대화 맥락을 고려한 질문
        - 사용자가 이미 언급한 내용은 제외
        """
```

---

## 상세 설계

### Phase 1: 초기 대화 (사건 유형 파악)

**사용자**: "친구가 돈을 빌려가서 잠적했어요"

**GPT 분석**:
```json
{
  "case_type": "CIVIL",
  "sub_case_type": "CIVIL_LOAN",
  "extracted_facts": {
    "counterparty": "친구",
    "amount": null,
    "incident_date": null,
    "evidence": null
  },
  "missing_fields": ["amount", "incident_date", "evidence"],
  "next_question": "언제 빌려주셨고, 얼마나 빌려주셨나요? 관련 증거는 있으신가요?"
}
```

**장점**: 
- 한 번의 입력으로 여러 정보 파악
- 자연스러운 추가 질문

---

### Phase 2: 정보 수집 (자유로운 대화)

**사용자**: "25년 1월 20일에 500만원 빌려줬고, 카톡 대화내역이 있어요"

**GPT 분석**:
```json
{
  "extracted_facts": {
    "incident_date": "2025-01-20",
    "amount": 5000000,
    "evidence": true,
    "evidence_type": "대화내역"
  },
  "updated_facts": {
    "case_type": "CIVIL",
    "sub_case_type": "CIVIL_LOAN",
    "counterparty": "친구",
    "incident_date": "2025-01-20",
    "amount": 5000000,
    "evidence": true,
    "evidence_type": "대화내역"
  },
  "missing_fields": [],
  "completion_rate": 100,
  "next_action": "summarize"
}
```

**장점**:
- 사용자가 원하는 순서로 정보 제공 가능
- GPT가 맥락을 이해하여 정확히 추출

---

### Phase 3: 추가 정보 수집 (필요시)

**누락된 정보가 있는 경우**:

**GPT 질문**: "상대방의 이름이나 연락처 정보를 알려주실 수 있나요? 그리고 빌려준 경위를 좀 더 자세히 설명해주시면 도움이 될 것 같습니다."

**장점**:
- 여러 필드를 한 번에 물어볼 수 있음
- 대화 맥락을 고려한 자연스러운 질문

---

## 구현 전략

### 1. 단순화된 노드 구조

```
INIT
  ↓
CONVERSATION (자유 대화)
  ↓
SUMMARY
  ↓
COMPLETED
```

**CONVERSATION 노드**가 모든 것을 처리:
- 대화 히스토리 관리
- GPT 기반 정보 추출
- 자연스러운 질문 생성
- 완료 여부 판단

### 2. GPT 프롬프트 설계

#### 정보 추출 프롬프트
```
당신은 법률 상담을 위한 정보 수집 AI입니다.

[대화 히스토리]
{conversation_history}

[현재까지 수집된 정보]
{current_facts}

[필수 정보 목록]
{required_fields}

위 대화 내용을 분석하여 다음 정보를 추출하세요:
1. 새로 추출된 정보
2. 업데이트된 정보
3. 여전히 누락된 정보
4. 각 정보의 신뢰도

JSON 형식으로 반환:
{
  "extracted_facts": {...},
  "updated_facts": {...},
  "missing_fields": [...],
  "confidence_scores": {...},
  "needs_clarification": [...]
}
```

#### 질문 생성 프롬프트
```
[누락된 정보]
{missing_fields}

[대화 맥락]
{conversation_context}

위 정보를 자연스럽게 물어보는 질문을 생성하세요.
- 여러 필드를 한 번에 물어볼 수 있습니다
- 이미 언급된 내용은 제외하세요
- 대화 맥락을 고려한 자연스러운 질문을 만드세요
```

### 3. 상태 관리 단순화

**기존 방식**:
```python
state = {
    "current_state": "FACT_COLLECTION",
    "expected_input": {"field": "evidence"},
    "asked_fields": ["incident_date", "amount"],
    "missing_fields": ["evidence"],
    "facts": {...}
}
```

**새로운 방식**:
```python
state = {
    "current_state": "CONVERSATION",
    "conversation_history": [...],
    "extracted_facts": {...},
    "completion_rate": 75
}
```

---

## 장점 분석

### 1. 사용자 경험
- ✅ 자유롭게 정보 제공 가능
- ✅ 자연스러운 대화 흐름
- ✅ 반복 질문 최소화

### 2. 개발 및 유지보수
- ✅ 복잡한 상태 관리 불필요
- ✅ 필드별 추출 로직 통합
- ✅ 새로운 필드 추가 용이

### 3. 정확도
- ✅ GPT의 맥락 이해 능력 활용
- ✅ 대화 전체를 고려한 정보 추출
- ✅ 모호한 답변도 해석 가능

---

## 고려사항 및 해결 방안

### 1. GPT API 비용
**문제**: 매 메시지마다 GPT 호출 시 비용 증가

**해결 방안**:
- 정보가 충분히 수집되면 GPT 호출 빈도 감소
- 배치 처리: 여러 메시지를 모아서 한 번에 분석
- 캐싱: 유사한 입력에 대한 결과 캐싱

### 2. 추출 정확도
**문제**: GPT가 잘못된 정보를 추출할 수 있음

**해결 방안**:
- 신뢰도 점수 기반 검증
- 사용자 확인 단계 추가 (중요 정보)
- 후처리 검증 로직

### 3. 대화 히스토리 관리
**문제**: 긴 대화 시 토큰 제한

**해결 방안**:
- 중요 정보만 요약하여 컨텍스트 유지
- 슬라이딩 윈도우 방식
- 대화 요약 및 압축

### 4. 필수 정보 보장
**문제**: 사용자가 필수 정보를 제공하지 않을 수 있음

**해결 방안**:
- 필수 정보 체크리스트 기반 질문
- 완성도 기반 자연스러운 안내
- 최소 정보 수집 후 요약 생성

---

## 구현 단계

### Phase 1: 프로토타입
1. 단순한 CONVERSATION 노드 구현
2. GPT 기반 정보 추출 테스트
3. 기본 질문 생성 테스트

### Phase 2: 개선
1. 신뢰도 기반 검증 로직 추가
2. 대화 히스토리 최적화
3. 자연스러운 질문 생성 개선

### Phase 3: 통합
1. 기존 시스템과 병행 운영
2. A/B 테스트
3. 점진적 전환

---

## 예시 시나리오

### 시나리오 1: 완벽한 정보 제공

**사용자**: "25년 1월 20일에 친구에게 500만원을 빌려줬는데, 연락이 안 돼요. 카톡 대화내역이 있어요."

**GPT 분석**:
- 사건 유형: CIVIL (대여금)
- 날짜: 2025-01-20 ✅
- 금액: 5,000,000원 ✅
- 상대방: 친구 ✅
- 증거: 카톡 대화내역 ✅

**응답**: "정보를 확인했습니다. 상담 요약을 작성하겠습니다."

---

### 시나리오 2: 부분적 정보 제공

**사용자**: "친구가 돈을 빌려갔어요"

**GPT 분석**:
- 사건 유형: CIVIL (추정)
- 상대방: 친구 ✅
- 날짜: ❌
- 금액: ❌
- 증거: ❌

**응답**: "언제 빌려주셨고, 얼마나 빌려주셨나요? 그리고 관련 증거가 있으신가요?"

**사용자**: "작년 12월에 300만원이요"

**GPT 분석**:
- 날짜: 2024-12 (추정) ✅
- 금액: 3,000,000원 ✅
- 증거: 여전히 ❌

**응답**: "알겠습니다. 혹시 계약서나 대화내역 같은 증거 자료가 있으신가요?"

---

### 시나리오 3: 모호한 답변

**사용자**: "어제 일어난 일이에요"

**GPT 분석**:
- 날짜: 어제 (2025-01-XX로 변환) ✅
- 맥락: 이전 대화에서 언급된 사건과 연결

**응답**: "어제 발생한 사건이군요. 구체적으로 어떤 일이 있었나요?"

---

## 기술적 세부사항

### 1. 정보 추출 프롬프트 구조

```python
def build_extraction_prompt(
    conversation_history: List[Message],
    current_facts: Dict,
    required_fields: List[str],
    case_type: Optional[str]
) -> str:
    """
    정보 추출을 위한 프롬프트 생성
    """
    prompt = f"""
당신은 법률 상담을 위한 정보 수집 AI입니다.

[대화 히스토리]
{format_conversation_history(conversation_history)}

[현재까지 수집된 정보]
{format_current_facts(current_facts)}

[필수 정보 목록]
{format_required_fields(required_fields)}

[사건 유형]
{case_type or "미분류"}

위 대화 내용을 분석하여 다음을 수행하세요:

1. 새로 추출된 정보 식별
2. 기존 정보 업데이트 (더 구체적인 정보로)
3. 누락된 필수 정보 확인
4. 각 정보의 신뢰도 평가

JSON 형식으로 반환:
{{
  "extracted_facts": {{
    "incident_date": "YYYY-MM-DD 또는 null",
    "amount": 숫자 또는 null,
    "counterparty": "문자열 또는 null",
    "evidence": true/false/null,
    "evidence_type": "문자열 또는 null"
  }},
  "updated_facts": {{
    // 전체 업데이트된 정보
  }},
  "missing_fields": ["필드명 리스트"],
  "confidence_scores": {{
    "incident_date": 0.0-1.0,
    "amount": 0.0-1.0,
    ...
  }},
  "needs_clarification": [
    {{"field": "필드명", "reason": "명확화 필요 이유"}}
  ]
}}
"""
    return prompt
```

### 2. 질문 생성 프롬프트 구조

```python
def build_question_prompt(
    missing_fields: List[str],
    conversation_history: List[Message],
    extracted_facts: Dict,
    case_type: Optional[str]
) -> str:
    """
    자연스러운 질문 생성을 위한 프롬프트
    """
    prompt = f"""
[누락된 필수 정보]
{format_missing_fields(missing_fields)}

[현재까지 수집된 정보]
{format_extracted_facts(extracted_facts)}

[대화 맥락]
{format_conversation_context(conversation_history)}

[사건 유형]
{case_type or "미분류"}

위 정보를 바탕으로 자연스럽고 친절한 질문을 생성하세요.

규칙:
1. 여러 필드를 한 번에 물어볼 수 있습니다
2. 이미 언급된 내용은 다시 물어보지 마세요
3. 대화 맥락을 고려하여 자연스러운 질문을 만드세요
4. 사용자가 편하게 답변할 수 있도록 친절하게 작성하세요
5. 질문이 2개 이상이면 번호를 매기거나 구분하세요

질문만 반환하세요 (JSON이나 추가 설명 없이):
"""
    return prompt
```

### 3. 신뢰도 기반 검증

```python
def validate_extraction(
    extracted_facts: Dict,
    confidence_scores: Dict,
    threshold: float = 0.7
) -> Tuple[Dict, List[str]]:
    """
    신뢰도 기반 정보 검증
    
    Returns:
        - validated_facts: 검증된 정보
        - needs_clarification: 명확화가 필요한 필드
    """
    validated_facts = {}
    needs_clarification = []
    
    for field, value in extracted_facts.items():
        confidence = confidence_scores.get(field, 0.0)
        
        if confidence >= threshold:
            validated_facts[field] = value
        elif confidence >= 0.5:
            # 중간 신뢰도: 사용자 확인 필요
            needs_clarification.append(field)
        else:
            # 낮은 신뢰도: 무시
            pass
    
    return validated_facts, needs_clarification
```

---

## 추천 모델 및 선택 가이드

### 모델 비교표

| 모델 | 컨텍스트 | 비용 (입력/출력) | 속도 | 정확도 | 추천 용도 |
|------|---------|-----------------|------|--------|----------|
| **gpt-4o** | 128K | $2.50/$10 /1M tokens | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **최신 모델, 최고 성능** |
| **gpt-4o-mini** | 128K | $0.15/$0.60 /1M tokens | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **비용 효율적, 빠른 응답** |
| **gpt-4-turbo** | 128K | $10/$30 /1M tokens | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 고품질, 긴 컨텍스트 |
| **gpt-4** | 8K | $30/$60 /1M tokens | ⭐⭐ | ⭐⭐⭐⭐⭐ | 레거시, 높은 정확도 |
| **gpt-3.5-turbo** | 16K | $0.50/$1.50 /1M tokens | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 빠른 응답, 저비용 |

### 상세 모델 정보

#### 1. GPT-4o (권장) ⭐
**특징**:
- 최신 모델 (2024년 5월 출시)
- 멀티모달 지원 (텍스트, 이미지, 오디오)
- 128K 컨텍스트 윈도우
- GPT-4 Turbo보다 2배 빠르고 50% 저렴
- 한국어 성능 우수

**비용**: 
- 입력: $2.50 / 1M tokens
- 출력: $10.00 / 1M tokens

**추천 시나리오**:
- ✅ 프로덕션 환경 (최고 품질 필요)
- ✅ 복잡한 법률 정보 추출
- ✅ 긴 대화 히스토리 관리
- ✅ 높은 정확도 요구

**예상 비용** (세션당):
- 평균 세션: 10턴, 500 tokens/턴
- 입력: 약 $0.0125 / 세션
- 출력: 약 $0.05 / 세션
- **총: 약 $0.06 / 세션**

---

#### 2. GPT-4o-mini (비용 효율) ⭐⭐
**특징**:
- GPT-4o의 경량 버전
- 128K 컨텍스트 윈도우
- GPT-4o보다 10배 저렴
- 속도 빠름
- 정확도는 GPT-4o보다 약간 낮지만 충분히 우수

**비용**: 
- 입력: $0.15 / 1M tokens
- 출력: $0.60 / 1M tokens

**추천 시나리오**:
- ✅ 개발/테스트 환경
- ✅ 대량 트래픽 예상
- ✅ 비용 최적화 필요
- ✅ 빠른 응답 시간 중요

**예상 비용** (세션당):
- 평균 세션: 10턴, 500 tokens/턴
- 입력: 약 $0.00075 / 세션
- 출력: 약 $0.003 / 세션
- **총: 약 $0.004 / 세션** (GPT-4o의 1/15)

---

#### 3. GPT-4 Turbo
**특징**:
- 128K 컨텍스트 윈도우
- GPT-4보다 빠르고 저렴
- 높은 정확도

**비용**: 
- 입력: $10.00 / 1M tokens
- 출력: $30.00 / 1M tokens

**추천 시나리오**:
- ⚠️ GPT-4o 사용 불가능한 경우
- ⚠️ 레거시 시스템 호환성 필요

**비고**: GPT-4o가 더 나은 선택 (더 빠르고 저렴)

---

#### 4. GPT-3.5 Turbo
**특징**:
- 매우 빠른 응답
- 매우 저렴한 비용
- 정확도는 상대적으로 낮음

**비용**: 
- 입력: $0.50 / 1M tokens
- 출력: $1.50 / 1M tokens

**추천 시나리오**:
- ⚠️ 매우 단순한 정보 추출만 필요
- ⚠️ 비용이 극도로 제한적인 경우
- ❌ 법률 상담 정보 수집에는 **비추천** (정확도 부족)

---

### 모델 선택 가이드

#### 시나리오별 추천

**1. 프로덕션 환경 (최고 품질)**
```
추천: gpt-4o
이유: 최신 모델, 최고 정확도, 긴 컨텍스트 지원
비용: 중간 (세션당 약 $0.06)
```

**2. 개발/테스트 환경**
```
추천: gpt-4o-mini
이유: 비용 효율적, 충분한 정확도, 빠른 응답
비용: 낮음 (세션당 약 $0.004)
```

**3. 대량 트래픽 예상**
```
추천: gpt-4o-mini (기본) + gpt-4o (중요 세션)
이유: 
  - 대부분의 세션: gpt-4o-mini로 처리
  - 복잡하거나 중요한 세션: gpt-4o로 업그레이드
비용: 최적화됨
```

**4. 비용 최적화**
```
추천: gpt-4o-mini
이유: GPT-4o의 1/15 비용, 충분한 성능
비용: 매우 낮음
```

---

### 하이브리드 전략

#### 1. 단계별 모델 사용
```python
# 초기 정보 수집: 빠르고 저렴한 모델
if conversation_turn < 3:
    model = "gpt-4o-mini"
# 복잡한 분석: 고품질 모델
elif needs_complex_analysis:
    model = "gpt-4o"
# 최종 요약: 고품질 모델
elif state == "SUMMARY":
    model = "gpt-4o"
```

#### 2. 신뢰도 기반 모델 선택
```python
# gpt-4o-mini로 먼저 시도
result = extract_with_model("gpt-4o-mini", ...)

# 신뢰도가 낮으면 gpt-4o로 재시도
if result.confidence < 0.7:
    result = extract_with_model("gpt-4o", ...)
```

#### 3. 사용자 유형별 모델
```python
# 일반 사용자: 비용 효율적 모델
if user_type == "free":
    model = "gpt-4o-mini"
# 프리미엄 사용자: 고품질 모델
elif user_type == "premium":
    model = "gpt-4o"
```

---

### 비용 최적화 전략

#### 1. 프롬프트 최적화
- 불필요한 설명 제거
- 구조화된 프롬프트 사용
- 예시 최소화

#### 2. 컨텍스트 관리
- 대화 히스토리 요약
- 중요 정보만 유지
- 슬라이딩 윈도우 사용

#### 3. 배치 처리
- 여러 메시지를 모아서 한 번에 분석
- 유사한 입력 캐싱

#### 4. 모델 선택 최적화
- 대부분의 경우: gpt-4o-mini
- 중요한 경우만: gpt-4o

---

### 구현 예시

```python
from enum import Enum
from typing import Optional

class ModelTier(Enum):
    """모델 등급"""
    FAST = "gpt-4o-mini"      # 빠르고 저렴
    STANDARD = "gpt-4o"       # 균형잡힌 성능
    PREMIUM = "gpt-4-turbo"   # 최고 품질

class ModelSelector:
    """상황에 맞는 모델 선택"""
    
    @staticmethod
    def select_model(
        conversation_turn: int,
        complexity: str = "normal",
        user_tier: str = "free"
    ) -> str:
        """
        상황에 맞는 모델 선택
        
        Args:
            conversation_turn: 대화 턴 수
            complexity: 복잡도 (simple/normal/complex)
            user_tier: 사용자 등급 (free/premium)
        """
        # 프리미엄 사용자는 항상 고품질 모델
        if user_tier == "premium":
            return ModelTier.STANDARD.value
        
        # 초기 대화: 빠른 모델
        if conversation_turn < 3:
            return ModelTier.FAST.value
        
        # 복잡한 분석 필요: 고품질 모델
        if complexity == "complex":
            return ModelTier.STANDARD.value
        
        # 일반적인 경우: 빠른 모델
        return ModelTier.FAST.value
```

---

### 모델별 설정 예시

#### gpt-4o 설정
```python
{
    "model": "gpt-4o",
    "temperature": 0.3,  # 낮은 온도로 일관성 확보
    "max_tokens": 2000,  # 충분한 출력 길이
    "top_p": 0.9
}
```

#### gpt-4o-mini 설정
```python
{
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 2000,
    "top_p": 0.9
}
```

---

### 모니터링 및 최적화

#### 추적할 지표
1. **비용**: 세션당 평균 비용
2. **정확도**: 정보 추출 정확도
3. **응답 시간**: 평균 응답 시간
4. **사용자 만족도**: 피드백 점수

#### A/B 테스트
```python
# 50%는 gpt-4o-mini, 50%는 gpt-4o 사용
if session_id % 2 == 0:
    model = "gpt-4o-mini"
else:
    model = "gpt-4o"

# 결과 비교 후 최적 모델 선택
```

---

### 최종 추천

**프로덕션 환경**:
- ✅ **1순위: gpt-4o** - 최고 품질과 합리적인 비용
- ✅ **2순위: gpt-4o-mini** - 비용 최적화가 중요한 경우

**개발/테스트 환경**:
- ✅ **gpt-4o-mini** - 충분한 성능, 저렴한 비용

**하이브리드 전략**:
- ✅ **기본: gpt-4o-mini** (대부분의 세션)
- ✅ **업그레이드: gpt-4o** (복잡하거나 중요한 세션)

---

## 비교 분석

### 기존 방식 vs 새로운 방식

| 항목 | 기존 방식 | 새로운 방식 |
|------|----------|------------|
| **상태 관리** | 복잡 (7개 노드, 여러 상태) | 단순 (3개 노드) |
| **질문 방식** | 필드별 순차 질문 | 자연스러운 통합 질문 |
| **정보 추출** | 키워드 + 규칙 기반 | GPT 기반 맥락 이해 |
| **사용자 경험** | 제한적 (특정 형식 요구) | 자유로운 (자연어) |
| **유지보수** | 어려움 (여러 곳 수정) | 용이 (중앙화) |
| **비용** | 낮음 | 높음 (GPT API) |
| **정확도** | 중간 (규칙 기반 한계) | 높음 (GPT 이해 능력) |

---

## 마이그레이션 전략

### 1. 하이브리드 접근
- 초기: 기존 방식 유지
- 점진적: GPT 기반 방식 추가
- 최종: GPT 기반 방식으로 전환

### 2. A/B 테스트
- 일부 세션만 GPT 방식 사용
- 사용자 만족도 및 정확도 비교
- 데이터 기반 결정

### 3. 폴백 메커니즘
- GPT API 실패 시 기존 방식 사용
- 신뢰도 낮을 때 기존 검증 로직 활용

---

## 결론

GPT 기반 자유 대화 방식은:
- ✅ 사용자 경험 크게 개선
- ✅ 개발 및 유지보수 용이
- ✅ 정보 추출 정확도 향상
- ⚠️ GPT API 비용 증가
- ⚠️ 구현 복잡도 (프롬프트 엔지니어링)

**권장 사항**: 
1. 프로토타입으로 먼저 테스트
2. 비용과 효과 분석
3. 점진적 도입

