"""
RAG 검색 통합 테스트
"""
import pytest
from src.rag.searcher import rag_searcher


def test_rag_search_by_knowledge_type():
    """지식 타입별 검색 테스트"""
    results = rag_searcher.search_by_knowledge_type(
        query="계약 분쟁",
        knowledge_type="K1",
        top_k=3
    )
    
    assert isinstance(results, list)
    # 인덱싱이 되어 있다면 결과가 있을 수 있음
    # assert len(results) > 0  # 인덱싱 후 활성화


def test_rag_search_with_filters():
    """필터를 사용한 검색 테스트"""
    results = rag_searcher.search(
        query="필수 필드",
        knowledge_type="K2",
        main_case_type="민사",
        sub_case_type="계약",
        top_k=1
    )
    
    assert isinstance(results, list)

