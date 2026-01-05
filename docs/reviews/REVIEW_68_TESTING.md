# 테스트 검토 보고서

## 검토 대상
- 테스트 디렉토리: `tests/`
- 검토 일자: 2024년
- 검토 범위: 단위 테스트, 통합 테스트, 테스트 커버리지, 모킹 전략

---

## ✅ 정상 동작 부분

### 1. 테스트 구조
- ✅ **단위 테스트와 통합 테스트 분리**: `tests/unit/`, `tests/integration/` 디렉토리 구조
- ✅ **테스트 파일 명명 규칙**: `test_*.py` 패턴 준수
- ✅ **conftest.py 존재**: 공통 픽스처 정의 (`client`, `sample_session_id`)
- ✅ **fixtures 디렉토리**: 테스트 픽스처 모듈화 준비

### 2. 테스트 도구 및 설정
- ✅ **pytest 사용**: 표준 Python 테스트 프레임워크
- ✅ **pytest-asyncio**: 비동기 테스트 지원
- ✅ **pytest-cov**: 커버리지 측정 도구
- ✅ **pyproject.toml 설정**: pytest 및 coverage 설정 포함

### 3. 단위 테스트
- ✅ **test_utils.py**: 유틸리티 함수 테스트 (6개 테스트)
  - 세션 ID 생성, UUID 생성, 텍스트 정규화, 개인정보 마스킹, 날짜 파싱/포맷팅
- ✅ **test_exceptions.py**: 예외 클래스 테스트 (5개 테스트)
  - 모든 커스텀 예외 클래스 테스트
- ✅ **test_response.py**: 응답 포맷 함수 테스트 (3개 테스트)
  - 성공/에러 응답 포맷 검증

### 4. 통합 테스트
- ✅ **test_chat_flow.py**: 채팅 플로우 테스트 (5개 테스트)
  - 세션 시작, 메시지 처리, 상태 조회, 유효하지 않은 세션, 상담 종료
- ✅ **test_rag_search.py**: RAG 검색 테스트 (2개 테스트)
  - 지식 타입별 검색, 필터 검색
- ✅ **test_langgraph_nodes.py**: LangGraph 노드 테스트 (4개 테스트)
  - INIT, CASE_CLASSIFICATION, VALIDATION 노드 테스트
- ✅ **test_db_connection.py**: DB 연결 및 테이블 확인 테스트
  - 상세한 DB 상태 확인 유틸리티

### 5. 모킹 가이드
- ✅ **TEST_MOCKING_GUIDE.md**: 모킹 전략 문서화
  - DB 모킹, GPT API 모킹, RAG 검색 모킹 예제 포함

---

## ⚠️ 발견된 문제점

### 1. 🔴 **높음**: 테스트 커버리지 목표 미설정

**문제**: `pyproject.toml`에 커버리지 목표(`fail-under`)가 설정되어 있지 않습니다.

**영향도**: 높음  
**위험성**: 
- 테스트 커버리지가 낮아도 CI/CD가 통과할 수 있음
- 코드 품질 저하 가능

**현재 상황**:
```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    # ...
]
# fail-under 설정 없음
```

**수정 권장**: 
```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
fail_under = 60  # 최소 60% 커버리지 목표
```

또는 `pytest.ini` 또는 `pyproject.toml`의 `[tool.pytest.ini_options]`에 추가:
```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=60",
]
```

---

### 2. 🟡 **중간**: pytest 마커 미설정

**문제**: `pyproject.toml`에 pytest 마커(`markers`)가 정의되어 있지 않습니다.

**영향도**: 중간  
**위험성**: 
- 테스트를 유형별로 분리 실행하기 어려움
- 통합 테스트와 단위 테스트 구분 불가

**현재 상황**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
# markers 설정 없음
```

**수정 권장**: 
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: 단위 테스트",
    "integration: 통합 테스트 (실제 DB/API 사용)",
    "slow: 느린 테스트",
    "requires_api: API 키가 필요한 테스트",
    "requires_db: DB 연결이 필요한 테스트",
]
```

**테스트 파일에 마커 추가**:
```python
# tests/unit/test_utils.py
import pytest

@pytest.mark.unit
def test_generate_session_id():
    # ...

# tests/integration/test_chat_flow.py
import pytest

@pytest.mark.integration
@pytest.mark.requires_db
def test_chat_start():
    # ...
```

