"""
예외 클래스 단위 테스트
"""
import pytest
from src.utils.exceptions import (
    SessionNotFoundError,
    InvalidInputError,
    GPTAPIError,
    RAGSearchError,
    DatabaseError
)


def test_session_not_found_error():
    """SessionNotFoundError 테스트"""
    error = SessionNotFoundError("sess_123")
    assert error.session_id == "sess_123"
    assert "sess_123" in str(error)


def test_invalid_input_error():
    """InvalidInputError 테스트"""
    error = InvalidInputError("잘못된 형식", "user_message")
    assert error.field == "user_message"
    assert "잘못된 입력" in str(error)


def test_gpt_api_error():
    """GPTAPIError 테스트"""
    error = GPTAPIError("API 호출 실패", 500)
    assert error.status_code == 500
    assert "GPT API 오류" in str(error)


def test_rag_search_error():
    """RAGSearchError 테스트"""
    error = RAGSearchError("검색 실패")
    assert "RAG 검색 오류" in str(error)


def test_database_error():
    """DatabaseError 테스트"""
    error = DatabaseError("연결 실패")
    assert "데이터베이스 오류" in str(error)

