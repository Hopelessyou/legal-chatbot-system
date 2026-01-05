"""
RAG 결과 활용 헬퍼 함수
RAG 검색 결과를 파싱하여 실제로 활용할 수 있도록 변환
"""
import yaml
from typing import Dict, Any, List, Optional
from src.rag.parser import RAGDocumentParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


def extract_required_fields_from_rag(rag_results: List[Dict[str, Any]]) -> List[str]:
    """
    RAG K2 결과에서 필수 필드 목록 추출
    
    Args:
        rag_results: RAG 검색 결과 리스트
    
    Returns:
        필수 필드 목록
    """
    if not rag_results:
        return []
    
    try:
        # 첫 번째 결과의 content 파싱 시도
        first_result = rag_results[0]
        content = first_result.get("content", "")
        
        if not content:
            return []
        
        # YAML 형식으로 파싱 시도
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                # K2 문서 구조에서 required_fields 추출
                required_fields = data.get("required_fields", [])
                if isinstance(required_fields, list):
                    # 리스트가 딕셔너리 리스트인 경우 field 키 추출
                    field_list = []
                    for field_item in required_fields:
                        if isinstance(field_item, dict):
                            field_key = field_item.get("field")
                            if field_key:
                                field_list.append(field_key)
                        elif isinstance(field_item, str):
                            field_list.append(field_item)
                    return field_list
        except yaml.YAMLError:
            # YAML 파싱 실패 시 텍스트에서 필드명 추출 시도
            logger.debug("RAG 결과 YAML 파싱 실패, 텍스트에서 필드 추출 시도")
            # 간단한 패턴 매칭으로 필드 추출
            import re
            field_pattern = r'field["\']?\s*:\s*["\']?(\w+)["\']?'
            fields = re.findall(field_pattern, content, re.IGNORECASE)
            if fields:
                return list(set(fields))  # 중복 제거
    
    except Exception as e:
        logger.warning(f"RAG 결과에서 필수 필드 추출 실패: {str(e)}")
    
    return []


def extract_question_template_from_rag(
    rag_results: List[Dict[str, Any]],
    field: str
) -> Optional[str]:
    """
    RAG K2 결과에서 특정 필드의 질문 템플릿 추출
    
    Args:
        rag_results: RAG 검색 결과 리스트
        field: 필드명 (예: "incident_date", "counterparty")
    
    Returns:
        질문 템플릿 문자열 또는 None
    """
    if not rag_results:
        return None
    
    try:
        # 모든 결과에서 질문 템플릿 찾기
        for result in rag_results:
            content = result.get("content", "")
            if not content:
                continue
            
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    # question_templates에서 해당 필드 찾기
                    question_templates = data.get("question_templates", {})
                    if isinstance(question_templates, dict):
                        question = question_templates.get(field)
                        if question:
                            return question
            except yaml.YAMLError:
                # YAML 파싱 실패 시 텍스트에서 검색
                import re
                # field: "질문" 패턴 찾기
                pattern = rf'{field}["\']?\s*:\s*["\']([^"\']+)["\']'
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
    
    except Exception as e:
        logger.warning(f"RAG 결과에서 질문 템플릿 추출 실패 (field={field}): {str(e)}")
    
    return None


def extract_k4_format_from_rag(rag_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    RAG K4 결과에서 출력 포맷 추출
    
    Args:
        rag_results: RAG 검색 결과 리스트
    
    Returns:
        K4 포맷 딕셔너리 또는 None
    """
    if not rag_results:
        return None
    
    try:
        # 첫 번째 결과의 content 파싱
        first_result = rag_results[0]
        content = first_result.get("content", "")
        
        if not content:
            return None
        
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                # K4 문서 구조에서 format 추출
                format_data = data.get("format", {})
                if isinstance(format_data, dict):
                    return format_data
        except yaml.YAMLError:
            logger.debug("RAG K4 결과 YAML 파싱 실패")
    
    except Exception as e:
        logger.warning(f"RAG 결과에서 K4 포맷 추출 실패: {str(e)}")
    
    return None