---

### 3. 🟡 **중간**: 통합 테스트가 실제 DB/API에 의존

**문제**: 통합 테스트가 실제 데이터베이스와 GPT API에 의존합니다.

**영향도**: 중간  
**위험성**: 
- 테스트 실행 시 실제 리소스 사용
- 테스트 환경 의존성으로 인한 불안정성
- CI/CD 환경에서 테스트 실패 가능

**현재 상황**:
- `test_chat_flow.py`: 실제 DB 세션 생성/삭제
- `test_langgraph_nodes.py`: 실제 GPT API 호출 가능
- `test_rag_search.py`: 실제 RAG 검색 수행

**수정 권장**: 
1. **모킹 활용**: `TEST_MOCKING_GUIDE.md`의 가이드에 따라 모킹 적용
2. **테스트 전용 DB**: SQLite 인메모리 DB 또는 테스트 전용 PostgreSQL 사용
3. **환경 변수 분리**: 테스트 환경과 프로덕션 환경 분리

**예제**:
```python
# tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from src.db.connection import db_manager

@pytest.fixture
def mock_db_session():
    """모킹된 DB 세션 픽스처"""
    with patch('src.db.connection.db_manager.get_db_session') as mock:
        session = MagicMock()
        mock.return_value.__enter__.return_value = session
        mock.return_value.__exit__.return_value = None
        yield session

@pytest.fixture
def mock_gpt_client():
    """모킹된 GPT 클라이언트 픽스처"""
    with patch('src.services.gpt_client.gpt_client.chat_completion') as mock:
        mock.return_value = {
            "content": '{"main_case_type": "민사", "sub_case_type": "계약"}',
            "usage": {"total_tokens": 100}
        }
        yield mock
```

---

### 4. 🟡 **중간**: 테스트 커버리지가 낮음

**문제**: 주요 서비스 로직, DB 모델, 에러 시나리오에 대한 테스트가 부족합니다.

**영향도**: 중간  
**위험성**: 
- 버그 발견 어려움
- 리팩토링 시 회귀 버그 가능성
- 코드 신뢰성 저하

**현재 상황**:
- ✅ 유틸리티 함수 테스트: 있음
- ✅ 예외 클래스 테스트: 있음
- ✅ 응답 포맷 테스트: 있음
- ❌ 서비스 로직 테스트: 부족
  - `services/gpt_client.py`: 테스트 없음
  - `services/entity_extractor.py`: 테스트 없음
  - `services/session_manager.py`: 테스트 없음
  - `services/summarizer.py`: 테스트 없음
- ❌ DB 모델 테스트: 없음
  - 모델 생성, 관계, 제약조건 테스트 없음
- ❌ 에러 시나리오 테스트: 부족
  - 예외 처리, 경계값 테스트 부족

**수정 권장**: 
1. **서비스 로직 테스트 추가**:
   ```python
   # tests/unit/test_gpt_client.py
   import pytest
   from unittest.mock import patch, MagicMock
   from src.services.gpt_client import gpt_client
   
   @pytest.mark.unit
   def test_chat_completion_success():
       # 성공 케이스 테스트
       pass
   
   @pytest.mark.unit
   def test_chat_completion_retry():
       # 재시도 로직 테스트
       pass
   
   @pytest.mark.unit
   def test_chat_completion_error():
       # 에러 처리 테스트
       pass
   ```

2. **DB 모델 테스트 추가**:
   ```python
   # tests/unit/test_models.py
   import pytest
   from src.db.models.chat_session import ChatSession
   from src.utils.helpers import get_kst_now
   
   @pytest.mark.unit
   def test_chat_session_creation():
       """ChatSession 생성 테스트"""
       session = ChatSession(
           session_id="sess_test_123",
           channel="web",
           current_state="INIT",
           status="ACTIVE"
       )
       assert session.session_id == "sess_test_123"
       assert session.channel == "web"
   
   @pytest.mark.unit
   def test_chat_session_defaults():
       """ChatSession 기본값 테스트"""
       session = ChatSession(session_id="sess_test_123")
       assert session.status == "ACTIVE"
       assert session.completion_rate == 0
   ```

