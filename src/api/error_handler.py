"""
API 에러 핸들러 모듈
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.utils.exceptions import (
    SessionNotFoundError,
    InvalidInputError,
    GPTAPIError,
    RAGSearchError,
    DatabaseError
)
from src.utils.response import error_response
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 에러 핸들러"""
    errors = exc.errors()
    error_details = {
        "field": errors[0].get("loc")[-1] if errors else None,
        "message": errors[0].get("msg") if errors else "검증 오류"
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            code="VALIDATION_ERROR",
            message="요청 데이터 검증 실패",
            details=error_details
        )
    )


async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    """세션 없음 에러 핸들러"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response(
            code="SESSION_NOT_FOUND",
            message=str(exc)
        )
    )


async def invalid_input_handler(request: Request, exc: InvalidInputError):
    """잘못된 입력 에러 핸들러"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response(
            code="INVALID_INPUT",
            message=str(exc),
            details={"field": exc.field} if exc.field else None
        )
    )


async def gpt_api_error_handler(request: Request, exc: GPTAPIError):
    """GPT API 에러 핸들러"""
    logger.error(f"GPT API 오류: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="GPT_API_ERROR",
            message="GPT API 호출 중 오류가 발생했습니다.",
            details={"status_code": exc.status_code} if exc.status_code else None
        )
    )


async def rag_search_error_handler(request: Request, exc: RAGSearchError):
    """RAG 검색 에러 핸들러"""
    logger.error(f"RAG 검색 오류: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="RAG_SEARCH_ERROR",
            message="RAG 검색 중 오류가 발생했습니다."
        )
    )


async def database_error_handler(request: Request, exc: DatabaseError):
    """데이터베이스 에러 핸들러"""
    logger.error(f"데이터베이스 오류: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="DATABASE_ERROR",
            message="데이터베이스 작업 중 오류가 발생했습니다."
        )
    )


async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다."
        )
    )

