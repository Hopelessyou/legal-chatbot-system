"""
유틸리티 함수 모듈
"""
import re
import uuid
import hashlib
from datetime import datetime
from typing import Optional


def parse_date(date_string: str) -> Optional[datetime]:
    """
    날짜 문자열 파싱
    
    Args:
        date_string: 날짜 문자열
    
    Returns:
        datetime 객체 또는 None
    """
    # 다양한 날짜 형식 지원
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m",
        "%Y/%m",
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None


def format_date(date: datetime, format_string: str = "%Y-%m-%d") -> str:
    """
    날짜 포맷팅
    
    Args:
        date: datetime 객체
        format_string: 포맷 문자열
    
    Returns:
        포맷된 날짜 문자열
    """
    return date.strftime(format_string)


def normalize_text(text: str) -> str:
    """
    텍스트 정규화
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정규화된 텍스트
    """
    # 공백 정규화
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()
    return text


def mask_personal_info(text: str, mask_char: str = "*") -> str:
    """
    개인정보 마스킹
    
    Args:
        text: 원본 텍스트
        mask_char: 마스킹 문자
    
    Returns:
        마스킹된 텍스트
    """
    # 전화번호 마스킹 (010-1234-5678 -> 010-****-5678)
    text = re.sub(r'(\d{3})-(\d{4})-(\d{4})', r'\1-****-\3', text)
    
    # 이메일 마스킹 (user@example.com -> u***@example.com)
    text = re.sub(r'(\w{1,3})(\w*)(@\w+\.\w+)', r'\1' + mask_char * 3 + r'\3', text)
    
    # 주민등록번호 마스킹 (123456-1234567 -> 123456-*******)
    text = re.sub(r'(\d{6})-(\d{7})', r'\1-*******', text)
    
    return text


def generate_uuid() -> str:
    """
    UUID 생성
    
    Returns:
        UUID 문자열
    """
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """
    세션 ID 생성 (sess_ 접두사 포함)
    
    Returns:
        세션 ID 문자열
    """
    return f"sess_{uuid.uuid4().hex[:12]}"


def generate_user_hash(user_identifier: str) -> str:
    """
    사용자 식별 해시 생성
    
    Args:
        user_identifier: 사용자 식별자
    
    Returns:
        해시 문자열
    """
    return hashlib.sha256(user_identifier.encode()).hexdigest()

