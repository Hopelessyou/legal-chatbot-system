"""
COMPLETED Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.utils.logger import get_logger, log_execution_time
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from datetime import datetime

logger = get_logger(__name__)


@log_execution_time(logger)
def completed_node(state: StateContext) -> Dict[str, Any]:
    """
    COMPLETED Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        최종 State 정보
    """
    try:
        session_id = state["session_id"]
        
        logger.info(f"[{session_id}] COMPLETED Node 실행: completion_rate={state.get('completion_rate', 0)}%")
        
        # 1. 세션 상태를 COMPLETED로 업데이트
        with db_manager.get_db_session() as db_session:
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                chat_session.status = "COMPLETED"
                chat_session.current_state = "COMPLETED"
                chat_session.ended_at = datetime.utcnow()
                chat_session.completion_rate = state.get("completion_rate", 0)
                db_session.commit()
        
        # 2. State 전이 로깅
        from src.langgraph.state_logger import log_state_transition
        log_state_transition(
            session_id=session_id,
            from_state="SUMMARY",
            to_state="COMPLETED",
            condition_key="summary_completed"
        )
        
        # 3. State 업데이트
        state["current_state"] = "COMPLETED"
        state["bot_message"] = "상담에 필요한 정보를 확인했습니다. 자료 확인 후 상담 전화를 드리오니 받아 주시기 부탁드립니다."
        
        logger.info(f"COMPLETED 완료: session_id={session_id}")
        
        return {
            **state,
            "next_state": None  # 종료
        }
    
    except Exception as e:
        logger.error(f"COMPLETED Node 실행 실패: {str(e)}")
        raise

