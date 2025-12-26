"""
데이터베이스 초기화 스크립트 (DDL 실행)
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from config.settings import settings
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def init_database():
    """데이터베이스 초기화 (DDL 실행)"""
    ddl_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        'migrations',
        'versions',
        '001_initial_schema.sql'
    )
    
    try:
        engine = create_engine(settings.database_url)
        
        with open(ddl_file, 'r', encoding='utf-8') as f:
            ddl_sql = f.read()
        
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            try:
                # SQL 문장들을 세미콜론으로 분리하여 실행
                statements = [s.strip() for s in ddl_sql.split(';') if s.strip()]
                
                for statement in statements:
                    # 주석 제거 및 빈 줄 필터링
                    lines = [line.strip() for line in statement.split('\n') if line.strip() and not line.strip().startswith('--')]
                    clean_statement = ' '.join(lines)
                    
                    # 빈 문장이나 주석만 있는 경우 스킵
                    if not clean_statement or clean_statement.isspace():
                        continue
                    
                    try:
                        conn.execute(text(clean_statement))
                        logger.debug(f"Executed: {clean_statement[:50]}...")
                    except Exception as e:
                        # 일부 오류는 무시 (예: 테이블이 이미 존재하는 경우)
                        error_msg = str(e).lower()
                        if 'already exists' in error_msg or 'duplicate' in error_msg:
                            logger.warning(f"Skipped (already exists): {clean_statement[:50]}...")
                            continue
                        else:
                            logger.error(f"SQL execution failed: {clean_statement[:100]}")
                            raise
                
                trans.commit()
                logger.info("데이터베이스 초기화 완료")
            except Exception as e:
                trans.rollback()
                logger.error(f"데이터베이스 초기화 실패: {str(e)}")
                raise
        
        engine.dispose()
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 오류: {str(e)}")
        raise


if __name__ == "__main__":
    init_database()

