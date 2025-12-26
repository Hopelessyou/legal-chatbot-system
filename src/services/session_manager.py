"""
세션 관리 서비스 모듈
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.langgraph.state import StateContext, create_initial_context
from src.utils.helpers import generate_session_id, generate_user_hash
from src.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class SessionManager:
    """세션 관리 클래스"""
    
    @staticmethod
    def create_session(
        channel: str = "web",
        user_identifier: Optional[str] = None
    ) -> str:
        """
        새 세션 생성
        
        Args:
            channel: 채널 (web/mobile/kakao)
            user_identifier: 사용자 식별자
        
        Returns:
            생성된 세션 ID
        """
        session_id = generate_session_id()
        user_hash = generate_user_hash(user_identifier) if user_identifier else None
        
        try:
            with db_manager.get_db_session() as db_session:
                session = ChatSession(
                    session_id=session_id,
                    channel=channel,
                    user_hash=user_hash,
                    current_state="INIT",
                    status="ACTIVE",
                    completion_rate=0,
                    started_at=datetime.utcnow()
                )
                db_session.add(session)
                db_session.commit()
            
            logger.info(f"세션 생성 완료: {session_id}")
            return session_id
        
        except Exception as e:
            logger.error(f"세션 생성 실패: {str(e)}")
            raise
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ChatSession]:
        """
        세션 조회
        
        Args:
            session_id: 세션 ID
        
        Returns:
            ChatSession 인스턴스 또는 None
        """
        try:
            with db_manager.get_db_session() as db_session:
                session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                return session
        except Exception as e:
            logger.error(f"세션 조회 실패: {session_id} - {str(e)}")
            return None
    
    @staticmethod
    def load_session_state(session_id: str) -> Optional[StateContext]:
        """
        세션 상태 로드
        
        Args:
            session_id: 세션 ID
        
        Returns:
            StateContext 또는 None
        """
        try:
            # DB 세션 컨텍스트 내에서 모든 속성 접근
            with db_manager.get_db_session() as db_session:
                session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if not session:
                    return None
                
                # DB에서 상태 복원 (DB 세션 컨텍스트 내에서 접근)
                context = create_initial_context(session_id)
                context["current_state"] = session.current_state
                context["completion_rate"] = session.completion_rate
                
                # case_master에서 추가 정보 로드
                from src.db.models.case_master import CaseMaster
                from src.db.models.case_fact import CaseFact
                from src.db.models.case_party import CaseParty
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if case:
                    context["case_type"] = case.main_case_type
                    context["sub_case_type"] = case.sub_case_type
                    
                    # CaseFact에서 facts 복원
                    facts = {}
                    
                    # 모든 CaseFact를 조회하여 최신 값으로 업데이트
                    all_facts = db_session.query(CaseFact).filter(
                        CaseFact.case_id == case.case_id
                    ).order_by(CaseFact.created_at.desc()).all()
                    
                    for fact in all_facts:
                        if fact.incident_date and not facts.get("incident_date"):
                            facts["incident_date"] = fact.incident_date.strftime("%Y-%m-%d")
                        if fact.amount and not facts.get("amount"):
                            facts["amount"] = fact.amount
                    
                    # CaseParty에서 counterparty 복원
                    counterparty = db_session.query(CaseParty).filter(
                        CaseParty.case_id == case.case_id,
                        CaseParty.party_role == "상대방"
                    ).first()
                    
                    if counterparty and counterparty.party_description:
                        facts["counterparty"] = counterparty.party_description
                    
                    # CaseEvidence에서 evidence 복원
                    from src.db.models.case_evidence import CaseEvidence
                    evidence = db_session.query(CaseEvidence).filter(
                        CaseEvidence.case_id == case.case_id
                    ).order_by(CaseEvidence.created_at.desc()).first()
                    
                    if evidence:
                        facts["evidence"] = evidence.available
                        if evidence.evidence_type:
                            facts["evidence_type"] = evidence.evidence_type
                    
                    context["facts"] = facts
                    logger.debug(f"세션 상태 로드 완료: {session_id}, facts={list(facts.keys())}")
            
            logger.debug(f"세션 상태 로드 완료: {session_id}")
            return context
        
        except Exception as e:
            logger.error(f"세션 상태 로드 실패: {session_id} - {str(e)}")
            return None
    
    @staticmethod
    def save_session_state(
        session_id: str,
        state: StateContext,
        db_session: Optional[Session] = None
    ):
        """
        세션 상태 저장
        
        Args:
            session_id: 세션 ID
            state: StateContext
            db_session: DB 세션 (None이면 새로 생성)
        """
        try:
            if db_session is None:
                with db_manager.get_db_session() as session:
                    _update_session(session, session_id, state)
            else:
                _update_session(db_session, session_id, state)
        
        except Exception as e:
            logger.error(f"세션 상태 저장 실패: {session_id} - {str(e)}")
            raise


def _update_session(session: Session, session_id: str, state: StateContext):
    """세션 업데이트 (내부 함수)"""
    chat_session = session.query(ChatSession).filter(
        ChatSession.session_id == session_id
    ).first()
    
    if chat_session:
        chat_session.current_state = state.get("current_state", "INIT")
        chat_session.completion_rate = state.get("completion_rate", 0)
        chat_session.updated_at = datetime.utcnow()
        session.commit()


def validate_session_id(session_id: str) -> bool:
    """
    세션 ID 검증
    
    Args:
        session_id: 세션 ID
    
    Returns:
        검증 결과 (True: 유효, False: 무효)
    """
    if not session_id:
        return False
    
    if not session_id.startswith("sess_"):
        return False
    
    if len(session_id) < 10:
        return False
    
    return True


def load_session_state(session_id: str) -> Optional[StateContext]:
    """
    세션 상태 로드 (독립 함수)
    
    Args:
        session_id: 세션 ID
    
    Returns:
        StateContext 또는 None
    """
    return SessionManager.load_session_state(session_id)


def save_session_state(
    session_id: str,
    state: StateContext,
    db_session: Optional[Session] = None
):
    """
    세션 상태 저장 (독립 함수)
    
    Args:
        session_id: 세션 ID
        state: StateContext
        db_session: DB 세션 (None이면 새로 생성)
    """
    SessionManager.save_session_state(session_id, state, db_session)


def cleanup_expired_sessions():
    """만료된 세션 정리"""
    try:
        expiry_hours = settings.session_expiry_hours
        expiry_time = datetime.utcnow() - timedelta(hours=expiry_hours)
        
        with db_manager.get_db_session() as db_session:
            expired_sessions = db_session.query(ChatSession).filter(
                ChatSession.status == "ACTIVE",
                ChatSession.updated_at < expiry_time
            ).all()
            
            for session in expired_sessions:
                session.status = "ABORTED"
            
            db_session.commit()
            
            logger.info(f"만료 세션 정리 완료: {len(expired_sessions)}개")
    
    except Exception as e:
        logger.error(f"만료 세션 정리 실패: {str(e)}")

