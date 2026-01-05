"""
질문 텍스트 로더 모듈
YAML 파일에서 질문 텍스트를 로드하고 관리
"""
import yaml
from yaml import YAMLError
from pathlib import Path
from typing import Dict, Optional, Any
from src.utils.logger import get_logger
from src.utils.constants import QUESTION_MESSAGES

logger = get_logger(__name__)

# 질문 텍스트 캐시
_questions_cache: Optional[Dict[str, Any]] = None


def load_questions_from_yaml() -> Dict[str, Any]:
    """
    YAML 파일에서 질문 텍스트 로드
    
    Returns:
        질문 텍스트 딕셔너리
    """
    global _questions_cache
    
    if _questions_cache is not None:
        return _questions_cache
    
    try:
        # config 디렉토리 경로
        config_dir = Path(__file__).parent.parent.parent / "config"
        questions_file = config_dir / "questions.yaml"
        
        if not questions_file.exists():
            logger.warning(f"질문 파일이 없습니다: {questions_file}, 기본값 사용")
            _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
            return _questions_cache
        
        with open(questions_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # 구조 검증
        if not isinstance(data, dict):
            raise ValueError("YAML 파일이 딕셔너리 형식이 아닙니다.")
        
        if "questions" not in data:
            logger.warning("YAML 파일에 'questions' 키가 없습니다. 기본 구조로 변환합니다.")
            data = {"questions": data}
        
        if not isinstance(data["questions"], dict):
            raise ValueError("'questions' 키의 값이 딕셔너리 형식이 아닙니다.")
        
        _questions_cache = data
        logger.info("질문 텍스트 YAML 파일 로드 완료")
        return _questions_cache
    
    except YAMLError as e:
        logger.error(f"YAML 파싱 오류: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except (IOError, ValueError) as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache
    except Exception as e:
        logger.error(f"질문 텍스트 로드 실패: {str(e)}, 기본값 사용")
        _questions_cache = {"questions": {"default": QUESTION_MESSAGES}}
        return _questions_cache


def get_question_message(field: str, case_type: Optional[str] = None) -> str:
    """
    필드에 대한 질문 메시지 가져오기
    
    Args:
        field: 필드 키 (incident_date, counterparty, amount, evidence 등)
        case_type: 사건 유형 (CIVIL, CRIMINAL, FAMILY, ADMIN), None이면 기본값 사용
    
    Returns:
        질문 메시지 문자열
    """
    questions_data = load_questions_from_yaml()
    questions = questions_data.get("questions", {})
    
    # 1. 사건 유형별 질문 확인
    if case_type:
        case_type_upper = case_type.upper()  # 대문자로 정규화
        case_questions = questions.get("case_types", {}).get(case_type_upper, {})
        if field in case_questions:
            return case_questions[field]
    
    # 2. 기본 질문 확인
    default_questions = questions.get("default", {})
    if field in default_questions:
        return default_questions[field]
    
    # 3. constants.py의 기본값 확인
    if field in QUESTION_MESSAGES:
        return QUESTION_MESSAGES[field]
    
    # 4. 폴백
    logger.warning(f"질문 메시지를 찾을 수 없습니다: field={field}, case_type={case_type}")
    return f"{field}에 대한 정보를 알려주세요."


def reload_questions() -> Dict[str, Any]:
    """
    질문 텍스트 캐시 재로드 (테스트 또는 동적 업데이트용)
    
    Returns:
        재로드된 질문 텍스트 딕셔너리
    """
    global _questions_cache
    _questions_cache = None
    return load_questions_from_yaml()

