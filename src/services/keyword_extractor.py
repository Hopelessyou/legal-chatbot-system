"""
키워드/의미 추출 함수 모듈 (CASE_CLASSIFICATION용)
"""
from typing import List, Dict, Any
from src.services.gpt_client import gpt_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KeywordExtractor:
    """키워드 및 의미 추출 클래스"""
    
    def __init__(self):
        self.gpt_client = gpt_client
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        핵심 키워드 추출
        
        Args:
            text: 입력 텍스트
            max_keywords: 최대 키워드 개수
        
        Returns:
            키워드 리스트
        """
        prompt = f"""다음 텍스트에서 법률 사건 분류에 중요한 핵심 키워드를 추출하세요.
키워드는 쉼표로 구분하여 나열하세요. 최대 {max_keywords}개까지 추출하세요.

텍스트: {text}

키워드:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            keywords_str = response["content"].strip()
            keywords = [kw.strip() for kw in keywords_str.split(",")]
            
            logger.debug(f"키워드 추출 완료: {len(keywords)}개")
            return keywords[:max_keywords]
        
        except Exception as e:
            logger.error(f"키워드 추출 실패: {str(e)}")
            return []
    
    def extract_semantic_features(self, text: str) -> Dict[str, Any]:
        """
        의미적 특징 추출 (사건 유형 분류용)
        
        Args:
            text: 입력 텍스트
        
        Returns:
            의미적 특징 딕셔너리
        """
        prompt = f"""다음 텍스트를 분석하여 법률 사건 분류에 필요한 의미적 특징을 추출하세요.
JSON 형식으로 반환하세요:
{{
    "domain": "민사/형사/가사/행정/기타",
    "keywords": ["키워드1", "키워드2", ...],
    "main_issue": "주요 쟁점 요약",
    "related_concepts": ["관련 개념1", "관련 개념2", ...]
}}

텍스트: {text}

JSON:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            result = parse_json_from_text(content, default={
                "domain": None,
                "keywords": [],
                "main_issue": None,
                "related_concepts": []
            })
            
            if result is None:
                raise ValueError("JSON 파싱 실패")
            
            logger.debug(f"의미적 특징 추출 완료: domain={result.get('domain')}")
            return result
        
        except Exception as e:
            logger.error(f"의미적 특징 추출 실패: {str(e)}")
            # 폴백: 기본 키워드만 추출
            keywords = self.extract_keywords(text, max_keywords=5)
            return {
                "domain": None,
                "keywords": keywords,
                "main_issue": None,
                "related_concepts": []
            }


# 전역 키워드 추출기 인스턴스
keyword_extractor = KeywordExtractor()

