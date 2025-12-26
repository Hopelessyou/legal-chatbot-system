"""
RAG 문서 인덱싱 스크립트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.pipeline import RAGIndexingPipeline
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    """RAG 문서 인덱싱 메인 함수"""
    logger.info("RAG 문서 인덱싱 시작...")
    
    # RAG 문서 디렉토리 경로
    rag_dir = Path(__file__).parent.parent / "data" / "rag"
    
    if not rag_dir.exists():
        logger.error(f"RAG 문서 디렉토리를 찾을 수 없습니다: {rag_dir}")
        return
    
    # 파이프라인 초기화
    pipeline = RAGIndexingPipeline()
    
    # 기존 인덱스 초기화 여부 확인
    import argparse
    parser = argparse.ArgumentParser(description="RAG 문서 인덱싱")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="기존 인덱스를 초기화하고 재인덱싱"
    )
    args = parser.parse_args()
    
    if args.clear:
        logger.info("기존 인덱스 초기화 중...")
        pipeline.clear_collection()
    
    # 인덱싱 수행
    try:
        total_chunks = pipeline.index_directory(rag_dir, recursive=True)
        logger.info(f"RAG 문서 인덱싱 완료! 총 {total_chunks}개 Chunk 인덱싱됨")
    except Exception as e:
        logger.error(f"인덱싱 실패: {str(e)}")
        raise


if __name__ == "__main__":
    main()

