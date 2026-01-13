"""
Q-A 매칭 방식 헬퍼 함수 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from src.langgraph.nodes.qa_helpers import (
    _analyze_initial_description,
    _extract_facts_from_conversation,
    _fallback_extract_facts_from_conversation
)


class TestAnalyzeInitialDescription:
    """1차 서술 분석 함수 테스트"""
    
    @pytest.mark.unit
    def test_analyze_initial_description_success(self):
        """정상적인 1차 서술 분석 테스트"""
        initial_description = "친구가 2024년 1월 2일에 300만원을 빌려갔는데 변제를 하지 않습니다."
        case_type = "CIVIL"
        required_fields = ["incident_date", "amount", "counterparty", "evidence"]
        
        # GPT 응답 모킹
        mock_response = {
            "content": """{
                "extracted_facts": {
                    "incident_date": "2024-01-02",
                    "amount": 3000000,
                    "counterparty": "친구",
                    "counterparty_type": "개인",
                    "evidence": null,
                    "evidence_type": null
                },
                "answered_fields": ["incident_date", "amount", "counterparty"],
                "missing_fields": ["evidence"]
            }"""
        }
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            mock_gpt.chat_completion.return_value = mock_response
            
            result = _analyze_initial_description(initial_description, case_type, required_fields)
            
            assert result is not None
            assert "extracted_facts" in result
            assert "answered_fields" in result
            assert "missing_fields" in result
            
            assert result["extracted_facts"]["incident_date"] == "2024-01-02"
            assert result["extracted_facts"]["amount"] == 3000000
            assert result["extracted_facts"]["counterparty"] == "친구"
            
            assert "incident_date" in result["answered_fields"]
            assert "amount" in result["answered_fields"]
            assert "counterparty" in result["answered_fields"]
            assert "evidence" in result["missing_fields"]
    
    @pytest.mark.unit
    def test_analyze_initial_description_empty_input(self):
        """빈 입력에 대한 테스트"""
        initial_description = ""
        case_type = "CIVIL"
        required_fields = ["incident_date", "amount", "counterparty", "evidence"]
        
        # GPT 응답 모킹 (빈 결과)
        mock_response = {
            "content": """{
                "extracted_facts": {},
                "answered_fields": [],
                "missing_fields": ["incident_date", "amount", "counterparty", "evidence"]
            }"""
        }
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            mock_gpt.chat_completion.return_value = mock_response
            
            result = _analyze_initial_description(initial_description, case_type, required_fields)
            
            assert result is not None
            assert len(result["answered_fields"]) == 0
            assert len(result["missing_fields"]) == len(required_fields)
    
    @pytest.mark.unit
    def test_analyze_initial_description_gpt_api_failure(self):
        """GPT API 실패 시 폴백 테스트"""
        initial_description = "친구가 돈을 빌려갔습니다."
        case_type = "CIVIL"
        required_fields = ["incident_date", "amount", "counterparty", "evidence"]
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            from src.utils.exceptions import GPTAPIError
            mock_gpt.chat_completion.side_effect = GPTAPIError("API 오류", status_code=500)
            
            result = _analyze_initial_description(initial_description, case_type, required_fields)
            
            # 폴백: 빈 결과 반환
            assert result is not None
            assert len(result["answered_fields"]) == 0
            assert len(result["missing_fields"]) == len(required_fields)
    
    @pytest.mark.unit
    def test_analyze_initial_description_json_parse_error(self):
        """JSON 파싱 오류 시 폴백 테스트"""
        initial_description = "친구가 돈을 빌려갔습니다."
        case_type = "CIVIL"
        required_fields = ["incident_date", "amount", "counterparty", "evidence"]
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            mock_gpt.chat_completion.return_value = {"content": "invalid json"}
            
            result = _analyze_initial_description(initial_description, case_type, required_fields)
            
            # 폴백: 빈 결과 반환
            assert result is not None
            assert len(result["answered_fields"]) == 0
            assert len(result["missing_fields"]) == len(required_fields)


class TestExtractFactsFromConversation:
    """Q-A 대화에서 facts 추출 함수 테스트"""
    
    @pytest.mark.unit
    def test_extract_facts_from_conversation_success(self):
        """정상적인 Q-A 대화 분석 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "question": "피해 금액은 얼마인가요?",
                "field": "amount",
                "answer": "300만원",
                "timestamp": "2024-01-01T10:01:00"
            },
            {
                "question": "관련 증거를 가지고 계신가요?",
                "field": "evidence",
                "answer": "네, 계약서가 있습니다.",
                "timestamp": "2024-01-01T10:02:00"
            }
        ]
        case_type = "CIVIL"
        
        # GPT 응답 모킹
        mock_response = {
            "content": """{
                "incident_date": "2024-01-02",
                "amount": 3000000,
                "counterparty": null,
                "counterparty_type": null,
                "evidence": true,
                "evidence_type": "계약서",
                "action_description": null
            }"""
        }
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            mock_gpt.chat_completion.return_value = mock_response
            
            result = _extract_facts_from_conversation(conversation_history, case_type)
            
            assert result is not None
            assert result["incident_date"] == "2024-01-02"
            assert result["amount"] == 3000000
            assert result["evidence"] is True
            assert result["evidence_type"] == "계약서"
    
    @pytest.mark.unit
    def test_extract_facts_from_conversation_empty_history(self):
        """빈 대화 기록 테스트"""
        conversation_history = []
        case_type = "CIVIL"
        
        result = _extract_facts_from_conversation(conversation_history, case_type)
        
        assert result == {}
    
    @pytest.mark.unit
    def test_extract_facts_from_conversation_gpt_api_failure(self):
        """GPT API 실패 시 폴백 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
        case_type = "CIVIL"
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            from src.utils.exceptions import GPTAPIError
            mock_gpt.chat_completion.side_effect = GPTAPIError("API 오류", status_code=500)
            
            # 폴백 함수도 모킹
            with patch('src.langgraph.nodes.qa_helpers._fallback_extract_facts_from_conversation') as mock_fallback:
                mock_fallback.return_value = {"incident_date": "2024-01-02"}
                
                result = _extract_facts_from_conversation(conversation_history, case_type)
                
                # 폴백 함수가 호출되었는지 확인
                mock_fallback.assert_called_once_with(conversation_history)
                assert result is not None
    
    @pytest.mark.unit
    def test_extract_facts_from_conversation_json_parse_error(self):
        """JSON 파싱 오류 시 폴백 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
        case_type = "CIVIL"
        
        with patch('src.langgraph.nodes.qa_helpers.gpt_client') as mock_gpt:
            mock_gpt.chat_completion.return_value = {"content": "invalid json"}
            
            result = _extract_facts_from_conversation(conversation_history, case_type)
            
            # JSON 파싱 오류 시 빈 결과 반환
            assert result == {}


