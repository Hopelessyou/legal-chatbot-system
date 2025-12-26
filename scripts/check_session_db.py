"""
세션의 DB 저장 상태 확인 스크립트
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.db.models.chat_session_state_log import ChatSessionStateLog
from src.db.models.case_master import CaseMaster
from src.db.models.case_party import CaseParty
from src.db.models.case_fact import CaseFact
from src.db.models.case_evidence import CaseEvidence
from src.db.models.case_emotion import CaseEmotion
from src.db.models.case_missing_field import CaseMissingField
from src.db.models.case_summary import CaseSummary
from src.db.models.ai_process_log import AIProcessLog
from src.utils.logger import setup_logging, get_logger
import json
from datetime import datetime

setup_logging()
logger = get_logger(__name__)


def check_session_db(session_id: str):
    """세션의 DB 저장 상태 확인"""
    try:
        with db_manager.get_db_session() as db_session:
            print(f"\n{'='*80}")
            print(f"세션 DB 저장 상태 확인: {session_id}")
            print(f"{'='*80}\n")
            
            # 1. ChatSession 확인
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                print(f"[ERROR] 세션을 찾을 수 없습니다: {session_id}")
                return
            
            print(f"[1] ChatSession 테이블")
            print(f"  [OK] 세션 ID: {session.session_id}")
            print(f"  [OK] 채널: {session.channel}")
            print(f"  [OK] 상태: {session.status}")
            print(f"  [OK] 현재 State: {session.current_state}")
            print(f"  [OK] 완성도: {session.completion_rate}%")
            print(f"  [OK] 시작 시간: {session.started_at}")
            print(f"  [OK] 종료 시간: {session.ended_at}")
            print(f"  [OK] 생성 시간: {session.created_at}")
            print(f"  [OK] 업데이트 시간: {session.updated_at}")
            
            # 2. ChatSessionStateLog 확인
            state_logs = db_session.query(ChatSessionStateLog).filter(
                ChatSessionStateLog.session_id == session_id
            ).order_by(ChatSessionStateLog.created_at).all()
            
            print(f"\n[2] ChatSessionStateLog 테이블 ({len(state_logs)}개)")
            if state_logs:
                for log in state_logs:
                    print(f"  [OK] {log.from_state} → {log.to_state} (조건: {log.condition_key}, 시간: {log.created_at})")
            else:
                print(f"  [WARN] 상태 로그가 없습니다.")
            
            # 3. CaseMaster 확인
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if not case:
                print(f"\n[3] CaseMaster 테이블")
                print(f"  [ERROR] 사건 정보가 없습니다.")
                return
            
            print(f"\n[3] CaseMaster 테이블")
            print(f"  [OK] Case ID: {case.case_id}")
            print(f"  [OK] 사건 유형: {case.main_case_type} / {case.sub_case_type}")
            print(f"  [OK] 사건 단계: {case.case_stage}")
            print(f"  [OK] 긴급도: {case.urgency_level}")
            print(f"  [OK] 예상 가치: {case.estimated_value:,}원" if case.estimated_value else "  [OK] 예상 가치: None")
            print(f"  [OK] 생성 시간: {case.created_at}")
            print(f"  [OK] 업데이트 시간: {case.updated_at}")
            
            # 4. CaseParty 확인
            parties = db_session.query(CaseParty).filter(
                CaseParty.case_id == case.case_id
            ).all()
            
            print(f"\n[4] CaseParty 테이블 ({len(parties)}개)")
            if parties:
                for party in parties:
                    print(f"  [OK] 역할: {party.party_role}, 유형: {party.party_type}, 설명: {party.party_description}")
            else:
                print(f"  [WARN] 당사자 정보가 없습니다.")
            
            # 5. CaseFact 확인
            facts = db_session.query(CaseFact).filter(
                CaseFact.case_id == case.case_id
            ).all()
            
            print(f"\n[5] CaseFact 테이블 ({len(facts)}개)")
            if facts:
                for fact in facts:
                    print(f"  [OK] 타입: {fact.fact_type}")
                    print(f"     - 사건일: {fact.incident_date}")
                    print(f"     - 장소: {fact.location}")
                    print(f"     - 금액: {fact.amount:,}원" if fact.amount else "     - 금액: None")
                    print(f"     - 설명: {fact.description[:50]}..." if fact.description and len(fact.description) > 50 else f"     - 설명: {fact.description}")
                    print(f"     - 신뢰도: {fact.confidence_score}%")
                    print(f"     - 원본 텍스트: {fact.source_text[:50]}..." if fact.source_text and len(fact.source_text) > 50 else f"     - 원본 텍스트: {fact.source_text}")
                    print(f"     - 생성 시간: {fact.created_at}")
                    print()
            else:
                print(f"  [WARN] 사실 정보가 없습니다.")
            
            # 6. CaseEvidence 확인
            evidences = db_session.query(CaseEvidence).filter(
                CaseEvidence.case_id == case.case_id
            ).all()
            
            print(f"[6] CaseEvidence 테이블 ({len(evidences)}개)")
            if evidences:
                for evidence in evidences:
                    print(f"  [OK] 타입: {evidence.evidence_type}")
                    print(f"     - 사용 가능: {evidence.available}")
                    print(f"     - 설명: {evidence.description[:50]}..." if evidence.description and len(evidence.description) > 50 else f"     - 설명: {evidence.description}")
                    print(f"     - 생성 시간: {evidence.created_at}")
            else:
                print(f"  [WARN] 증거 정보가 없습니다.")
            
            # 7. CaseEmotion 확인
            emotions = db_session.query(CaseEmotion).filter(
                CaseEmotion.case_id == case.case_id
            ).all()
            
            print(f"\n[7] CaseEmotion 테이블 ({len(emotions)}개)")
            if emotions:
                for emotion in emotions:
                    print(f"  [OK] 타입: {emotion.emotion_type}, 강도: {emotion.intensity}")
                    print(f"     - 원본 텍스트: {emotion.source_text[:50]}..." if emotion.source_text and len(emotion.source_text) > 50 else f"     - 원본 텍스트: {emotion.source_text}")
            else:
                print(f"  [WARN] 감정 정보가 없습니다.")
            
            # 8. CaseMissingField 확인
            missing_fields = db_session.query(CaseMissingField).filter(
                CaseMissingField.case_id == case.case_id
            ).all()
            
            print(f"\n[8] CaseMissingField 테이블 ({len(missing_fields)}개)")
            if missing_fields:
                for field in missing_fields:
                    resolved_status = "[OK] 해결됨" if field.resolved else "[X] 미해결"
                    print(f"  {resolved_status} 필드: {field.field_key}, 필수: {field.required}")
                    if field.resolved_at:
                        print(f"     - 해결 시간: {field.resolved_at}")
            else:
                print(f"  [OK] 누락 필드가 없습니다 (모든 필드 수집 완료)")
            
            # 9. CaseSummary 확인
            summary = db_session.query(CaseSummary).filter(
                CaseSummary.case_id == case.case_id
            ).first()
            
            print(f"\n[9] CaseSummary 테이블")
            if summary:
                print(f"  [OK] Summary ID: {summary.id}")
                print(f"  [OK] AI 버전: {summary.ai_version}")
                print(f"  [OK] 리스크 레벨: {summary.risk_level}")
                print(f"  [OK] 생성 시간: {summary.created_at}")
                print(f"  [OK] 요약 텍스트 길이: {len(summary.summary_text)}자")
                print(f"  [OK] 구조화된 데이터: {json.dumps(summary.structured_json, ensure_ascii=False, indent=2) if summary.structured_json else 'None'}")
            else:
                print(f"  [ERROR] 요약 정보가 없습니다.")
            
            # 10. AIProcessLog 확인
            ai_logs = db_session.query(AIProcessLog).filter(
                AIProcessLog.session_id == session_id
            ).order_by(AIProcessLog.created_at).all()
            
            print(f"\n[10] AIProcessLog 테이블 ({len(ai_logs)}개)")
            if ai_logs:
                print(f"  [OK] 총 {len(ai_logs)}개의 AI 처리 로그")
                total_input_tokens = sum(log.token_input or 0 for log in ai_logs)
                total_output_tokens = sum(log.token_output or 0 for log in ai_logs)
                total_latency = sum(log.latency_ms or 0 for log in ai_logs)
                print(f"  [OK] 총 입력 토큰: {total_input_tokens:,}")
                print(f"  [OK] 총 출력 토큰: {total_output_tokens:,}")
                print(f"  [OK] 총 지연 시간: {total_latency}ms ({total_latency/1000:.2f}초)")
            else:
                print(f"  [WARN] AI 처리 로그가 없습니다.")
            
            # 요약
            print(f"\n{'='*80}")
            print(f"[요약]")
            print(f"  [OK] 세션: {session.status}")
            print(f"  [OK] 사건: {case.main_case_type} / {case.sub_case_type}")
            print(f"  [OK] 당사자: {len(parties)}명")
            print(f"  [OK] 사실: {len(facts)}개")
            print(f"  [OK] 증거: {len(evidences)}개")
            print(f"  [OK] 감정: {len(emotions)}개")
            print(f"  [OK] 누락 필드: {len(missing_fields)}개")
            print(f"  [OK] 요약: {'있음' if summary else '없음'}")
            print(f"  [OK] 상태 로그: {len(state_logs)}개")
            print(f"  [OK] AI 로그: {len(ai_logs)}개")
            print(f"{'='*80}\n")
            
    except Exception as e:
        logger.error(f"세션 DB 확인 실패: {str(e)}", exc_info=True)
        print(f"[ERROR] 오류 발생: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/check_session_db.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    check_session_db(session_id)

