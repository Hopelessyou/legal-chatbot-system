"""
FastAPI 애플리케이션 메인 파일
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from src.api.rate_limit_middleware import RateLimitMiddleware
from config.settings import settings
from src.utils.logger import setup_logging, get_logger
from src.api.middleware import LoggingMiddleware
from src.api.error_handler import (
    validation_exception_handler,
    session_not_found_handler,
    invalid_input_handler,
    gpt_api_error_handler,
    rag_search_error_handler,
    database_error_handler,
    general_exception_handler
)
from src.utils.exceptions import (
    SessionNotFoundError,
    InvalidInputError,
    GPTAPIError,
    RAGSearchError,
    DatabaseError
)

# 로깅 초기화
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="법률 상담문의 수집 챗봇 API",
    description="RAG + LangGraph 기반 법률 상담문의 수집 시스템",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 미들웨어
app.add_middleware(LoggingMiddleware)

# Rate Limiting 미들웨어
app.add_middleware(RateLimitMiddleware)

# 에러 핸들러 등록
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SessionNotFoundError, session_not_found_handler)
app.add_exception_handler(InvalidInputError, invalid_input_handler)
app.add_exception_handler(GPTAPIError, gpt_api_error_handler)
app.add_exception_handler(RAGSearchError, rag_search_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("애플리케이션 시작")
    
    from config.settings import settings
    from src.db.connection import db_manager
    from src.rag.vector_db import vector_db_manager
    from src.utils.env import validate_required_env_vars, REQUIRED_ENV_VARS
    
    # 필수 환경변수 검증
    try:
        validate_required_env_vars(REQUIRED_ENV_VARS)
        logger.info("필수 환경변수 검증 완료")
    except ValueError as e:
        logger.error(f"필수 환경변수 검증 실패: {str(e)}")
        raise RuntimeError(f"애플리케이션 시작 실패: {str(e)}")
    
    # 환경별 strict 모드 확인
    is_production = settings.environment.lower() == "production"
    strict_mode = os.getenv("STRICT_DB_CHECK", "false").lower() == "true" or is_production
    
    # DB 연결 테스트
    db_connected = db_manager.health_check()
    if db_connected:
        logger.info("데이터베이스 연결 확인 완료")
    else:
        error_msg = "데이터베이스 연결 확인 실패"
        if strict_mode:
            logger.error(f"{error_msg} - strict 모드로 인해 애플리케이션을 종료합니다.")
            raise RuntimeError(f"{error_msg}. 애플리케이션을 시작할 수 없습니다.")
        else:
            logger.warning(f"{error_msg} - 개발 모드이므로 계속 진행합니다.")
    
    # 벡터 DB 연결 테스트
    vector_db_connected = vector_db_manager.health_check()
    if vector_db_connected:
        logger.info("벡터 DB 연결 확인 완료")
    else:
        error_msg = "벡터 DB 연결 확인 실패"
        if strict_mode:
            logger.error(f"{error_msg} - strict 모드로 인해 애플리케이션을 종료합니다.")
            raise RuntimeError(f"{error_msg}. 애플리케이션을 시작할 수 없습니다.")
        else:
            logger.warning(f"{error_msg} - 개발 모드이므로 계속 진행합니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info("애플리케이션 종료")
    
    # 리소스 정리
    from src.db.connection import db_manager
    db_manager.close()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "법률 상담문의 수집 챗봇 API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    from src.db.connection import db_manager
    from src.rag.vector_db import vector_db_manager
    
    db_healthy = db_manager.health_check()
    vector_db_healthy = vector_db_manager.health_check()
    
    status = "healthy" if (db_healthy and vector_db_healthy) else "unhealthy"
    
    return {
        "status": status,
        "database": "healthy" if db_healthy else "unhealthy",
        "vector_db": "healthy" if vector_db_healthy else "unhealthy"
    }


# 정적 파일 서빙 (채팅 인터페이스)
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"정적 파일 디렉토리 마운트: {static_dir}")


@app.get("/favicon.ico")
async def favicon():
    """Favicon 요청 처리 (404 방지)"""
    from fastapi.responses import Response
    # 빈 응답 반환 (또는 실제 favicon 파일이 있다면 FileResponse 사용)
    return Response(status_code=204)  # No Content

# 라우터 등록
from src.api.routers import chat, rag
app.include_router(chat.router)
app.include_router(rag.router)

