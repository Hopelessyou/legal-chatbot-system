"""
RAG 문서 인덱싱 관련 API 라우터
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
from src.rag.pipeline import RAGIndexingPipeline
from src.utils.response import success_response, error_response
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


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
_indexing_status = {
    "is_indexing": False,
    "last_indexed": None,
    "total_chunks": None
}


def _index_documents(clear_existing: bool, directory: Optional[str] = None):
    """백그라운드에서 문서 인덱싱 수행"""
    global _indexing_status
    
    try:
        _indexing_status["is_indexing"] = True
        
        # 디렉토리 경로 설정
        if directory:
            rag_dir = Path(directory)
        else:
            rag_dir = Path(__file__).parent.parent.parent.parent / "data" / "rag"
        
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
        from datetime import datetime
        _indexing_status["is_indexing"] = False
        _indexing_status["last_indexed"] = datetime.utcnow().isoformat()
        _indexing_status["total_chunks"] = total_chunks
        
        logger.info(f"RAG 문서 인덱싱 완료! 총 {total_chunks}개 Chunk 인덱싱됨")
        
    except Exception as e:
        _indexing_status["is_indexing"] = False
        logger.error(f"인덱싱 실패: {str(e)}", exc_info=True)
        raise


@router.post("/index", response_model=IndexResponse)
async def index_documents(
    request: IndexRequest,
    background_tasks: BackgroundTasks
):
    """
    RAG 문서 인덱싱 시작
    
    - **clear_existing**: 기존 인덱스를 초기화하고 재인덱싱할지 여부
    - **directory**: 인덱싱할 디렉토리 경로 (기본값: data/rag)
    
    백그라운드에서 인덱싱이 수행되므로 즉시 응답이 반환됩니다.
    인덱싱 상태는 `/rag/status` 엔드포인트로 확인할 수 있습니다.
    """
    global _indexing_status
    
    # 이미 인덱싱 중이면 에러 반환
    if _indexing_status["is_indexing"]:
        raise HTTPException(
            status_code=409,
            detail="이미 인덱싱이 진행 중입니다. 잠시 후 다시 시도해주세요."
        )
    
    # 디렉토리 경로 설정
    if request.directory:
        rag_dir = Path(request.directory)
    else:
        rag_dir = Path(__file__).parent.parent.parent.parent / "data" / "rag"
    
    if not rag_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"RAG 문서 디렉토리를 찾을 수 없습니다: {rag_dir}"
        )
    
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
async def get_index_status():
    """
    RAG 문서 인덱싱 상태 조회
    
    현재 인덱싱 진행 상태와 마지막 인덱싱 정보를 반환합니다.
    """
    global _indexing_status
    
    # 현재 인덱스의 Chunk 개수 확인
    try:
        from src.rag.vector_db import vector_db_manager
        collection = vector_db_manager.get_or_create_collection(name="rag_documents")
        count = collection.count()
        _indexing_status["total_chunks"] = count
    except Exception as e:
        logger.warning(f"인덱스 Chunk 개수 확인 실패: {str(e)}")
    
    return IndexStatusResponse(
        is_indexing=_indexing_status["is_indexing"],
        last_indexed=_indexing_status["last_indexed"],
        total_chunks=_indexing_status["total_chunks"]
    )


@router.delete("/index")
async def clear_index():
    """
    RAG 문서 인덱스 초기화
    
    기존 인덱스를 완전히 삭제합니다. 주의: 이 작업은 되돌릴 수 없습니다.
    """
    global _indexing_status
    
    # 인덱싱 중이면 에러 반환
    if _indexing_status["is_indexing"]:
        raise HTTPException(
            status_code=409,
            detail="인덱싱이 진행 중일 때는 인덱스를 초기화할 수 없습니다."
        )
    
    try:
        from src.rag.vector_db import vector_db_manager
        vector_db_manager.delete_collection("rag_documents")
        
        # 상태 초기화
        _indexing_status["last_indexed"] = None
        _indexing_status["total_chunks"] = None
        
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

