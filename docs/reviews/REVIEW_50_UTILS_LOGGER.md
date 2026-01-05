# Utils Logger 검토 보고서

## 검토 대상
- 파일: `src/utils/logger.py`
- 검토 일자: 2024년
- 검토 범위: 로깅 설정, 로거 생성, 구조화 로깅

---

## ✅ 정상 동작 부분

### 1. 모듈 구조 (Lines 1-11)
- ✅ 명확한 모듈 docstring
- ✅ 필요한 import 모두 포함
- ✅ `config.settings`에서 설정 로드

### 2. `setup_logging` 함수 (Lines 14-49)
- ✅ YAML 설정 파일 지원
- ✅ 로그 디렉토리 자동 생성
- ✅ 기본 로깅 설정 fallback
- ✅ UTF-8 인코딩 사용

### 3. `get_logger` 함수 (Lines 52-62)
- ✅ 간단하고 명확한 인터페이스
- ✅ 표준 `logging.getLogger` 사용

### 4. 데코레이터 함수들 (Lines 65-123)
- ✅ `log_execution_time`: 실행 시간 측정
- ✅ `log_function_call`: 함수 호출 로깅
- ✅ `functools.wraps` 사용으로 메타데이터 보존

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 에러 처리 부족

**문제**: `setup_logging` 함수에서 YAML 파일 로드나 설정 적용 시 예외 처리가 없습니다. 파일이 손상되었거나 잘못된 형식일 경우 예외가 발생할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 예외 처리 추가

**수정 예시**:
```python
def setup_logging(config_path: str = "config/logging.yaml") -> None:
    """
    로깅 설정 초기화
    
    Args:
        config_path: 로깅 설정 파일 경로
    """
    config_file = Path(config_path)
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
                # 로그 디렉토리 자동 생성
                if 'handlers' in config:
                    for handler_name, handler_config in config['handlers'].items():
                        if 'filename' in handler_config:
                            log_file = Path(handler_config['filename'])
                            log_dir = log_file.parent
                            if not log_dir.exists():
                                log_dir.mkdir(parents=True, exist_ok=True)
                
                logging.config.dictConfig(config)
        except (yaml.YAMLError, KeyError, ValueError) as e:
            # YAML 파싱 오류 또는 설정 오류 시 기본 설정 사용
            logging.warning(f"로깅 설정 파일 로드 실패 ({config_path}): {e}. 기본 설정을 사용합니다.")
            _setup_default_logging()
    else:
        _setup_default_logging()

def _setup_default_logging():
    """기본 로깅 설정"""
    log_dir = Path(settings.log_file_path).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename=settings.log_file_path
    )
```

---

### 2. 🟢 **낮음**: 구조화 로깅 미지원

**문제**: 현재 로깅은 단순 문자열 포맷만 지원합니다. 구조화 로깅(JSON 형식)을 지원하지 않아 로그 분석 도구와의 통합이 어렵습니다.

**영향도**: 낮음 (현재는 문제가 없지만, 향후 로그 분석 필요 시 개선)  
**수정 권장**: 선택적 구조화 로깅 지원 추가 (선택적)

**참고**: `structlog` 같은 라이브러리를 사용하면 구조화 로깅을 쉽게 구현할 수 있습니다.

---

### 3. 🟢 **낮음**: `log_execution_time` 데코레이터의 비동기 함수 미지원

**문제**: `log_execution_time` 데코레이터는 동기 함수만 지원합니다. `async def` 함수에 사용하면 제대로 작동하지 않습니다.

**영향도**: 낮음 (현재 비동기 함수에서 사용하지 않는다면 문제 없음)  
**수정 권장**: 비동기 함수 지원 추가 (선택적)

