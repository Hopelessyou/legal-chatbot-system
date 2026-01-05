"""
API 인증 모듈
"""
import secrets
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    API 키 검증 (타이밍 공격 방지)
    
    Args:
        credentials: HTTP Bearer 토큰
    
    Returns:
        검증된 API 키
    
    Raises:
        HTTPException: 인증 실패 시
    
    Note:
        secrets.compare_digest를 사용하여 타이밍 공격을 방지합니다.
    """
    token = credentials.credentials
    
    # 타이밍 공격 방지를 위해 secrets.compare_digest 사용
    if not secrets.compare_digest(token, settings.api_secret_key):
        logger.warning(f"잘못된 API 키 시도: {token[:10] if len(token) > 10 else '***'}...")
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API 키입니다."
        )
    
    return token

