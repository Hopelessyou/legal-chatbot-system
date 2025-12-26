"""
MySQL 데이터베이스 생성 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from urllib.parse import urlparse
from config.settings import settings
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_database():
    """MySQL 데이터베이스 생성"""
    # 데이터베이스 이름 추출
    db_url = settings.database_url
    
    # URL 파싱
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    
    # 연결 파라미터 추출
    username = parsed.username
    password = parsed.password
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    
    try:
        # MySQL 서버에 연결 (데이터베이스 이름 없이)
        # MySQL의 경우 기본 데이터베이스는 없으므로 None을 사용
        base_url = f"mysql+pymysql://{username}:{password}@{host}:{port}"
        
        engine = create_engine(
            base_url,
            connect_args={'charset': 'utf8mb4'}
        )
        
        with engine.connect() as conn:
            # 데이터베이스 존재 여부 확인
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            
            if result.fetchone():
                logger.info(f"데이터베이스 '{db_name}'가 이미 존재합니다.")
            else:
                # 데이터베이스 생성
                # MySQL은 UTF8MB4를 사용하여 이모지 등도 지원
                conn.execute(text(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                logger.info(f"데이터베이스 '{db_name}' 생성 완료")
        
        engine.dispose()
        
    except Exception as e:
        logger.error(f"데이터베이스 생성 실패: {str(e)}")
        raise


if __name__ == "__main__":
    create_database()