class TestFallbackExtractFactsFromConversation:
    """폴백 엔티티 추출 함수 테스트"""
    
    @pytest.mark.unit
    def test_fallback_extract_facts_success(self):
        """폴백 엔티티 추출 성공 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "question": "피해 금액은 얼마인가요?",
                "field": "amount",
                "answer": "300만원",
                "timestamp": "2024-01-01T10:01:00"
            },
            {
                "question": "관련 증거를 가지고 계신가요?",
                "field": "evidence",
                "answer": "네",
                "timestamp": "2024-01-01T10:02:00"
            }
        ]
        
        # 기존 엔티티 추출 함수 모킹
        with patch('src.langgraph.nodes.qa_helpers.extract_date_from_input') as mock_date, \
             patch('src.langgraph.nodes.qa_helpers.extract_amount_from_input') as mock_amount, \
             patch('src.langgraph.nodes.qa_helpers.extract_evidence_from_input') as mock_evidence:
            
            mock_date.return_value = "2024-01-02"
            mock_amount.return_value = 3000000
            mock_evidence.return_value = (True, None)
            
            result = _fallback_extract_facts_from_conversation(conversation_history)
            
            assert result is not None
            assert result.get("incident_date") == "2024-01-02"
            assert result.get("amount") == 3000000
            assert result.get("evidence") is True
    
    @pytest.mark.unit
    def test_fallback_extract_facts_empty_history(self):
        """빈 대화 기록 테스트"""
        conversation_history = []
        
        result = _fallback_extract_facts_from_conversation(conversation_history)
        
        assert result == {}
    
    @pytest.mark.unit
    def test_fallback_extract_facts_extraction_failure(self):
        """엔티티 추출 실패 시 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "모름",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
        
        # 기존 엔티티 추출 함수 모킹 (None 반환)
        with patch('src.langgraph.nodes.qa_helpers.extract_date_from_input') as mock_date:
            mock_date.return_value = None
            
            result = _fallback_extract_facts_from_conversation(conversation_history)
            
            # 추출 실패 시 빈 facts 반환
            assert result is not None
            assert result.get("incident_date") is None
    
    @pytest.mark.unit
    def test_fallback_extract_facts_exception_handling(self):
        """예외 처리 테스트"""
        conversation_history = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
        
        # 예외 발생 시뮬레이션
        with patch('src.langgraph.nodes.qa_helpers.extract_date_from_input') as mock_date:
            mock_date.side_effect = Exception("추출 오류")
            
            result = _fallback_extract_facts_from_conversation(conversation_history)
            
            # 예외 발생 시 빈 결과 반환
            assert result == {}

