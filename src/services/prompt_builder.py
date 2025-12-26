"""
프롬프트 빌더 모듈
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    """프롬프트 빌더 클래스"""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        프롬프트 빌더 초기화
        
        Args:
            templates_dir: 템플릿 디렉토리 경로
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "prompts"
        
        self.templates_dir = templates_dir
        self.templates: Dict[str, str] = {}
        self._load_templates()
    
    def _load_templates(self):
        """템플릿 파일 로드"""
        if not self.templates_dir.exists():
            logger.warning(f"템플릿 디렉토리를 찾을 수 없습니다: {self.templates_dir}")
            return
        
        for template_file in self.templates_dir.glob("*.txt"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.templates[template_file.stem] = f.read()
                logger.debug(f"템플릿 로드 완료: {template_file.stem}")
            except Exception as e:
                logger.error(f"템플릿 로드 실패: {template_file} - {str(e)}")
    
    def load_template(self, template_name: str) -> Optional[str]:
        """
        템플릿 로드
        
        Args:
            template_name: 템플릿 이름
        
        Returns:
            템플릿 내용 또는 None
        """
        return self.templates.get(template_name)
    
    def build_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any],
        fallback_template: Optional[str] = None
    ) -> str:
        """
        프롬프트 빌드
        
        Args:
            template_name: 템플릿 이름
            variables: 변수 딕셔너리
            fallback_template: 템플릿이 없을 때 사용할 기본 템플릿
        
        Returns:
            빌드된 프롬프트 문자열
        """
        template = self.load_template(template_name)
        
        if template is None:
            if fallback_template:
                template = fallback_template
            else:
                logger.warning(f"템플릿을 찾을 수 없습니다: {template_name}")
                return ""
        
        # 변수 치환
        try:
            prompt = template.format(**variables)
            return prompt
        except KeyError as e:
            logger.error(f"템플릿 변수 누락: {template_name} - {str(e)}")
            return template
    
    def inject_rag_context(
        self,
        prompt: str,
        rag_results: List[Dict[str, Any]],
        max_context_length: int = 2000
    ) -> str:
        """
        RAG 검색 결과를 프롬프트에 주입
        
        Args:
            prompt: 원본 프롬프트
            rag_results: RAG 검색 결과 리스트
            max_context_length: 최대 컨텍스트 길이 (문자 수)
        
        Returns:
            RAG 컨텍스트가 주입된 프롬프트
        """
        if not rag_results:
            return prompt
        
        # RAG 컨텍스트 구성
        context_parts = []
        current_length = 0
        
        for result in rag_results:
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            
            context_line = f"[{metadata.get('doc_id', '')}] {content}"
            
            if current_length + len(context_line) > max_context_length:
                break
            
            context_parts.append(context_line)
            current_length += len(context_line)
        
        if context_parts:
            rag_context = "\n\n참고 문서:\n" + "\n".join(context_parts)
            return prompt + rag_context
        
        return prompt
    
    def combine_prompts(self, prompts: List[str], separator: str = "\n\n") -> str:
        """
        여러 프롬프트 결합
        
        Args:
            prompts: 프롬프트 리스트
            separator: 구분자
        
        Returns:
            결합된 프롬프트
        """
        return separator.join([p for p in prompts if p])


# 전역 프롬프트 빌더 인스턴스
prompt_builder = PromptBuilder()

