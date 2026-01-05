"""
요약 생성 함수 모듈
"""
from typing import Dict, Any, Optional
from src.services.gpt_client import gpt_client
from src.services.prompt_loader import prompt_loader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Summarizer:
    """요약 생성 클래스"""
    
    def __init__(self):
        self.gpt_client = gpt_client
    
    def generate_intermediate_summary(self, facts: Dict[str, Any]) -> str:
        """
        중간 요약 생성 (수집된 사실 요약)
        
        Args:
            facts: 수집된 사실 딕셔너리
        
        Returns:
            요약 텍스트
        """
        facts_text = "\n".join([
            f"- {key}: {value}"
            for key, value in facts.items()
            if value is not None
        ])
        
        prompt = f"""다음 수집된 사실 정보를 간단히 요약하세요.
요약은 객관적이고 사실 중심으로 작성하세요.

수집된 사실:
{facts_text}

요약:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )
            
            summary = response["content"].strip()
            logger.debug("중간 요약 생성 완료")
            return summary
        
        except Exception as e:
            logger.error(f"중간 요약 생성 실패: {str(e)}")
            return ""
    
    def generate_final_summary(
        self,
        context: Dict[str, Any],
        format_template: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        최종 요약 생성
        
        Args:
            context: 전체 Context 딕셔너리
            format_template: K4 포맷 템플릿
        
        Returns:
            구조화된 요약 딕셔너리
        """
        # Context 정보 정리
        main_case_type = context.get('case_type', '') or context.get('main_case_type', '')
        sub_case_type = context.get('sub_case_type', '')
        if main_case_type and sub_case_type:
            case_type = f"{main_case_type} / {sub_case_type}"
        elif main_case_type:
            case_type = main_case_type
        elif sub_case_type:
            case_type = sub_case_type
        else:
            case_type = "미분류"
        
        facts = context.get('facts', {})
        emotions = context.get('emotion', [])
        completion_rate = context.get('completion_rate', 0)
        user_inputs = context.get('user_inputs', '')  # 사용자 입력 텍스트
        
        # 포맷 템플릿이 있으면 사용
        if format_template:
            sections = format_template.get("sections", [])
            target = format_template.get("target", "COUNSELOR")
        else:
            sections = [
                {"name": "사건 유형"},
                {"name": "핵심 사실관계"},
                {"name": "금액 및 증거"},
                {"name": "특이사항"}
            ]
            target = "COUNSELOR"
        
        # 케이스 타입별 중요 정보 가이드 생성
        important_info_guide = _get_case_specific_guide(main_case_type, sub_case_type)
        
        # 사용자 입력 텍스트가 있으면 포함
        user_inputs_section = ""
        date_context_note = ""
        if user_inputs:
            # 날짜 관련 맥락 확인 (사기 케이스에서 "인지" 키워드 확인)
            if main_case_type == "CRIMINAL" and sub_case_type == "사기":
                if any(keyword in user_inputs for keyword in ["인지", "알게", "발견", "알았"]):
                    date_context_note = "\n⚠️ 중요: 사용자 입력에 '인지', '알게', '발견' 등의 키워드가 있습니다. incident_date는 '사기 발생 날짜'가 아니라 '피해 인지 날짜'로 해석해야 합니다."
                elif any(keyword in user_inputs for keyword in ["계약", "체결", "송금", "입금"]):
                    date_context_note = "\n⚠️ 중요: 사용자 입력에 '계약', '체결', '송금', '입금' 등의 키워드가 있습니다. incident_date는 '사기 발생/계약 체결 날짜'로 해석할 수 있습니다."
            
            user_inputs_section = f"""
사용자 입력 내용 (전체):
{user_inputs}
{date_context_note}

위 사용자 입력 내용에서 언급된 모든 중요한 정보를 반드시 포함하여 요약하세요:
{important_info_guide}"""
        
        # 섹션 정보를 JSON 형식으로 변환
        sections_info = "\n".join([f"- {section.get('name', section.get('title', ''))}: {section.get('content_rule', section.get('description', ''))}" for section in sections])
        
        # 케이스 타입별 프롬프트 템플릿 로드
        prompt_template_name = prompt_loader.get_summary_prompt_name(main_case_type, sub_case_type)
        prompt_template = prompt_loader.load_prompt(prompt_template_name, sub_dir="summary")
        
        # 프롬프트 템플릿이 없으면 기본 템플릿 사용
        if not prompt_template:
            logger.warning(f"프롬프트 템플릿을 찾을 수 없습니다: {prompt_template_name}, 기본 템플릿 사용")
            prompt_template = prompt_loader.load_prompt("default", sub_dir="summary")
        
        # 프롬프트 변수 준비
        important_info_guide_first = important_info_guide.split('\n')[0].replace('- ', '') if important_info_guide else "중요한 사실 관계"
        
        # facts와 emotions를 문자열로 변환
        facts_text = "\n".join([
            f"- {key}: {value}"
            for key, value in facts.items()
            if value is not None
        ]) if facts else "없음"
        
        emotions_text = ", ".join(str(e) for e in emotions) if emotions else "없음"
        
        prompt_variables = {
            "case_type": case_type,
            "facts": facts_text,
            "emotions": emotions_text,
            "completion_rate": completion_rate,
            "user_inputs_section": user_inputs_section,
            "sections_info": sections_info,
            "important_info_guide_first": important_info_guide_first
        }
        
        # 프롬프트 템플릿이 있으면 변수 치환, 없으면 기본 프롬프트 사용
        if prompt_template:
            try:
                prompt = prompt_template.format(**prompt_variables)
                logger.debug(f"프롬프트 템플릿 사용: {prompt_template_name}")
            except KeyError as e:
                logger.warning(f"프롬프트 템플릿 변수 누락: {e}, 기본 프롬프트 사용")
                prompt = self._build_default_prompt(
                    case_type, facts_text, emotions_text, completion_rate,
                    user_inputs_section, sections_info, important_info_guide_first
                )
        else:
            # 기본 프롬프트 사용
            prompt = self._build_default_prompt(
                case_type, facts_text, emotions_text, completion_rate,
                user_inputs_section, sections_info, important_info_guide_first
            )
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            # 응답에서 JSON 추출 (견고한 파싱 사용)
            from src.utils.helpers import parse_json_from_text
            content = response["content"].strip()
            summary_dict = parse_json_from_text(content, default={})
            
            if summary_dict is None:
                summary_dict = {}
            
            # 요약 텍스트 생성
            summary_text = "\n".join([
                f"{key}: {value}"
                for key, value in summary_dict.items()
            ])
            
            result = {
                "summary_text": summary_text,
                "structured_data": summary_dict,
                "completion_rate": completion_rate
            }
            
            logger.info("최종 요약 생성 완료")
            return result
        
        except Exception as e:
            logger.error(f"최종 요약 생성 실패: {str(e)}")
            return {
                "summary_text": "",
                "structured_data": {},
                "completion_rate": completion_rate
            }
    
    def _build_default_prompt(
        self,
        case_type: str,
        facts: str,
        emotions: str,
        completion_rate: int,
        user_inputs_section: str,
        sections_info: str,
        important_info_guide_first: str
    ) -> str:
        """
        기본 프롬프트 생성 (템플릿 파일이 없을 때 사용)
        
        Args:
            case_type: 사건 유형
            facts: 수집된 사실 (문자열)
            emotions: 감정 정보 (문자열)
            completion_rate: 완성도
            user_inputs_section: 사용자 입력 섹션
            sections_info: 섹션 정보
            important_info_guide_first: 중요 정보 가이드 첫 줄
        
        Returns:
            기본 프롬프트 문자열
        """
        return f"""다음 정보를 바탕으로 법률 상담용 사건 요약을 작성하세요.

사건 유형: {case_type}
수집된 사실: {facts}
감정 정보: {emotions}
완성도: {completion_rate}%
{user_inputs_section}

요약 섹션 구성:
{sections_info}

중요 지침:
1. 사용자 입력 내용에 언급된 모든 중요한 사실을 반드시 포함하세요
2. {important_info_guide_first} 등 언급된 모든 사항을 명시적으로 기록하세요
3. "특이사항" 필드에는 모든 중요한 특이사항을 포함하세요 (없으면 '없음')
4. 금액이 명확하지 않거나 날짜로 오인될 수 있는 경우(예: "10월")는 금액으로 기록하지 마세요

다음 형식으로 JSON으로 반환하세요:
{{
    "사건_유형": "{case_type}",
    "핵심_사실관계": "사실 중심 요약 (사용자 입력의 모든 중요한 정보 포함)",
    "금액_및_증거": "금액과 증거 정보 (금액이 불명확하면 '불명확' 또는 '해당 없음')",
    "특이사항": "모든 중요한 특이사항 (없으면 '없음')"
}}

JSON:"""
    
    def convert_to_legal_language(self, text: str) -> str:
        """
        일상 언어를 법률 언어로 변환
        
        Args:
            text: 일상 언어 텍스트
        
        Returns:
            법률 언어로 변환된 텍스트
        """
        prompt = f"""다음 텍스트를 법률 용어를 사용하여 정확하고 전문적으로 변환하세요.
의미는 유지하되 법률 용어를 사용하세요.

텍스트: {text}

법률 언어:"""
        
        try:
            response = self.gpt_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            legal_text = response["content"].strip()
            logger.debug("법률 언어 변환 완료")
            return legal_text
        
        except Exception as e:
            logger.error(f"법률 언어 변환 실패: {str(e)}")
            return text