3. **에러 시나리오 테스트 추가**:
   ```python
   # tests/unit/test_entity_extractor.py
   import pytest
   from src.services.entity_extractor import entity_extractor
   
   @pytest.mark.unit
   def test_extract_date_invalid_format():
       """잘못된 날짜 형식 테스트"""
       result = entity_extractor.extract_date("잘못된 형식")
       assert result is None
   
   @pytest.mark.unit
   def test_extract_amount_negative():
       """음수 금액 테스트"""
       result = entity_extractor.extract_amount("-100만원")
       # 음수 처리 로직 확인
       pass
   ```

---

### 5. 🟢 **낮음**: fixtures 디렉토리 비어있음

**문제**: `tests/fixtures/` 디렉토리가 비어있습니다.

**영향도**: 낮음  
**수정 권장**: 
- 공통 픽스처를 `tests/fixtures/`에 모듈화
- 예: `db_fixtures.py`, `gpt_fixtures.py`, `rag_fixtures.py`

---

### 6. 🟢 **낮음**: 테스트 실행 스크립트 없음

**문제**: 테스트 실행을 위한 스크립트나 Makefile이 없습니다.

**영향도**: 낮음  
**수정 권장**: 
```makefile
# Makefile
.PHONY: test test-unit test-integration test-cov

test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-cov-fail:
	pytest --cov=src --cov-report=html --cov-fail-under=60
```

또는 `scripts/run_tests.py`:
```python
#!/usr/bin/env python3
"""테스트 실행 스크립트"""
import subprocess
import sys

def run_tests(test_type="all"):
    """테스트 실행"""
    if test_type == "unit":
        cmd = ["pytest", "-m", "unit", "-v"]
    elif test_type == "integration":
        cmd = ["pytest", "-m", "integration", "-v"]
    elif test_type == "cov":
        cmd = ["pytest", "--cov=src", "--cov-report=html", "--cov-report=term-missing"]
    else:
        cmd = ["pytest", "-v"]
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_tests(test_type)
```

---

### 7. 🟢 **낮음**: CI/CD 파이프라인 없음

**문제**: GitHub Actions 또는 다른 CI/CD 파이프라인이 설정되어 있지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_USER: test_user
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run unit tests
      run: |
        pytest -m unit --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 📊 검토 요약

### 테스트 현황
- **단위 테스트**: 3개 파일, 약 14개 테스트
- **통합 테스트**: 4개 파일, 약 11개 테스트
- **총 테스트**: 약 25개 테스트
- **테스트 커버리지**: 측정되지 않음 (목표 미설정)

### 발견된 문제
- 🔴 **높음**: 1개 (커버리지 목표 미설정)
- 🟡 **중간**: 3개 (pytest 마커, 실제 DB/API 의존, 낮은 커버리지)
- 🟢 **낮음**: 3개 (fixtures 비어있음, 테스트 스크립트 없음, CI/CD 없음)

### 우선순위별 수정 권장
1. 🔴 **높음**: 테스트 커버리지 목표 설정 (권장)
2. 🟡 **중간**: pytest 마커 설정 및 테스트 분류 (권장)
3. 🟡 **중간**: 통합 테스트 모킹 적용 (권장)
4. 🟡 **중간**: 주요 서비스 로직 테스트 추가 (권장)
5. 🟢 **낮음**: fixtures 모듈화 (선택적)
6. 🟢 **낮음**: 테스트 실행 스크립트 추가 (선택적)
7. 🟢 **낮음**: CI/CD 파이프라인 설정 (선택적)

---

## 🔧 수정 제안

### 수정 1: pytest 마커 및 커버리지 목표 설정

#### `pyproject.toml` 수정
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: 단위 테스트",
    "integration: 통합 테스트 (실제 DB/API 사용)",
    "slow: 느린 테스트",
    "requires_api: API 키가 필요한 테스트",
    "requires_db: DB 연결이 필요한 테스트",
]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=60",
    "-v",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
