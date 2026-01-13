"""
SUMMARY Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.summarizer import summarizer
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
from src.utils.constants import CASE_TYPE_MAPPING
from src.utils.rag_helpers import extract_k4_format_from_rag
from src.db.connection import db_manager
from src.db.models.case_summary import CaseSummary
from src.db.models.case_master import CaseMaster
import json

logger = get_logger(__name__)


@log_execution_time(logger)
def summary_node(state: StateContext) -> Dict[str, Any]:
    """
    SUMMARY Node 실행
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State 및 다음 State 정보
    """
    try:
        session_id = state["session_id"]
        facts = state.get("facts", {})
        
        # 단계 표시
        print("\n" + "="*70)
        print("📍 [STEP 6] SUMMARY 노드 실행")
        print("="*70)
        print(f"📌 세션 ID: {session_id}")
        print(f"📊 수집된 Facts: {list(facts.keys())}")
        print(f"📈 완성도: {state.get('completion_rate', 0)}%")
        print("="*70 + "\n")
        logger.info("="*70)
        logger.info("📍 [STEP 6] SUMMARY 노드 실행")
        logger.info("="*70)
        logger.info(f"📌 세션 ID: {session_id}")
        logger.info(f"📊 수집된 Facts: {list(facts.keys())}")
        logger.info(f"📈 완성도: {state.get('completion_rate', 0)}%")
        logger.info("="*70)
        
        # 1. 전체 Context 취합
        # 사용자 입력 텍스트 수집 (DB의 CaseFact에서 source_text 수집)
        user_inputs = []
        with db_manager.get_db_session() as db_session:
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if case:
                from src.db.models.case_fact import CaseFact
                case_facts = db_session.query(CaseFact).filter(
                    CaseFact.case_id == case.case_id
                ).all()
                
                for fact in case_facts:
                    if fact.source_text:
                        user_inputs.append(fact.source_text)
        
        # 마지막 사용자 입력도 추가
        last_user_input = state.get("last_user_input", "")
        if last_user_input and last_user_input not in user_inputs:
            user_inputs.append(last_user_input)
        
        # 사용자 입력 텍스트 통합
        user_input_text = "\n".join(user_inputs) if user_inputs else ""
        
        context = {
            "case_type": state.get("case_type"),
            "sub_case_type": state.get("sub_case_type"),
            "facts": facts,
            "emotion": state.get("emotion", []),
            "completion_rate": state.get("completion_rate", 0),
            "user_inputs": user_input_text  # 사용자 입력 텍스트 추가
        }
        
        # 2. RAG K4 포맷 기준 조회 (케이스 타입별)
        case_type = state.get("case_type")
        sub_case_type = state.get("sub_case_type")
        
        # case_type 변환 (한글 → 영문)
        main_case_type_en = CASE_TYPE_MAPPING.get(case_type, case_type) if case_type else None
        
        format_template = None
        try:
            rag_results = rag_searcher.search(
                query="요약 포맷",
                knowledge_type="K4",
                main_case_type=main_case_type_en,
                sub_case_type=sub_case_type,
                top_k=1
            )
            
            # RAG 결과에서 K4 포맷 추출
            format_template = extract_k4_format_from_rag(rag_results)
            if format_template:
                format_template["main_case_type"] = main_case_type_en
                format_template["sub_case_type"] = sub_case_type
                logger.info(f"[{session_id}] RAG K4 포맷 템플릿 추출 성공: {len(format_template.get('sections', []))}개 섹션")
            else:
                logger.debug(f"[{session_id}] RAG K4 포맷 추출 실패, 기본 포맷 사용")
        except Exception as e:
            logger.warning(f"[{session_id}] RAG K4 검색 실패 (기본 포맷 사용): {str(e)}")
            rag_results = []
        
        # 3. GPT API로 요약 생성
        logger.info(f"[{session_id}] 요약 생성 시작...")
        summary_result = summarizer.generate_final_summary(
            context=context,
            format_template=format_template
        )
        
        logger.info(f"[{session_id}] 요약 생성 완료: summary_text 길이={len(summary_result.get('summary_text', ''))}")
        logger.debug(f"[{session_id}] 요약 내용 (일부): {summary_result.get('summary_text', '')[:200]}...")
        
        # 4. DB에 case_summary 저장
        with db_manager.get_db_session() as db_session:
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if case:
                # 기존 요약 삭제
                db_session.query(CaseSummary).filter(
                    CaseSummary.case_id == case.case_id
                ).delete()
                
                # 새 요약 저장
                summary = CaseSummary(
                    case_id=case.case_id,
                    summary_text=summary_result["summary_text"],
                    structured_json=summary_result["structured_data"],
                    risk_level=None,  # K3에서 계산
                    ai_version="gpt-4-turbo-preview"
                )
                db_session.add(summary)
                db_session.commit()
                logger.info(f"[{session_id}] CaseSummary DB 저장 완료: case_id={case.case_id}, summary_id={summary.id}")
            else:
                logger.warning(f"[{session_id}] CaseMaster를 찾을 수 없어 요약을 저장할 수 없습니다.")
        
        # 5. State 업데이트
        bot_message = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
        state["bot_message"] = bot_message
        state["expected_input"] = None
        
        logger.info(f"[{session_id}] SUMMARY 완료: bot_message={bot_message}")
        logger.debug(f"[{session_id}] SUMMARY: state['bot_message']={state.get('bot_message')}")
        
        # 6. 그래프 엣지를 통한 자동 전이 (COMPLETED 노드 직접 호출 제거)
        # graph.py에서 이미 SUMMARY → COMPLETED 엣지가 정의되어 있으므로
        # next_state만 반환하면 LangGraph가 자동으로 COMPLETED 노드로 전이함
        return {
            **state,
            "bot_message": bot_message,  # 명시적으로 반환
            "next_state": "COMPLETED"
        }
    
    except Exception as e:
        logger.error(f"SUMMARY Node 실행 실패: {str(e)}", exc_info=True)
        # 폴백 처리: 기본 메시지 반환하고 COMPLETED로 이동
        state["bot_message"] = "요약 생성 중 오류가 발생했습니다. 다시 시도해주세요."
        return {
            **state,
            "next_state": "COMPLETED"
        }

