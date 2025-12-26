"""
API 인증 모듈
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    API 키 검증
    
    Args:
        credentials: HTTP Bearer 토큰
    
    Returns:
        검증된 API 키
    
    Raises:
        HTTPException: 인증 실패 시
    """
    token = credentials.credentials
    
    if token != settings.api_secret_key:
        logger.warning(f"잘못된 API 키 시도: {token[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API 키입니다."
        )
    
    return token

