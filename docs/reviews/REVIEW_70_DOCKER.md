# Docker 검토 보고서

## 검토 대상
- Dockerfile
- docker-compose.yml
- 검토 일자: 2024년
- 검토 범위: 컨테이너 설정, 의존성, 환경변수, 볼륨 마운트

---

## ✅ 정상 동작 부분

### 1. Dockerfile 구조
- ✅ **Python 3.11-slim 기반**: 경량 베이스 이미지 사용
- ✅ **시스템 의존성 설치**: gcc, postgresql-client, MySQL 클라이언트 포함
- ✅ **의존성 캐싱**: `requirements.txt`를 먼저 복사하여 레이어 캐싱 활용
- ✅ **포트 노출**: 8000 포트 명시
- ✅ **작업 디렉토리 설정**: `/app`으로 명확히 지정

### 2. docker-compose.yml 구조
- ✅ **서비스 분리**: DB와 API 서비스 분리
- ✅ **PostgreSQL 설정**: postgres:15-alpine 이미지 사용
- ✅ **헬스체크**: DB 서비스에 헬스체크 설정
- ✅ **의존성 관리**: `depends_on`으로 DB 준비 후 API 시작
- ✅ **볼륨 마운트**: 데이터와 로그 디렉토리 마운트
- ✅ **네임드 볼륨**: PostgreSQL 데이터 영속성 보장

### 3. 환경 변수 관리
- ✅ **환경 변수 전달**: `${OPENAI_API_KEY}` 형식으로 호스트 환경 변수 사용
- ✅ **DATABASE_URL 설정**: docker-compose 내에서 명시적 설정

---

## ⚠️ 발견된 문제점

### 1. 🔴 **높음**: .dockerignore 파일 없음

**문제**: `.dockerignore` 파일이 없어 불필요한 파일이 Docker 이미지에 포함될 수 있습니다.

**영향도**: 높음  
**위험성**: 
- 이미지 크기 증가
- 빌드 시간 증가
- 민감한 정보 노출 가능 (.env, .git 등)
- 불필요한 파일 포함 (__pycache__, .pyc 등)

**수정 권장**: 
```dockerignore
# .dockerignore 파일 생성
# Git
.git
.gitignore
.gitattributes

# 환경 변수
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# 가상환경
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 테스트
.pytest_cache/
.coverage
htmlcov/
.tox/

# 로그
logs/
*.log

# 데이터 (빌드 시 불필요)
data/rag/
data/uploads/
data/vector_db/

# 문서
docs/
*.md
!README.md

# 스크립트 (선택적)
scripts/

# 기타
.DS_Store
*.bak
*.tmp
```

---

### 2. 🟡 **중간**: Dockerfile 최적화 부족

**문제**: Dockerfile이 최적화되지 않았습니다.

**영향도**: 중간  
**위험성**: 
- 이미지 크기 증가
- 빌드 시간 증가
- 레이어 캐싱 효율 저하

**현재 상황**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ...
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .  # 모든 파일 복사
```

**수정 권장**: 
```dockerfile
# 멀티스테이지 빌드 사용 (선택적)
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 런타임 스테이지
FROM python:3.11-slim

WORKDIR /app

# 런타임 시스템 의존성만 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 빌더 스테이지에서 Python 패키지 복사
COPY --from=builder /root/.local /root/.local

# PATH 업데이트
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs data/uploads data/vector_db

# 비root 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 3. 🟡 **중간**: docker-compose.yml 환경 변수 관리 부족

**문제**: 필수 환경 변수가 docker-compose.yml에 명시되지 않았습니다.

**영향도**: 중간  
**위험성**: 
- 환경 변수 누락으로 인한 런타임 에러
- 설정 불일치

**현재 상황**:
```yaml
environment:
  DATABASE_URL: postgresql://legal_user:legal_password@db:5432/legal_chatbot_db
  OPENAI_API_KEY: ${OPENAI_API_KEY}
```

