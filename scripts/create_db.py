"""
MySQL 데이터베이스 생성 스크립트
"""
import sys
import os
from getpass import getpass

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
    target_username = parsed.username
    target_password = parsed.password
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    
    # 먼저 현재 사용자로 연결 시도
    try:
        # 현재 설정된 사용자로 연결 시도
        current_url = f"mysql+pymysql://{target_username}:{target_password}@{host}:{port}"
        engine = create_engine(
            current_url,
            connect_args={'charset': 'utf8mb4'}
        )
        
        # 연결 테스트
        with engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
        logger.info(f"사용자 '{target_username}'로 연결 성공. 이 사용자로 데이터베이스를 생성합니다.")
        use_root = False
        
    except Exception as e:
        logger.info(f"사용자 '{target_username}'로 연결 실패: {str(e)}")
        logger.info("root 사용자로 연결을 시도합니다...")
        use_root = True
        
        # root 사용자 정보 (환경 변수에서 가져오거나 입력받기)
        root_user = os.getenv('MYSQL_ROOT_USER', 'root')
        root_password = os.getenv('MYSQL_ROOT_PASSWORD')
        
        # root 비밀번호가 없으면 환경 변수 확인 후 안내
        if not root_password:
            logger.error("MySQL root 사용자 비밀번호가 필요합니다.")
            logger.info("")
            logger.info("해결 방법:")
            logger.info("1. 환경 변수 설정:")
            logger.info("   PowerShell: $env:MYSQL_ROOT_PASSWORD = 'your_password'")
            logger.info("   그 다음: python scripts/create_db.py")
            logger.info("")
            logger.info("2. MySQL CLI 스크립트 사용 (권장):")
            logger.info("   powershell -ExecutionPolicy Bypass -File scripts/create_db_mysql_cli.ps1")
            logger.info("")
            logger.info("3. MySQL CLI 직접 사용:")
            logger.info("   mysql -u root -p")
            logger.info("   CREATE DATABASE legal_chat_info_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            raise ValueError("MYSQL_ROOT_PASSWORD 환경 변수가 설정되지 않았습니다.")
        
        # root 사용자로 MySQL 서버에 연결 (데이터베이스 이름 없이)
        root_url = f"mysql+pymysql://{root_user}:{root_password}@{host}:{port}"
        
        engine = create_engine(
            root_url,
            connect_args={'charset': 'utf8mb4'}
        )
    
    try:
        
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
            
            # root를 사용한 경우에만 사용자 생성 및 권한 부여
            if use_root and target_username and target_username != root_user:
                user_check = conn.execute(
                    text(f"SELECT User FROM mysql.user WHERE User = '{target_username}' AND Host = 'localhost'")
                )
                
                if not user_check.fetchone():
                    logger.info(f"사용자 '{target_username}' 생성 중...")
                    conn.execute(text(f"CREATE USER '{target_username}'@'localhost' IDENTIFIED BY '{target_password}'"))
                    conn.commit()
                    logger.info(f"사용자 '{target_username}' 생성 완료")
                
                # 권한 부여
                logger.info(f"사용자 '{target_username}'에게 권한 부여 중...")
                conn.execute(text(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{target_username}'@'localhost'"))
                conn.execute(text("FLUSH PRIVILEGES"))
                conn.commit()
                logger.info(f"권한 부여 완료")
        
        engine.dispose()
        
    except Exception as e:
        logger.error(f"데이터베이스 생성 실패: {str(e)}")
        logger.info("힌트: MySQL root 사용자 비밀번호를 확인하거나, 환경 변수 MYSQL_ROOT_PASSWORD를 설정하세요.")
        raise


if __name__ == "__main__":
    create_database()
