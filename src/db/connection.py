"""
데이터베이스 연결 관리 모듈
"""
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """데이터베이스 연결 관리 클래스"""
    
    def __init__(self):
        self.engine: Engine = None
        self.SessionLocal: sessionmaker = None
        self._initialize()
    
    def _initialize(self):
        """데이터베이스 연결 초기화"""
        try:
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # 연결 유효성 사전 확인
                echo=False,  # SQL 쿼리 로깅 (개발 시 True)
            )
            
            self.SessionLocal = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
            )
            
            logger.info("데이터베이스 연결 초기화 완료")
        except Exception as e:
            logger.error(f"데이터베이스 연결 초기화 실패: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """
        데이터베이스 세션 획득
        
        Returns:
            Session 인스턴스
        """
        return self.SessionLocal()
    
    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """
        컨텍스트 매니저를 사용한 데이터베이스 세션 획득
        
        Yields:
            Session 인스턴스
        
        Example:
            with db_manager.get_db_session() as session:
                # DB 작업 수행
                pass
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"데이터베이스 세션 오류: {str(e)}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        데이터베이스 연결 상태 확인
        
        Returns:
            연결 상태 (True: 정상, False: 오류)
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.debug("데이터베이스 연결 상태: 정상")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 연결 상태 확인 실패: {str(e)}")
            return False
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("데이터베이스 연결 종료")


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 의존성 주입용 데이터베이스 세션 생성기
    
    Yields:
        Session 인스턴스
    """
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

