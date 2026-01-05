"""
누락 필드 관리 모듈
"""
from typing import List, Dict, Any, Optional
from src.langgraph.state import StateContext
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger
from src.utils.constants import REQUIRED_FIELDS_BY_CASE_TYPE, CASE_TYPE_MAPPING
from config.priority import get_next_priority_field

logger = get_logger(__name__)


def detect_missing_fields(state: StateContext) -> List[str]:
    """
    누락 필드 감지
    
    Args:
        state: StateContext
    
    Returns:
        누락된 필드 키 리스트
    """
    try:
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        facts = state.get("facts", {})
        
        # case_type 변환 (한글 → 영문)
        main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None
        
        # RAG K2에서 필수 필드 목록 조회
        rag_results = rag_searcher.search(
            query="필수 필드",
            knowledge_type="K2",
            main_case_type=main_case_type_en,
            sub_case_type=sub_case_type,
            node_scope="VALIDATION",
            top_k=1
        )
        
        # 필수 필드 목록 (RAG 결과에서 추출 시도, 실패 시 기본값 사용)
        required_fields = REQUIRED_FIELDS_BY_CASE_TYPE.get(
            main_case_type_en, 
            REQUIRED_FIELDS_BY_CASE_TYPE.get("CIVIL", [])
        )
        
        # RAG 검색 결과에서 required_fields 추출
        if rag_results:
            try:
                from src.rag.parser import RAGDocumentParser
                import yaml
                
                result = rag_results[0]
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                
                # content가 YAML 문자열이면 파싱
                if isinstance(content, str):
                    try:
                        k2_data = yaml.safe_load(content)
                    except:
                        k2_data = metadata
                else:
                    k2_data = content if content else metadata
                
                # K2 문서 파싱
                try:
                    k2_doc = RAGDocumentParser.parse_k2_document(k2_data)
                    # required_fields는 이미 문자열 리스트로 변환됨 (parser에서 처리)
                    # 또는 원본 데이터에서 required=True인 필드만 추출
                    if k2_data.get("required_fields"):
                        raw_fields = k2_data.get("required_fields", [])
                        if raw_fields and isinstance(raw_fields[0], dict):
                            # 딕셔너리 리스트인 경우 required=True인 필드만 추출
                            required_fields = [
                                field.get("field") for field in raw_fields 
                                if field.get("required", True)
                            ]
                        else:
                            # 이미 문자열 리스트인 경우
                            required_fields = k2_doc.required_fields
                    else:
                        required_fields = k2_doc.required_fields
                    logger.debug(f"RAG에서 필수 필드 추출: {required_fields}")
                except Exception as parse_error:
                    logger.warning(f"K2 문서 파싱 실패, 기본 필드 사용: {str(parse_error)}")
            except Exception as e:
                logger.warning(f"RAG 결과에서 필수 필드 추출 실패, 기본 필드 사용: {str(e)}")
        
        # 누락 필드 찾기
        missing_fields = []
        for field in required_fields:
            value = facts.get(field)
            if value is None or value == "":
                missing_fields.append(field)
        
        logger.debug(f"누락 필드 감지: {missing_fields}")
        return missing_fields
    
    except Exception as e:
        logger.error(f"누락 필드 감지 실패: {str(e)}")
        return []


def get_next_missing_field(missing_fields: List[str], case_type: Optional[str] = None) -> Optional[str]:
    """
    다음 질문할 누락 필드 선택 (우선순위 기반)
    
    Args:
        missing_fields: 누락 필드 리스트
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        다음 질문할 필드 키 또는 None
    """
    if not missing_fields:
        return None
    
    # config/priority.py의 우선순위 함수 사용
    return get_next_priority_field(missing_fields, case_type)

