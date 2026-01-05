"""
API 미들웨어 모듈
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.logger import get_logger
from src.utils.helpers import mask_personal_info

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        """요청 처리 및 로깅"""
        start_time = time.time()
        
        # 요청 정보 로깅
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        logger.info(
            f"요청 수신: {method} {path} - IP: {client_ip}"
        )
        
        # 요청 바디 로깅 (개인정보 마스킹)
        # 바디를 읽은 후 재사용할 수 있도록 request.state에 저장하고 복원
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode("utf-8")
                masked_body = mask_personal_info(body_str)
                logger.debug(f"요청 바디: {masked_body}")
                
                # 바디를 request.state에 저장하여 재사용 가능하도록 함
                request.state.body = body
                request.state.body_str = body_str
                
                # Starlette Request의 _body를 복원하여 후속 핸들러에서 사용 가능하도록 함
                async def receive():
                    return {"type": "http.request", "body": body}
                
                # request._receive를 재정의하여 바디를 재사용할 수 있도록 함
                request._receive = receive
            except Exception as e:
                logger.warning(f"요청 바디 로깅 실패: {str(e)}")
        
        # 응답 처리
        try:
            response = await call_next(request)
            
            # 응답 시간 계산
            process_time = time.time() - start_time
            
            # 응답 정보 로깅
            logger.info(
                f"응답 완료: {method} {path} - "
                f"상태: {response.status_code} - "
                f"소요 시간: {process_time:.3f}초"
            )
            
            # 응답 시간 헤더 추가
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"요청 처리 실패: {method} {path} - "
                f"오류: {str(e)} - "
                f"소요 시간: {process_time:.3f}초"
            )
            raise

