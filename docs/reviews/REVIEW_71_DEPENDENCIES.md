# 의존성 검토 보고서

## 검토 대상
- requirements.txt
- pyproject.toml
- 검토 일자: 2024년
- 검토 범위: 패키지 버전, 호환성, 보안 취약점

---

## ✅ 정상 동작 부분

### 1. requirements.txt 구조
- ✅ **의존성 분류**: Core, LangGraph, Database, Vector DB 등으로 명확히 분류
- ✅ **버전 범위 지정**: `>=` 연산자로 최소 버전 명시
- ✅ **주요 패키지 포함**: FastAPI, LangGraph, OpenAI, SQLAlchemy, ChromaDB 등

### 2. pyproject.toml 구조
- ✅ **프로젝트 메타데이터**: 이름, 버전, 설명 등 명시
- ✅ **Python 버전 요구사항**: `>=3.10` 명시
- ✅ **개발 의존성 분리**: `[project.optional-dependencies]`에 dev 의존성 분리
- ✅ **도구 설정**: black, mypy, pytest 설정 포함

### 3. 핵심 의존성
- ✅ **FastAPI**: `>=0.104.0` (최신 버전)
- ✅ **Pydantic**: `>=2.0.0` (v2 사용)
- ✅ **SQLAlchemy**: `>=2.0.0` (v2 사용)
- ✅ **LangGraph**: `>=0.0.40`
- ✅ **OpenAI**: `>=1.0.0`

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: PostgreSQL 드라이버 누락

**문제**: `requirements.txt`에 PostgreSQL 드라이버(`psycopg2` 또는 `psycopg2-binary`)가 없습니다.

**영향도**: 중간  
**위험성**: 
- PostgreSQL을 사용하는 경우 런타임 에러 발생
- `docker-compose.yml`에서 PostgreSQL을 사용하지만 의존성 누락

**현재 상황**:
- `requirements.txt`에 `pymysql>=1.1.0`만 있음
- PostgreSQL 드라이버 없음

**수정 권장**: 
```txt
# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
pymysql>=1.1.0
psycopg2-binary>=2.9.9  # PostgreSQL 드라이버 추가
cryptography>=41.0.0
```

또는 환경별로 분리:
```txt
# Database (공통)
sqlalchemy>=2.0.0
alembic>=1.12.0
cryptography>=41.0.0

# Database Drivers (선택적)
# MySQL
pymysql>=1.1.0

# PostgreSQL (프로덕션에서 사용)
# psycopg2-binary>=2.9.9
```

---

### 2. 🟡 **중간**: structlog 사용 여부 불명확

**문제**: `requirements.txt`에 `structlog>=23.2.0`이 있지만, 실제 코드에서 사용되는지 확인이 필요합니다.

**영향도**: 중간  
**위험성**: 
- 사용하지 않는 의존성 포함으로 이미지 크기 증가
- 또는 사용하는데 import가 누락된 경우

**확인 필요**: 
- `src/utils/logger.py`에서 `structlog` 사용 여부 확인
- 사용하지 않으면 제거, 사용하면 import 추가

**수정 권장**: 
```python
# src/utils/logger.py 확인 후
# 사용하지 않으면 requirements.txt에서 제거
# 사용하면 import 추가
```

---

### 3. 🟡 **중간**: slowapi 사용 여부 불명확

**문제**: `requirements.txt`에 `slowapi>=0.1.9`가 있지만, 실제 코드에서 사용되는지 확인이 필요합니다.

**영향도**: 중간  
**위험성**: 
- 사용하지 않는 의존성 포함
- 또는 사용하는데 설정이 누락된 경우

**확인 필요**: 
- `src/api/main.py` 또는 미들웨어에서 rate limiting 사용 여부 확인

---

### 4. 🟢 **낮음**: 버전 범위가 넓음

**문제**: 일부 패키지의 버전 범위가 너무 넓어 호환성 문제가 발생할 수 있습니다.

**영향도**: 낮음  
**위험성**: 
- 최신 버전에서 breaking change 발생 가능
- 재현 가능한 빌드 어려움

**현재 상황**:
```txt
fastapi>=0.104.0  # 최신 버전까지 허용
langgraph>=0.0.40  # 매우 넓은 범위
```

**수정 권장**: 
```txt
# 상한선 추가 (선택적)
fastapi>=0.104.0,<0.110.0
langgraph>=0.0.40,<0.1.0
```

또는 `requirements-lock.txt` 생성:
```bash
pip freeze > requirements-lock.txt
```

---

### 5. 🟢 **낮음**: 보안 취약점 스캔 도구 없음

**문제**: 보안 취약점을 자동으로 스캔하는 도구나 프로세스가 없습니다.

