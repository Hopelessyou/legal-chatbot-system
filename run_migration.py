"""
DB 마이그레이션 실행 스크립트
conversation_history 컬럼 추가
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.db.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """conversation_history 컬럼 추가 마이그레이션 실행"""
    try:
        with db_manager.get_db_session() as db_session:
            # MySQL/MariaDB에서 JSON 컬럼 추가
            sql = """
            ALTER TABLE chat_session 
            ADD COLUMN conversation_history JSON NULL COMMENT 'Q-A 쌍 리스트 (질답 내용)';
            """
            
            try:
                from sqlalchemy import text
                db_session.execute(text(sql))
                db_session.commit()
                logger.info("[SUCCESS] 마이그레이션 성공: conversation_history 컬럼 추가 완료")
                print("[SUCCESS] 마이그레이션 성공: conversation_history 컬럼 추가 완료")
                return True
            except Exception as e:
                error_msg = str(e).lower()
                # 이미 컬럼이 있는 경우
                if "duplicate column" in error_msg or "already exists" in error_msg or "1060" in error_msg:
                    logger.info("[INFO] conversation_history 컬럼이 이미 존재합니다.")
                    print("[INFO] conversation_history 컬럼이 이미 존재합니다.")
                    return True
                else:
                    raise
    
    except Exception as e:
        logger.error(f"[ERROR] 마이그레이션 실패: {str(e)}")
        print(f"[ERROR] 마이그레이션 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*70)
    print("DB 마이그레이션 실행: conversation_history 컬럼 추가")
    print("="*70)
    
    success = run_migration()
    
    if success:
        print("\n[SUCCESS] 마이그레이션 완료!")
        print("이제 conversation_history가 자동으로 DB에 저장됩니다.")
    else:
        print("\n[ERROR] 마이그레이션 실패!")
        print("수동으로 SQL을 실행해주세요:")
        print("ALTER TABLE chat_session ADD COLUMN conversation_history JSON NULL;")
        sys.exit(1)
