"""
MySQL 데이터베이스 설정 확인 스크립트
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


def check_database_setup():
    """데이터베이스 설정 상태 확인"""
    db_url = settings.database_url
    
    # URL 파싱
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    username = parsed.username
    password = parsed.password
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    
    print("=" * 60)
    print("MySQL Database Setup Check")
    print("=" * 60)
    print()
    print(f"Database URL: {db_url.split('@')[0]}@***/***")
    print(f"Database Name: {db_name}")
    print(f"User: {username}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print()
    
    try:
        # 연결 시도
        print("[1/4] Testing connection...")
        engine = create_engine(
            db_url,
            connect_args={'charset': 'utf8mb4'}
        )
        
        with engine.connect() as conn:
            print("  [OK] Connection successful!")
            
            # 데이터베이스 존재 확인
            print()
            print("[2/4] Checking if database exists...")
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
            )
            
            if result.fetchone():
                print(f"  [OK] Database '{db_name}' exists")
            else:
                print(f"  [ERROR] Database '{db_name}' does NOT exist")
                print()
                print("  To create the database, run:")
                print("    python scripts/create_db.py")
                return False
            
            # 사용자 확인
            print()
            print("[3/4] Checking if user exists...")
            result = conn.execute(
                text(f"SELECT User, Host FROM mysql.user WHERE User = '{username}' AND Host = 'localhost'")
            )
            user_info = result.fetchone()
            
            if user_info:
                print(f"  [OK] User '{username}'@'localhost' exists")
            else:
                print(f"  [WARNING] User '{username}'@'localhost' does NOT exist")
                print("  (This is OK if you're using root user)")
            
            # 권한 확인
            print()
            print("[4/4] Checking privileges...")
            # root 사용자는 항상 모든 권한을 가지고 있음
            if username == 'root':
                print(f"  [OK] User '{username}' is root user (has all privileges)")
            else:
                # 다른 사용자의 경우 권한 확인
                try:
                    result = conn.execute(
                        text(f"""
                            SELECT COUNT(*) as count 
                            FROM information_schema.user_privileges 
                            WHERE grantee = CONCAT('\\'', REPLACE(USER(), '@', '\\'@\\''), '\\'')
                            AND privilege_type = 'ALL PRIVILEGES'
                        """)
                    )
                    priv_count = result.fetchone()[0]
                    
                    if priv_count > 0:
                        print(f"  [OK] User '{username}' has privileges")
                    else:
                        print(f"  [WARNING] User '{username}' privileges may be limited")
                        print("  To grant privileges, run:")
                        print(f"    GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'localhost';")
                        print("    FLUSH PRIVILEGES;")
                except Exception as e:
                    print(f"  [WARNING] Could not check privileges: {str(e)}")
                    print(f"  (Assuming user '{username}' has necessary privileges)")
            
            # 테이블 확인
            print()
            print("[5/5] Checking tables...")
            result = conn.execute(
                text(f"SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = '{db_name}'")
            )
            table_count = result.fetchone()[0]
            
            if table_count > 0:
                print(f"  [OK] Found {table_count} table(s) in database")
                
                # 테이블 목록
                result = conn.execute(
                    text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{db_name}' ORDER BY table_name")
                )
                tables = [row[0] for row in result.fetchall()]
                print("  Tables:")
                for table in tables:
                    print(f"    - {table}")
            else:
                print(f"  [WARNING] No tables found in database '{db_name}'")
                print("  To create tables, run:")
                print("    python scripts/init_db.py")
        
        engine.dispose()
        
        print()
        print("=" * 60)
        print("[OK] Database setup check completed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("X Database setup check failed!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Possible issues:")
        print("1. MySQL server is not running")
        print("2. Wrong username or password")
        print("3. Database does not exist")
        print("4. User does not have privileges")
        print()
        print("To fix:")
        print("1. Check MySQL service: net start MySQL80")
        print("2. Verify .env file DATABASE_URL")
        print("3. Create database: python scripts/create_db.py")
        return False


if __name__ == "__main__":
    check_database_setup()

