"""
Q-A 매칭 방식 통합 테스트
전체 대화 흐름 테스트 (1차 서술 분석 → 질문 필터링 → Q-A 저장 → Facts 추출)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.langgraph.state import create_initial_context, StateContext
from src.langgraph.nodes import (
    case_classification_node,
    fact_collection_node,
    validation_node,
    re_question_node
)


@pytest.mark.integration
class TestQAMatchingFlow:
    """Q-A 매칭 방식 전체 흐름 테스트"""
    
    def test_complete_qa_matching_flow(self):
        """전체 Q-A 매칭 흐름 테스트"""
        session_id = "sess_test_qa_flow"
        state = create_initial_context(session_id)
        
        # 1. 초기 사용자 입력 (1차 서술)
        initial_description = "친구가 2024년 1월 2일에 300만원을 빌려갔는데 변제를 하지 않습니다. 계약서도 있습니다."
        state["last_user_input"] = initial_description
        
        # 2. CASE_CLASSIFICATION (1차 서술 분석 포함)
        with patch('src.langgraph.nodes.case_classification_node.rag_searcher') as mock_rag, \
             patch('src.langgraph.nodes.case_classification_node.gpt_client') as mock_gpt, \
             patch('src.langgraph.nodes.case_classification_node.db_manager') as mock_db:
            
            # RAG 모킹
            mock_rag.search_by_knowledge_type.return_value = []
            
            # GPT 분류 모킹
            mock_gpt.chat_completion.return_value = {
                "content": '{"main_case_type": "민사", "sub_case_type": "대여금"}'
            }
            
            # 1차 서술 분석 모킹
            with patch('src.langgraph.nodes.case_classification_node._analyze_initial_description') as mock_analyze:
                mock_analyze.return_value = {
                    "extracted_facts": {
                        "incident_date": "2024-01-02",
                        "amount": 3000000,
                        "counterparty": "친구",
                        "counterparty_type": "개인",
                        "evidence": True,
                        "evidence_type": "계약서"
                    },
                    "answered_fields": ["incident_date", "amount", "counterparty", "evidence", "evidence_type"],
                    "missing_fields": []
                }
                
                # DB 모킹
                mock_session = MagicMock()
                mock_db.get_db_session.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = MagicMock()
                
                result = case_classification_node(state)
                
                # 검증
                assert result["next_state"] == "FACT_COLLECTION"
                assert result.get("case_type") is not None
                assert result.get("skipped_fields") == ["incident_date", "amount", "counterparty", "evidence", "evidence_type"]
                assert len(result.get("conversation_history", [])) > 0
    
    def test_qa_matching_with_partial_initial_info(self):
        """부분 정보만 포함된 1차 서술 테스트"""
        session_id = "sess_test_partial"
        state = create_initial_context(session_id)
        
        # 부분 정보만 포함된 초기 입력
        initial_description = "친구가 돈을 빌려갔습니다."
        state["last_user_input"] = initial_description
        
        with patch('src.langgraph.nodes.case_classification_node.rag_searcher') as mock_rag, \
             patch('src.langgraph.nodes.case_classification_node.gpt_client') as mock_gpt, \
             patch('src.langgraph.nodes.case_classification_node.db_manager') as mock_db:
            
            mock_rag.search_by_knowledge_type.return_value = []
            mock_gpt.chat_completion.return_value = {
                "content": '{"main_case_type": "민사", "sub_case_type": "대여금"}'
            }
            
            # 1차 서술 분석 모킹 (부분 정보만 추출)
            with patch('src.langgraph.nodes.case_classification_node._analyze_initial_description') as mock_analyze:
                mock_analyze.return_value = {
                    "extracted_facts": {
                        "counterparty": "친구",
                        "counterparty_type": "개인"
                    },
                    "answered_fields": ["counterparty"],
                    "missing_fields": ["incident_date", "amount", "evidence"]
                }
                
                mock_session = MagicMock()
                mock_db.get_db_session.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = MagicMock()
                
                result = case_classification_node(state)
                
                # 검증: 일부 필드만 답변됨
                assert result.get("skipped_fields") == ["counterparty"]
                assert len(result.get("missing_fields", [])) > 0
    
    def test_fact_collection_qa_storage(self):
        """FACT_COLLECTION에서 Q-A 쌍 저장 테스트"""
        session_id = "sess_test_qa_storage"
        state = create_initial_context(session_id)
        state["case_type"] = "CIVIL"
        state["current_state"] = "FACT_COLLECTION"
        state["current_question"] = {
            "question": "사건이 발생한 날짜를 알려주세요.",
            "field": "incident_date"
        }
        state["last_user_input"] = "2024년 1월 2일"
        state["conversation_history"] = []
        state["skipped_fields"] = []
        
        with patch('src.langgraph.nodes.fact_collection_node.rag_searcher') as mock_rag:
            mock_rag.search.return_value = []
            
            result = fact_collection_node(state)
            
            # Q-A 쌍이 저장되었는지 확인
            assert len(result.get("conversation_history", [])) > 0
            qa_pair = result["conversation_history"][0]
            assert qa_pair["field"] == "incident_date"
            assert qa_pair["answer"] == "2024년 1월 2일"
            assert "timestamp" in qa_pair
    
    def test_validation_facts_extraction(self):
        """VALIDATION에서 Q-A 쌍에서 facts 추출 테스트"""
        session_id = "sess_test_validation"
        state = create_initial_context(session_id)
        state["case_type"] = "CIVIL"
        state["current_state"] = "VALIDATION"
        state["conversation_history"] = [
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
            }
        ]
        
        with patch('src.langgraph.nodes.validation_node.rag_searcher') as mock_rag, \
             patch('src.langgraph.nodes.validation_node._extract_facts_from_conversation') as mock_extract, \
             patch('src.langgraph.nodes.validation_node.db_manager') as mock_db:
            
            mock_rag.search.return_value = []
            
            # GPT facts 추출 모킹
            mock_extract.return_value = {
                "incident_date": "2024-01-02",
                "amount": 3000000,
                "counterparty": None,
                "evidence": None
            }
            
            mock_session = MagicMock()
            mock_db.get_db_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = MagicMock()
            
            result = validation_node(state)
            
            # 검증: facts가 추출되었는지 확인
            assert result.get("facts") is not None
            assert result["facts"].get("incident_date") == "2024-01-02"
            assert result["facts"].get("amount") == 3000000
    
    def test_skipped_fields_filtering(self):
        """skipped_fields 필터링 테스트"""
        session_id = "sess_test_skipped"
        state = create_initial_context(session_id)
        state["case_type"] = "CIVIL"
        state["current_state"] = "FACT_COLLECTION"
        state["skipped_fields"] = ["incident_date", "amount"]  # 1차 서술에서 이미 답변됨
        state["conversation_history"] = []
        state["last_user_input"] = ""  # 사용자 입력 없음
        
        with patch('src.langgraph.nodes.fact_collection_node.rag_searcher') as mock_rag:
            mock_rag.search.return_value = []
            
            result = fact_collection_node(state)
            
            # 다음 질문이 skipped_fields에 포함되지 않았는지 확인
            next_question = result.get("current_question", {})
            next_field = next_question.get("field")
            
            if next_field:
                assert next_field not in state["skipped_fields"]
    
    def test_re_question_with_skipped_fields(self):
        """RE_QUESTION에서 skipped_fields 반영 테스트"""
        session_id = "sess_test_re_question"
        state = create_initial_context(session_id)
        state["case_type"] = "CIVIL"
        state["current_state"] = "RE_QUESTION"
        state["missing_fields"] = ["incident_date", "amount", "counterparty", "evidence"]
        state["skipped_fields"] = ["incident_date", "amount"]  # 이미 답변됨
        state["conversation_history"] = []
        
        with patch('src.langgraph.nodes.re_question_node.rag_searcher') as mock_rag, \
             patch('src.langgraph.nodes.re_question_node.get_next_missing_field') as mock_next:
            
            mock_rag.search.return_value = []
            mock_next.return_value = "counterparty"  # skipped_fields 제외한 필드
            
            result = re_question_node(state)
            
            # 검증: skipped_fields에 포함되지 않은 필드 질문
            assert result["next_state"] == "FACT_COLLECTION"
            current_question = result.get("current_question", {})
            assert current_question.get("field") == "counterparty"
            assert current_question.get("field") not in state["skipped_fields"]


@pytest.mark.integration
class TestQAMatchingErrorHandling:
    """Q-A 매칭 방식 에러 처리 테스트"""
    
    def test_gpt_api_failure_fallback(self):
        """GPT API 실패 시 폴백 테스트"""
        session_id = "sess_test_fallback"
        state = create_initial_context(session_id)
        state["case_type"] = "CIVIL"
        state["current_state"] = "VALIDATION"
        state["conversation_history"] = [
            {
                "question": "사건이 발생한 날짜를 알려주세요.",
                "field": "incident_date",
                "answer": "2024년 1월 2일",
                "timestamp": "2024-01-01T10:00:00"
            }
        ]
        
        with patch('src.langgraph.nodes.validation_node.rag_searcher') as mock_rag, \
             patch('src.langgraph.nodes.validation_node._extract_facts_from_conversation') as mock_extract, \
             patch('src.langgraph.nodes.validation_node.db_manager') as mock_db:
            
            mock_rag.search.return_value = []
            
            # GPT API 실패 시뮬레이션
            from src.utils.exceptions import GPTAPIError
            mock_extract.side_effect = GPTAPIError("API 오류", status_code=500)
            
            mock_session = MagicMock()
            mock_db.get_db_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = MagicMock()
            
            result = validation_node(state)
            
            # 검증: 에러가 발생해도 계속 진행
            assert result is not None
            assert "next_state" in result

