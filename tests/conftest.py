"""
Pytest 설정 및 픽스처
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """테스트 클라이언트 픽스처"""
    return TestClient(app)


@pytest.fixture
def sample_session_id():
    """샘플 세션 ID 픽스처"""
    return "sess_test_12345"

