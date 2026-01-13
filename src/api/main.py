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

# LangGraph 로깅을 위한 강제 콘솔 출력 설정
import logging
import sys
# uvicorn의 로깅을 우회하기 위해 직접 sys.stdout/stderr 사용
# root logger에 강제 출력 핸들러 추가
root_logger = logging.getLogger()
# 기존 핸들러 확인
has_stderr_handler = any(
    isinstance(h, logging.StreamHandler) and 
    hasattr(h, 'stream') and 
    h.stream == sys.stderr 
    for h in root_logger.handlers
)
if not has_stderr_handler:
    # stderr에 직접 출력하는 핸들러
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.INFO)
    stderr_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(logging.INFO)
    
    # langgraph 로거에도 추가
    langgraph_logger = logging.getLogger('src.langgraph')
    if not any(isinstance(h, logging.StreamHandler) for h in langgraph_logger.handlers):
        langgraph_handler = logging.StreamHandler(sys.stderr)
        langgraph_handler.setLevel(logging.INFO)
        langgraph_handler.setFormatter(logging.Formatter('[LANGGRAPH] %(message)s'))
        langgraph_logger.addHandler(langgraph_handler)
        langgraph_logger.setLevel(logging.INFO)
    
    logger.info("콘솔 핸들러 추가 완료 (LangGraph 로깅용)")

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


# 라우터 등록 플래그 (lazy loading)
_routers_registered = False

def register_routers_lazy():
    """라우터 등록 (lazy loading)"""
    global _routers_registered
    if _routers_registered:
        return
    
    try:
        from src.api.routers import chat, rag
        app.include_router(chat.router)
        app.include_router(rag.router)
        _routers_registered = True
        logger.info("라우터 등록 완료 (lazy loading)")
    except Exception as e:
        logger.error(f"라우터 등록 실패: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("애플리케이션 시작")
    # 라우터 등록은 백그라운드에서 수행 (서버 시작을 블로킹하지 않음)
    import asyncio
    async def _register_routers():
        await asyncio.sleep(0.1)  # 서버 시작 완료 대기
        register_routers_lazy()
        # 준비 완료 로그 출력
        logger.info("="*70)
        logger.info("✅ 서버 준비 완료!")
        logger.info(f"   - API 문서: http://localhost:8000/docs")
        logger.info(f"   - 채팅 인터페이스: http://localhost:8000/static/chat_gpt.html")
        logger.info(f"   - 관리자 대시보드: http://localhost:8000/static/admin_dashboard.html")
        logger.info(f"   - Health Check: http://localhost:8000/health")
        logger.info("="*70)
        # 콘솔에도 출력
        import sys
        print("="*70)
        print("✅ 서버 준비 완료!")
        print(f"   - API 문서: http://localhost:8000/docs")
        print(f"   - 채팅 인터페이스: http://localhost:8000/static/chat_gpt.html")
        print(f"   - 관리자 대시보드: http://localhost:8000/static/admin_dashboard.html")
        print(f"   - Health Check: http://localhost:8000/health")
        print("="*70)
    asyncio.create_task(_register_routers())
    # DB/벡터 DB 연결 확인은 /health 엔드포인트에서 수행하므로
    # startup에서는 최소한의 작업만 수행하여 서버 시작을 블로킹하지 않음
    logger.info("애플리케이션 시작 완료 (DB 연결 확인은 /health 엔드포인트에서 수행)")

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
    # 라우터가 아직 등록되지 않았다면 등록
    register_routers_lazy()
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

# 라우터 등록은 첫 요청 시 lazy loading으로 수행
# (모듈 import 시 블로킹 방지)

