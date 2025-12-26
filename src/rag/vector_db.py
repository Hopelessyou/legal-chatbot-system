"""
벡터 DB 연결 및 관리 모듈
"""
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorDBManager:
    """벡터 DB 관리 클래스"""
    
    def __init__(self):
        self.client: chromadb.Client = None
        self.collections: Dict[str, chromadb.Collection] = {}
        self._initialize()
    
    def _initialize(self):
        """벡터 DB 초기화"""
        try:
            if settings.vector_db_type == "chroma":
                # ChromaDB 초기화
                db_path = Path(settings.vector_db_path)
                db_path.mkdir(parents=True, exist_ok=True)
                
                self.client = chromadb.PersistentClient(
                    path=str(db_path),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                logger.info(f"ChromaDB 초기화 완료: {db_path}")
            else:
                raise ValueError(f"지원하지 않는 벡터 DB 타입: {settings.vector_db_type}")
        
        except Exception as e:
            logger.error(f"벡터 DB 초기화 실패: {str(e)}")
            raise
    
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> chromadb.Collection:
        """
        컬렉션 획득 또는 생성
        
        Args:
            name: 컬렉션 이름
            metadata: 컬렉션 메타데이터
        
        Returns:
            Collection 인스턴스
        """
        if name not in self.collections:
            try:
                # ChromaDB는 빈 metadata를 허용하지 않으므로 기본값 제공
                if metadata is None or len(metadata) == 0:
                    metadata = {"description": f"Collection for {name}"}
                
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata=metadata
                )
                logger.info(f"컬렉션 획득/생성 완료: {name}")
            except Exception as e:
                logger.error(f"컬렉션 생성 실패: {name} - {str(e)}")
                raise
        
        return self.collections[name]
    
    def get_collection(self, name: str) -> Optional[chromadb.Collection]:
        """
        컬렉션 획득
        
        Args:
            name: 컬렉션 이름
        
        Returns:
            Collection 인스턴스 또는 None
        """
        if name in self.collections:
            return self.collections[name]
        
        try:
            collection = self.client.get_collection(name)
            self.collections[name] = collection
            return collection
        except Exception as e:
            logger.warning(f"컬렉션을 찾을 수 없음: {name} - {str(e)}")
            return None
    
    def delete_collection(self, name: str):
        """
        컬렉션 삭제
        
        Args:
            name: 컬렉션 이름
        """
        try:
            self.client.delete_collection(name)
            if name in self.collections:
                del self.collections[name]
            logger.info(f"컬렉션 삭제 완료: {name}")
        except Exception as e:
            logger.error(f"컬렉션 삭제 실패: {name} - {str(e)}")
            raise
    
    def list_collections(self) -> List[str]:
        """
        컬렉션 목록 조회
        
        Returns:
            컬렉션 이름 리스트
        """
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"컬렉션 목록 조회 실패: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """
        벡터 DB 연결 상태 확인
        
        Returns:
            연결 상태 (True: 정상, False: 오류)
        """
        try:
            self.client.heartbeat()
            logger.debug("벡터 DB 연결 상태: 정상")
            return True
        except Exception as e:
            logger.error(f"벡터 DB 연결 상태 확인 실패: {str(e)}")
            return False


# 전역 벡터 DB 매니저 인스턴스
vector_db_manager = VectorDBManager()

