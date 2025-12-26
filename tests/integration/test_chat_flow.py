"""
채팅 플로우 통합 테스트
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.utils.helpers import generate_session_id

client = TestClient(app)


@pytest.fixture
def test_session():
    """테스트용 세션 생성"""
    session_id = generate_session_id()
    
    with db_manager.get_db_session() as db_session:
        test_session = ChatSession(
            session_id=session_id,
            channel="web",
            current_state="INIT",
            status="ACTIVE",
            completion_rate=0
        )
        db_session.add(test_session)
        db_session.commit()
    
    yield session_id
    
    # 정리
    with db_manager.get_db_session() as db_session:
        db_session.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).delete()
        db_session.commit()


def test_chat_start():
    """상담 시작 테스트"""
    response = client.post(
        "/chat/start",
        json={"channel": "web"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "session_id" in data["data"]
    assert data["data"]["state"] == "INIT"
    assert "bot_message" in data["data"]


def test_chat_message_flow(test_session):
    """채팅 메시지 플로우 테스트"""
    # 첫 메시지 전송
    response = client.post(
        "/chat/message",
        json={
            "session_id": test_session,
            "user_message": "작년 10월에 계약을 했는데 대금을 받지 못했습니다."
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["current_state"] in ["CASE_CLASSIFICATION", "FACT_COLLECTION"]
    assert "bot_message" in data["data"]


def test_chat_status(test_session):
    """상담 상태 조회 테스트"""
    response = client.get(f"/chat/status?session_id={test_session}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["session_id"] == test_session


def test_invalid_session():
    """유효하지 않은 세션 테스트"""
    response = client.post(
        "/chat/message",
        json={
            "session_id": "invalid_session_id",
            "user_message": "테스트 메시지"
        }
    )
    
    assert response.status_code == 404


def test_chat_end(test_session):
    """상담 종료 테스트"""
    # 먼저 메시지를 몇 개 보내서 진행
    client.post(
        "/chat/message",
        json={
            "session_id": test_session,
            "user_message": "테스트 메시지"
        }
    )
    
    # 상담 종료
    response = client.post(
        "/chat/end",
        json={"session_id": test_session}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

