"""
요약 내용 및 DB 저장 여부 확인 스크립트
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.db.connection import db_manager
from src.db.models.case_master import CaseMaster
from src.db.models.case_summary import CaseSummary
from src.db.models.chat_session import ChatSession
from src.utils.logger import setup_logging, get_logger
import json

setup_logging()
logger = get_logger(__name__)


def check_summary_by_session_id(session_id: str):
    """세션 ID로 요약 확인"""
    try:
        with db_manager.get_db_session() as db_session:
            # 세션 조회
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                print(f"❌ 세션을 찾을 수 없습니다: {session_id}")
                return
            
            print(f"\n{'='*60}")
            print(f"세션 정보: {session_id}")
            print(f"{'='*60}")
            print(f"상태: {session.status}")
            print(f"현재 State: {session.current_state}")
            print(f"완성도: {session.completion_rate}%")
            print(f"시작 시간: {session.started_at}")
            print(f"종료 시간: {session.ended_at}")
            
            # Case 조회
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if not case:
                print(f"\n❌ 사건 정보를 찾을 수 없습니다.")
                return
            
            print(f"\n{'='*60}")
            print(f"사건 정보 (Case ID: {case.case_id})")
            print(f"{'='*60}")
            print(f"사건 유형: {case.main_case_type} / {case.sub_case_type}")
            print(f"사건 단계: {case.case_stage}")
            print(f"긴급도: {case.urgency_level}")
            print(f"예상 가치: {case.estimated_value}")
            
            # 요약 조회
            summary = db_session.query(CaseSummary).filter(
                CaseSummary.case_id == case.case_id
            ).first()
            
            if not summary:
                print(f"\n❌ 요약 정보를 찾을 수 없습니다.")
                print(f"   SUMMARY Node가 아직 실행되지 않았거나 오류가 발생했을 수 있습니다.")
                return
            
            print(f"\n{'='*60}")
            print(f"요약 정보 (Summary ID: {summary.id})")
            print(f"{'='*60}")
            print(f"생성 시간: {summary.created_at}")
            print(f"AI 버전: {summary.ai_version}")
            print(f"리스크 레벨: {summary.risk_level}")
            
            print(f"\n{'='*60}")
            print("요약 텍스트")
            print(f"{'='*60}")
            print(summary.summary_text)
            
            if summary.structured_json:
                print(f"\n{'='*60}")
                print("구조화된 데이터 (JSON)")
                print(f"{'='*60}")
                print(json.dumps(summary.structured_json, ensure_ascii=False, indent=2))
            
            print(f"\n{'='*60}")
            print("✅ 요약이 정상적으로 저장되었습니다!")
            print(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"요약 확인 실패: {str(e)}", exc_info=True)
        print(f"❌ 오류 발생: {str(e)}")


def list_recent_sessions(limit: int = 10):
    """최근 세션 목록 조회"""
    try:
        with db_manager.get_db_session() as db_session:
            sessions = db_session.query(ChatSession).order_by(
                ChatSession.created_at.desc()
            ).limit(limit).all()
            
            print(f"\n{'='*60}")
            print(f"최근 세션 목록 (최대 {limit}개)")
            print(f"{'='*60}")
            
            for session in sessions:
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session.session_id
                ).first()
                
                has_summary = False
                if case:
                    summary = db_session.query(CaseSummary).filter(
                        CaseSummary.case_id == case.case_id
                    ).first()
                    has_summary = summary is not None
                
                summary_status = "✅" if has_summary else "❌"
                print(f"{summary_status} {session.session_id} | {session.status} | {session.current_state} | {session.completion_rate}% | {session.created_at}")
            
            print(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {str(e)}", exc_info=True)
        print(f"❌ 오류 발생: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        check_summary_by_session_id(session_id)
    else:
        list_recent_sessions(10)
        print("\n사용법:")
        print("  python scripts/check_summary.py <session_id>  # 특정 세션의 요약 확인")
        print("  python scripts/check_summary.py                # 최근 세션 목록 조회")

