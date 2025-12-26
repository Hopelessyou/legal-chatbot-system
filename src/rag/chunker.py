"""
RAG 문서 Chunking 전략 구현
"""
from typing import List, Dict, Any
from src.rag.schema import K1Document, K2Document, K3Document, K4Document, FACTDocument
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Chunk:
    """Chunk 데이터 클래스"""
    def __init__(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any],
        chunk_index: int = 0
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.metadata = metadata
        self.chunk_index = chunk_index
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index
        }


class RAGChunker:
    """RAG 문서 Chunking 클래스"""
    
    @staticmethod
    def chunk_k1_document(doc: K1Document) -> List[Chunk]:
        """
        K1 문서 Chunking (시나리오별로 Chunk 생성)
        
        Args:
            doc: K1Document 인스턴스
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        # 레벨 정보
        level1 = doc.level1 or ""
        level2_code = doc.level2_code or ""
        level2_name = doc.level2_name or ""
        
        # 각 시나리오를 개별 Chunk로 생성
        for idx, scenario in enumerate(doc.scenarios):
            content_parts = []
            
            scenario_code = scenario.get("scenario_code", "")
            scenario_name = scenario.get("scenario_name", "")
            keywords = scenario.get("keywords", [])
            typical_expressions = scenario.get("typical_expressions", [])
            disambiguation_question = scenario.get("disambiguation_question")
            disambiguation_options = scenario.get("disambiguation_options", [])
            
            content_parts.append(f"LEVEL1: {level1}")
            content_parts.append(f"LEVEL2: {level2_code} ({level2_name})")
            content_parts.append(f"시나리오: {scenario_code} ({scenario_name})")
            
            if keywords:
                content_parts.append("\n키워드:")
                content_parts.append(", ".join(keywords))
            
            if typical_expressions:
                content_parts.append("\n대표 표현:")
                content_parts.extend([f"- {expr}" for expr in typical_expressions])
            
            if disambiguation_question:
                content_parts.append(f"\n확인 질문: {disambiguation_question}")
            
            if disambiguation_options:
                content_parts.append("선택지:")
                for option in disambiguation_options:
                    content_parts.append(f"- {option}")
            
            # 전체 키워드/표현도 포함
            if doc.typical_keywords:
                content_parts.append("\n전체 키워드:")
                content_parts.append(", ".join(doc.typical_keywords))
            
            if doc.typical_expressions:
                content_parts.append("\n전체 대표 표현:")
                content_parts.extend([f"- {expr}" for expr in doc.typical_expressions])
            
            content = "\n".join(content_parts)
            
            chunk = Chunk(
                chunk_id=f"{doc.metadata.doc_id}-{scenario_code}-chunk-{idx}",
                content=content,
                metadata={
                    "doc_id": doc.metadata.doc_id,
                    "knowledge_type": doc.metadata.knowledge_type,
                    "main_case_type": doc.metadata.main_case_type,
                    "sub_case_type": doc.metadata.sub_case_type,
                    "node_scope": doc.metadata.node_scope,
                    "level1": level1,
                    "level2_code": level2_code,
                    "level2_name": level2_name,
                    "scenario_code": scenario_code,
                    "scenario_name": scenario_name,
                },
                chunk_index=idx
            )
            
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def chunk_k2_document(doc: K2Document) -> List[Chunk]:
        """
        K2 문서 Chunking (사건 유형별 필수 질문 세트)
        
        Args:
            doc: K2Document 인스턴스
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        # 필수 필드와 질문을 하나의 Chunk로 생성
        content_parts = []
        
        # 레벨 정보
        if doc.level1:
            content_parts.append(f"LEVEL1: {doc.level1}")
        if doc.level2:
            content_parts.append(f"LEVEL2: {doc.level2}")
        if doc.scenario:
            content_parts.append(f"시나리오: {doc.scenario}")
        
        # 필수 필드
        if doc.required_fields:
            content_parts.append("\n필수 필드:")
            for field in doc.required_fields:
                content_parts.append(f"- {field}")
        
        # 질문 목록
        if doc.questions:
            content_parts.append("\n질문 목록:")
            for question in doc.questions:
                order = question.get("order", 0)
                field = question.get("field", "")
                question_text = question.get("question", "")
                answer_type = question.get("answer_type", "")
                required = question.get("required", False)
                
                q_info = f"{order}. [{field}] {question_text}"
                if answer_type:
                    q_info += f" (타입: {answer_type})"
                if required:
                    q_info += " (필수)"
                
                content_parts.append(q_info)
        
        content = "\n".join(content_parts)
        
        chunk = Chunk(
            chunk_id=f"{doc.metadata.doc_id}-chunk-0",
            content=content,
            metadata={
                "doc_id": doc.metadata.doc_id,
                "knowledge_type": doc.metadata.knowledge_type,
                "main_case_type": doc.metadata.main_case_type,
                "sub_case_type": doc.metadata.sub_case_type,
                "node_scope": doc.metadata.node_scope,
                "level1": doc.level1,
                "level2": doc.level2,
                "scenario": doc.scenario,
            },
            chunk_index=0
        )
        
        chunks.append(chunk)
        return chunks
    
    @staticmethod
    def chunk_k3_document(doc: K3Document) -> List[Chunk]:
        """
        K3 문서 Chunking (리스크 규칙 3~5개 단위)
        
        Args:
            doc: K3Document 인스턴스
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        # 레벨 정보
        level1 = doc.level1 or ""
        level2 = doc.level2 or ""
        scenario = doc.scenario or ""
        
        # 리스크 규칙을 그룹으로 나눔 (3~5개씩)
        chunk_size = 4
        rules = doc.rules
        
        for i in range(0, len(rules), chunk_size):
            group = rules[i:i + chunk_size]
            
            content_parts = []
            content_parts.append(f"LEVEL1: {level1}")
            content_parts.append(f"LEVEL2: {level2}")
            content_parts.append(f"시나리오: {scenario}")
            content_parts.append("\n리스크 규칙:")
            
            for rule in group:
                rule_code = rule.get("rule_code", "")
                trigger_facts = rule.get("trigger_facts", [])
                risk_level = rule.get("risk_level", "")
                risk_tag = rule.get("risk_tag", "")
                description = rule.get("description", "")
                action_hint = rule.get("action_hint", "")
                
                content_parts.append(f"\n규칙 코드: {rule_code}")
                if trigger_facts:
                    content_parts.append(f"발동 사실: {', '.join(trigger_facts)}")
                content_parts.append(f"리스크 레벨: {risk_level}")
                if risk_tag:
                    content_parts.append(f"태그: {risk_tag}")
                if description:
                    content_parts.append(f"설명: {description}")
                if action_hint:
                    content_parts.append(f"액션 힌트: {action_hint}")
                content_parts.append("---")
            
            content = "\n".join(content_parts)
            
            chunk = Chunk(
                chunk_id=f"{doc.metadata.doc_id}-chunk-{i // chunk_size}",
                content=content,
                metadata={
                    "doc_id": doc.metadata.doc_id,
                    "knowledge_type": doc.metadata.knowledge_type,
                    "main_case_type": doc.metadata.main_case_type,
                    "sub_case_type": doc.metadata.sub_case_type,
                    "node_scope": doc.metadata.node_scope,
                    "level1": level1,
                    "level2": level2,
                    "scenario": scenario,
                },
                chunk_index=i // chunk_size
            )
            
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def chunk_k4_document(doc: K4Document) -> List[Chunk]:
        """
        K4 문서 Chunking (포맷 1개 = 1 Chunk)
        
        Args:
            doc: K4Document 인스턴스
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        content_parts = []
        
        # 대상 사용자
        if doc.target:
            content_parts.append(f"대상: {doc.target}")
        
        # 섹션 목록
        if doc.sections:
            content_parts.append("\n섹션:")
            for section in doc.sections:
                order = section.get("order", 0)
                key = section.get("key", "")
                title = section.get("title", "")
                content_rule = section.get("content_rule", "")
                source = section.get("source", "")
                style = section.get("style", "")
                
                section_info = f"{order}. [{key}] {title}"
                if content_rule:
                    section_info += f"\n  내용 규칙: {content_rule}"
                if source:
                    section_info += f"\n  소스: {source}"
                if style:
                    section_info += f"\n  스타일: {style}"
                
                content_parts.append(section_info)
        
        content = "\n".join(content_parts)
        
        chunk = Chunk(
            chunk_id=f"{doc.metadata.doc_id}-chunk-0",
            content=content,
            metadata={
                "doc_id": doc.metadata.doc_id,
                "knowledge_type": doc.metadata.knowledge_type,
                "main_case_type": doc.metadata.main_case_type,
                "sub_case_type": doc.metadata.sub_case_type,
                "node_scope": doc.metadata.node_scope,
                "target": doc.target,
            },
            chunk_index=0
        )
        
        chunks.append(chunk)
        return chunks
    
    @staticmethod
    def chunk_fact_document(doc: FACTDocument) -> List[Chunk]:
        """
        FACT 문서 Chunking (사실 패턴 1개 = 1 Chunk)
        
        Args:
            doc: FACTDocument 인스턴스
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        content_parts = []
        
        # 레벨 정보
        if doc.level1:
            content_parts.append(f"LEVEL1: {doc.level1}")
        if doc.level2:
            content_parts.append(f"LEVEL2: {doc.level2}")
        if doc.scenario:
            content_parts.append(f"시나리오: {doc.scenario}")
        
        # 사실 패턴 목록
        if doc.facts:
            content_parts.append("\n사실 패턴:")
            for fact in doc.facts:
                fact_code = fact.get("fact_code", "")
                name = fact.get("name", "")
                description = fact.get("description", "")
                critical = fact.get("critical", False)
                related_field = fact.get("related_field", "")
                
                fact_info = f"- {fact_code}: {name}"
                if critical:
                    fact_info += " (중요)"
                if description:
                    fact_info += f"\n  설명: {description}"
                if related_field:
                    fact_info += f"\n  관련 필드: {related_field}"
                
                content_parts.append(fact_info)
        
        content = "\n".join(content_parts)
        
        chunk = Chunk(
            chunk_id=f"{doc.metadata.doc_id}-chunk-0",
            content=content,
            metadata={
                "doc_id": doc.metadata.doc_id,
                "knowledge_type": doc.metadata.knowledge_type,
                "main_case_type": doc.metadata.main_case_type,
                "sub_case_type": doc.metadata.sub_case_type,
                "node_scope": doc.metadata.node_scope,
                "level1": doc.level1,
                "level2": doc.level2,
                "scenario": doc.scenario,
            },
            chunk_index=0
        )
        
        chunks.append(chunk)
        return chunks
    
    @staticmethod
    def chunk_k0_document(doc: Dict[str, Any]) -> List[Chunk]:
        """
        K0 문서 Chunking (인입 메시지 1개 = 1 Chunk)
        
        Args:
            doc: K0 문서 딕셔너리
        
        Returns:
            Chunk 리스트
        """
        chunks = []
        
        doc_id = doc.get("doc_id", "K0-UNKNOWN")
        knowledge_type = doc.get("knowledge_type", "K0")
        messages = doc.get("messages", [])
        
        # 각 메시지를 하나의 Chunk로 생성
        for idx, message in enumerate(messages):
            content_parts = []
            
            step_code = message.get("step_code", "")
            order = message.get("order", idx)
            message_text = message.get("message_text", "")
            answer_type = message.get("answer_type", "")
            next_action = message.get("next_action", "")
            
            content_parts.append(f"STEP: {step_code}")
            content_parts.append(f"순서: {order}")
            content_parts.append(f"메시지: {message_text}")
            if answer_type:
                content_parts.append(f"답변 타입: {answer_type}")
            if next_action:
                content_parts.append(f"다음 액션: {next_action}")
            
            content = "\n".join(content_parts)
            
            chunk = Chunk(
                chunk_id=f"{doc_id}-chunk-{idx}",
                content=content,
                metadata={
                    "doc_id": doc_id,
                    "knowledge_type": knowledge_type,
                    "step_code": step_code,
                    "order": order,
                    "answer_type": answer_type,
                    "next_action": next_action,
                },
                chunk_index=idx
            )
            
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def chunk_document(doc: Any) -> List[Chunk]:
        """
        문서 타입에 따라 자동 Chunking
        
        Args:
            doc: 문서 객체 (K0Document(dict), K1Document, K2Document, K3Document, K4Document, FACTDocument)
        
        Returns:
            Chunk 리스트
        """
        # K0는 dict로 반환됨
        if isinstance(doc, dict) and doc.get("knowledge_type") == "K0":
            return RAGChunker.chunk_k0_document(doc)
        elif isinstance(doc, K1Document):
            return RAGChunker.chunk_k1_document(doc)
        elif isinstance(doc, K2Document):
            return RAGChunker.chunk_k2_document(doc)
        elif isinstance(doc, K3Document):
            return RAGChunker.chunk_k3_document(doc)
        elif isinstance(doc, K4Document):
            return RAGChunker.chunk_k4_document(doc)
        elif isinstance(doc, FACTDocument):
            return RAGChunker.chunk_fact_document(doc)
        else:
            raise ValueError(f"지원하지 않는 문서 타입: {type(doc)}")

