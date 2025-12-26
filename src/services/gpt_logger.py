"""
GPT API 호출 로깅 모듈
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.db.models.ai_process_log import AIProcessLog
from src.db.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GPTLogger:
    """GPT API 호출 로깅 클래스"""
    
    @staticmethod
    def log_api_call(
        session_id: str,
        node_name: str,
        model: str,
        token_input: int,
        token_output: int,
        latency_ms: int,
        db_session: Optional[Session] = None
    ):
        """
        GPT API 호출 로그 저장
        
        Args:
            session_id: 세션 ID
            node_name: LangGraph Node 이름
            model: 사용한 모델명
            token_input: 입력 토큰 수
            token_output: 출력 토큰 수
            latency_ms: 응답 시간 (밀리초)
            db_session: DB 세션 (None이면 새로 생성)
        """
        try:
            if db_session is None:
                with db_manager.get_db_session() as session:
                    GPTLogger._save_log(
                        session, session_id, node_name, model,
                        token_input, token_output, latency_ms
                    )
            else:
                GPTLogger._save_log(
                    db_session, session_id, node_name, model,
                    token_input, token_output, latency_ms
                )
        
        except Exception as e:
            logger.error(f"GPT API 로그 저장 실패: {str(e)}")
    
    @staticmethod
    def _save_log(
        session: Session,
        session_id: str,
        node_name: str,
        model: str,
        token_input: int,
        token_output: int,
        latency_ms: int
    ):
        """로그 저장 (내부 함수)"""
        log_entry = AIProcessLog(
            session_id=session_id,
            node_name=node_name,
            model=model,
            token_input=token_input,
            token_output=token_output,
            latency_ms=latency_ms
        )
        
        session.add(log_entry)
        session.commit()
    
    @staticmethod
    def log_with_timing(
        session_id: str,
        node_name: str,
        model: str,
        usage: Dict[str, int],
        start_time: float,
        db_session: Optional[Session] = None
    ):
        """
        사용량과 시간 정보로 로그 저장
        
        Args:
            session_id: 세션 ID
            node_name: LangGraph Node 이름
            model: 사용한 모델명
            usage: 토큰 사용량 딕셔너리 (prompt_tokens, completion_tokens 등)
            start_time: 시작 시간 (time.time())
            db_session: DB 세션
        """
        import time
        latency_ms = int((time.time() - start_time) * 1000)
        
        token_input = usage.get("prompt_tokens", 0)
        token_output = usage.get("completion_tokens", 0)
        
        GPTLogger.log_api_call(
            session_id=session_id,
            node_name=node_name,
            model=model,
            token_input=token_input,
            token_output=token_output,
            latency_ms=latency_ms,
            db_session=db_session
        )


# 전역 GPT 로거 인스턴스
gpt_logger = GPTLogger()

