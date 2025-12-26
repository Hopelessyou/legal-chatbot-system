"""
CASE_CLASSIFICATION Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.keyword_extractor import keyword_extractor
from src.services.gpt_client import gpt_client
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.db.connection import db_manager
from src.db.models.case_master import CaseMaster
from src.db.models.chat_session import ChatSession

logger = get_logger(__name__)


@log_execution_time(logger)
def case_classification_node(state: StateContext) -> Dict[str, Any]:
    """
    CASE_CLASSIFICATION Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        user_input = state.get("last_user_input", "")
        
        logger.info(f"CASE_CLASSIFICATION Node 실행: session_id={session_id}, user_input={user_input[:50] if user_input else 'None'}...")
        
        if not user_input:
            logger.warning("사용자 입력이 없습니다.")
            return {
                **state,
                "bot_message": "사건과 관련된 내용을 알려주세요.",
                "next_state": "CASE_CLASSIFICATION"
            }
        
        # 1. 키워드 및 의미 추출
        semantic_features = keyword_extractor.extract_semantic_features(user_input)
        keywords = semantic_features.get("keywords", [])
        
        # 2. RAG K1 조회 (사건 유형 분류 기준)
        query = " ".join(keywords) if keywords else user_input
        rag_results = rag_searcher.search_by_knowledge_type(
            query=query,
            knowledge_type="K1",
            top_k=3
        )
        
        # 3. 사건 유형 결정
        main_case_type = None
        sub_case_type = None
        
        if rag_results:
            # 가장 유사도 높은 결과 사용
            best_match = rag_results[0]
            metadata = best_match.get("metadata", {})
            main_case_type = metadata.get("main_case_type")
            sub_case_type = metadata.get("sub_case_type")
        
        # GPT API로 최종 분류 (RAG 결과를 참고)
        if not main_case_type:
            classification_prompt = f"""다음 텍스트를 분석하여 법률 사건 유형을 분류하세요.
가능한 분류:
- 민사: 계약, 불법행위, 대여금, 손해배상
- 형사: 사기, 성범죄, 폭행
- 가사: 이혼, 상속
- 행정: 행정처분, 세무

텍스트: {user_input}

JSON 형식으로 반환:
{{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}}"""
            
            try:
                response = gpt_client.chat_completion(
                    messages=[{"role": "user", "content": classification_prompt}],
                    temperature=0.3,
                    max_tokens=100
                )
                
                import json
                import re
                
                # 응답에서 JSON 추출 (마크다운 코드 블록 제거)
                content = response["content"].strip()
                
                # ```json ... ``` 또는 ``` ... ``` 제거
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                else:
                    # JSON 객체만 추출
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(0)
                
                classification = json.loads(content)
                main_case_type = classification.get("main_case_type")
                sub_case_type = classification.get("sub_case_type")
            except Exception as e:
                logger.error(f"GPT 분류 실패: {str(e)}")
                # 폴백: 키워드 기반 간단한 분류
                if any(kw in user_input for kw in ["돈", "빌려", "대여금", "계약", "미지급"]):
                    main_case_type = "CIVIL"
                    sub_case_type = "CIVIL_CONTRACT"
                elif any(kw in user_input for kw in ["사기", "절도", "폭행", "성범죄"]):
                    main_case_type = "CRIMINAL"
                    sub_case_type = "CRIMINAL_FRAUD"
                else:
                    main_case_type = "CIVIL"  # 기본값
                    sub_case_type = "CIVIL_CONTRACT"
        
        # 4. case_type 변환 (한글 → 영문)
        case_type_mapping = {
            "민사": "CIVIL",
            "형사": "CRIMINAL",
            "가사": "FAMILY",
            "행정": "ADMIN"
        }
        main_case_type_en = case_type_mapping.get(main_case_type, main_case_type) if main_case_type else None
        
        # 5. State 업데이트
        state["case_type"] = main_case_type_en
        state["sub_case_type"] = sub_case_type
        
        # 5. DB에 case_master 생성/업데이트
        with db_manager.get_db_session() as db_session:
            chat_session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                # case_master 생성 또는 업데이트
                from src.db.models.case_master import CaseMaster
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session_id
                ).first()
                
                if not case:
                    case = CaseMaster(
                        session_id=session_id,
                        main_case_type=main_case_type_en,
                        sub_case_type=sub_case_type,
                        case_stage="상담전"
                    )
                    db_session.add(case)
                else:
                    case.main_case_type = main_case_type_en
                    case.sub_case_type = sub_case_type
                
                # 세션 상태 업데이트
                chat_session.current_state = "CASE_CLASSIFICATION"
                db_session.commit()
        
        # 6. State 전이 로깅
        from src.langgraph.state_logger import log_state_transition
        log_state_transition(
            session_id=session_id,
            from_state="INIT",
            to_state="CASE_CLASSIFICATION",
            condition_key="user_input_received"
        )
        
        # 7. 다음 질문 생성
        state["bot_message"] = "사건과 관련된 구체적인 내용을 알려주세요."
        state["expected_input"] = {
            "type": "text",
            "field": "fact_description"
        }
        
        logger.info(f"CASE_CLASSIFICATION 완료: {main_case_type_en} / {sub_case_type}")
        
        return {
            **state,
            "next_state": "FACT_COLLECTION"
        }
    
    except Exception as e:
        logger.error(f"CASE_CLASSIFICATION Node 실행 실패: {str(e)}")
        raise

