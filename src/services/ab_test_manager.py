"""
A/B 테스트 관리 모듈
기존 방식 vs Q-A 매칭 방식 비교 테스트
"""
from typing import Dict, Any, Optional, Literal
from enum import Enum
from src.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class FactExtractionMethod(str, Enum):
    """사실 추출 방식"""
    LEGACY = "legacy"  # 기존 방식 (엔티티 추출)
    QA_MATCHING = "qa_matching"  # Q-A 매칭 방식


class ABTestManager:
    """A/B 테스트 관리 클래스"""
    
    def __init__(self):
        """A/B 테스트 관리자 초기화"""
        # 기본 방식 설정 (환경 변수 또는 설정에서 가져옴)
        self.default_method = getattr(
            settings,
            'fact_extraction_method',
            FactExtractionMethod.QA_MATCHING.value
        )
        
        # 세션별 방식 할당: {session_id: method}
        self.session_methods: Dict[str, str] = {}
        
        # 통계 추적: {method: {"session_count": int, "success_count": int, "error_count": int}}
        self.stats: Dict[str, Dict[str, int]] = {
            FactExtractionMethod.LEGACY.value: {
                "session_count": 0,
                "success_count": 0,
                "error_count": 0
            },
            FactExtractionMethod.QA_MATCHING.value: {
                "session_count": 0,
                "success_count": 0,
                "error_count": 0
            }
        }
        
        logger.info(f"A/B 테스트 관리자 초기화: 기본 방식={self.default_method}")
    
    def assign_method(self, session_id: str, method: Optional[str] = None) -> str:
        """
        세션에 방식 할당
        
        Args:
            session_id: 세션 ID
            method: 할당할 방식 (None이면 기본 방식 또는 랜덤 할당)
        
        Returns:
            할당된 방식
        """
        if method is None:
            # 기본 방식 사용 또는 랜덤 할당 (50:50)
            import random
            method = random.choice([
                FactExtractionMethod.LEGACY.value,
                FactExtractionMethod.QA_MATCHING.value
            ]) if getattr(settings, 'ab_test_enabled', False) else self.default_method
        
        self.session_methods[session_id] = method
        self.stats[method]["session_count"] += 1
        
        logger.info(f"[A/B 테스트] 세션 {session_id}에 {method} 방식 할당")
        return method
    
    def get_method(self, session_id: str) -> str:
        """
        세션의 할당된 방식 조회
        
        Args:
            session_id: 세션 ID
        
        Returns:
            할당된 방식
        """
        if session_id not in self.session_methods:
            # 할당되지 않은 경우 기본 방식 할당
            return self.assign_method(session_id)
        
        return self.session_methods[session_id]
    
    def record_success(self, session_id: str):
        """
        성공 기록
        
        Args:
            session_id: 세션 ID
        """
        method = self.get_method(session_id)
        self.stats[method]["success_count"] += 1
        logger.debug(f"[A/B 테스트] {method} 방식 성공 기록: session_id={session_id}")
    
    def record_error(self, session_id: str, error: Optional[str] = None):
        """
        오류 기록
        
        Args:
            session_id: 세션 ID
            error: 오류 메시지 (선택적)
        """
        method = self.get_method(session_id)
        self.stats[method]["error_count"] += 1
        logger.warning(f"[A/B 테스트] {method} 방식 오류 기록: session_id={session_id}, error={error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        통계 조회
        
        Returns:
            통계 딕셔너리
        """
        result = {}
        for method, stat in self.stats.items():
            total = stat["session_count"]
            success = stat["success_count"]
            error = stat["error_count"]
            
            result[method] = {
                "session_count": total,
                "success_count": success,
                "error_count": error,
                "success_rate": (success / total * 100) if total > 0 else 0.0,
                "error_rate": (error / total * 100) if total > 0 else 0.0
            }
        
        return result
    
    def reset_stats(self):
        """통계 초기화"""
        for method in self.stats:
            self.stats[method] = {
                "session_count": 0,
                "success_count": 0,
                "error_count": 0
            }
        logger.info("A/B 테스트 통계 초기화 완료")
    
    def is_legacy_method(self, session_id: str) -> bool:
        """
        세션이 기존 방식인지 확인
        
        Args:
            session_id: 세션 ID
        
        Returns:
            True면 기존 방식, False면 Q-A 매칭 방식
        """
        method = self.get_method(session_id)
        return method == FactExtractionMethod.LEGACY.value
    
    def is_qa_matching_method(self, session_id: str) -> bool:
        """
        세션이 Q-A 매칭 방식인지 확인
        
        Args:
            session_id: 세션 ID
        
        Returns:
            True면 Q-A 매칭 방식, False면 기존 방식
        """
        method = self.get_method(session_id)
        return method == FactExtractionMethod.QA_MATCHING.value


# 전역 A/B 테스트 관리자 인스턴스
ab_test_manager = ABTestManager()

