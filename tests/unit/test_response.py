"""
응답 포맷 함수 단위 테스트
"""
from src.utils.response import success_response, error_response


def test_success_response():
    """성공 응답 테스트"""
    response = success_response({"key": "value"}, "성공")
    assert response["success"] is True
    assert response["data"] == {"key": "value"}
    assert response["error"] is None
    assert response["message"] == "성공"


def test_success_response_without_message():
    """메시지 없는 성공 응답 테스트"""
    response = success_response({"key": "value"})
    assert response["success"] is True
    assert "message" not in response


def test_error_response():
    """에러 응답 테스트"""
    response = error_response("INVALID_INPUT", "잘못된 입력", {"field": "user_message"})
    assert response["success"] is False
    assert response["data"] is None
    assert response["error"]["code"] == "INVALID_INPUT"
    assert response["error"]["message"] == "잘못된 입력"
    assert response["error"]["details"] == {"field": "user_message"}

