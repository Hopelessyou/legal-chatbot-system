"""
INIT Node 구현
"""
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from src.langgraph.state import StateContext
from src.utils.helpers import generate_session_id, get_kst_now
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import SessionStatus
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.rag.parser import RAGDocumentParser
from datetime import datetime

logger = get_logger(__name__)


def _load_k0_messages() -> Optional[Dict[str, Any]]:
    """
    K0 Intake YAML 파일 로드
    
    Returns:
        K0 메시지 데이터 또는 None (파일이 없는 경우)
    """
    try:
        # 프로젝트 루트 경로 찾기
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        k0_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
        
        if not k0_path.exists():
            logger.warning(f"K0 YAML 파일을 찾을 수 없습니다: {k0_path}")
            return None
        
        k0_data = RAGDocumentParser.load_yaml(k0_path)
        logger.info(f"K0 메시지 로드 완료: {len(k0_data.get('messages', []))}개 메시지")
        return k0_data
    
    except Exception as e:
        logger.error(f"K0 YAML 로드 실패: {str(e)}")
        return None


def _build_initial_message(k0_data: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """
    초기 메시지 생성
    
    Args:
        k0_data: K0 YAML 데이터
    
    Returns:
        (bot_message, expected_input) 튜플
    """
    if k0_data and "messages" in k0_data:
        # MESSAGE_ORDER 순서대로 메시지 결합
        messages = sorted(k0_data["messages"], key=lambda x: x.get("order", 999))
        
        # CONTINUE 또는 CLASSIFY로 시작하는 메시지만 포함
        message_parts = []
        expected_input = None
        
        for msg in messages:
            next_action = msg.get("next_action", "").upper()
            step_code = msg.get("step_code", "").upper()
            
            # STOP 또는 INTERNAL_ONLY는 제외
            if next_action in ["STOP", "INTERNAL_ONLY"]:
                continue
            
            # ROUTE_EMERGENCY는 나중에 처리 (현재는 제외)
            if next_action == "ROUTE_EMERGENCY":
                continue
            
            message_text = msg.get("message_text", "")
            if message_text:
                message_parts.append(message_text)
            
            # CLASSIFY로 시작하는 메시지가 있으면 expected_input 설정
            if next_action in ["CLASSIFY", "CLASSIFY_TEXT", "CLASSIFY_MENU"]:
                answer_type = msg.get("answer_type", "string")
                expected_input = {
                    "type": answer_type,
                    "description": "사건 상황 설명" if answer_type == "string" else "선택"
                }
                if answer_type == "choice":
                    # 선택지가 있으면 추가
                    if "options" in msg:
                        expected_input["options"] = msg["options"]
        
        bot_message = "\n\n".join(message_parts) if message_parts else "안녕하세요. 법률 상담을 도와드리겠습니다."
        
        if not expected_input:
            expected_input = {
                "type": "string",
                "description": "사건 상황 설명"
            }
        
        return bot_message, expected_input
    
    # K0 데이터가 없으면 기본 메시지
    return "안녕하세요. 법률 상담을 도와드리겠습니다. 상황을 3~5줄로 편하게 적어주세요.", {
        "type": "string",
        "description": "사건 상황 설명"
    }


@log_execution_time(logger)
def init_node(state: StateContext) -> Dict[str, Any]:
    """
    INIT Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state.get("session_id")
        user_input = state.get("last_user_input", "").strip()
        
        # 세션 ID가 없으면 생성
        if not session_id:
            session_id = generate_session_id()
            state["session_id"] = session_id
        
        # DB에 세션 생성
        try:
            with db_manager.get_db_session() as db_session:
                # 기존 세션 확인
                existing_session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if not existing_session:
                    # 새 세션 생성
                    new_session = ChatSession(
                        session_id=session_id,
                        channel=state.get("channel", "web"),
                        user_hash=state.get("user_hash"),
                        current_state="INIT",
                        status=SessionStatus.ACTIVE.value,
                        completion_rate=0,
                        started_at=get_kst_now()
                    )
                    db_session.add(new_session)
                    db_session.commit()
                    logger.info(f"새 세션 생성: {session_id}")
                else:
                    logger.info(f"기존 세션 사용: {session_id}")
        except Exception as db_error:
            logger.error(f"DB 세션 생성 실패: {str(db_error)}")
            # DB 오류가 있어도 계속 진행 (세션은 메모리에 저장됨)
        
        # 사용자 입력이 있으면 CASE_CLASSIFICATION으로 바로 이동
        if user_input and len(user_input) >= 2:
            logger.info(f"[{session_id}] INIT: 사용자 입력 감지, CASE_CLASSIFICATION으로 이동: {user_input[:50]}")
            # 사용자 입력을 그대로 전달하고 CASE_CLASSIFICATION으로 이동
            # 그래프 엣지에 의해 자동으로 CASE_CLASSIFICATION 노드가 실행됨
            return {
                **state,
                "current_state": "CASE_CLASSIFICATION",
                "next_state": "CASE_CLASSIFICATION"
            }
        
        # 사용자 입력이 없으면 초기 메시지 표시
        # K0 메시지 로드
        k0_data = _load_k0_messages()
        bot_message, expected_input = _build_initial_message(k0_data)
        
        # State 업데이트
        state["current_state"] = "INIT"
        state["bot_message"] = bot_message
        state["expected_input"] = expected_input
        
        logger.info(f"[{session_id}] INIT Node 완료: 초기 메시지 표시")
        
        return {
            **state,
            "next_state": "CASE_CLASSIFICATION"
        }
    
    except Exception as e:
        logger.error(f"INIT Node 실행 실패: {str(e)}", exc_info=True)
        # 에러가 발생해도 기본 메시지로 응답
        return {
            **state,
            "current_state": "INIT",
            "bot_message": "안녕하세요. 법률 상담을 도와드리겠습니다. 상황을 3~5줄로 편하게 적어주세요.",
            "expected_input": {
                "type": "string",
                "description": "사건 상황 설명"
            },
            "next_state": "CASE_CLASSIFICATION"
        }