**수정 권장**: 
```yaml
environment:
  # 데이터베이스
  DATABASE_URL: postgresql://legal_user:legal_password@db:5432/legal_chatbot_db
  
  # OpenAI
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4-turbo-preview}
  OPENAI_EMBEDDING_MODEL: ${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}
  
  # API
  API_SECRET_KEY: ${API_SECRET_KEY}
  API_HOST: ${API_HOST:-0.0.0.0}
  API_PORT: ${API_PORT:-8000}
  
  # 로깅
  LOG_LEVEL: ${LOG_LEVEL:-INFO}
  LOG_FILE_PATH: /app/logs/app.log
  
  # 환경
  ENVIRONMENT: ${ENVIRONMENT:-production}
  
  # RAG
  VECTOR_DB_TYPE: ${VECTOR_DB_TYPE:-chroma}
  VECTOR_DB_PATH: /app/data/vector_db
  EMBEDDING_MODEL: ${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}
  
  # 세션
  SESSION_EXPIRY_HOURS: ${SESSION_EXPIRY_HOURS:-24}
  
  # 파일 업로드
  UPLOAD_DIR: /app/data/uploads
  MAX_FILE_SIZE_MB: ${MAX_FILE_SIZE_MB:-10}
```

---

### 4. 🟡 **중간**: 보안 설정 부족

**문제**: 하드코딩된 비밀번호와 보안 설정이 부족합니다.

**영향도**: 중간  
**위험성**: 
- 비밀번호 노출
- root 권한으로 실행
- 민감한 정보 노출

**현재 상황**:
- `docker-compose.yml`에 비밀번호 하드코딩
- Dockerfile에서 root 사용자로 실행

**수정 권장**: 
1. **비밀번호를 환경 변수로 관리**:
```yaml
# docker-compose.yml
services:
  db:
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-legal_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-legal_password}
      POSTGRES_DB: ${POSTGRES_DB:-legal_chatbot_db}
  
  api:
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-legal_user}:${POSTGRES_PASSWORD:-legal_password}@db:5432/${POSTGRES_DB:-legal_chatbot_db}
```

2. **비root 사용자로 실행** (Dockerfile에 추가):
```dockerfile
# 비root 사용자 생성
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

3. **.env.example 파일 생성**:
```bash
# .env.example
POSTGRES_USER=legal_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=legal_chatbot_db
OPENAI_API_KEY=your_openai_api_key_here
API_SECRET_KEY=your_api_secret_key_here
```

---

### 5. 🟢 **낮음**: 헬스체크 설정 부족

**문제**: API 서비스에 헬스체크가 설정되어 있지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```yaml
# docker-compose.yml
services:
  api:
    # ... 기존 설정 ...
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      start_period: 40s
      retries: 3
```

또는 curl 사용:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  start_period: 40s
  retries: 3
```

---

### 6. 🟢 **낮음**: 리소스 제한 없음

**문제**: 컨테이너에 리소스 제한이 설정되어 있지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```yaml
# docker-compose.yml
services:
  api:
    # ... 기존 설정 ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  db:
    # ... 기존 설정 ...
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
```

---

### 7. 🟢 **낮음**: 재시작 정책 없음

**문제**: 컨테이너 재시작 정책이 설정되어 있지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```yaml
# docker-compose.yml
services:
  api:
    # ... 기존 설정 ...
    restart: unless-stopped
  
  db:
    # ... 기존 설정 ...
    restart: unless-stopped
```

---

### 8. 🟢 **낮음**: 네트워크 설정 명시 없음

**문제**: 명시적인 네트워크 설정이 없습니다.

**영향도**: 낮음  
**수정 권장**: 
```yaml
# docker-compose.yml
networks:
  legal_chatbot_network:
    driver: bridge

services:
  db:
    # ... 기존 설정 ...
    networks:
      - legal_chatbot_network
  
  api:
    # ... 기존 설정 ...
    networks:
      - legal_chatbot_network
```

---

## 📊 검토 요약

### Docker 설정 현황
- **Dockerfile**: 기본 구조 존재, 최적화 필요
- **docker-compose.yml**: 기본 설정 존재, 환경 변수 및 보안 강화 필요
- **.dockerignore**: 없음 (생성 필요)

### 발견된 문제
- 🔴 **높음**: 1개 (.dockerignore 파일 없음)
- 🟡 **중간**: 3개 (Dockerfile 최적화, 환경 변수 관리, 보안 설정)
- 🟢 **낮음**: 4개 (헬스체크, 리소스 제한, 재시작 정책, 네트워크 설정)

### 우선순위별 수정 권장
1. 🔴 **높음**: .dockerignore 파일 생성 (권장)
2. 🟡 **중간**: Dockerfile 최적화 (권장)
3. 🟡 **중간**: docker-compose.yml 환경 변수 관리 개선 (권장)
4. 🟡 **중간**: 보안 설정 강화 (권장)
5. 🟢 **낮음**: 헬스체크, 리소스 제한, 재시작 정책, 네트워크 설정 (선택적)

