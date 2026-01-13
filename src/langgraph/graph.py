"""
LangGraph 그래프 구성
"""
import sys
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.langgraph.state import StateContext
from src.langgraph.nodes import (
    init_node,
    case_classification_node,
    fact_collection_node,
    validation_node,
    re_question_node,
    summary_node,
    completed_node
)
from src.langgraph.edges.conditional_edges import route_after_validation
from src.utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)

# 강제로 콘솔 출력 (uvicorn이 캡처해도 보이도록)
# root logger에도 핸들러 추가
root_logger = logging.getLogger()
has_stderr_handler = any(isinstance(h, logging.StreamHandler) and h.stream == sys.stderr for h in root_logger.handlers)
if not has_stderr_handler:
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

# 이 모듈의 logger에도 추가
if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stderr for h in logger.handlers):
    module_handler = logging.StreamHandler(sys.stderr)
    module_handler.setLevel(logging.INFO)
    module_handler.setFormatter(logging.Formatter('[GRAPH] %(message)s'))
    logger.addHandler(module_handler)
    logger.setLevel(logging.INFO)

# 최대 재귀 깊이 (무한 루프 방지)
DEFAULT_RECURSION_LIMIT = 50


def create_graph() -> StateGraph: 
    """
    LangGraph 그래프 생성
    
    Returns:
        컴파일된 StateGraph 인스턴스
    """
    # 그래프 생성
    workflow = StateGraph(dict)  # StateContext는 TypedDict이므로 dict로 사용
    
    # Node 추가
    workflow.add_node("INIT", init_node)
    workflow.add_node("CASE_CLASSIFICATION", case_classification_node)
    workflow.add_node("FACT_COLLECTION", fact_collection_node)
    workflow.add_node("VALIDATION", validation_node)
    workflow.add_node("RE_QUESTION", re_question_node)
    workflow.add_node("SUMMARY", summary_node)
    workflow.add_node("COMPLETED", completed_node)
    
    # Edge 연결
    workflow.set_entry_point("INIT")
    workflow.add_edge("INIT", "CASE_CLASSIFICATION")
    workflow.add_edge("CASE_CLASSIFICATION", "FACT_COLLECTION")
    workflow.add_edge("FACT_COLLECTION", "VALIDATION")
    
    # Conditional Edge: VALIDATION → RE_QUESTION or SUMMARY
    workflow.add_conditional_edges(
        "VALIDATION",
        route_after_validation,
        {
            "RE_QUESTION": "RE_QUESTION",
            "SUMMARY": "SUMMARY"
        }
    )
    
    # Loop: RE_QUESTION → FACT_COLLECTION
    workflow.add_edge("RE_QUESTION", "FACT_COLLECTION")
    
    # SUMMARY → COMPLETED
    workflow.add_edge("SUMMARY", "COMPLETED")
    
    # COMPLETED → END
    workflow.add_edge("COMPLETED", END)
    
    # 그래프 컴파일 (recursion_limit 설정으로 무한 루프 방지)
    recursion_limit = getattr(settings, 'graph_recursion_limit', DEFAULT_RECURSION_LIMIT)
    app = workflow.compile(checkpointer=None, interrupt_before=None, interrupt_after=None)
    
    logger.info(f"LangGraph 그래프 생성 완료 (recursion_limit: {recursion_limit})")
    return app