**영향도**: 낮음  
**수정 권장**: 
```bash
# safety 사용
pip install safety
safety check -r requirements.txt

# 또는 pip-audit 사용
pip install pip-audit
pip-audit -r requirements.txt
```

**CI/CD에 추가**:
```yaml
# .github/workflows/security.yml
- name: Check for security vulnerabilities
  run: |
    pip install safety
    safety check -r requirements.txt
```

---

### 6. 🟢 **낮음**: pyproject.toml과 requirements.txt 불일치

**문제**: `pyproject.toml`의 `[project.optional-dependencies]`에 있는 패키지가 `requirements.txt`에도 있습니다.

**영향도**: 낮음  
**위험성**: 
- 의존성 관리 일관성 부족
- 두 파일 간 동기화 필요

**현재 상황**:
- `requirements.txt`: 모든 의존성 포함
- `pyproject.toml`: dev 의존성만 분리

**수정 권장**: 
1. **옵션 1**: `requirements.txt`를 `pyproject.toml`에서 생성
   ```bash
   pip-compile pyproject.toml
   ```

2. **옵션 2**: `requirements.txt`를 메인으로 사용하고 `pyproject.toml`은 프로젝트 메타데이터만 관리

3. **옵션 3**: `requirements.txt`를 `requirements-dev.txt`로 분리
   ```txt
   # requirements.txt (프로덕션)
   fastapi>=0.104.0
   # ...
   
   # requirements-dev.txt (개발)
   -r requirements.txt
   pytest>=7.4.0
   black>=23.0.0
   # ...
   ```

---

### 7. 🟢 **낮음**: 의존성 그룹화 부족

**문제**: 프로덕션과 개발 의존성이 명확히 구분되지 않았습니다.

**영향도**: 낮음  
**수정 권장**: 
```txt
# requirements.txt
# ============================================================================
# 프로덕션 의존성
# ============================================================================

# Core Dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# ... (프로덕션 의존성만)

# ============================================================================
# 개발 의존성 (requirements-dev.txt로 분리 권장)
# ============================================================================
# Testing
# pytest>=7.4.0
# pytest-asyncio>=0.21.0
# pytest-cov>=4.1.0

# Code Quality
# black>=23.0.0
# flake8>=6.0.0
# mypy>=1.6.0
```

---

## 📊 검토 요약

### 의존성 현황
- **총 패키지 수**: 약 20개 (requirements.txt)
- **핵심 의존성**: FastAPI, LangGraph, OpenAI, SQLAlchemy, ChromaDB
- **개발 의존성**: pytest, black, flake8, mypy

### 발견된 문제
- 🟡 **중간**: 3개 (PostgreSQL 드라이버 누락, structlog/slowapi 사용 여부 불명확)
- 🟢 **낮음**: 4개 (버전 범위, 보안 스캔, 파일 불일치, 그룹화)

### 우선순위별 수정 권장
1. 🟡 **중간**: PostgreSQL 드라이버 추가 (권장)
2. 🟡 **중간**: structlog/slowapi 사용 여부 확인 및 정리 (권장)
3. 🟢 **낮음**: 보안 취약점 스캔 도구 추가 (선택적)
4. 🟢 **낮음**: requirements.txt 구조 개선 (선택적)

---

## 🔧 수정 제안

### 수정 1: PostgreSQL 드라이버 추가

#### `requirements.txt` 수정
```txt
# Core Dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# LangGraph & LangChain
langgraph>=0.0.40
langchain>=0.1.0
langchain-openai>=0.0.2

# OpenAI
openai>=1.0.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
pymysql>=1.1.0
psycopg2-binary>=2.9.9  # PostgreSQL 드라이버 추가
cryptography>=41.0.0

# Vector DB (ChromaDB)
chromadb>=0.4.0

# Embeddings
sentence-transformers>=2.2.0

# Utilities
python-dotenv>=1.0.0
python-multipart>=0.0.6
httpx>=0.25.0
pandas>=2.0.0
openpyxl>=3.1.0
pyyaml>=6.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Code Quality
black>=23.0.0
flake8>=6.0.0
mypy>=1.6.0

# Logging
structlog>=23.2.0  # 사용 여부 확인 후 유지/제거

# Rate Limiting
slowapi>=0.1.9  # 사용 여부 확인 후 유지/제거
```

---

### 수정 2: requirements.txt 구조 개선

#### `requirements.txt` (프로덕션)
```txt
# ============================================================================
# 프로덕션 의존성
# ============================================================================

# Core Dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# LangGraph & LangChain
langgraph>=0.0.40
langchain>=0.1.0
langchain-openai>=0.0.2

# OpenAI
openai>=1.0.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
pymysql>=1.1.0
psycopg2-binary>=2.9.9
cryptography>=41.0.0

# Vector DB (ChromaDB)
chromadb>=0.4.0

# Embeddings
sentence-transformers>=2.2.0

# Utilities
python-dotenv>=1.0.0
python-multipart>=0.0.6
httpx>=0.25.0
pandas>=2.0.0
openpyxl>=3.1.0
pyyaml>=6.0.0

# Logging (사용 여부 확인 필요)
# structlog>=23.2.0

# Rate Limiting (사용 여부 확인 필요)
# slowapi>=0.1.9
```