---

## 🔧 수정 제안

### 수정 1: .dockerignore 파일 생성

#### `.dockerignore` 생성
```dockerignore
# Git
.git
.gitignore
.gitattributes

# 환경 변수
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# 가상환경
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 테스트
.pytest_cache/
.coverage
htmlcov/
.tox/
tests/

# 로그
logs/
*.log

# 데이터 (빌드 시 불필요, 런타임에 볼륨으로 마운트)
data/rag/
data/uploads/
data/vector_db/

# 문서
docs/
*.md
!README.md

# 스크립트 (선택적)
scripts/

# 기타
.DS_Store
*.bak
*.tmp
```

---

### 수정 2: Dockerfile 최적화

#### `Dockerfile` 개선
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (레이어 캐싱 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p logs data/uploads data/vector_db

# 비root 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 수정 3: docker-compose.yml 개선

#### `docker-compose.yml` 개선
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: legal_chatbot_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-legal_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-legal_password}
      POSTGRES_DB: ${POSTGRES_DB:-legal_chatbot_db}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-legal_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - legal_chatbot_network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: legal_chatbot_api
    ports:
      - "${API_PORT:-8000}:8000"
    environment:
      # 데이터베이스
      DATABASE_URL: postgresql://${POSTGRES_USER:-legal_user}:${POSTGRES_PASSWORD:-legal_password}@db:5432/${POSTGRES_DB:-legal_chatbot_db}
      
      # OpenAI
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4-turbo-preview}
      OPENAI_EMBEDDING_MODEL: ${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}
      
      # API
      API_SECRET_KEY: ${API_SECRET_KEY}
      API_HOST: ${API_HOST:-0.0.0.0}
      API_PORT: ${API_PORT:-8000}
      
      # 로깅
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      LOG_FILE_PATH: /app/logs/app.log
      
      # 환경
      ENVIRONMENT: ${ENVIRONMENT:-production}
      
      # RAG
      VECTOR_DB_TYPE: ${VECTOR_DB_TYPE:-chroma}
      VECTOR_DB_PATH: /app/data/vector_db
      EMBEDDING_MODEL: ${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}
      
      # 세션
      SESSION_EXPIRY_HOURS: ${SESSION_EXPIRY_HOURS:-24}
      
      # 파일 업로드
      UPLOAD_DIR: /app/data/uploads
      MAX_FILE_SIZE_MB: ${MAX_FILE_SIZE_MB:-10}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - legal_chatbot_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      start_period: 40s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_data:
    driver: local

networks:
  legal_chatbot_network:
    driver: bridge
```

---

### 수정 4: .env.example 파일 생성

#### `.env.example` 생성
```bash
# PostgreSQL Database
POSTGRES_USER=legal_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=legal_chatbot_db
POSTGRES_PORT=5432

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# API
API_SECRET_KEY=your_api_secret_key_here
API_PORT=8000

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=production

# RAG
VECTOR_DB_TYPE=chroma
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Session
SESSION_EXPIRY_HOURS=24

# File Upload
MAX_FILE_SIZE_MB=10
```

---

## 📋 Docker 사용 가이드

### 빌드 및 실행
```bash
# 이미지 빌드
docker-compose build

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 서비스 중지
docker-compose down

# 볼륨 포함 삭제
docker-compose down -v
```

### 개발 환경
```bash
# 개발 모드로 실행 (코드 변경 시 자동 재시작)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 프로덕션 환경
```bash
# 프로덕션 모드로 실행
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## ✅ 결론

Docker 설정은 기본적으로 잘 구성되어 있지만, **.dockerignore 파일 생성**, **Dockerfile 최적화**, **환경 변수 관리**, **보안 설정** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🔴 **높음**: .dockerignore 파일 생성 (권장)
2. 🟡 **중간**: Dockerfile 최적화 (권장)
3. 🟡 **중간**: docker-compose.yml 환경 변수 관리 개선 (권장)
4. 🟡 **중간**: 보안 설정 강화 (권장)
5. 🟢 **낮음**: 헬스체크, 리소스 제한, 재시작 정책, 네트워크 설정 (선택적)

**참고**: 
- Dockerfile과 docker-compose.yml이 기본적으로 잘 구성되어 있음
- PostgreSQL과 API 서비스가 적절히 분리되어 있음
- 헬스체크와 의존성 관리가 설정되어 있음
- 볼륨 마운트가 적절히 구성되어 있음

