"""
GPT API 클라이언트 모듈
"""
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError
from config.settings import settings
from src.utils.logger import get_logger
from src.utils.exceptions import GPTAPIError

logger = get_logger(__name__)


class GPTClient:
    """GPT API 클라이언트 래퍼 클래스"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        GPT 클라이언트 초기화
        
        Args:
            api_key: OpenAI API 키 (None이면 설정에서 가져옴)
            model: 사용할 모델명 (None이면 설정에서 가져옴)
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"GPT 클라이언트 초기화 완료: 모델={self.model}")
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        지수 백오프를 사용한 재시도 로직
        
        Args:
            func: 실행할 함수
            *args, **kwargs: 함수 인자
        
        Returns:
            함수 실행 결과
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            
            except RateLimitError as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Rate Limit 오류 (시도 {attempt + 1}/{self.max_retries}), "
                    f"{wait_time}초 대기 후 재시도..."
                )
                time.sleep(wait_time)
                last_exception = e
            
            except (APIConnectionError, APITimeoutError) as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"연결 오류 (시도 {attempt + 1}/{self.max_retries}), "
                    f"{wait_time}초 대기 후 재시도..."
                )
                time.sleep(wait_time)
                last_exception = e
            
            except APIError as e:
                # 재시도 불가능한 오류
                logger.error(f"GPT API 오류: {str(e)}")
                raise GPTAPIError(f"API 오류: {str(e)}", status_code=getattr(e, 'status_code', None))
        
        # 모든 재시도 실패
        raise GPTAPIError(
            f"최대 재시도 횟수 초과: {str(last_exception)}",
            status_code=getattr(last_exception, 'status_code', None) if last_exception else None
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat Completion API 호출
        
        Args:
            messages: 메시지 리스트
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            **kwargs: 추가 파라미터
        
        Returns:
            API 응답 딕셔너리
        """
        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        
        try:
            response = self._retry_with_backoff(_call)
            
            # 응답 파싱
            result = {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason
            }
            
            logger.debug(f"Chat Completion 성공: 토큰 사용량={result['usage']['total_tokens']}")
            return result
        
        except Exception as e:
            logger.error(f"Chat Completion 실패: {str(e)}")
            raise
    
    def embedding(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Embedding API 호출
        
        Args:
            texts: 텍스트 리스트
            model: Embedding 모델명 (None이면 설정에서 가져옴)
        
        Returns:
            Embedding 벡터 리스트
        """
        embedding_model = model or settings.openai_embedding_model
        
        def _call():
            return self.client.embeddings.create(
                model=embedding_model,
                input=texts
            )
        
        try:
            response = self._retry_with_backoff(_call)
            
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(f"Embedding 생성 성공: {len(texts)}개 텍스트")
            return embeddings
        
        except Exception as e:
            logger.error(f"Embedding 생성 실패: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        API 연결 테스트
        
        Returns:
            연결 상태 (True: 정상, False: 오류)
        """
        try:
            response = self.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logger.info("GPT API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"GPT API 연결 테스트 실패: {str(e)}")
            return False


# 전역 GPT 클라이언트 인스턴스
gpt_client = GPTClient()

