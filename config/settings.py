"""
애플리케이션 설정 관리 모듈
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv(encoding='utf-8')


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Database
    # 기본값: PostgreSQL (docker-compose.yml과 일치)
    # MySQL을 사용하려면 환경변수 DATABASE_URL을 mysql+pymysql://... 형식으로 설정
    database_url: str = "postgresql://legal_user:legal_password@localhost:5432/legal_chatbot_db"
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Vector DB
    vector_db_type: str = "chroma"
    vector_db_path: str = "./data/vector_db"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # API
    api_secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Session
    session_expiry_hours: int = 24
    
    # Logging
    log_level: str = "INFO"
    log_file_path: str = "./logs/app.log"
    
    # Environment
    environment: str = "development"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # LangGraph
    graph_recursion_limit: int = 50  # 무한 루프 방지를 위한 최대 재귀 깊이
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    
    # Naver Works Bot
    naverworks_service_account: Optional[str] = None
    naverworks_private_key: Optional[str] = None
    naverworks_private_key_path: Optional[str] = None
    naverworks_client_id: Optional[str] = None
    naverworks_client_secret: Optional[str] = None
    naverworks_bot_id: Optional[str] = None
    naverworks_user_id: Optional[str] = None
    
    # File Upload
    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 10
    
    # A/B Testing
    ab_test_enabled: bool = False  # A/B 테스트 활성화 여부
    fact_extraction_method: str = "qa_matching"  # "legacy" 또는 "qa_matching"
    
    # GPT API Optimization
    gpt_cache_enabled: bool = False  # GPT API 응답 캐싱 활성화 여부
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("OPENAI_API_KEY는 필수 환경 변수입니다.")
        return v
    
    @field_validator('api_secret_key')
    @classmethod
    def validate_api_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("API_SECRET_KEY는 필수 환경 변수입니다.")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level은 다음 중 하나여야 합니다: {', '.join(valid_levels)}")
        return v.upper()
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS Origins를 리스트로 변환"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()