**수정 예시**:
```python
import asyncio
from typing import Callable, Any, Coroutine

def log_execution_time(logger: logging.Logger = None):
    """
    함수 실행 시간 측정 데코레이터 (동기/비동기 지원)
    
    Args:
        logger: 로거 인스턴스 (None이면 함수명으로 로거 생성)
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if logger is None:
                    log = get_logger(func.__module__)
                else:
                    log = logger
                
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    log.info(
                        f"{func.__name__} 실행 완료 - 실행 시간: {execution_time:.3f}초"
                    )
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    log.error(
                        f"{func.__name__} 실행 실패 - 실행 시간: {execution_time:.3f}초 - 오류: {str(e)}"
                    )
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # 기존 동기 함수 로직
                ...
            
            return wrapper
    return decorator
```

---

### 4. 🟢 **낮음**: 로그 레벨 검증 없음

**문제**: `setup_logging` 함수에서 `settings.log_level.upper()`를 사용하지만, 유효한 로그 레벨인지 검증하지 않습니다. 잘못된 값이 들어오면 `getattr`가 실패할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 로그 레벨 검증 추가

**수정 예시**:
```python
def _setup_default_logging():
    """기본 로깅 설정"""
    log_dir = Path(settings.log_file_path).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 로그 레벨 검증
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = settings.log_level.upper()
    if log_level not in valid_levels:
        logging.warning(f"잘못된 로그 레벨: {log_level}. INFO를 사용합니다.")
        log_level = 'INFO'
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename=settings.log_file_path
    )
```

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 4개 (에러 처리 부족, 구조화 로깅 미지원, 비동기 함수 미지원, 로그 레벨 검증 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 에러 처리 추가
2. 🟢 **낮음**: 로그 레벨 검증 추가
3. 🟢 **낮음**: 비동기 함수 지원 추가 (선택적)
4. 🟢 **낮음**: 구조화 로깅 지원 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: 에러 처리 및 로그 레벨 검증 추가

```python
"""
로깅 유틸리티 모듈
"""
import logging
import logging.config
import time
import functools
from pathlib import Path
from typing import Callable, Any
import yaml
from config.settings import settings


def _setup_default_logging():
    """기본 로깅 설정"""
    log_dir = Path(settings.log_file_path).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 로그 레벨 검증
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    log_level = settings.log_level.upper()
    if log_level not in valid_levels:
        logging.warning(f"잘못된 로그 레벨: {log_level}. INFO를 사용합니다.")
        log_level = 'INFO'
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename=settings.log_file_path
    )


def setup_logging(config_path: str = "config/logging.yaml") -> None:
    """
    로깅 설정 초기화
    
    Args:
        config_path: 로깅 설정 파일 경로
    """
    config_file = Path(config_path)
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
                if config is None:
                    raise ValueError("YAML 파일이 비어있습니다.")
                
                # 로그 디렉토리 자동 생성
                if 'handlers' in config:
                    for handler_name, handler_config in config['handlers'].items():
                        if isinstance(handler_config, dict) and 'filename' in handler_config:
                            log_file = Path(handler_config['filename'])
                            log_dir = log_file.parent
                            if not log_dir.exists():
                                log_dir.mkdir(parents=True, exist_ok=True)
                
                logging.config.dictConfig(config)
        except (yaml.YAMLError, KeyError, ValueError, TypeError) as e:
            # YAML 파싱 오류 또는 설정 오류 시 기본 설정 사용
            logging.warning(f"로깅 설정 파일 로드 실패 ({config_path}): {e}. 기본 설정을 사용합니다.")
            _setup_default_logging()
    else:
        _setup_default_logging()
```

---

## ✅ 결론

`utils/logger.py` 모듈은 전반적으로 잘 구현되어 있습니다. **에러 처리 추가**와 **로그 레벨 검증 추가**를 권장합니다. 비동기 함수 지원과 구조화 로깅은 향후 필요 시 추가할 수 있습니다.

**우선순위**:
1. 🟢 **낮음**: 에러 처리 추가
2. 🟢 **낮음**: 로그 레벨 검증 추가
3. 🟢 **낮음**: 비동기 함수 지원 추가 (선택적)
4. 🟢 **낮음**: 구조화 로깅 지원 추가 (선택적)

