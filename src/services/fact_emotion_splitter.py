"""
사실/감정 분리 함수 모듈
"""
from typing import Dict, List, Any
from src.services.gpt_client import gpt_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FactEmotionSplitter:
    """사실과 감정을 분리하는 클래스"""
    
    def __init__(self):
        self.gpt_client = gpt_client
    
    def split_fact_emotion(self, text: str) -> Dict[str, Any]:
        """
        사실과 감정을 분리
        
        Args:
            text: 입력 텍스트
        
        Returns:
            사실과 감정이 분리된 딕셔너리
        """
        try:
            # 프롬프트 파일에서 로드 시도
            from src.services.prompt_loader import prompt_loader
            prompt_template = prompt_loader.load_prompt("split", sub_dir="fact_emotion")
            if prompt_template:
                prompt = prompt_template.format(text=text)
            else:
                # 기본 프롬프트 사용
                prompt = f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요.
JSON 형식으로 반환하세요:
{{
    "facts": [
        {{
            "content": "객관적 사실 내용",
            "type": "날짜/금액/행위/기타"
        }}
    ],
    "emotions": [
        {{
            "type": "억울함/불안/화남/기타",
            "intensity": 1-5,
            "source_text": "원문에서 감정이 드러난 부분"
        }}
    ]
}}

주의사항:
- 사실은 객관적이고 검증 가능한 정보만 포함
- 감정은 주관적 표현과 느낌만 포함
- 감정 표현이 없으면 emotions는 빈 배열

텍스트: {text}

JSON:"""
        except Exception as prompt_error:
            logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
            prompt = f"""다음 텍스트를 사실(fact)과 감정(emotion)으로 분리하세요.
JSON 형식으로 반환하세요:
{{
    "facts": [
        {{
            "content": "객관적 사실 내용",
            "type": "날짜/금액/행위/기타"
        }}
    ],
    "emotions": [
        {{
            "type": "억울함/불안/화남/기타",
            "intensity": 1-5,
            "source_text": "원문에서 감정이 드러난 부분"
        }}
    ]
}}

주의사항:
- 사실은 객관적이고 검증 가능한 정보만 포함
- 감정은 주관적 표현과 느낌만 포함
- 감정 표현이 없으면 emotions는 빈 배열

텍스트: {text}

JSON:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 더 낮은 temperature로 일관성 향상
                max_tokens=500  # 더 짧은 응답으로 속도 향상
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            result = parse_json_from_text(content, default={
                "facts": [],
                "emotions": []
            })
            
            if result is None:
                result = {"facts": [], "emotions": []}
            
            # 기본값 설정
            if "facts" not in result:
                result["facts"] = []
            if "emotions" not in result:
                result["emotions"] = []
            
            logger.debug(f"사실/감정 분리 완료: 사실 {len(result['facts'])}개, 감정 {len(result['emotions'])}개")
            
            return result
        
        except Exception as e:
            logger.error(f"사실/감정 분리 실패: {str(e)}")
            # 기본값 반환
            return {
                "facts": [],
                "emotions": []
            }


# 전역 사실/감정 분리기 인스턴스
fact_emotion_splitter = FactEmotionSplitter()

