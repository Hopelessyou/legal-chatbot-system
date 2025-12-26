"""
RAG 문서 인덱싱 파이프라인
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from src.rag.parser import RAGDocumentParser
from src.rag.chunker import RAGChunker, Chunk
from src.rag.vector_db import vector_db_manager
from src.rag.embeddings import embedding_model
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RAGIndexingPipeline:
    """RAG 문서 인덱싱 파이프라인"""
    
    def __init__(self, collection_name: str = "rag_documents"):
        self.collection_name = collection_name
        self.collection = None
        self.parser = RAGDocumentParser()
        self.chunker = RAGChunker()
        self._initialize_collection()
    
    def _initialize_collection(self):
        """컬렉션 초기화"""
        self.collection = vector_db_manager.get_or_create_collection(
            name=self.collection_name
        )
    
    @staticmethod
    def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChromaDB 호환을 위해 metadata 정리
        ChromaDB는 None 값을 허용하지 않으므로 None은 제거하거나 빈 문자열로 변환
        
        Args:
            metadata: 원본 metadata 딕셔너리
        
        Returns:
            정리된 metadata 딕셔너리 (None 값 제외)
        """
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                # None은 제거 (ChromaDB가 None을 허용하지 않음)
                continue
            elif isinstance(value, list):
                # 리스트는 쉼표로 구분된 문자열로 변환
                if len(value) > 0:
                    cleaned[key] = ", ".join(str(item) for item in value)
                # 빈 리스트는 제거
            elif isinstance(value, (str, int, float, bool)):
                # 허용되는 타입은 그대로
                cleaned[key] = value
            elif isinstance(value, dict):
                # 딕셔너리는 JSON 문자열로 변환
                cleaned[key] = json.dumps(value, ensure_ascii=False)
            else:
                # 기타 타입은 문자열로 변환
                cleaned[key] = str(value)
        return cleaned
    
    def index_document(self, file_path: Path) -> int:
        """
        단일 문서 인덱싱
        
        Args:
            file_path: 문서 파일 경로
        
        Returns:
            인덱싱된 Chunk 개수
        """
        try:
            # 문서 파싱
            doc = self.parser.parse_document(file_path)
            logger.info(f"문서 파싱 완료: {file_path.name}")
            
            # Chunking
            chunks = self.chunker.chunk_document(doc)

            logger.info(f"Chunking 완료: {len(chunks)}개 Chunk 생성")
            
            # Embedding 생성 및 저장
            chunk_ids = []
            chunk_contents = []
            chunk_embeddings = []
            chunk_metadatas = []
            
            for chunk in chunks:
                # Embedding 생성 (단일 텍스트이므로 첫 번째 결과만 사용)
                embedding_result = embedding_model.encode(chunk.content)
                # encode()는 항상 2차원 배열을 반환하므로, 단일 텍스트의 경우 [0]으로 첫 번째 벡터 추출
                if embedding_result.ndim == 2:
                    embedding = embedding_result[0].tolist()
                else:
                    embedding = embedding_result.tolist()
                
                # ChromaDB metadata는 리스트를 허용하지 않으므로 변환
                cleaned_metadata = RAGIndexingPipeline._clean_metadata(chunk.metadata)
                
                chunk_ids.append(chunk.chunk_id)
                chunk_contents.append(chunk.content)
                chunk_embeddings.append(embedding)
                chunk_metadatas.append(cleaned_metadata)


            # 벡터 DB에 저장
            self.collection.add(
                ids=chunk_ids,
                embeddings=chunk_embeddings,
                documents=chunk_contents,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"인덱싱 완료: {file_path.name} ({len(chunks)}개 Chunk)")
            return len(chunks)
        
        except Exception as e:
            logger.error(f"문서 인덱싱 실패: {file_path} - {str(e)}")
            raise
    
    def index_directory(self, directory: Path, recursive: bool = True) -> int:
        """
        디렉토리 내 모든 문서 인덱싱
        
        Args:
            directory: 문서 디렉토리 경로
            recursive: 재귀적 검색 여부
        
        Returns:
            인덱싱된 총 Chunk 개수
        """
        total_chunks = 0
        
        # 지원하는 파일 확장자
        extensions = [".yaml", ".yml", ".json"]
        
        # 파일 검색
        if recursive:
            files = []
            for ext in extensions:
                files.extend(directory.rglob(f"*{ext}"))
        else:
            files = []
            for ext in extensions:
                files.extend(directory.glob(f"*{ext}"))
        
        logger.info(f"인덱싱 대상 파일: {len(files)}개")
        
        for file_path in files:
            try:
                chunks_count = self.index_document(file_path)
                total_chunks += chunks_count
            except Exception as e:
                logger.error(f"파일 인덱싱 실패: {file_path} - {str(e)}")
                continue
        
        logger.info(f"전체 인덱싱 완료: {total_chunks}개 Chunk")
        return total_chunks
    
    def clear_collection(self):
        """컬렉션 초기화"""
        try:
            vector_db_manager.delete_collection(self.collection_name)
            self._initialize_collection()
            logger.info(f"컬렉션 초기화 완료: {self.collection_name}")
        except Exception as e:
            logger.error(f"컬렉션 초기화 실패: {str(e)}")
            raise

