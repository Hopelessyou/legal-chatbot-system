"""
엔티티 추출 함수 모듈
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.services.gpt_client import gpt_client
from src.utils.logger import get_logger
from src.utils.constants import KOREAN_NUMBER_MAPPING, Limits
from src.utils.helpers import get_kst_now

logger = get_logger(__name__)


class EntityExtractor:
    """엔티티 추출 클래스"""
    
    def __init__(self):
        self.gpt_client = gpt_client
    
    def extract_date(self, text: str) -> Optional[str]:
        """
        날짜 추출
        
        Args:
            text: 입력 텍스트
        
        Returns:
            추출된 날짜 문자열 (YYYY-MM-DD 형식) 또는 None
        """
        try:
            # 프롬프트 파일에서 로드 시도
            from src.services.prompt_loader import prompt_loader
            prompt_template = prompt_loader.load_prompt("date", sub_dir="entity_extraction")
            if prompt_template:
                prompt = prompt_template.format(text=text)
            else:
                # 기본 프롬프트 사용
                prompt = f"""다음 텍스트에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환하세요.

텍스트: {text}

YYYY-MM-DD 형식의 날짜만 반환하세요. 날짜를 찾을 수 없으면 "null"을 반환하세요."""
        except Exception as prompt_error:
            logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
            prompt = f"""다음 텍스트에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환하세요.

텍스트: {text}

YYYY-MM-DD 형식의 날짜만 반환하세요. 날짜를 찾을 수 없으면 "null"을 반환하세요."""
        
        try:
            # 상대적 날짜 패턴
            now = get_kst_now()
            relative_patterns = {
                r'어제': lambda m: (now - timedelta(days=1)).strftime("%Y-%m-%d"),
                r'오늘': lambda m: now.strftime("%Y-%m-%d"),
                r'내일': lambda m: (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                r'(\d+)일\s*전': lambda m: (now - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d"),
                r'(\d+)일\s*후': lambda m: (now + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d"),
                r'작년\s*(\d+)월\s*(\d+)일?': lambda m: self._get_relative_date(-1, int(m.group(1)), int(m.group(2))),
                r'작년\s*(\d+)월': lambda m: self._get_relative_date(-1, int(m.group(1))),
                r'올해\s*(\d+)월\s*(\d+)일?': lambda m: self._get_relative_date(0, int(m.group(1)), int(m.group(2))),
                r'올해\s*(\d+)월': lambda m: self._get_relative_date(0, int(m.group(1))),
                r'(\d+)월\s*(\d+)일': lambda m: self._get_relative_date(0, int(m.group(1)), int(m.group(2))),  # "11월 20일" 형식
                r'(\d+)월': lambda m: self._get_relative_date(0, int(m.group(1))),  # "11월" 형식
                r'(\d+)개월\s*전': lambda m: (now - timedelta(days=30 * int(m.group(1)))).strftime("%Y-%m-%d"),
                r'(\d+)년\s*전': lambda m: (now - timedelta(days=365 * int(m.group(1)))).strftime("%Y-%m-%d"),
            }
            
            # 절대적 날짜 패턴
            absolute_patterns = [
                r'(\d{4})[년\.\-\/](\d{1,2})[월\.\-\/](\d{1,2})일?',  # 2023-10-15
                r'(\d{4})[년\.\-\/](\d{1,2})월',  # 2023-10
            ]
            
            # 상대적 날짜 매칭
            for pattern, func in relative_patterns.items():
                match = re.search(pattern, text)
                if match:
                    date = func(match)
                    if isinstance(date, datetime):
                        return date.strftime("%Y-%m-%d")
                    return date
            
            # 절대적 날짜 매칭
            for pattern in absolute_patterns:
                match = re.search(pattern, text)
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3)) if len(match.groups()) >= 3 else 1
                    try:
                        date = datetime(year, month, day)
                        return date.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            
            # GPT API를 사용한 날짜 추출 (패턴 매칭 실패 시)
            return self._extract_date_with_gpt(text)
        
        except Exception as e:
            logger.error(f"날짜 추출 실패: {str(e)}")
            return None
    
    def _get_relative_date(self, year_offset: int, month: int, day: int = 1) -> datetime:
        """상대적 날짜 계산"""
        now = get_kst_now()
        target_year = now.year + year_offset
        try:
            return datetime(target_year, month, day)
        except ValueError:
            # 잘못된 날짜(예: 2월 30일)인 경우 해당 월의 마지막 날로 조정
            from calendar import monthrange
            last_day = monthrange(target_year, month)[1]
            return datetime(target_year, month, min(day, last_day))
    
    def _extract_date_with_gpt(self, text: str) -> Optional[str]:
        """GPT API를 사용한 날짜 추출"""
        prompt = f"""다음 텍스트에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환하세요.
텍스트에 날짜가 없으면 "없음"을 반환하세요.

텍스트: {text}

