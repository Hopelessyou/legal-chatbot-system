"""
RAG 문서 인덱싱 관련 API 라우터
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import os
from src.rag.pipeline import RAGIndexingPipeline
from src.api.auth import verify_api_key
from src.utils.response import success_response, error_response
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

# 허용된 RAG 디렉토리 경로 (프로젝트 루트 기준)
ALLOWED_RAG_BASE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "rag"


def _validate_directory_path(directory_path: str) -> Path:
    """
    디렉토리 경로 검증 및 정규화
    
    Args:
        directory_path: 검증할 디렉토리 경로
    
    Returns:
        정규화된 Path 객체
    
    Raises:
        HTTPException: 경로가 유효하지 않거나 허용되지 않은 경우
    """
    try:
        # 경로 정규화 (상대 경로 처리)
        if os.path.isabs(directory_path):
            # 절대 경로인 경우
            requested_path = Path(directory_path).resolve()
        else:
            # 상대 경로인 경우 프로젝트 루트 기준으로 해석
            project_root = Path(__file__).parent.parent.parent.parent
            requested_path = (project_root / directory_path).resolve()
        
        # 허용된 디렉토리 내부인지 확인
        allowed_base = ALLOWED_RAG_BASE_DIR.resolve()
        
        # 경로 탐색 공격 방지: 허용된 디렉토리 외부 접근 차단
        try:
            # requested_path가 allowed_base의 하위 디렉토리인지 확인
            requested_path.relative_to(allowed_base)
        except ValueError:
            # ValueError가 발생하면 allowed_base의 하위 디렉토리가 아님
            logger.warning(f"허용되지 않은 디렉토리 접근 시도: {requested_path}")
            raise HTTPException(
                status_code=403,
                detail=f"접근할 수 없는 디렉토리 경로입니다. 허용된 경로: {allowed_base}"
            )
        
        # 디렉토리 존재 확인
        if not requested_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"디렉토리를 찾을 수 없습니다: {requested_path}"
            )
        
        if not requested_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"디렉토리가 아닙니다: {requested_path}"
            )
        
        return requested_path
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"디렉토리 경로 검증 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 디렉토리 경로입니다: {str(e)}"
        )


# Request/Response 모델
class IndexRequest(BaseModel):
    """인덱싱 요청 모델"""
    clear_existing: bool = False
    """기존 인덱스를 초기화하고 재인덱싱할지 여부"""
    directory: Optional[str] = None
    """인덱싱할 디렉토리 경로 (기본값: data/rag)"""


class IndexResponse(BaseModel):
    """인덱싱 응답 모델"""
    success: bool
    message: str
    total_chunks: Optional[int] = None
    """인덱싱된 총 Chunk 개수"""
    directory: str
    """인덱싱된 디렉토리 경로"""


class IndexStatusResponse(BaseModel):
    """인덱싱 상태 응답 모델"""
    is_indexing: bool
    """현재 인덱싱 진행 중인지 여부"""
    last_indexed: Optional[str] = None
    """마지막 인덱싱 시간"""
    total_chunks: Optional[int] = None
    """현재 인덱스에 저장된 총 Chunk 개수"""


# 전역 인덱싱 상태 관리
# 주의: 현재는 단일 프로세스 환경에서만 동작합니다.
# 멀티프로세스 환경이나 분산 환경에서는 Redis 또는 DB를 사용해야 합니다.
# TODO: 향후 Redis 또는 DB 기반 상태 관리로 마이그레이션
_indexing_status = {
    "is_indexing": False,
    "last_indexed": None,
    "total_chunks": None
}


class IndexingStatusManager:
    """
    인덱싱 상태 관리 클래스
    
    향후 Redis 또는 DB 기반으로 확장 가능하도록 클래스로 분리했습니다.
    """
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """인덱싱 상태 조회"""
        global _indexing_status
        return _indexing_status.copy()
    
    @staticmethod
    def set_indexing(is_indexing: bool):
        """인덱싱 상태 설정"""
        global _indexing_status
        _indexing_status["is_indexing"] = is_indexing
    
    @staticmethod
    def update_last_indexed(total_chunks: int):
        """마지막 인덱싱 정보 업데이트"""
        global _indexing_status
        from src.utils.helpers import get_kst_now
        _indexing_status["is_indexing"] = False
        _indexing_status["last_indexed"] = get_kst_now().isoformat()
        _indexing_status["total_chunks"] = total_chunks
    
    @staticmethod
    def reset():
        """상태 초기화"""
        global _indexing_status
        _indexing_status["last_indexed"] = None
        _indexing_status["total_chunks"] = None


def _index_documents(clear_existing: bool, directory: Optional[str] = None):
    """백그라운드에서 문서 인덱싱 수행"""
    try:
        IndexingStatusManager.set_indexing(True)
        
        # 디렉토리 경로 설정 및 검증
        if directory:
            rag_dir = _validate_directory_path(directory)
        else:
            rag_dir = ALLOWED_RAG_BASE_DIR
        
        if not rag_dir.exists():
            raise FileNotFoundError(f"RAG 문서 디렉토리를 찾을 수 없습니다: {rag_dir}")
        
        # 파이프라인 초기화
        pipeline = RAGIndexingPipeline()
        
        # 기존 인덱스 초기화
        if clear_existing:
            logger.info("기존 인덱스 초기화 중...")
            pipeline.clear_collection()
        
        # 인덱싱 수행
        total_chunks = pipeline.index_directory(rag_dir, recursive=True)
        
        # 상태 업데이트
        IndexingStatusManager.update_last_indexed(total_chunks)
        
        logger.info(f"RAG 문서 인덱싱 완료! 총 {total_chunks}개 Chunk 인덱싱됨")
        
    except Exception as e:
        IndexingStatusManager.set_indexing(False)
        logger.error(f"인덱싱 실패: {str(e)}", exc_info=True)
        raise


@router.post("/index", response_model=IndexResponse)
async def index_documents(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    """
    RAG 문서 인덱싱 시작
    
    - **clear_existing**: 기존 인덱스를 초기화하고 재인덱싱할지 여부
    - **directory**: 인덱싱할 디렉토리 경로 (기본값: data/rag)
    
    백그라운드에서 인덱싱이 수행되므로 즉시 응답이 반환됩니다.
    인덱싱 상태는 `/rag/status` 엔드포인트로 확인할 수 있습니다.
    """
    status = IndexingStatusManager.get_status()
    
    # 이미 인덱싱 중이면 에러 반환
    if status["is_indexing"]:
        raise HTTPException(
            status_code=409,
            detail="이미 인덱싱이 진행 중입니다. 잠시 후 다시 시도해주세요."
        )
    
    # 디렉토리 경로 설정 및 검증
    if request.directory:
        rag_dir = _validate_directory_path(request.directory)
    else:
        rag_dir = ALLOWED_RAG_BASE_DIR
    
    # 백그라운드 작업으로 인덱싱 시작
    background_tasks.add_task(
        _index_documents,
        clear_existing=request.clear_existing,
        directory=str(rag_dir) if request.directory else None
    )
    
    return IndexResponse(
        success=True,
        message="인덱싱이 시작되었습니다. 상태는 /rag/status 엔드포인트로 확인할 수 있습니다.",
        directory=str(rag_dir)
    )


@router.get("/status", response_model=IndexStatusResponse)
async def get_index_status(_: str = Depends(verify_api_key)):
    """
    RAG 문서 인덱싱 상태 조회
    
    현재 인덱싱 진행 상태와 마지막 인덱싱 정보를 반환합니다.
    """
    status = IndexingStatusManager.get_status()
    
    # 현재 인덱스의 Chunk 개수 확인
    try:
        from src.rag.vector_db import vector_db_manager
        collection = vector_db_manager.get_or_create_collection(name="rag_documents")
        count = collection.count()
        status["total_chunks"] = count
    except Exception as e:
        logger.warning(f"인덱스 Chunk 개수 확인 실패: {str(e)}")
    
    return IndexStatusResponse(
        is_indexing=status["is_indexing"],
        last_indexed=status["last_indexed"],
        total_chunks=status["total_chunks"]
    )


@router.delete("/index")
async def clear_index(_: str = Depends(verify_api_key)):
    """
    RAG 문서 인덱스 초기화
    
    기존 인덱스를 완전히 삭제합니다. 주의: 이 작업은 되돌릴 수 없습니다.
    """
    status = IndexingStatusManager.get_status()
    
    # 인덱싱 중이면 에러 반환
    if status["is_indexing"]:
        raise HTTPException(
            status_code=409,
            detail="인덱싱이 진행 중일 때는 인덱스를 초기화할 수 없습니다."
        )
    
    try:
        from src.rag.vector_db import vector_db_manager
        vector_db_manager.delete_collection("rag_documents")
        
        # 상태 초기화
        IndexingStatusManager.reset()
        
        logger.info("RAG 인덱스 초기화 완료")
        
        return {
            "success": True,
            "message": "인덱스가 초기화되었습니다."
        }
    except Exception as e:
        logger.error(f"인덱스 초기화 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"인덱스 초기화 실패: {str(e)}"
        )