def run_graph_step(state: StateContext) -> StateContext:
    """
    LangGraph 1 step 실행 (현재 State에 해당하는 Node만 실행)
    
    현재 State에 해당하는 Node만 직접 실행하여 상태 전이를 처리합니다.
    무한 루프 방지를 위해 재귀 제한을 확인합니다.
    
    Args:
        state: 현재 State Context
    
    Returns:
        업데이트된 State Context
    
    Raises:
        RuntimeError: 재귀 제한 초과 시
    """
    try:
        session_id = state.get("session_id", "unknown")
        current_state = state.get("current_state", "INIT")
        
        # 노드 실행 시작 로깅 (강제 출력 - 터미널에 표시)
        import sys
        import os
        # stderr에 직접 출력 (uvicorn이 캡처하지 않음)
        msg = f"\n{'='*70}\n🔄 [GRAPH] 노드 실행 시작: {current_state}\n📌 세션 ID: {session_id}\n{'='*70}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        # logger도 사용
        logger.info(f"🔄 [GRAPH] 노드 실행 시작: {current_state}")
        logger.info(f"📌 세션 ID: {session_id}")
        
        # 재귀 제한 확인
        if _check_recursion_limit(session_id):
            logger.error(f"[{session_id}] 무한 루프 감지, 그래프 실행 중단")
            state["current_state"] = "COMPLETED"
            state["bot_message"] = "죄송합니다. 시스템 오류가 발생했습니다. 세션을 다시 시작해주세요."
            _reset_session_step_count(session_id)
            return state
        
        # 현재 State에 해당하는 Node 실행
        from src.langgraph.nodes import (
            init_node,
            case_classification_node,
            fact_collection_node,
            validation_node,
            re_question_node,
            summary_node,
            completed_node
        )
        
        node_map = {
            "INIT": init_node,
            "CASE_CLASSIFICATION": case_classification_node,
            "FACT_COLLECTION": fact_collection_node,
            "VALIDATION": validation_node,
            "RE_QUESTION": re_question_node,
            "SUMMARY": summary_node,
            "COMPLETED": completed_node
        }
        
        node_func = node_map.get(current_state)
        if not node_func:
            logger.error(f"[{session_id}] 알 수 없는 State: {current_state}")
            return state
        
        # Node 실행
        import sys
        import os
        msg = f"▶️  노드 함수 실행: {current_state}\n"
        os.write(2, msg.encode('utf-8'))
        sys.stderr.write(msg)
        sys.stderr.flush()
        logger.info(f"▶️  노드 함수 실행: {current_state}")
        
        # 노드 실행 전 디버깅
        import sys
        import os
        pre_msg = f"🔍 [PRE] 노드 실행 전: current_state={current_state}, state.keys()={list(state.keys())[:10]}\n"
        os.write(2, pre_msg.encode('utf-8'))
        sys.stderr.write(pre_msg)
        sys.stderr.flush()
        logger.error(f"🔍 [PRE] 노드 실행 전: current_state={current_state}")
        
        result = node_func(state)
        
        # 노드 실행 직후 디버깅 (예외 없이 도달)
        import sys
        import os
        post_msg = f"🔍 [POST] 노드 실행 직후: result 타입={type(result)}, result.keys()={list(result.keys())[:10] if isinstance(result, dict) else 'NOT_DICT'}\n"
        os.write(2, post_msg.encode('utf-8'))
        sys.stderr.write(post_msg)
        sys.stderr.flush()
        logger.error(f"🔍 [POST] 노드 실행 직후: result 타입={type(result)}")
        
        # last_user_input 보존 (Node가 반환하지 않았을 수 있음)
        if "last_user_input" not in result and "last_user_input" in state:
            result["last_user_input"] = state["last_user_input"]
        
        # next_state 업데이트
        next_state = result.get("next_state")
        bot_message = result.get("bot_message", "")
        
        # 강제 디버깅: result 내용 확인 (항상 실행)
        import sys
        import os
        try:
            result_keys = list(result.keys())
            missing_fields_value = result.get('missing_fields', 'N/A')
            debug_msg = f"\n{'='*70}\n🔍 [CRITICAL DEBUG] 노드 실행 후 즉시 체크\n"
            debug_msg += f"current_state={current_state}\n"
            debug_msg += f"next_state={next_state}\n"
            debug_msg += f"result.keys()={result_keys}\n"
            debug_msg += f"missing_fields={missing_fields_value}\n"
            debug_msg += f"{'='*70}\n"
            # stderr에 직접 출력
            os.write(2, debug_msg.encode('utf-8'))
            sys.stderr.write(debug_msg)
            sys.stderr.flush()
            # logger에도 출력
            logger.error(f"🔍 [CRITICAL DEBUG] 노드 실행 후: current_state={current_state}, next_state={next_state}")
            logger.error(f"🔍 [CRITICAL DEBUG] result.keys(): {result_keys}")
            logger.error(f"🔍 [CRITICAL DEBUG] result.get('missing_fields'): {missing_fields_value}")
        except Exception as e:
            error_msg = f"❌ [DEBUG ERROR] {str(e)}\n"
            os.write(2, error_msg.encode('utf-8'))
            sys.stderr.write(error_msg)
            sys.stderr.flush()
            logger.error(f"❌ [DEBUG ERROR] {str(e)}", exc_info=True)
        
        if next_state:
            # 디버깅: next_state가 있을 때
            import sys
            import os
            debug_msg = f"🔍 [DEBUG-2] next_state 확인됨: {current_state} → {next_state}\n"
            os.write(2, debug_msg.encode('utf-8'))
            sys.stderr.write(debug_msg)
            sys.stderr.flush()
            logger.error(f"🔍 [DEBUG-2] next_state 확인됨: {current_state} → {next_state}")
        
        if next_state:
            # next_state가 있으면 current_state 업데이트
            result["current_state"] = next_state
            
            # 디버깅: 항상 출력 (조건 확인 전에)
            import sys
            import os
            is_chain_condition = current_state == "VALIDATION" and next_state in ["RE_QUESTION", "SUMMARY"]
            debug_msg = f"🔍 [DEBUG] State 전이 감지: {current_state} → {next_state}, 체인조건={is_chain_condition}\n"
            os.write(2, debug_msg.encode('utf-8'))
            sys.stderr.write(debug_msg)
            sys.stderr.flush()
            logger.info(f"🔍 [DEBUG] State 전이 감지: {current_state} → {next_state}, 체인조건={is_chain_condition}")
            
            msg = f"✅ State 전이: {current_state} → {next_state}\n"
            if bot_message:
                msg += f"💬 Bot 메시지: {bot_message[:100]}...\n"
            else:
                msg += f"⚠️  Bot 메시지 없음!\n"
            os.write(2, msg.encode('utf-8'))
            sys.stderr.write(msg)
            sys.stderr.flush()
            logger.info(f"✅ State 전이: {current_state} → {next_state}")
            if bot_message:
                logger.info(f"💬 Bot 메시지: {bot_message[:100]}...")
            else:
                logger.warning(f"⚠️  Bot 메시지 없음!")
            
            # 특정 State 전이 시 다음 노드를 즉시 실행하여 bot_message 생성
            # VALIDATION → RE_QUESTION: RE_QUESTION 노드를 즉시 실행하여 질문 생성
            # VALIDATION → SUMMARY: SUMMARY 노드는 사용자 입력을 기다리지 않으므로 즉시 실행 가능
            if is_chain_condition:
                import sys
                import os
                missing_fields = result.get('missing_fields', [])
                conv_history_len = len(result.get('conversation_history', []))
                # 강제 출력 (stderr에 직접)
                msg = f"\n{'='*70}\n🔄 VALIDATION → {next_state} 전이 감지\n📋 missing_fields: {missing_fields}\n💬 conversation_history: {conv_history_len}개\n{'='*70}\n"
                os.write(2, msg.encode('utf-8'))
                sys.stderr.write(msg)
                sys.stderr.flush()
                logger.info(f"🔄 VALIDATION → {next_state} 전이 감지")
                logger.info(f"📋 missing_fields: {missing_fields}")
                logger.info(f"💬 conversation_history: {conv_history_len}개")
                
                # RE_QUESTION 노드에 전달할 state 검증
                if next_state == "RE_QUESTION":
                    missing_fields = result.get("missing_fields", [])
                    if not missing_fields:
                        logger.error(f"[{session_id}] ❌ CRITICAL: RE_QUESTION 노드에 missing_fields가 없습니다! VALIDATION 노드가 제대로 설정하지 않았을 수 있습니다.")
                        logger.error(f"[{session_id}] result.keys(): {list(result.keys())}")
                        logger.error(f"[{session_id}] result 내용: {result}")
                    else:
                        logger.info(f"[{session_id}] ✅ RE_QUESTION 노드에 missing_fields 전달: {missing_fields}")
                
                next_node_func = node_map.get(next_state)
                if next_node_func:
                    # 다음 노드 실행 (result를 state로 전달)
                    try:
                        import sys
                        import os
                        msg = f"▶️  {next_state} 노드 실행 시작...\n"
                        os.write(2, msg.encode('utf-8'))
                        sys.stderr.write(msg)
                        sys.stderr.flush()
                        logger.info(f"▶️  {next_state} 노드 실행 시작...")
                        logger.info(f"[{session_id}] {next_state} 노드에 전달할 state keys: {list(result.keys())}")
                        logger.info(f"[{session_id}] {next_state} 노드에 전달할 missing_fields: {result.get('missing_fields', '없음')}")
                        next_result = next_node_func(result)
                        next_bot_msg = next_result.get('bot_message', '(없음)')
                        next_next_state = next_result.get('next_state', '(없음)')
                        msg = f"✅ {next_state} 노드 실행 완료\n💬 반환 bot_message: {next_bot_msg[:100] if isinstance(next_bot_msg, str) else next_bot_msg}\n➡️  반환 next_state: {next_next_state}\n"
                        os.write(2, msg.encode('utf-8'))
                        sys.stderr.write(msg)
                        sys.stderr.flush()
                        logger.info(f"✅ {next_state} 노드 실행 완료")
                        logger.info(f"💬 반환 bot_message: {next_bot_msg[:100] if isinstance(next_bot_msg, str) else next_bot_msg}")
                        logger.info(f"➡️  반환 next_state: {next_next_state}")
                        
                        # next_result의 모든 필드를 result에 병합 (덮어쓰기)
                        # bot_message는 반드시 병합 (더 엄격한 검증)
                        if "bot_message" in next_result and next_result["bot_message"]:
                            result["bot_message"] = next_result["bot_message"]
                            merged_msg = next_result['bot_message'][:100] if next_result['bot_message'] else '(빈 문자열)'
                            msg = f"✅ bot_message 병합 완료: {merged_msg}...\n"
                            os.write(2, msg.encode('utf-8'))
                            sys.stderr.write(msg)
                            sys.stderr.flush()
                            logger.info(f"✅ bot_message 병합 완료: {merged_msg}...")
                        else:
                            msg = f"⚠️  {next_state} 노드에서 bot_message가 없거나 비어있습니다!\n"
                            os.write(2, msg.encode('utf-8'))
                            sys.stderr.write(msg)
                            sys.stderr.flush()
                            logger.warning(f"⚠️  {next_state} 노드에서 bot_message가 없거나 비어있음!")
                            # bot_message가 없으면 기본 메시지 설정
                            result["bot_message"] = "추가 정보가 필요합니다." if next_state == "RE_QUESTION" else "처리 중입니다."
                            logger.warning(f"[{session_id}] ⚠️  기본 bot_message 설정: {result['bot_message']}")
                        
                        # expected_input 병합
                        if "expected_input" in next_result:
                            result["expected_input"] = next_result["expected_input"]
                        
                        # next_result의 다른 필드들도 병합 (conversation_history, current_question 등)
                        for key in ["conversation_history", "current_question", "skipped_fields", "asked_fields", "missing_fields", "facts"]:
                            if key in next_result:
                                result[key] = next_result[key]
                        
                        # next_result의 next_state가 있으면 업데이트
                        # 예: RE_QUESTION → FACT_COLLECTION 또는 RE_QUESTION → SUMMARY
                        if next_result.get("next_state"):
                            new_next_state = next_result["next_state"]
                            
                            # RE_QUESTION → SUMMARY 전이는 비정상적임 (missing_fields가 있어야 함)
                            # 이 경우 RE_QUESTION 노드의 bot_message를 보존해야 함
                            if next_state == "RE_QUESTION" and new_next_state == "SUMMARY":
                                logger.warning(f"[{session_id}] ⚠️  RE_QUESTION → SUMMARY 전이 감지 (비정상적). RE_QUESTION bot_message 보존: {result.get('bot_message', '(없음)')[:100]}")
                                # RE_QUESTION 노드의 bot_message를 보존
                                re_question_bot_message = result.get("bot_message", "")
                            
                            result["current_state"] = new_next_state
                            result["next_state"] = new_next_state
                            logger.info(f"[{session_id}] {next_state} → {new_next_state} 전이 (연쇄 전이)")
                            
                            # RE_QUESTION → SUMMARY 전이인 경우 SUMMARY 노드도 즉시 실행
                            if next_state == "RE_QUESTION" and new_next_state == "SUMMARY":
                                logger.info(f"[{session_id}] RE_QUESTION → SUMMARY 연쇄 전이 감지, SUMMARY 노드 즉시 실행")
                                summary_node_func = node_map.get("SUMMARY")
                                if summary_node_func:
                                    summary_result = summary_node_func(result)
                                    logger.info(f"[{session_id}] SUMMARY 노드 실행 완료")
                                    
                                    # SUMMARY 노드 결과 병합
                                    # 단, RE_QUESTION 노드의 bot_message가 있으면 우선 보존
                                    if re_question_bot_message and re_question_bot_message.strip():
                                        result["bot_message"] = re_question_bot_message
                                        logger.info(f"[{session_id}] RE_QUESTION bot_message 보존: {re_question_bot_message[:100]}...")
                                    elif "bot_message" in summary_result:
                                        result["bot_message"] = summary_result["bot_message"]
                                    
                                    for key in ["summary", "risk_tags", "completion_rate"]:
                                        if key in summary_result:
                                            result[key] = summary_result[key]
                                    
                                    if summary_result.get("next_state"):
                                        result["current_state"] = summary_result["next_state"]
                                        result["next_state"] = summary_result["next_state"]
                        else:
                            # next_state가 없으면 현재 next_state 유지 (RE_QUESTION → FACT_COLLECTION)
                            logger.info(f"[{session_id}] {next_state} 노드가 next_state를 반환하지 않음, 현재 next_state 유지: {next_state}")
                    except Exception as e:
                        import sys
                        import os
                        import traceback
                        error_msg = f"❌ {next_state} 노드 실행 중 오류: {e}\n"
                        os.write(2, error_msg.encode('utf-8'))
                        sys.stderr.write(error_msg)
                        sys.stderr.write(traceback.format_exc())
                        sys.stderr.flush()
                        logger.error(f"[{session_id}] ❌ {next_state} 노드 실행 중 오류 발생: {str(e)}", exc_info=True)
                        # 오류 발생 시 기본 메시지 설정
                        if not result.get("bot_message"):
                            result["bot_message"] = "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."
                            logger.warning(f"[{session_id}] ⚠️  기본 bot_message 설정: {result['bot_message']}")
                else:
                    import sys
                    import os
                    error_msg = f"❌ {next_state} 노드 함수를 찾을 수 없습니다! node_map keys: {list(node_map.keys())}\n"
                    os.write(2, error_msg.encode('utf-8'))
                    sys.stderr.write(error_msg)
                    sys.stderr.flush()
                    logger.error(f"[{session_id}] ❌ {next_state} 노드 함수를 찾을 수 없습니다!")
                    logger.error(f"[{session_id}] node_map keys: {list(node_map.keys())}")
                    if not result.get("bot_message"):
                        result["bot_message"] = "시스템 오류가 발생했습니다."
        elif "current_state" not in result:
            # current_state가 없으면 현재 상태 유지
            result["current_state"] = current_state
            logger.debug(f"[{session_id}] State 유지: {current_state}")
            logger.info(f"⏸️  State 유지: {current_state}")
        
        # current_state가 명시적으로 설정된 경우 확인
        if "current_state" in result and result["current_state"] != current_state:
            logger.info(f"[{session_id}] State 변경: {current_state} → {result['current_state']}")
            logger.info(f"🔄 State 변경: {current_state} → {result['current_state']}")
        
        logger.info("="*70)
        
        # _check_recursion_limit에서 이미 카운트를 증가시키므로 여기서는 증가하지 않음
        return result
    
    except Exception as e:
        session_id = state.get("session_id", "unknown")
        logger.error(f"[{session_id}] Graph step 실행 실패: {str(e)}", exc_info=True)
        _reset_session_step_count(session_id)
        raise