def _get_case_specific_guide(main_case_type: str, sub_case_type: str) -> str:
    """
    케이스 타입별 중요 정보 가이드 생성
    
    Args:
        main_case_type: 주 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN)
        sub_case_type: 세부 사건 유형
    
    Returns:
        중요 정보 가이드 문자열
    """
    guides = {
        "FAMILY": {
            "이혼": "- 불륜, 외도, 배신 등 관계 문제\n- 자녀, 양육권, 양육비 등 자녀 관련 사항\n- 재산 분할, 재산 분쟁 등 재산 관련 사항\n- 위자료, 정신적 피해 등 손해 관련 사항",
            "상속": "- 상속인, 상속재산 등 상속 관련 사항\n- 유언, 유류분 등 상속 분쟁 사항",
            "기타": "- 가족 관계 문제\n- 자녀 관련 사항\n- 재산 관련 사항"
        },
        "CIVIL": {
            "대여금": "- 대출 금액, 상환 약속 등 대출 관련 사항\n- 잠적, 연락두절, 약속 불이행 등 특이사항\n- 증거 자료 (계약서, 대화 내역, 송금 내역 등)",
            "계약": "- 계약 내용, 계약 위반 사항\n- 손해 금액, 손해 배상 관련 사항\n- 증거 자료",
            "손해배상": "- 피해 금액, 피해 내용\n- 가해자 정보\n- 증거 자료",
            "기타": "- 계약 관련 사항\n- 금액 관련 사항\n- 증거 자료"
        },
        "CRIMINAL": {
            "사기": "- 피해 금액, 사기 수법\n- 가해자 정보\n- 증거 자료 (대화 내역, 송금 내역 등)",
            "폭행": "- 폭행 일시, 장소, 피해 내용\n- 가해자 정보\n- 증거 자료 (진단서, 사진 등)",
            "기타": "- 피해 내용\n- 가해자 정보\n- 증거 자료"
        },
        "ADMIN": {
            "기타": "- 행정처분 내용\n- 관련 법령\n- 증거 자료"
        }
    }
    
    # 주 사건 유형별 가이드
    main_guide = guides.get(main_case_type, {}).get("기타", "- 중요한 사실 관계\n- 증거 자료")
    
    # 세부 사건 유형별 가이드 (있으면 우선 사용)
    if sub_case_type and sub_case_type in guides.get(main_case_type, {}):
        return guides[main_case_type][sub_case_type]
    
    return main_guide


# 전역 요약 생성기 인스턴스
summarizer = Summarizer()

