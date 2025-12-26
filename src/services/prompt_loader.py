"""
프롬프트 템플릿 로더 모듈
"""
from pathlib import Path
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptLoader:
    """프롬프트 템플릿 로더 클래스"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        프롬프트 로더 초기화
        
        Args:
            prompts_dir: 프롬프트 디렉토리 경로
        """
        if prompts_dir is None:
            # 프로젝트 루트 기준으로 prompts 디렉토리 찾기
            current_file = Path(__file__)
            prompts_dir = current_file.parent.parent / "prompts"
        
        self.prompts_dir = prompts_dir
        logger.debug(f"프롬프트 디렉토리: {self.prompts_dir}")
    
    def load_prompt(
        self,
        template_name: str,
        sub_dir: str = "summary"
    ) -> Optional[str]:
        """
        프롬프트 템플릿 로드
        
        Args:
            template_name: 템플릿 파일명 (확장자 제외, 예: "family_divorce")
            sub_dir: 하위 디렉토리명 (기본값: "summary")
        
        Returns:
            프롬프트 템플릿 내용 또는 None
        """
        try:
            prompt_path = self.prompts_dir / sub_dir / f"{template_name}.txt"
            
            if not prompt_path.exists():
                logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
                return None
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"프롬프트 로드 완료: {template_name}")
            return content
        
        except Exception as e:
            logger.error(f"프롬프트 로드 실패: {template_name} - {str(e)}")
            return None
    
    def get_summary_prompt_name(
        self,
        main_case_type: str,
        sub_case_type: str
    ) -> str:
        """
        케이스 타입에 따른 요약 프롬프트 파일명 결정
        
        Args:
            main_case_type: 주 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
            sub_case_type: 세부 사건 유형
        
        Returns:
            프롬프트 파일명 (확장자 제외)
        """
        # 케이스 타입별 매핑 (한글 및 영문 코드 모두 지원)
        prompt_mapping = {
            "FAMILY": {
                "이혼": "family_divorce",
                "FAMILY_DIVORCE": "family_divorce",
                "상속": "family_inheritance",
                "FAMILY_INHERITANCE": "family_inheritance",
                "기타": "family_default"
            },
            "CIVIL": {
                "대여금": "civil_loan",
                "CIVIL_LOAN": "civil_loan",
                "계약": "civil_contract",
                "CIVIL_CONTRACT": "civil_contract",
                "손해배상": "civil_damages",
                "CIVIL_DAMAGES": "civil_damages",
                "기타": "civil_default"
            },
            "CRIMINAL": {
                "사기": "criminal_fraud",
                "CRIMINAL_FRAUD": "criminal_fraud",
                "폭행": "criminal_assault",
                "CRIMINAL_ASSAULT": "criminal_assault",
                "절도": "criminal_theft",
                "CRIMINAL_THEFT": "criminal_theft",
                "성범죄": "criminal_sex_crime",
                "CRIMINAL_SEX_CRIME": "criminal_sex_crime",
                "기타": "criminal_default"
            },
            "ADMIN": {
                "기타": "admin_default"
            }
        }
        
        # 세부 사건 유형별 프롬프트 선택
        if main_case_type in prompt_mapping:
            if sub_case_type and sub_case_type in prompt_mapping[main_case_type]:
                return prompt_mapping[main_case_type][sub_case_type]
            else:
                # 세부 사건 유형이 없거나 매핑에 없으면 "기타" 사용
                return prompt_mapping[main_case_type].get("기타", "default")
        
        # 주 사건 유형이 매핑에 없으면 기본값
        return "default"


# 전역 프롬프트 로더 인스턴스
prompt_loader = PromptLoader()

