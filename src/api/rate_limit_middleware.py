"""
Rate Limiting 미들웨어
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from collections import defaultdict
from datetime import datetime, timedelta
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP 기반 Rate Limiting 미들웨어
    
    간단한 in-memory 기반 Rate Limiter입니다.
    프로덕션 환경에서는 Redis 등을 사용하는 것을 권장합니다.
    """
    
    def __init__(self, app, calls: int = None, period: int = 60):
        """
        Args:
            app: FastAPI 애플리케이션
            calls: 허용된 호출 수 (기본값: settings.rate_limit_per_minute)
            period: 기간 (초, 기본값: 60초 = 1분)
        """
        super().__init__(app)
        self.calls = calls or settings.rate_limit_per_minute
        self.period = period
        # IP별 호출 기록: {ip: [(timestamp1, timestamp2, ...)]}
        self.requests = defaultdict(list)
        # 정리 작업을 위한 마지막 정리 시간
        self.last_cleanup = datetime.now()
    
    async def dispatch(self, request: Request, call_next):
        # 정적 파일 및 헬스체크는 제외
        if request.url.path.startswith("/static/") or request.url.path == "/health":
            return await call_next(request)
        
        # IP 주소 가져오기
        client_ip = request.client.host if request.client else "unknown"
        
        # 프록시를 통한 경우 X-Forwarded-For 헤더 확인
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        now = datetime.now()
        
        # 주기적으로 오래된 기록 정리 (메모리 절약)
        if (now - self.last_cleanup).seconds > 300:  # 5분마다 정리
            self._cleanup_old_requests(now)
            self.last_cleanup = now
        
        # 해당 IP의 최근 호출 기록 필터링 (period 내의 것만)
        cutoff_time = now - timedelta(seconds=self.period)
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > cutoff_time
        ]
        
        # Rate Limit 초과 확인
        if len(self.requests[client_ip]) >= self.calls:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.period),
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # 호출 기록 추가
        self.requests[client_ip].append(now)
        
        # 요청 처리
        response = await call_next(request)
        
        # Rate Limit 헤더 추가
        remaining = max(0, self.calls - len(self.requests[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((now + timedelta(seconds=self.period)).timestamp()))
        
        return response
    
    def _cleanup_old_requests(self, now: datetime):
        """오래된 요청 기록 정리"""
        cutoff_time = now - timedelta(seconds=self.period * 2)  # period의 2배만큼만 보관
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                ts for ts in self.requests[ip] if ts > cutoff_time
            ]
            # 빈 리스트는 제거
            if not self.requests[ip]:
                del self.requests[ip]