날짜:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=Limits.MAX_TOKENS_DATE_EXTRACTION
            )
            
            date_str = response["content"].strip()
            if date_str == "없음" or not date_str:
                return None
            
            # 날짜 형식 검증
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
            except ValueError:
                return None
        
        except Exception as e:
            logger.error(f"GPT 날짜 추출 실패: {str(e)}")
            return None
    
    def extract_amount(self, text: str) -> Optional[int]:
        """
        금액 추출
        
        Args:
            text: 입력 텍스트
        
        Returns:
            추출된 금액 (원 단위 정수) 또는 None
        """
        try:
            # 패턴: 숫자 + 단위 (예: 5천만원, 5000만원)
            patterns = [
                r'(\d+(?:\.\d+)?)\s*(만|억|조)?\s*원',
                r'(\d+(?:\.\d+)?)\s*(천|만|억|조)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    number = float(match.group(1))
                    unit = match.group(2) if len(match.groups()) >= 2 else None
                    
                    if unit:
                        multiplier = KOREAN_NUMBER_MAPPING.get(unit, 1)
                        amount = int(number * multiplier)
                    else:
                        amount = int(number)
                    
                    return amount
            
            # 한글 숫자 패턴 (예: 오천만원)
            korean_pattern = r'([일이삼사오육칠팔구]+)\s*(천|만|억|조)?\s*원'
            match = re.search(korean_pattern, text)
            if match:
                # 간단한 한글 숫자 변환 (복잡한 경우 GPT 사용)
                return self._extract_amount_with_gpt(text)
            
            # GPT API를 사용한 금액 추출
            return self._extract_amount_with_gpt(text)
        
        except Exception as e:
            logger.error(f"금액 추출 실패: {str(e)}")
            return None
    
    def _extract_amount_with_gpt(self, text: str) -> Optional[int]:
        """GPT API를 사용한 금액 추출"""
        prompt = f"""다음 텍스트에서 금액을 추출하여 숫자만 반환하세요 (원 단위).
금액이 없으면 "없음"을 반환하세요.

텍스트: {text}

금액 (숫자만):"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=Limits.MAX_TOKENS_DATE_EXTRACTION
            )
            
            amount_str = response["content"].strip()
            if amount_str == "없음" or not amount_str:
                return None
            
            # 숫자만 추출
            numbers = re.findall(r'\d+', amount_str)
            if numbers:
                return int(numbers[0])
            
            return None
        
        except Exception as e:
            logger.error(f"GPT 금액 추출 실패: {str(e)}")
            return None
    
    def extract_party(self, text: str) -> Dict[str, Any]:
        """
        인물/당사자 추출
        
        Args:
            text: 입력 텍스트
        
        Returns:
            당사자 정보 딕셔너리
        """
        try:
            # 프롬프트 파일에서 로드 시도
            from src.services.prompt_loader import prompt_loader
            prompt_template = prompt_loader.load_prompt("party", sub_dir="entity_extraction")
            if prompt_template:
                prompt = prompt_template.format(text=text)
            else:
                # 기본 프롬프트 사용
                prompt = f"""다음 텍스트에서 계약 상대방 또는 관련 인물 정보를 추출하세요.
JSON 형식으로 반환하세요:
{{
    "name": "이름 또는 없음",
    "role": "의뢰인/상대방/기타",
    "type": "개인/법인/기타",
    "relationship": "관계 설명 또는 없음"
}}

텍스트: {text}

JSON:"""
        except Exception as prompt_error:
            logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
            prompt = f"""다음 텍스트에서 계약 상대방 또는 관련 인물 정보를 추출하세요.
JSON 형식으로 반환하세요:
{{
    "name": "이름 또는 없음",
    "role": "의뢰인/상대방/기타",
    "type": "개인/법인/기타",
    "relationship": "관계 설명 또는 없음"
}}

텍스트: {text}

JSON:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=Limits.MAX_TOKENS_ENTITY_EXTRACTION
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            result = parse_json_from_text(content, default={})
            return result if result is not None else {}
        
        except Exception as e:
            logger.error(f"당사자 추출 실패: {str(e)}")
            return {
                "name": None,
                "role": None,
                "type": None,
                "relationship": None
            }
    
    def extract_action(self, text: str) -> Dict[str, Any]:
        """
        행위 추출
        
        Args:
            text: 입력 텍스트
        
        Returns:
            행위 정보 딕셔너리
        """
        try:
            # 프롬프트 파일에서 로드 시도
            from src.services.prompt_loader import prompt_loader
            prompt_template = prompt_loader.load_prompt("action", sub_dir="entity_extraction")
            if prompt_template:
                prompt = prompt_template.format(text=text)
            else:
                # 기본 프롬프트 사용
                prompt = f"""다음 텍스트에서 핵심 행위나 사건 내용을 추출하세요.
JSON 형식으로 반환하세요:
{{
    "action_verb": "행위 동사",
    "action_description": "행위 내용 요약",
    "result": "결과 또는 없음"
}}

텍스트: {text}

JSON:"""
        except Exception as prompt_error:
            logger.debug(f"프롬프트 로드 실패, 기본 프롬프트 사용: {str(prompt_error)}")
            prompt = f"""다음 텍스트에서 핵심 행위나 사건 내용을 추출하세요.
JSON 형식으로 반환하세요:
{{
    "action_verb": "행위 동사",
    "action_description": "행위 내용 요약",
    "result": "결과 또는 없음"
}}

텍스트: {text}

JSON:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=Limits.MAX_TOKENS_ENTITY_EXTRACTION
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            result = parse_json_from_text(content, default={})
            return result if result is not None else {}
        
        except Exception as e:
            logger.error(f"행위 추출 실패: {str(e)}")
            return {
                "action_verb": None,
                "action_description": None,
                "result": None
            }
    
    def extract_all_entities(self, text: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        모든 엔티티 추출 (통합 GPT 호출)
        
        Args:
            text: 입력 텍스트
            fields: 추출할 필드 리스트 (None이면 모든 필드 추출)
        
        Returns:
            추출된 모든 엔티티 딕셔너리
        """
        # 1. 먼저 로컬 패턴 매칭 시도 (GPT 호출 없이)
        result = {}
        
        # 날짜 추출 (패턴 매칭 우선)
        if fields is None or "date" in fields or "incident_date" in fields:
            date = self.extract_date(text)
            if date:
                result["date"] = date
        
        # 금액 추출 (패턴 매칭 우선)
        if fields is None or "amount" in fields:
            amount = self.extract_amount(text)
            if amount:
                result["amount"] = amount
        
        # 2. 패턴 매칭으로 추출되지 않은 필드만 GPT로 통합 추출
        missing_fields = []
        if fields is None:
            # 모든 필드 추출
            if not result.get("date"):
                missing_fields.append("date")
            if not result.get("amount"):
                missing_fields.append("amount")
            missing_fields.extend(["party", "action"])
        else:
            # 지정된 필드만 추출
            if ("date" in fields or "incident_date" in fields) and not result.get("date"):
                missing_fields.append("date")
            if "amount" in fields and not result.get("amount"):
                missing_fields.append("amount")
            if "party" in fields or "counterparty" in fields:
                missing_fields.append("party")
            if "action" in fields:
                missing_fields.append("action")
        
        # 3. GPT 통합 추출 (필요한 필드만)
        if missing_fields:
            gpt_result = self._extract_entities_with_gpt(text, missing_fields)
            result.update(gpt_result)
        
        return result
    
    def _extract_entities_with_gpt(self, text: str, fields: List[str]) -> Dict[str, Any]:
        """
        GPT API를 사용한 통합 엔티티 추출
        
        Args:
            text: 입력 텍스트
            fields: 추출할 필드 리스트
        
        Returns:
            추출된 엔티티 딕셔너리
        """
        # 필드별 설명
        field_descriptions = {
            "date": "날짜 (YYYY-MM-DD 형식, 없으면 null)",
            "amount": "금액 (원 단위 숫자만, 없으면 null)",
            "party": "계약 상대방 또는 관련 인물 정보",
            "action": "핵심 행위나 사건 내용"
        }
        
        # 요청할 필드 설명 생성
        requested_fields = [field_descriptions.get(f, f) for f in fields]
        
        prompt = f"""다음 텍스트에서 다음 정보를 추출하여 JSON 형식으로 반환하세요:
{chr(10).join([f"- {f}" for f in requested_fields])}

JSON 형식:
{{
    "date": "YYYY-MM-DD 또는 null",
    "amount": 숫자 또는 null,
    "party": {{
        "name": "이름 또는 없음",
        "role": "의뢰인/상대방/기타",
        "type": "개인/법인/기타",
        "relationship": "관계 설명 또는 없음"
    }} 또는 null,
    "action": {{
        "action_verb": "행위 동사",
        "action_description": "행위 내용 요약",
        "result": "결과 또는 없음"
    }} 또는 null
}}

주의사항:
- 추출할 수 없는 필드는 null로 반환
- 날짜는 YYYY-MM-DD 형식으로 정확히 반환
- 금액은 숫자만 반환 (원, 만원 등 단위 제거)
- party와 action은 객체 또는 null만 반환

텍스트: {text}

JSON:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 낮은 temperature로 일관성 향상
                max_tokens=400  # 통합 응답이므로 토큰 증가
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            gpt_result = parse_json_from_text(content, default={})
            
            if gpt_result is None:
                gpt_result = {}
            
            # 필드 필터링 (요청한 필드만 반환)
            result = {}
            if "date" in fields and gpt_result.get("date"):
                result["date"] = gpt_result["date"]
            if "amount" in fields and gpt_result.get("amount"):
                result["amount"] = gpt_result["amount"]
            if "party" in fields and gpt_result.get("party"):
                result["party"] = gpt_result["party"]
            if "action" in fields and gpt_result.get("action"):
                result["action"] = gpt_result["action"]
            
            logger.debug(f"GPT 통합 엔티티 추출 완료: {list(result.keys())}")
            return result
        
        except Exception as e:
            logger.error(f"GPT 통합 엔티티 추출 실패: {str(e)}")
            # 기본값 반환
            return {}


# 전역 엔티티 추출기 인스턴스
entity_extractor = EntityExtractor()

