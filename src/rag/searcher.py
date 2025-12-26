"""
RAG 검색 모듈
"""
from typing import List, Dict, Any, Optional
import numpy as np
from src.rag.vector_db import vector_db_manager
from src.rag.embeddings import embedding_model
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RAGSearcher:
    """RAG 검색 클래스"""
    
    def __init__(self, collection_name: str = "rag_documents"):
        self.collection_name = collection_name
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """컬렉션 초기화"""
        self.collection = vector_db_manager.get_or_create_collection(
            name=self.collection_name
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        knowledge_type: Optional[str] = None,
        main_case_type: Optional[str] = None,
        sub_case_type: Optional[str] = None,
        node_scope: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        RAG 검색 수행
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 결과 개수
            knowledge_type: 지식 타입 필터 (K1, K2, K3, K4)
            main_case_type: 주 사건 유형 필터
            sub_case_type: 세부 사건 유형 필터
            node_scope: Node 범위 필터
            min_score: 최소 유사도 점수
        
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리 Embedding 생성
            query_embedding = embedding_model.encode_query(query).tolist()
            
            # 메타데이터 필터 구성 (ChromaDB는 $and 연산자 필요)
            where_conditions = []
            if knowledge_type:
                where_conditions.append({"knowledge_type": knowledge_type})
            if main_case_type:
                where_conditions.append({"main_case_type": main_case_type})
            if sub_case_type:
                where_conditions.append({"sub_case_type": sub_case_type})
            if node_scope:
                # node_scope는 리스트이므로 $in 사용 또는 각 요소 확인
                # ChromaDB는 배열 필드에 대해 직접 매칭이 어려우므로 일단 제외
                # 필요시 메타데이터에 별도 필드로 저장하는 것을 권장
                pass
            
            # where 필터 구성
            if len(where_conditions) == 0:
                where = None
            elif len(where_conditions) == 1:
                where = where_conditions[0]
            else:
                where = {"$and": where_conditions}
            
            # 검색 수행
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            # 결과 포맷팅
            formatted_results = []
            
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    distance = results["distances"][0][i] if results["distances"] else None
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    document = results["documents"][0][i] if results["documents"] else ""
                    
                    # 유사도 점수 계산 (distance를 score로 변환)
                    score = 1.0 - distance if distance is not None else 0.0
                    
                    # 최소 점수 필터링
                    if score >= min_score:
                        formatted_results.append({
                            "doc_id": doc_id,
                            "content": document,
                            "metadata": metadata,
                            "score": score,
                            "distance": distance
                        })
            
            # 점수 순으로 정렬
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.debug(f"검색 완료: 쿼리='{query}', 결과={len(formatted_results)}개")
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"RAG 검색 실패: {str(e)}")
            raise
    
    def search_by_knowledge_type(
        self,
        query: str,
        knowledge_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        지식 타입별 검색
        
        Args:
            query: 검색 쿼리
            knowledge_type: 지식 타입 (K1, K2, K3, K4)
            top_k: 반환할 결과 개수
        
        Returns:
            검색 결과 리스트
        """
        return self.search(
            query=query,
            top_k=top_k,
            knowledge_type=knowledge_type
        )
    
    def search_by_case_type(
        self,
        query: str,
        main_case_type: str,
        sub_case_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        사건 유형별 검색
        
        Args:
            query: 검색 쿼리
            main_case_type: 주 사건 유형
            sub_case_type: 세부 사건 유형
            top_k: 반환할 결과 개수
        
        Returns:
            검색 결과 리스트
        """
        return self.search(
            query=query,
            top_k=top_k,
            main_case_type=main_case_type,
            sub_case_type=sub_case_type
        )
    
    def search_by_node_scope(
        self,
        query: str,
        node_scope: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Node 범위별 검색
        
        Args:
            query: 검색 쿼리
            node_scope: Node 범위
            top_k: 반환할 결과 개수
        
        Returns:
            검색 결과 리스트
        """
        return self.search(
            query=query,
            top_k=top_k,
            node_scope=node_scope
        )


# 전역 RAG 검색기 인스턴스
rag_searcher = RAGSearcher()

