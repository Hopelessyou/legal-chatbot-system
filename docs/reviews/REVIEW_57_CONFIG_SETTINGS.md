# Config Settings 검토 보고서

## 검토 대상
- 파일: `config/settings.py`
- 검토 일자: 2024년
- 검토 범위: 애플리케이션 설정, 환경변수 로드, Pydantic 설정

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-10)
- ✅ 명확한 모듈 docstring
- ✅ Pydantic Settings 사용
- ✅ 환경 변수 로드 (`load_dotenv`)

### 2. Settings 클래스 (Lines 13-74)
- ✅ Pydantic `BaseSettings` 상속
- ✅ 명확한 설정 그룹화 (Database, OpenAI, Vector DB, API, Session, Logging 등)
- ✅ 적절한 기본값 설정
- ✅ 타입 힌팅 적절

### 3. 속성 메서드 (Lines 65-68)
- ✅ `cors_origins_list` property로 CORS origins 리스트 변환

### 4. Config 클래스 (Lines 70-73)
- ✅ Pydantic Config 설정
- ✅ UTF-8 인코딩 명시
- ✅ 대소문자 구분 없음 설정

### 5. 전역 인스턴스 (Lines 76-77)
- ✅ 싱글톤 패턴으로 `settings` 인스턴스 생성

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 필수 필드 검증 부재

**문제**: `openai_api_key`와 `api_secret_key`는 필수 필드이지만, Pydantic의 기본 검증만 수행합니다. 환경 변수가 없을 때 명확한 에러 메시지가 없을 수 있습니다.

**영향도**: 중간  
**수정 권장**: 필수 필드 검증 추가

**수정 예시**:
```python
from pydantic import field_validator, ValidationError

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI
    openai_api_key: str
    
    # API
    api_secret_key: str
    
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
```

---

### 2. 🟢 **낮음**: 설정값 검증 부재

**문제**: 일부 설정값에 대한 검증이 없습니다. 예를 들어:
- `api_port`는 1-65535 범위여야 함
- `session_expiry_hours`는 양수여야 함
- `max_file_size_mb`는 양수여야 함
- `log_level`은 유효한 로그 레벨이어야 함

**영향도**: 낮음  
**수정 권장**: 설정값 검증 추가 (선택적)

**수정 예시**:
```python
from pydantic import field_validator

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    api_port: int = 8000
    session_expiry_hours: int = 24
    max_file_size_mb: int = 10
    log_level: str = "INFO"
    
    @field_validator('api_port')
    @classmethod
    def validate_api_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("api_port는 1-65535 범위여야 합니다.")
        return v
    
    @field_validator('session_expiry_hours')
    @classmethod
    def validate_session_expiry_hours(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("session_expiry_hours는 양수여야 합니다.")
        return v
    
    @field_validator('max_file_size_mb')
    @classmethod
    def validate_max_file_size_mb(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_file_size_mb는 양수여야 합니다.")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level은 다음 중 하나여야 합니다: {', '.join(valid_levels)}")
        return v.upper()
```

---

### 3. 🟢 **낮음**: Pydantic v2 설정 방식

**문제**: `Config` 클래스를 사용하는 방식은 Pydantic v1 방식입니다. Pydantic v2에서는 `model_config = SettingsConfigDict(...)`를 사용하는 것이 권장됩니다.

**영향도**: 낮음  
**수정 권장**: Pydantic v2 방식으로 업데이트 (선택적, 현재도 동작함)

**수정 예시**:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # ... 나머지 필드들
```

---

### 4. 🟢 **낮음**: 환경 변수 로드 중복

**문제**: 파일 상단에서 `load_dotenv(encoding='utf-8')`를 호출하고, `Config` 클래스에서도 `env_file = ".env"`를 설정하고 있습니다. Pydantic Settings가 자동으로 `.env` 파일을 로드하므로 중복일 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 중복 제거 (선택적, 현재도 동작함)

**참고**: `load_dotenv()`를 먼저 호출하면 시스템 환경 변수보다 `.env` 파일의 값이 우선됩니다. 이는 의도된 동작일 수 있습니다.

---

### 5. 🟢 **낮음**: `cors_origins_list` 빈 문자열 처리

**문제**: `cors_origins_list` property에서 빈 문자열이 포함될 수 있습니다. `split(",")` 후 `strip()`만 하면 빈 문자열이 남을 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 빈 문자열 필터링

**수정 예시**:
```python
@property
def cors_origins_list(self) -> List[str]:
    """CORS Origins를 리스트로 변환"""
    return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
```

---

### 6. 🟢 **낮음**: 타입 힌팅 개선

**문제**: 일부 필드의 타입 힌팅이 불완전합니다. 예를 들어, `cors_origins_list`의 반환 타입이 `List[str]`이지만, Pydantic v2에서는 `list[str]`를 사용할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재도 충분히 명확함)

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중간**: 1개 (필수 필드 검증 부재)
- 🟢 **낮음**: 5개 (설정값 검증, Pydantic v2 방식, 환경 변수 로드 중복, cors_origins_list 빈 문자열, 타입 힌팅)

### 우선순위별 수정 권장
1. 🟡 **중간**: 필수 필드 검증 추가
2. 🟢 **낮음**: `cors_origins_list` 빈 문자열 필터링
3. 🟢 **낮음**: 설정값 검증 추가 (선택적)
4. 🟢 **낮음**: Pydantic v2 방식으로 업데이트 (선택적)
5. 🟢 **낮음**: 환경 변수 로드 중복 검토 (선택적)

---

## 🔧 수정 제안

### 수정 1: 필수 필드 검증 및 cors_origins_list 개선

```python
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
```

---

## ✅ 결론

`config/settings.py` 모듈은 전반적으로 잘 구현되어 있습니다. **필수 필드 검증 추가**와 **cors_origins_list 빈 문자열 필터링**을 권장합니다.

**우선순위**:
1. 🟡 **중간**: 필수 필드 검증 추가
2. 🟢 **낮음**: `cors_origins_list` 빈 문자열 필터링
3. 🟢 **낮음**: 설정값 검증 추가 (선택적)
4. 🟢 **낮음**: Pydantic v2 방식으로 업데이트 (선택적)
5. 🟢 **낮음**: 환경 변수 로드 중복 검토 (선택적)

