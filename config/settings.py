"""
애플리케이션 설정 관리 모듈
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv(encoding='utf-8')


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Database
    database_url: str = "mysql+pymysql://user:password@localhost:3306/legal_chatbot_db"
    
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
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    
    # File Upload
    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 10
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS Origins를 리스트로 변환"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()

