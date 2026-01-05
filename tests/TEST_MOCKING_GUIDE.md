# 테스트 모킹 가이드

## 개요

이 문서는 통합 테스트에서 실제 DB/API 호출 대신 모킹을 사용하는 방법을 설명합니다.

## 모킹 전략

### 1. 데이터베이스 모킹

#### SQLAlchemy 세션 모킹

```python
from unittest.mock import MagicMock, patch
from src.db.connection import db_manager

@patch('src.db.connection.db_manager.get_db_session')
def test_with_mocked_db(mock_get_db_session):
    # 모킹된 세션 생성
    mock_session = MagicMock()
    mock_get_db_session.return_value.__enter__.return_value = mock_session
    mock_get_db_session.return_value.__exit__.return_value = None
    
    # 테스트 실행
    # ...
    
    # 검증
    mock_session.query.assert_called()
```

#### 컨텍스트 매니저 패턴

```python
from contextlib import contextmanager
from unittest.mock import MagicMock

@contextmanager
def mock_db_session():
    mock_session = MagicMock()
    yield mock_session

@patch('src.db.connection.db_manager.get_db_session', mock_db_session)
def test_example():
    # 테스트 코드
    pass
```

### 2. OpenAI API 모킹

#### GPT Client 모킹

```python
from unittest.mock import patch, MagicMock
from src.services.gpt_client import gpt_client

@patch.object(gpt_client, 'chat_completion')
def test_with_mocked_gpt(mock_chat_completion):
    # 모킹된 응답 설정
    mock_chat_completion.return_value = {
        "content": '{"main_case_type": "민사", "sub_case_type": "계약"}',
        "usage": {"total_tokens": 100}
    }
    
    # 테스트 실행
    result = some_function_using_gpt()
    
    # 검증
    mock_chat_completion.assert_called_once()
    assert result["main_case_type"] == "민사"
```

### 3. RAG 검색 모킹

```python
from unittest.mock import patch
from src.rag.searcher import rag_searcher

@patch.object(rag_searcher, 'search')
def test_with_mocked_rag(mock_search):
    # 모킹된 검색 결과
    mock_search.return_value = [
        {
            "content": "검색 결과 내용",
            "metadata": {"knowledge_type": "K2"}
        }
    ]
    
    # 테스트 실행
    result = some_function_using_rag()
    
    # 검증
    mock_search.assert_called_once()
```

### 4. 벡터 DB 모킹

```python
from unittest.mock import patch
from src.rag.vector_db import vector_db_manager

@patch.object(vector_db_manager, 'add_documents')
@patch.object(vector_db_manager, 'search')
def test_with_mocked_vector_db(mock_search, mock_add):
    # 모킹 설정
    mock_search.return_value = []
    mock_add.return_value = True
    
    # 테스트 실행
    # ...
```

## 모킹 라이브러리

### pytest-mock

```python
import pytest

def test_example(mocker):
    # mocker는 pytest-mock에서 제공하는 fixture
    mock_db = mocker.patch('src.db.connection.db_manager')
    mock_db.get_db_session.return_value.__enter__.return_value = MagicMock()
    
    # 테스트 실행
    # ...
```

### unittest.mock

```python
from unittest.mock import patch, MagicMock

class TestExample:
    @patch('src.services.gpt_client.gpt_client.chat_completion')
    def test_example(self, mock_gpt):
        mock_gpt.return_value = {"content": "test"}
        # 테스트 실행
        # ...
```

## 모범 사례

### 1. Fixture 사용 (pytest)

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_db_session():
    with patch('src.db.connection.db_manager.get_db_session') as mock:
        session = MagicMock()
        mock.return_value.__enter__.return_value = session
        mock.return_value.__exit__.return_value = None
        yield session

def test_example(mock_db_session):
    # mock_db_session을 사용하여 테스트
    # ...
```

### 2. 데코레이터 체이닝

```python
@patch('src.services.gpt_client.gpt_client')
@patch('src.db.connection.db_manager')
def test_integration(mock_db, mock_gpt):
    # 여러 의존성을 한 번에 모킹
    # ...
```

### 3. 모킹 데이터 재사용

```python
# conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def sample_gpt_response():
    return {
        "content": '{"main_case_type": "민사"}',
        "usage": {"total_tokens": 100}
    }

@pytest.fixture
def sample_rag_results():
    return [
        {
            "content": "검색 결과",
            "metadata": {"knowledge_type": "K2"}
        }
    ]
```

## 주의사항

1. **모킹 범위**: 실제 동작을 테스트할 부분과 모킹할 부분을 명확히 구분
2. **검증**: 모킹된 함수가 올바르게 호출되었는지 검증
3. **의존성**: 모킹 순서에 주의 (데코레이터는 아래에서 위로 적용)
4. **격리**: 각 테스트가 독립적으로 실행되도록 모킹 상태 초기화

## 예제 테스트

```python
import pytest
from unittest.mock import patch, MagicMock
from src.langgraph.nodes.case_classification_node import case_classification_node

@pytest.fixture
def mock_gpt_response():
    return {
        "content": '{"main_case_type": "민사", "sub_case_type": "계약"}',
        "usage": {"total_tokens": 100}
    }

@pytest.fixture
def mock_rag_results():
    return []

def test_case_classification(mock_gpt_response, mock_rag_results):
    with patch('src.services.gpt_client.gpt_client.chat_completion') as mock_gpt, \
         patch('src.rag.searcher.rag_searcher.search') as mock_rag:
        
        mock_gpt.return_value = mock_gpt_response
        mock_rag.return_value = mock_rag_results
        
        state = {
            "session_id": "test_session",
            "current_state": "INIT",
            "last_user_input": "계약 문제가 있습니다"
        }
        
        result = case_classification_node(state)
        
        assert result["case_type"] == "CIVIL"
        mock_gpt.assert_called_once()
```

