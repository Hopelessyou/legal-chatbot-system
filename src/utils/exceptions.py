"""
커스텀 예외 클래스 정의
"""


class LegalChatbotError(Exception):
    """기본 예외 클래스"""
    pass


class SessionNotFoundError(LegalChatbotError):
    """세션을 찾을 수 없을 때 발생하는 예외"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"세션을 찾을 수 없습니다: {session_id}")


class InvalidInputError(LegalChatbotError):
    """잘못된 입력일 때 발생하는 예외"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(f"잘못된 입력: {message}")


class GPTAPIError(LegalChatbotError):
    """GPT API 호출 실패 시 발생하는 예외"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(f"GPT API 오류: {message}")


class RAGSearchError(LegalChatbotError):
    """RAG 검색 실패 시 발생하는 예외"""
    def __init__(self, message: str):
        super().__init__(f"RAG 검색 오류: {message}")


class DatabaseError(LegalChatbotError):
    """데이터베이스 오류 시 발생하는 예외"""
    def __init__(self, message: str):
        super().__init__(f"데이터베이스 오류: {message}")


class ValidationError(LegalChatbotError):
    """검증 실패 시 발생하는 예외"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(f"검증 실패: {message}")

