"""
State 전이 로깅 모듈
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.db.connection import db_manager
from src.db.models.chat_session_state_log import ChatSessionStateLog
from src.utils.logger import get_logger

logger = get_logger(__name__)


def log_state_transition(
    session_id: str,
    from_state: str,
    to_state: str,
    condition_key: Optional[str] = None,
    db_session: Optional[Session] = None
):
    """
    State 전이 로깅
    
    Args:
        session_id: 세션 ID
        from_state: 이전 State
        to_state: 다음 State
        condition_key: 분기 조건 키
        db_session: DB 세션 (None이면 새로 생성)
    """
    try:
        if db_session is None:
            with db_manager.get_db_session() as session:
                _save_state_log(
                    session, session_id, from_state, to_state, condition_key
                )
        else:
            _save_state_log(
                db_session, session_id, from_state, to_state, condition_key
            )
        
        logger.debug(f"State 전이 로깅: {from_state} → {to_state}")
    
    except Exception as e:
        logger.error(f"State 전이 로깅 실패: {str(e)}")


def _save_state_log(
    session: Session,
    session_id: str,
    from_state: str,
    to_state: str,
    condition_key: Optional[str]
):
    """State 로그 저장 (내부 함수)"""
    log_entry = ChatSessionStateLog(
        session_id=session_id,
        from_state=from_state,
        to_state=to_state,
        condition_key=condition_key
    )
    
    session.add(log_entry)
    session.commit()

