# Utils Helpers 검토 보고서

## 검토 대상
- 파일: `src/utils/helpers.py`
- 검토 일자: 2024년
- 검토 범위: 유틸리티 함수, JSON 파싱, 날짜 처리, 개인정보 마스킹

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-12)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 모두 포함
- ✅ KST 시간대 상수 정의

### 2. 날짜 처리 함수들 (Lines 15-64)
- ✅ `get_kst_now()`: 한국 시간 반환 (tzinfo 제거로 SQLAlchemy 호환)
- ✅ `parse_date()`: 다양한 날짜 형식 지원
- ✅ `format_date()`: 날짜 포맷팅

### 3. 텍스트 처리 함수들 (Lines 67-104)
- ✅ `normalize_text()`: 공백 정규화
- ✅ `mask_personal_info()`: 개인정보 마스킹 (전화번호, 이메일, 주민등록번호)

### 4. ID 생성 함수들 (Lines 107-137)
- ✅ `generate_uuid()`: UUID 생성
- ✅ `generate_session_id()`: 세션 ID 생성 (sess_ 접두사)
- ✅ `generate_user_hash()`: 사용자 해시 생성 (SHA256)

### 5. JSON 파싱 함수 (Lines 140-213)
- ✅ `parse_json_from_text()`: 텍스트에서 JSON 추출
- ✅ 마크다운 코드 블록 제거
- ✅ 중첩된 괄호 매칭
- ✅ 주석 제거 및 후행 쉼표 처리

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: `get_kst_now()` 반환값의 tzinfo 처리

**문제**: `get_kst_now()` 함수가 `datetime.now(KST)`를 반환하는데, 이는 timezone-aware datetime입니다. 하지만 이전에 수정한 내용을 보면 SQLAlchemy 호환을 위해 `tzinfo`를 제거해야 합니다.

**영향도**: 낮음 (현재 코드가 작동 중이라면 문제 없음)  
**수정 권장**: SQLAlchemy 호환을 위해 `tzinfo` 제거 확인

**현재 코드 확인 필요**: 이전 수정에서 `replace(tzinfo=None)`을 추가했는지 확인

---

### 2. 🟢 **낮음**: `parse_date()` 함수의 날짜 형식 제한

**문제**: `parse_date()` 함수가 지원하는 날짜 형식이 제한적입니다. 예를 들어:
- "2024년 1월 1일" 같은 한글 형식 미지원
- "1/1/2024" 같은 미국식 형식 미지원
- 상대 날짜 ("어제", "오늘", "3일 전") 미지원

**영향도**: 낮음  
**수정 권장**: 추가 날짜 형식 지원 (선택적)

---

### 3. 🟢 **낮음**: `mask_personal_info()` 함수의 마스킹 범위 제한

**문제**: `mask_personal_info()` 함수가 전화번호, 이메일, 주민등록번호만 마스킹합니다. 다른 개인정보(예: 계좌번호, 신용카드 번호, 이름 등)는 마스킹하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 추가 개인정보 마스킹 지원 (선택적)

---

### 4. 🟢 **낮음**: `parse_json_from_text()` 함수의 예외 처리

**문제**: `parse_json_from_text()` 함수에서 `except Exception:` (Line 211)이 너무 광범위합니다. 구체적인 예외 타입을 명시하는 것이 좋습니다.

**영향도**: 낮음  
**수정 권장**: 구체적인 예외 타입 명시

**수정 예시**:
```python
except (json.JSONDecodeError, ValueError, TypeError) as e:
    return default
```

---

### 5. 🟢 **낮음**: `generate_session_id()` 함수의 길이 제한

**문제**: `generate_session_id()` 함수가 `uuid.uuid4().hex[:12]`를 사용하여 12자리 세션 ID를 생성합니다. 이는 충돌 가능성이 있습니다 (약 2.8×10^14 가지 조합).

**영향도**: 낮음 (현재 사용량에서는 문제 없을 수 있음)  
**수정 권장**: 충돌 가능성 고려 (선택적)

---

### 6. 🟢 **낮음**: 함수 문서화 개선

**문제**: 일부 함수의 docstring이 간단합니다. 예를 들어, `parse_json_from_text()` 함수는 복잡한 로직을 가지고 있지만 예제나 사용 사례가 없습니다.

**영향도**: 낮음  
**수정 권장**: 문서화 개선 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 6개 (tzinfo 처리, 날짜 형식 제한, 마스킹 범위 제한, 예외 처리, 세션 ID 길이, 문서화)

### 우선순위별 수정 권장
1. 🟢 **낮음**: `get_kst_now()` 반환값의 tzinfo 처리 확인
2. 🟢 **낮음**: `parse_json_from_text()` 예외 처리 개선
3. 🟢 **낮음**: 날짜 형식 지원 확장 (선택적)
4. 🟢 **낮음**: 개인정보 마스킹 범위 확장 (선택적)
5. 🟢 **낮음**: 세션 ID 길이 고려 (선택적)
6. 🟢 **낮음**: 문서화 개선 (선택적)

---

## 🔧 수정 제안

### 수정 1: get_kst_now() tzinfo 처리 확인 및 parse_json_from_text() 예외 처리 개선

```python
def get_kst_now() -> datetime:
    """
    현재 한국 시간(KST) 반환
    
    SQLAlchemy 호환을 위해 timezone-aware datetime을 반환하지만
    tzinfo를 제거한 naive datetime을 반환합니다.
    
    Returns:
        한국 시간대의 현재 datetime 객체 (naive)
    """
    kst_timezone = timezone(timedelta(hours=9))
    return datetime.now(kst_timezone).replace(tzinfo=None)

def parse_json_from_text(text: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    텍스트에서 JSON 객체를 안전하게 파싱
    
    마크다운 코드 블록, 주석, 불필요한 텍스트를 제거하고 JSON을 추출합니다.
    
    Args:
        text: JSON이 포함된 텍스트
        default: 파싱 실패 시 반환할 기본값
    
    Returns:
        파싱된 JSON 딕셔너리 또는 default
    
    Example:
        >>> parse_json_from_text('```json\n{"key": "value"}\n```')
        {'key': 'value'}
    """
    if not text:
        return default
    
    try:
        # ... (기존 로직) ...
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 더 공격적인 정리 시도
        try:
            # ... (기존 로직) ...
        except (json.JSONDecodeError, ValueError, TypeError):
            return default
    except (ValueError, TypeError, AttributeError) as e:
        # 예상치 못한 예외 처리
        return default
```

---

## ✅ 결론

`utils/helpers.py` 모듈은 전반적으로 잘 구현되어 있습니다. **`get_kst_now()` 반환값의 tzinfo 처리 확인**과 **`parse_json_from_text()` 예외 처리 개선**을 권장합니다. 나머지는 선택적 개선 사항입니다.

**우선순위**:
1. 🟢 **낮음**: `get_kst_now()` 반환값의 tzinfo 처리 확인
2. 🟢 **낮음**: `parse_json_from_text()` 예외 처리 개선
3. 🟢 **낮음**: 날짜 형식 지원 확장 (선택적)
4. 🟢 **낮음**: 개인정보 마스킹 범위 확장 (선택적)
5. 🟢 **낮음**: 세션 ID 길이 고려 (선택적)
6. 🟢 **낮음**: 문서화 개선 (선택적)

