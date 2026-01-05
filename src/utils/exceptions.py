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

