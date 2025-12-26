"""
환경 변수 로드 및 검증 모듈
"""
import os
from typing import List, Optional
from dotenv import load_dotenv


def load_environment_variables(env_file: str = ".env") -> None:
    """
    환경 변수 로드
    
    Args:
        env_file: 환경 변수 파일 경로
    """
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        raise FileNotFoundError(f"환경 변수 파일을 찾을 수 없습니다: {env_file}")


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    환경 변수 조회
    
    Args:
        key: 환경 변수 키
        default: 기본값
        required: 필수 여부
    
    Returns:
        환경 변수 값
    
    Raises:
        ValueError: 필수 환경 변수가 없을 경우
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"필수 환경 변수가 설정되지 않았습니다: {key}")
    
    return value


def validate_required_env_vars(required_vars: List[str]) -> None:
    """
    필수 환경 변수 검증
    
    Args:
        required_vars: 필수 환경 변수 키 리스트
    
    Raises:
        ValueError: 필수 환경 변수가 없을 경우
    """
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(
            f"다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
        )


# 필수 환경 변수 목록
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "API_SECRET_KEY",
]

