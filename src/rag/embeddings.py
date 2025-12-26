"""
Embedding 모델 관리 모듈
"""
from typing import List, Union
import numpy as np
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sentence Transformers를 사용하는 경우
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers가 설치되지 않았습니다.")

# OpenAI Embeddings를 사용하는 경우
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmbeddingModel:
    """Embedding 모델 래퍼 클래스"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.embedding_model
        self._initialize()
    
    def _initialize(self):
        """Embedding 모델 초기화"""
        try:
            # OpenAI Embeddings 사용 여부 확인
            if "text-embedding" in self.model_name.lower() or "openai" in self.model_name.lower():
                if not OPENAI_AVAILABLE:
                    raise ImportError("openai 라이브러리가 설치되지 않았습니다.")
                
                from config.settings import settings
                self.client = OpenAI(api_key=settings.openai_api_key)
                self.model_type = "openai"
                logger.info(f"OpenAI Embedding 모델 초기화: {self.model_name}")
            
            # Sentence Transformers 사용
            else:
                if not SENTENCE_TRANSFORMERS_AVAILABLE:
                    raise ImportError("sentence-transformers 라이브러리가 설치되지 않았습니다.")
                
                self.model = SentenceTransformer(self.model_name)
                self.model_type = "sentence_transformers"
                logger.info(f"Sentence Transformers 모델 초기화: {self.model_name}")
        
        except Exception as e:
            logger.error(f"Embedding 모델 초기화 실패: {str(e)}")
            raise
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        텍스트를 벡터로 변환
        
        Args:
            texts: 변환할 텍스트 또는 텍스트 리스트
            batch_size: 배치 크기
        
        Returns:
            Embedding 벡터 배열
        """
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            if self.model_type == "openai":
                # OpenAI Embeddings API 호출
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
                return np.array(embeddings)
            
            else:
                # Sentence Transformers 사용
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                return embeddings
        
        except Exception as e:
            logger.error(f"Embedding 생성 실패: {str(e)}")
            raise
    
    def encode_query(self, query: str) -> np.ndarray:
        """
        쿼리 텍스트를 벡터로 변환
        
        Args:
            query: 쿼리 텍스트
        
        Returns:
            Embedding 벡터
        """
        return self.encode(query)[0]


# 전역 Embedding 모델 인스턴스
embedding_model = EmbeddingModel()

