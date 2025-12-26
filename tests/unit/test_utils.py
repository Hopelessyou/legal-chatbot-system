"""
유틸리티 함수 단위 테스트
"""
import pytest
from datetime import datetime
from src.utils import helpers


def test_generate_session_id():
    """세션 ID 생성 테스트"""
    session_id = helpers.generate_session_id()
    assert session_id.startswith("sess_")
    assert len(session_id) > 10


def test_generate_uuid():
    """UUID 생성 테스트"""
    uuid_str = helpers.generate_uuid()
    assert len(uuid_str) == 36
    assert uuid_str.count("-") == 4


def test_normalize_text():
    """텍스트 정규화 테스트"""
    text = "  안녕하세요   반갑습니다  "
    normalized = helpers.normalize_text(text)
    assert normalized == "안녕하세요 반갑습니다"


def test_mask_personal_info():
    """개인정보 마스킹 테스트"""
    text = "연락처는 010-1234-5678입니다"
    masked = helpers.mask_personal_info(text)
    assert "****" in masked
    assert "010" in masked
    assert "5678" in masked


def test_parse_date():
    """날짜 파싱 테스트"""
    date_str = "2023-10-15"
    parsed = helpers.parse_date(date_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2023
    assert parsed.month == 10
    assert parsed.day == 15


def test_format_date():
    """날짜 포맷팅 테스트"""
    date = datetime(2023, 10, 15)
    formatted = helpers.format_date(date)
    assert formatted == "2023-10-15"

