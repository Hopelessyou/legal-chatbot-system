"""
COMPLETED Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import SessionStatus
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.utils.helpers import get_kst_now
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
        
        # 단계 표시
        print("\n" + "="*70)
        print("📍 [STEP 7] COMPLETED 노드 실행 (최종 단계)")
        print("="*70)
        print(f"📌 세션 ID: {session_id}")
        print(f"📈 최종 완성도: {state.get('completion_rate', 0)}%")
        print(f"✅ 세션 상태: COMPLETED")
        print("="*70 + "\n")
        logger.info("="*70)
        logger.info("📍 [STEP 7] COMPLETED 노드 실행 (최종 단계)")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📈 최종 완성도: {state.get('completion_rate', 0)}%")
        logger.info(f"✅ 세션 상태: COMPLETED")
        logger.info("="*70)
        
        # 1. 세션 상태를 COMPLETED로 업데이트
        with db_manager.get_db_session() as db_session:
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                chat_session.status = SessionStatus.COMPLETED.value
                chat_session.current_state = "COMPLETED"
                chat_session.ended_at = get_kst_now()
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
        logger.error(f"COMPLETED Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 최소한의 상태 업데이트
        state["current_state"] = "COMPLETED"
        state["bot_message"] = "상담이 완료되었습니다."
        return {
            **state,
            "next_state": None
        }

