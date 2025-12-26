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


def setup_logging(config_path: str = "config/logging.yaml") -> None:
    """
    로깅 설정 초기화
    
    Args:
        config_path: 로깅 설정 파일 경로
    """
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        # 기본 로깅 설정
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def get_logger(name: str) -> logging.Logger:
    """
    로거 획득
    
    Args:
        name: 로거 이름
    
    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)


def log_execution_time(logger: logging.Logger = None):
    """
    함수 실행 시간 측정 데코레이터
    
    Args:
        logger: 로거 인스턴스 (None이면 함수명으로 로거 생성)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if logger is None:
                log = get_logger(func.__module__)
            else:
                log = logger
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
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
        
        return wrapper
    return decorator


def log_function_call(logger: logging.Logger = None, log_args: bool = False):
    """
    함수 호출 로깅 데코레이터
    
    Args:
        logger: 로거 인스턴스
        log_args: 인자 로깅 여부
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if logger is None:
                log = get_logger(func.__module__)
            else:
                log = logger
            
            if log_args:
                log.debug(f"{func.__name__} 호출 - args: {args}, kwargs: {kwargs}")
            else:
                log.debug(f"{func.__name__} 호출")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

