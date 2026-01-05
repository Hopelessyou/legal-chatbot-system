# Utils Exceptions 검토 보고서

## 검토 대상
- 파일: `src/utils/exceptions.py`
- 검토 일자: 2024년
- 검토 범위: 커스텀 예외 클래스, 에러 메시지

---

## ✅ 정상 동작 부분

### 1. 예외 클래스 구조 (Lines 6-49)
- ✅ 기본 예외 클래스 `LegalChatbotError` 정의
- ✅ 계층적 예외 구조 (모든 예외가 `LegalChatbotError` 상속)
- ✅ 명확한 예외 클래스 이름과 용도

### 2. 예외 클래스 정의
- ✅ `SessionNotFoundError`: 세션 ID 저장 및 사용자 친화적 메시지
- ✅ `InvalidInputError`: 필드 정보 저장
- ✅ `GPTAPIError`: 상태 코드 저장
- ✅ `RAGSearchError`: 간단한 메시지 전달
- ✅ `DatabaseError`: 데이터베이스 오류 처리
- ✅ `ValidationError`: 필드 정보 저장

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 타입 힌팅 부족

**문제**: 예외 클래스의 `__init__` 메서드에 타입 힌팅이 없습니다. Python 3.5+에서는 타입 힌팅을 사용하는 것이 권장됩니다.

**영향도**: 낮음  
**수정 권장**: 타입 힌팅 추가

**수정 예시**:
```python
from typing import Optional

class SessionNotFoundError(LegalChatbotError):
    """세션을 찾을 수 없을 때 발생하는 예외"""
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"세션을 찾을 수 없습니다: {session_id}")

class InvalidInputError(LegalChatbotError):
    """잘못된 입력일 때 발생하는 예외"""
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        self.field = field
        super().__init__(f"잘못된 입력: {message}")
```

---

### 2. 🟢 **낮음**: 에러 코드 부재

**문제**: 예외 클래스에 에러 코드가 없습니다. API 응답에서 일관된 에러 코드를 제공하기 어렵습니다.

**영향도**: 낮음  
**수정 권장**: 에러 코드 추가 (선택적)

**수정 예시**:
```python
class SessionNotFoundError(LegalChatbotError):
    """세션을 찾을 수 없을 때 발생하는 예외"""
    ERROR_CODE = "SESSION_NOT_FOUND"
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.error_code = self.ERROR_CODE
        super().__init__(f"세션을 찾을 수 없습니다: {session_id}")
```

---

### 3. 🟢 **낮음**: `to_dict` 메서드 부재

**문제**: 예외를 딕셔너리로 변환하는 메서드가 없어서 API 응답 생성 시 불편합니다.

**영향도**: 낮음  
**수정 권장**: `to_dict` 메서드 추가 (선택적)

**수정 예시**:
```python
class LegalChatbotError(Exception):
    """기본 예외 클래스"""
    ERROR_CODE = "GENERAL_ERROR"
    
    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        self.message = message
        self.error_code = error_code or self.ERROR_CODE
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """예외를 딕셔너리로 변환"""
        return {
            "error": {
                "code": self.error_code,
                "message": str(self)
            }
        }
```

---

### 4. 🟢 **낮음**: 추가 예외 클래스 필요성

**문제**: 일부 시나리오에 대한 예외 클래스가 없을 수 있습니다. 예를 들어:
- `FileUploadError`: 파일 업로드 실패
- `RAGIndexingError`: RAG 인덱싱 실패
- `PromptLoadError`: 프롬프트 로드 실패

**영향도**: 낮음  
**수정 권장**: 필요 시 추가 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 4개 (타입 힌팅 부족, 에러 코드 부재, to_dict 메서드 부재, 추가 예외 클래스 필요성)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 타입 힌팅 추가
2. 🟢 **낮음**: 에러 코드 추가 (선택적)
3. 🟢 **낮음**: `to_dict` 메서드 추가 (선택적)
4. 🟢 **낮음**: 추가 예외 클래스 추가 (필요 시)

---

## 🔧 수정 제안

### 수정 1: 타입 힌팅 추가

```python
"""
커스텀 예외 클래스 정의
"""
from typing import Optional


class LegalChatbotError(Exception):
    """기본 예외 클래스"""
    ERROR_CODE = "GENERAL_ERROR"
    
    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        self.message = message
        self.error_code = error_code or self.ERROR_CODE
        super().__init__(message)


class SessionNotFoundError(LegalChatbotError):
    """세션을 찾을 수 없을 때 발생하는 예외"""
    ERROR_CODE = "SESSION_NOT_FOUND"
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"세션을 찾을 수 없습니다: {session_id}", self.ERROR_CODE)


class InvalidInputError(LegalChatbotError):
    """잘못된 입력일 때 발생하는 예외"""
    ERROR_CODE = "INVALID_INPUT"
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        self.field = field
        super().__init__(f"잘못된 입력: {message}", self.ERROR_CODE)


class GPTAPIError(LegalChatbotError):
    """GPT API 호출 실패 시 발생하는 예외"""
    ERROR_CODE = "GPT_API_ERROR"
    
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        self.status_code = status_code
        super().__init__(f"GPT API 오류: {message}", self.ERROR_CODE)


class RAGSearchError(LegalChatbotError):
    """RAG 검색 실패 시 발생하는 예외"""
    ERROR_CODE = "RAG_SEARCH_ERROR"
    
    def __init__(self, message: str) -> None:
        super().__init__(f"RAG 검색 오류: {message}", self.ERROR_CODE)


class DatabaseError(LegalChatbotError):
    """데이터베이스 오류 시 발생하는 예외"""
    ERROR_CODE = "DATABASE_ERROR"
    
    def __init__(self, message: str) -> None:
        super().__init__(f"데이터베이스 오류: {message}", self.ERROR_CODE)


class ValidationError(LegalChatbotError):
    """검증 실패 시 발생하는 예외"""
    ERROR_CODE = "VALIDATION_ERROR"
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        self.field = field
        super().__init__(f"검증 실패: {message}", self.ERROR_CODE)
```

---

## ✅ 결론

`utils/exceptions.py` 모듈은 전반적으로 잘 구현되어 있습니다. **타입 힌팅 추가**를 권장합니다. 에러 코드와 `to_dict` 메서드는 향후 API 응답 일관성을 위해 추가할 수 있습니다.

**우선순위**:
1. 🟢 **낮음**: 타입 힌팅 추가
2. 🟢 **낮음**: 에러 코드 추가 (선택적)
3. 🟢 **낮음**: `to_dict` 메서드 추가 (선택적)
4. 🟢 **낮음**: 추가 예외 클래스 추가 (필요 시)

