"""
유틸리티 함수 모듈
"""
import re
import uuid
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# 한국 시간대 (KST, UTC+9)
KST = timezone(timedelta(hours=9))


def get_kst_now() -> datetime:
    """
    현재 한국 시간(KST) 반환
    
    SQLAlchemy 호환을 위해 timezone-aware datetime을 반환하지만
    tzinfo를 제거한 naive datetime을 반환합니다.
    
    Returns:
        한국 시간대의 현재 datetime 객체 (naive)
    """
    kst_timezone = timezone(timedelta(hours=9))
    return datetime.now(kst_timezone).replace(tzinfo=None)


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


def parse_json_from_text(text: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    텍스트에서 JSON 객체를 안전하게 파싱
    
    마크다운 코드 블록, 주석, 불필요한 텍스트를 제거하고 JSON을 추출합니다.
    
    Args:
        text: JSON이 포함된 텍스트
        default: 파싱 실패 시 반환할 기본값
    
    Returns:
        파싱된 JSON 딕셔너리 또는 default
    """
    if not text:
        return default
    
    try:
        # 1. 마크다운 코드 블록 제거
        # ```json ... ``` 또는 ``` ... ``` 패턴
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
        
        # 2. 첫 번째 { 부터 마지막 } 까지 추출 (중첩된 객체 지원)
        # 단순 정규식 대신 괄호 매칭으로 정확하게 추출
        start_idx = text.find('{')
        if start_idx == -1:
            return default
        
        # 중첩된 괄호를 고려하여 마지막 } 찾기
        brace_count = 0
        end_idx = start_idx
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if brace_count != 0:
            # 괄호가 맞지 않으면 전체 텍스트에서 시도
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            else:
                return default
        else:
            text = text[start_idx:end_idx]
        
        # 3. JSON 파싱 시도
        result = json.loads(text)
        return result if isinstance(result, dict) else default
        
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 더 공격적인 정리 시도
        try:
            # 주석 제거 (// 또는 /* */)
            text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
            
            # 후행 쉼표 제거
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            
            result = json.loads(text)
            return result if isinstance(result, dict) else default
        except (json.JSONDecodeError, ValueError, TypeError):
            return default
    except (ValueError, TypeError, AttributeError):
        return default

