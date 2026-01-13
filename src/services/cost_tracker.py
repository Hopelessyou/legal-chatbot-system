"""
GPT API 비용 추적 모듈
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from src.utils.logger import get_logger

logger = get_logger(__name__)


# 모델별 토큰 가격 (USD per 1K tokens)
# 출처: https://openai.com/pricing (2024년 기준)
MODEL_PRICING = {
    # GPT-4o 모델
    "gpt-4o": {
        "input": 0.0025,   # $2.50 per 1M tokens
        "output": 0.010    # $10.00 per 1M tokens
    },
    "gpt-4o-mini": {
        "input": 0.00015,  # $0.15 per 1M tokens
        "output": 0.0006   # $0.60 per 1M tokens
    },
    # GPT-4 Turbo 모델
    "gpt-4-turbo": {
        "input": 0.01,     # $10 per 1M tokens
        "output": 0.03     # $30 per 1M tokens
    },
    "gpt-4-turbo-preview": {
        "input": 0.01,
        "output": 0.03
    },
    # GPT-3.5 모델
    "gpt-3.5-turbo": {
        "input": 0.0005,   # $0.50 per 1M tokens
        "output": 0.0015   # $1.50 per 1M tokens
    },
    # 기본값 (gpt-4o-mini와 동일)
    "default": {
        "input": 0.00015,
        "output": 0.0006
    }
}


class CostTracker:
    """GPT API 비용 추적 클래스"""
    
    def __init__(self):
        """비용 추적기 초기화"""
        # 세션별 비용 추적: {session_id: {"total_cost": float, "call_count": int, "tokens": {...}}}
        self.session_costs: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_cost": 0.0,
            "call_count": 0,
            "tokens": {
                "input": 0,
                "output": 0,
                "total": 0
            },
            "last_updated": datetime.now()
        })
        
        # 일일 통계: {date: {"total_cost": float, "call_count": int, "tokens": {...}}}
        self.daily_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_cost": 0.0,
            "call_count": 0,
            "tokens": {
                "input": 0,
                "output": 0,
                "total": 0
            }
        })
        
        logger.info("비용 추적기 초기화 완료")
    
    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        토큰 사용량으로 비용 계산
        
        Args:
            model: 모델명
            prompt_tokens: 입력 토큰 수
            completion_tokens: 출력 토큰 수
        
        Returns:
            계산된 비용 (USD)
        """
        # 모델별 가격 정보 가져오기
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        
        # 비용 계산: (토큰 수 / 1000) * 가격
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        total_cost = input_cost + output_cost
        
        return total_cost
    
    def track_api_call(
        self,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        node_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        API 호출 추적 및 비용 계산
        
        Args:
            session_id: 세션 ID
            model: 모델명
            prompt_tokens: 입력 토큰 수
            completion_tokens: 출력 토큰 수
            node_name: 노드 이름 (선택적)
        
        Returns:
            추적 정보 딕셔너리
        """
        # 비용 계산
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens
        
        # 세션별 통계 업데이트
        session_stat = self.session_costs[session_id]
        session_stat["total_cost"] += cost
        session_stat["call_count"] += 1
        session_stat["tokens"]["input"] += prompt_tokens
        session_stat["tokens"]["output"] += completion_tokens
        session_stat["tokens"]["total"] += total_tokens
        session_stat["last_updated"] = datetime.now()
        
        # 일일 통계 업데이트
        today = datetime.now().strftime("%Y-%m-%d")
        daily_stat = self.daily_stats[today]
        daily_stat["total_cost"] += cost
        daily_stat["call_count"] += 1
        daily_stat["tokens"]["input"] += prompt_tokens
        daily_stat["tokens"]["output"] += completion_tokens
        daily_stat["tokens"]["total"] += total_tokens
        
        # 로깅
        logger.info(
            f"[비용 추적] session_id={session_id}, node={node_name}, "
            f"model={model}, cost=${cost:.6f}, "
            f"tokens={total_tokens} (input={prompt_tokens}, output={completion_tokens})"
        )
        
        return {
            "cost": cost,
            "total_tokens": total_tokens,
            "session_total_cost": session_stat["total_cost"],
            "session_call_count": session_stat["call_count"]
        }
    
    def get_session_cost(self, session_id: str) -> Dict[str, Any]:
        """
        세션별 비용 통계 조회
        
        Args:
            session_id: 세션 ID
        
        Returns:
            세션별 통계 딕셔너리
        """
        if session_id not in self.session_costs:
            return {
                "total_cost": 0.0,
                "call_count": 0,
                "tokens": {"input": 0, "output": 0, "total": 0}
            }
        
        stat = self.session_costs[session_id].copy()
        # datetime 객체를 문자열로 변환
        if "last_updated" in stat:
            stat["last_updated"] = stat["last_updated"].isoformat()
        return stat
    
    def get_daily_cost(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        일일 비용 통계 조회
        
        Args:
            date: 날짜 (YYYY-MM-DD 형식, None이면 오늘)
        
        Returns:
            일일 통계 딕셔너리
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date not in self.daily_stats:
            return {
                "date": date,
                "total_cost": 0.0,
                "call_count": 0,
                "tokens": {"input": 0, "output": 0, "total": 0}
            }
        
        stat = self.daily_stats[date].copy()
        stat["date"] = date
        return stat
    
    def get_all_daily_costs(self, days: int = 7) -> Dict[str, Dict[str, Any]]:
        """
        최근 N일간의 일일 비용 통계 조회
        
        Args:
            days: 조회할 일수 (기본값: 7일)
        
        Returns:
            날짜별 통계 딕셔너리
        """
        result = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            result[date] = self.get_daily_cost(date)
        
        return result
    
    def get_total_cost(self) -> Dict[str, Any]:
        """
        전체 비용 통계 조회
        
        Returns:
            전체 통계 딕셔너리
        """
        total_cost = sum(stat["total_cost"] for stat in self.session_costs.values())
        total_calls = sum(stat["call_count"] for stat in self.session_costs.values())
        total_input_tokens = sum(stat["tokens"]["input"] for stat in self.session_costs.values())
        total_output_tokens = sum(stat["tokens"]["output"] for stat in self.session_costs.values())
        
        return {
            "total_cost": total_cost,
            "total_call_count": total_calls,
            "total_tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens
            },
            "session_count": len(self.session_costs)
        }
    
    def reset_session_cost(self, session_id: str):
        """
        세션별 비용 통계 초기화
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.session_costs:
            del self.session_costs[session_id]
            logger.info(f"세션 비용 통계 초기화: session_id={session_id}")


# 전역 비용 추적기 인스턴스
cost_tracker = CostTracker()

