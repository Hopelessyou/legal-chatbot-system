"""
디버그 모드로 서버 실행 (LangGraph 로그 출력)
"""
import uvicorn
import logging
import sys
import os

# Python의 기본 출력을 강제로 stderr로 리다이렉트
# uvicorn이 stdout을 캡처하므로 stderr를 사용
class ForceStderr:
    """강제로 stderr에 출력하는 클래스"""
    def write(self, text):
        os.write(2, text.encode('utf-8') if isinstance(text, str) else text)
        sys.stderr.write(text)
        sys.stderr.flush()
    def flush(self):
        sys.stderr.flush()

# sys.stdout을 stderr로 리다이렉트 (print()가 stderr로 가도록)
# 하지만 이건 위험할 수 있으므로, 대신 직접 stderr에 쓰는 방식 사용

# 로깅 설정 (uvicorn이 캡처하기 전에 설정)
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # stderr로 출력
    ],
    force=True  # 기존 설정 덮어쓰기
)

# uvicorn 로깅 설정
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "src.langgraph": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": True,  # root로 전파
        },
    },
}

if __name__ == "__main__":
    import os
    msg = "="*70 + "\n🚀 디버그 모드로 서버 시작 (LangGraph 로그 출력)\n" + "="*70 + "\n"
    os.write(2, msg.encode('utf-8'))
    sys.stderr.write(msg)
    sys.stderr.flush()
    
    # uvicorn 실행 (access log 비활성화하여 LangGraph 로그가 더 잘 보이도록)
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        log_config=log_config,
        access_log=False,  # access log 비활성화
    )