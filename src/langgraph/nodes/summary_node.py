"""
SUMMARY Node 구현
"""
from typing import Dict, Any
from src.langgraph.state import StateContext
from src.services.summarizer import summarizer
from src.rag.searcher import rag_searcher
from src.utils.logger import get_logger, log_execution_time
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
        
        logger.info(f"[{session_id}] SUMMARY Node 실행: facts={list(facts.keys())}, completion_rate={state.get('completion_rate', 0)}%")
        
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
        case_type_mapping = {
            "민사": "CIVIL",
            "형사": "CRIMINAL",
            "가사": "FAMILY",
            "행정": "ADMIN"
        }
        main_case_type_en = case_type_mapping.get(case_type, case_type) if case_type else None
        
        format_template = None
        try:
            rag_results = rag_searcher.search(
                query="요약 포맷",
                knowledge_type="K4",
                main_case_type=main_case_type_en,
                sub_case_type=sub_case_type,
                top_k=1
            )
            
            if rag_results:
                # K4 문서 파싱
                from src.rag.parser import RAGDocumentParser
                import yaml
                
                # RAG 검색 결과에서 content 추출 (YAML 문자열 또는 딕셔너리)
                result = rag_results[0]
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                
                # content가 YAML 문자열이면 파싱
                if isinstance(content, str):
                    try:
                        k4_data = yaml.safe_load(content)
                    except:
                        # YAML 파싱 실패 시 metadata에서 정보 추출
                        k4_data = metadata
                else:
                    k4_data = content if content else metadata
                
                # K4 문서 파싱
                try:
                    k4_doc = RAGDocumentParser.parse_k4_document(k4_data)
                    format_template = {
                        "sections": k4_doc.sections,
                        "target": k4_doc.target,
                        "main_case_type": main_case_type_en,
                        "sub_case_type": sub_case_type
                    }
                    logger.info(f"[{session_id}] K4 포맷 템플릿 로드 완료: {len(k4_doc.sections)}개 섹션")
                except Exception as parse_error:
                    logger.warning(f"[{session_id}] K4 문서 파싱 실패: {str(parse_error)}, 기본 포맷 사용")
                    format_template = None
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
        state["bot_message"] = "모든 필수 정보가 수집되었습니다. 요약을 생성하겠습니다."
        state["expected_input"] = None
        
        logger.info(f"SUMMARY 완료: session_id={session_id}")
        
        # 6. COMPLETED Node를 즉시 실행
        from src.langgraph.nodes.completed_node import completed_node
        logger.info(f"[{session_id}] SUMMARY 완료, COMPLETED Node 실행 시작")
        completed_result = completed_node(state)
        logger.info(f"[{session_id}] COMPLETED Node 실행 완료")
        
        return completed_result
    
    except Exception as e:
        logger.error(f"SUMMARY Node 실행 실패: {str(e)}")
        raise