fail_under = 60
```

---

### 수정 2: 통합 테스트 모킹 적용

#### `tests/conftest.py` 확장
```python
"""
Pytest 설정 및 픽스처
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.db.connection import db_manager


@pytest.fixture
def client():
    """테스트 클라이언트 픽스처"""
    return TestClient(app)


@pytest.fixture
def sample_session_id():
    """샘플 세션 ID 픽스처"""
    return "sess_test_12345"


@pytest.fixture
def mock_db_session():
    """모킹된 DB 세션 픽스처"""
    with patch('src.db.connection.db_manager.get_db_session') as mock:
        session = MagicMock()
        mock.return_value.__enter__.return_value = session
        mock.return_value.__exit__.return_value = None
        yield session


@pytest.fixture
def mock_gpt_client():
    """모킹된 GPT 클라이언트 픽스처"""
    with patch('src.services.gpt_client.gpt_client.chat_completion') as mock:
        mock.return_value = {
            "content": '{"main_case_type": "민사", "sub_case_type": "계약"}',
            "usage": {"total_tokens": 100}
        }
        yield mock


@pytest.fixture
def mock_rag_searcher():
    """모킹된 RAG 검색 픽스처"""
    with patch('src.rag.searcher.rag_searcher.search') as mock:
        mock.return_value = [
            {
                "content": "검색 결과 내용",
                "metadata": {"knowledge_type": "K2"}
            }
        ]
        yield mock
```

---

### 수정 3: 테스트 마커 추가

#### `tests/unit/test_utils.py` 수정
```python
"""
유틸리티 함수 단위 테스트
"""
import pytest
from datetime import datetime
from src.utils import helpers


@pytest.mark.unit
def test_generate_session_id():
    """세션 ID 생성 테스트"""
    session_id = helpers.generate_session_id()
    assert session_id.startswith("sess_")
    assert len(session_id) > 10

# ... (나머지 테스트에도 @pytest.mark.unit 추가)
```

#### `tests/integration/test_chat_flow.py` 수정
```python
"""
채팅 플로우 통합 테스트
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.requires_db
def test_chat_start():
    """상담 시작 테스트"""
    response = client.post(
        "/chat/start",
        json={"channel": "web"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "session_id" in data["data"]

# ... (나머지 테스트에도 마커 추가)
```

---

### 수정 4: 서비스 로직 테스트 추가

#### `tests/unit/test_gpt_client.py` 생성
```python
"""
GPT Client 단위 테스트
"""
import pytest
from unittest.mock import patch, MagicMock
from src.services.gpt_client import gpt_client
from src.utils.exceptions import GPTAPIError


@pytest.mark.unit
@patch('openai.OpenAI')
def test_chat_completion_success(mock_openai):
    """GPT API 성공 케이스 테스트"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "success"}'
    mock_response.usage.total_tokens = 100
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    result = gpt_client.chat_completion(
        messages=[{"role": "user", "content": "test"}]
    )
    
    assert result["content"] == '{"result": "success"}'
    assert result["usage"]["total_tokens"] == 100


@pytest.mark.unit
@patch('openai.OpenAI')
def test_chat_completion_error(mock_openai):
    """GPT API 에러 케이스 테스트"""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mock_openai.return_value = mock_client
    
    with pytest.raises(GPTAPIError):
        gpt_client.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
```

---

## 📋 테스트 실행 가이드

### 기본 테스트 실행
```bash
# 모든 테스트 실행
pytest

# 단위 테스트만 실행
pytest -m unit

# 통합 테스트만 실행
pytest -m integration

# 커버리지 포함 실행
pytest --cov=src --cov-report=html

# 커버리지 목표 포함 실행 (60% 미만 시 실패)
pytest --cov=src --cov-fail-under=60
```

### 특정 테스트 실행
```bash
# 특정 파일 실행
pytest tests/unit/test_utils.py

# 특정 테스트 함수 실행
pytest tests/unit/test_utils.py::test_generate_session_id

# 패턴 매칭
pytest -k "test_generate"
```

---

## ✅ 결론

테스트 구조는 잘 구성되어 있지만, **테스트 커버리지 목표 설정**, **pytest 마커 설정**, **모킹 전략 적용**, **주요 서비스 로직 테스트 추가**가 필요합니다.

**우선순위**:
1. 🔴 **높음**: 테스트 커버리지 목표 설정 (권장)
2. 🟡 **중간**: pytest 마커 설정 및 테스트 분류 (권장)
3. 🟡 **중간**: 통합 테스트 모킹 적용 (권장)
4. 🟡 **중간**: 주요 서비스 로직 테스트 추가 (권장)
5. 🟢 **낮음**: fixtures 모듈화, 테스트 스크립트, CI/CD (선택적)

**참고**: 
- 테스트 구조가 잘 분리되어 있음 (unit/integration)
- 모킹 가이드 문서가 존재함
- pytest 및 coverage 설정이 기본적으로 구성되어 있음
- 테스트 실행 환경이 준비되어 있음

