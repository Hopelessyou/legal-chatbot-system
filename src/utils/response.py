"""
공통 응답 포맷 함수
"""
from typing import Any, Optional, Dict
from pydantic import BaseModel


class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool
    data: Any = None
    error: Optional[Dict[str, Any]] = None


class ErrorDetail(BaseModel):
    """에러 상세 정보 모델"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


def success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """
    성공 응답 생성
    
    Args:
        data: 응답 데이터
        message: 응답 메시지
    
    Returns:
        성공 응답 딕셔너리
    """
    response = {
        "success": True,
        "data": data,
        "error": None
    }
    
    if message:
        response["message"] = message
    
    return response


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    에러 응답 생성
    
    Args:
        code: 에러 코드
        message: 에러 메시지
        details: 추가 상세 정보
    
    Returns:
        에러 응답 딕셔너리
    """
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details
        }
    }