#### `requirements-dev.txt` 생성
```txt
# ============================================================================
# 개발 의존성
# ============================================================================

# 프로덕션 의존성 포함
-r requirements.txt

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Code Quality
black>=23.0.0
flake8>=6.0.0
mypy>=1.6.0

# Security Scanning
safety>=2.3.0
pip-audit>=2.6.0
```

---

### 수정 3: 보안 취약점 스캔 스크립트

#### `scripts/check_security.py` 생성
```python
"""
의존성 보안 취약점 스캔 스크립트
"""
import subprocess
import sys
from pathlib import Path

def check_security():
    """의존성 보안 취약점 확인"""
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ requirements.txt를 찾을 수 없습니다: {requirements_file}")
        return False
    
    print("=" * 60)
    print("의존성 보안 취약점 스캔")
    print("=" * 60)
    
    # safety 사용
    try:
        print("\n[1/2] safety로 스캔 중...")
        result = subprocess.run(
            ["safety", "check", "-r", str(requirements_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ safety: 취약점 없음")
        else:
            print("⚠️  safety: 취약점 발견")
            print(result.stdout)
            print(result.stderr)
    except FileNotFoundError:
        print("⚠️  safety가 설치되지 않았습니다. 설치: pip install safety")
    except Exception as e:
        print(f"❌ safety 실행 실패: {str(e)}")
    
    # pip-audit 사용
    try:
        print("\n[2/2] pip-audit로 스캔 중...")
        result = subprocess.run(
            ["pip-audit", "-r", str(requirements_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ pip-audit: 취약점 없음")
        else:
            print("⚠️  pip-audit: 취약점 발견")
            print(result.stdout)
            print(result.stderr)
    except FileNotFoundError:
        print("⚠️  pip-audit가 설치되지 않았습니다. 설치: pip install pip-audit")
    except Exception as e:
        print(f"❌ pip-audit 실행 실패: {str(e)}")
    
    print("\n" + "=" * 60)
    return True

if __name__ == "__main__":
    check_security()
```

---

### 수정 4: pyproject.toml 의존성 동기화

#### `pyproject.toml` 수정
```toml
[project]
name = "legal-chatbot-api"
version = "0.1.0"
description = "RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "langgraph>=0.0.40",
    "langchain>=0.1.0",
    "langchain-openai>=0.0.2",
    "openai>=1.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pymysql>=1.1.0",
    "psycopg2-binary>=2.9.9",
    "cryptography>=41.0.0",
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    "python-dotenv>=1.0.0",
    "python-multipart>=0.0.6",
    "httpx>=0.25.0",
    "pandas>=2.0.0",
    "openpyxl>=3.1.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.6.0",
    "safety>=2.3.0",
    "pip-audit>=2.6.0",
]
```

---

## 📋 의존성 관리 체크리스트

### 설치 전
- [ ] Python 버전 확인 (`>=3.10`)
- [ ] 가상환경 생성 및 활성화
- [ ] `.env` 파일 설정

### 설치
```bash
# 프로덕션
pip install -r requirements.txt

# 개발
pip install -r requirements-dev.txt
# 또는
pip install -e ".[dev]"
```

### 업데이트
```bash
# 패키지 업데이트 확인
pip list --outdated

# 보안 취약점 스캔
python scripts/check_security.py

# requirements.txt 업데이트
pip freeze > requirements-lock.txt
```

### 정기 점검
- [ ] 월 1회 보안 취약점 스캔
- [ ] 분기별 주요 패키지 업데이트 검토
- [ ] 사용하지 않는 의존성 제거

---

## ✅ 결론

의존성 관리는 전반적으로 잘 구성되어 있지만, **PostgreSQL 드라이버 누락**, **사용 여부 불명확한 패키지**, **보안 스캔 도구** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: PostgreSQL 드라이버 추가 (권장)
2. 🟡 **중간**: structlog/slowapi 사용 여부 확인 및 정리 (권장)
3. 🟢 **낮음**: 보안 취약점 스캔 도구 추가 (선택적)
4. 🟢 **낮음**: requirements.txt 구조 개선 (선택적)

**참고**: 
- requirements.txt가 명확히 분류되어 있음
- pyproject.toml이 프로젝트 메타데이터를 잘 관리하고 있음
- 주요 의존성이 적절히 포함되어 있음
- Python 버전 요구사항이 명시되어 있음