# 전역 그래프 인스턴스 (캐싱)
_graph_instance = None

# 세션별 실행 횟수 추적 (무한 루프 방지)
_session_step_count = {}


def get_graph() -> StateGraph:
    """
    그래프 인스턴스 획득 (싱글톤)
    
    Returns:
        컴파일된 StateGraph 인스턴스
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_graph()
    return _graph_instance


def _check_recursion_limit(session_id: str) -> bool:
    """
    재귀 제한 확인
    
    Args:
        session_id: 세션 ID
    
    Returns:
        제한 초과 여부 (True: 초과, False: 정상)
    """
    global _session_step_count
    recursion_limit = getattr(settings, 'graph_recursion_limit', DEFAULT_RECURSION_LIMIT)
    
    if session_id not in _session_step_count:
        _session_step_count[session_id] = 0
    
    _session_step_count[session_id] += 1
    
    if _session_step_count[session_id] > recursion_limit:
        logger.error(
            f"[{session_id}] 재귀 제한 초과: {_session_step_count[session_id]} > {recursion_limit}. "
            "무한 루프 가능성이 있습니다."
        )
        return True
    
    return False


def _reset_session_step_count(session_id: str):
    """세션별 실행 횟수 초기화"""
    global _session_step_count
    if session_id in _session_step_count:
        del _session_step_count[session_id]
