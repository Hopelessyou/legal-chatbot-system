"""
GPT API 응답 캐싱 모듈
동일한 프롬프트에 대한 중복 호출 방지
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GPTCache:
    """GPT API 응답 캐시 클래스"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        GPT 캐시 초기화
        
        Args:
            ttl_seconds: 캐시 유효 시간 (초, 기본값: 1시간)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        logger.info(f"GPT 캐시 초기화: TTL={ttl_seconds}초")
    
    def _generate_key(self, messages: list, model: str, **kwargs) -> str:
        """
        캐시 키 생성
        
        Args:
            messages: 메시지 리스트
            model: 모델명
            **kwargs: 추가 파라미터
        
        Returns:
            캐시 키 (해시값)
        """
        # 메시지와 파라미터를 JSON으로 직렬화하여 해시 생성
        cache_data = {
            "messages": messages,
            "model": model,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": kwargs.get("response_format")
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.md5(cache_str.encode('utf-8')).hexdigest()
        
        return cache_key
    
    def get(self, messages: list, model: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        캐시에서 응답 조회
        
        Args:
            messages: 메시지 리스트
            model: 모델명
            **kwargs: 추가 파라미터
        
        Returns:
            캐시된 응답 또는 None
        """
        cache_key = self._generate_key(messages, model, **kwargs)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            cached_time = cached_item["timestamp"]
            
            # TTL 확인
            if datetime.now() - cached_time < timedelta(seconds=self.ttl_seconds):
                logger.debug(f"GPT 캐시 히트: key={cache_key[:8]}...")
                return cached_item["response"]
            else:
                # 만료된 캐시 제거
                del self.cache[cache_key]
                logger.debug(f"GPT 캐시 만료: key={cache_key[:8]}...")
        
        logger.debug(f"GPT 캐시 미스: key={cache_key[:8]}...")
        return None
    
    def set(self, messages: list, model: str, response: Dict[str, Any], **kwargs):
        """
        캐시에 응답 저장
        
        Args:
            messages: 메시지 리스트
            model: 모델명
            response: API 응답
            **kwargs: 추가 파라미터
        """
        cache_key = self._generate_key(messages, model, **kwargs)
        
        self.cache[cache_key] = {
            "response": response,
            "timestamp": datetime.now()
        }
        
        logger.debug(f"GPT 캐시 저장: key={cache_key[:8]}...")
    
    def clear(self):
        """캐시 전체 삭제"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"GPT 캐시 전체 삭제: {count}개 항목")
    
    def clear_expired(self):
        """만료된 캐시만 삭제"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now - item["timestamp"] >= timedelta(seconds=self.ttl_seconds)
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"GPT 캐시 만료 항목 삭제: {len(expired_keys)}개")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회
        
        Returns:
            통계 딕셔너리
        """
        now = datetime.now()
        total_count = len(self.cache)
        expired_count = sum(
            1 for item in self.cache.values()
            if now - item["timestamp"] >= timedelta(seconds=self.ttl_seconds)
        )
        
        return {
            "total_entries": total_count,
            "expired_entries": expired_count,
            "active_entries": total_count - expired_count,
            "ttl_seconds": self.ttl_seconds
        }


# 전역 GPT 캐시 인스턴스 (TTL: 1시간)
gpt_cache = GPTCache(ttl_seconds=3600)

