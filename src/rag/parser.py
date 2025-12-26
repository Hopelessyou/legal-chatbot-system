"""
RAG 문서 파싱 모듈
"""
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.rag.schema import (
    RAGDocumentMetadata,
    K1Document,
    K2Document,
    K3Document,
    K4Document,
    FACTDocument
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RAGDocumentParser:
    """RAG 문서 파서"""
    
    @staticmethod
    def load_yaml(file_path: Path) -> Dict[str, Any]:
        """
        YAML 파일 로드
        
        Args:
            file_path: 파일 경로
        
        Returns:
            파싱된 딕셔너리
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"YAML 파일 로드 실패: {file_path} - {str(e)}")
            raise
    
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """
        JSON 파일 로드
        
        Args:
            file_path: 파일 경로
        
        Returns:
            파싱된 딕셔너리
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 파일 로드 실패: {file_path} - {str(e)}")
            raise
    
    @staticmethod
    def extract_metadata(data: Dict[str, Any]) -> RAGDocumentMetadata:
        """
        메타데이터 추출
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            RAGDocumentMetadata 인스턴스
        """
        metadata_dict = {
            "doc_id": data.get("doc_id"),
            "knowledge_type": data.get("knowledge_type"),
            "main_case_type": data.get("main_case_type"),
            "sub_case_type": data.get("sub_case_type"),
            "node_scope": data.get("node_scope", []),
            "version": data.get("version", "v1.0"),
        }
        
        # last_updated 파싱
        if "last_updated" in data:
            from datetime import datetime
            if isinstance(data["last_updated"], str):
                metadata_dict["last_updated"] = datetime.fromisoformat(
                    data["last_updated"].replace('Z', '+00:00')
                )
            else:
                metadata_dict["last_updated"] = data["last_updated"]
        
        return RAGDocumentMetadata(**metadata_dict)
    
    @staticmethod
    def parse_k1_document(data: Dict[str, Any]) -> K1Document:
        """
        K1 문서 파싱
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            K1Document 인스턴스
        """
        metadata = RAGDocumentParser.extract_metadata(data)
        
        return K1Document(
            metadata=metadata,
            level1=data.get("level1"),
            level2_code=data.get("level2_code"),
            level2_name=data.get("level2_name"),
            scenarios=data.get("scenarios", []),
            typical_keywords=data.get("typical_keywords"),
            typical_expressions=data.get("typical_expressions")
        )
    
    @staticmethod
    def parse_k2_document(data: Dict[str, Any]) -> K2Document:
        """
        K2 문서 파싱
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            K2Document 인스턴스
        """
        metadata = RAGDocumentParser.extract_metadata(data)
        
        # required_fields는 문자열 리스트로 변환 (이미 문자열 리스트일 수도 있음)
        required_fields = data.get("required_fields", [])
        if required_fields and isinstance(required_fields[0], dict):
            # 딕셔너리 리스트인 경우 필드명만 추출
            required_fields = [field.get("field", field) if isinstance(field, dict) else field for field in required_fields]
        
        return K2Document(
            metadata=metadata,
            required_fields=required_fields,
            questions=data.get("questions", []),
            level1=data.get("level1"),
            level2=data.get("level2"),
            scenario=data.get("scenario")
        )
    
    @staticmethod
    def parse_k3_document(data: Dict[str, Any]) -> K3Document:
        """
        K3 문서 파싱
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            K3Document 인스턴스
        """
        metadata = RAGDocumentParser.extract_metadata(data)
        
        return K3Document(
            metadata=metadata,
            level1=data.get("level1"),
            level2=data.get("level2"),
            scenario=data.get("scenario"),
            rules=data.get("rules", [])
        )
    
    @staticmethod
    def parse_k4_document(data: Dict[str, Any]) -> K4Document:
        """
        K4 문서 파싱
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            K4Document 인스턴스
        """
        metadata = RAGDocumentParser.extract_metadata(data)
        
        return K4Document(
            metadata=metadata,
            target=data.get("target"),
            sections=data.get("sections", [])
        )
    
    @staticmethod
    def parse_fact_document(data: Dict[str, Any]) -> FACTDocument:
        """
        FACT 문서 파싱
        
        Args:
            data: 파싱된 문서 데이터
        
        Returns:
            FACTDocument 인스턴스
        """
        metadata = RAGDocumentParser.extract_metadata(data)
        
        return FACTDocument(
            metadata=metadata,
            level1=data.get("level1"),
            level2=data.get("level2"),
            scenario=data.get("scenario"),
            facts=data.get("facts", [])
        )
    
    @staticmethod
    def parse_document(file_path: Path) -> Any:
        """
        문서 타입에 따라 자동 파싱
        
        Args:
            file_path: 파일 경로
        
        Returns:
            파싱된 문서 객체 (K0Document, K1Document, K2Document, K3Document, K4Document, FACTDocument)
        """
        if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
            data = RAGDocumentParser.load_yaml(file_path)
        elif file_path.suffix == '.json':
            data = RAGDocumentParser.load_json(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {file_path.suffix}")
        
        knowledge_type = data.get("knowledge_type")
        
        if knowledge_type == "K0":
            # K0는 간단한 구조이므로 그대로 반환
            return data
        elif knowledge_type == "K1":
            return RAGDocumentParser.parse_k1_document(data)
        elif knowledge_type == "K2":
            return RAGDocumentParser.parse_k2_document(data)
        elif knowledge_type == "K3":
            return RAGDocumentParser.parse_k3_document(data)
        elif knowledge_type == "K4":
            return RAGDocumentParser.parse_k4_document(data)
        elif knowledge_type == "FACT":
            return RAGDocumentParser.parse_fact_document(data)
        else:
            raise ValueError(f"알 수 없는 knowledge_type: {knowledge_type}")

