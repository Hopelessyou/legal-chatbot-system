"""
각 노드가 순차적으로 작동하는지 테스트하는 스크립트

사용법:
    python tests/test_nodes_sequential.py
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.langgraph.state import StateContext, create_initial_context
from src.utils.helpers import generate_session_id
from src.langgraph.nodes import (
    init_node,
    case_classification_node,
    fact_collection_node,
    validation_node,
    re_question_node,
    summary_node,
    completed_node
)
from src.langgraph.graph import run_graph_step
from src.utils.logger import get_logger
from src.services.session_manager import save_session_state, load_session_state
import json
from typing import Dict, Any

logger = get_logger(__name__)


def print_state_summary(state: StateContext, node_name: str):
    """State 상태 요약 출력"""
    print("\n" + "="*70)
    print(f"📍 [{node_name}] 실행 후 State 요약")
    print("="*70)
    print(f"  세션 ID: {state.get('session_id', 'N/A')}")
    print(f"  현재 State: {state.get('current_state', 'N/A')}")
    print(f"  다음 State: {state.get('next_state', 'N/A')}")
    print(f"  사건 유형: {state.get('case_type', 'N/A')} / {state.get('sub_case_type', 'N/A')}")
    print(f"  완성도: {state.get('completion_rate', 0)}%")
    
    # Bot 메시지 안전하게 처리
    bot_message = state.get('bot_message')
    if bot_message:
        bot_msg_display = bot_message[:100] + "..." if len(bot_message) > 100 else bot_message
    else:
        bot_msg_display = "(없음)"
    print(f"  Bot 메시지: {bot_msg_display}")
    
    print(f"  누락 필드: {state.get('missing_fields', [])}")
    print(f"  질문한 필드: {state.get('asked_fields', [])}")
    print(f"  건너뛴 필드: {state.get('skipped_fields', [])}")
    print(f"  대화 기록 수: {len(state.get('conversation_history', []))}")
    print(f"  Facts: {list(state.get('facts', {}).keys())}")
    print("="*70 + "\n")


def validate_state(state: StateContext, node_name: str) -> bool:
    """
    State 유효성 검증
    
    Args:
        state: 검증할 State
        node_name: 노드 이름
    
    Returns:
        검증 결과 (True: 유효, False: 무효)
    """
    try:
        from src.langgraph.state import StateContextModel
        StateContextModel(**state)
        return True
    except Exception as e:
        print(f"⚠️  [{node_name}] State 검증 실패: {str(e)}")
        return False


def test_node(node_func, state: StateContext, node_name: str, expected_next_state: str = None) -> StateContext:
    """
    단일 노드 테스트
    
    Args:
        node_func: 실행할 노드 함수
        state: 현재 State
        node_name: 노드 이름
        expected_next_state: 예상되는 다음 State (검증용)
    
    Returns:
        업데이트된 State
    """
    try:
        print(f"\n{'='*70}")
        print(f"🧪 [{node_name}] 노드 테스트 시작")
        print(f"{'='*70}")
        print(f"입력 State: current_state={state.get('current_state')}")
        
        # 입력 State 검증
        if not validate_state(state, f"{node_name} (입력)"):
            print(f"⚠️  [{node_name}] 입력 State 검증 실패했지만 계속 진행합니다...")
        
        # 노드 실행
        print(f"▶️  [{node_name}] 노드 실행 중...")
        result = node_func(state)
        
        # 결과 확인
        if not isinstance(result, dict):
            print(f"❌ [{node_name}] 반환값이 dict가 아닙니다: {type(result)}")
            return state
        
        # 출력 State 검증
        if not validate_state(result, f"{node_name} (출력)"):
            print(f"⚠️  [{node_name}] 출력 State 검증 실패했지만 계속 진행합니다...")
        
        # conversation_history가 있으면 DB에 저장 (실제 웹과 동일하게)
        # 실제 웹에서는 chat.py에서 save_session_state 호출
        session_id = result.get("session_id", state.get("session_id"))
        if session_id and session_id.startswith("sess_"):
            try:
                save_session_state(session_id, result)
                conv_history_count = len(result.get("conversation_history", []))
                if conv_history_count > 0:
                    logger.debug(f"테스트: conversation_history 저장 완료 ({conv_history_count}개 Q-A 쌍)")
                    # 저장 후 복원 테스트 (실제 웹과 동일한 동작 확인)
                    restored_state = load_session_state(session_id)
                    if restored_state:
                        restored_count = len(restored_state.get("conversation_history", []))
                        if restored_count == conv_history_count:
                            logger.debug(f"테스트: conversation_history 복원 확인 완료 ({restored_count}개 Q-A 쌍)")
                        else:
                            logger.warning(f"테스트: conversation_history 복원 불일치 (저장: {conv_history_count}, 복원: {restored_count})")
            except Exception as e:
                logger.warning(f"테스트: conversation_history 저장/복원 실패 (무시): {str(e)}")
        
        # next_state 확인
        next_state = result.get('next_state')
        current_state = result.get('current_state', state.get('current_state'))
        
        print(f"✅ [{node_name}] 실행 완료")
        print(f"   현재 State: {current_state}")
        print(f"   다음 State: {next_state}")
        
        if expected_next_state and next_state != expected_next_state:
            print(f"⚠️  경고: 예상한 다음 State는 '{expected_next_state}'이지만 '{next_state}'가 반환되었습니다.")
        
        # 필수 필드 확인
        required_fields = ["session_id", "current_state"]
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            print(f"⚠️  경고: 필수 필드가 누락되었습니다: {missing_fields}")
        
        # State 요약 출력
        print_state_summary(result, node_name)
        
        return result
        
    except Exception as e:
        print(f"\n❌ [{node_name}] 노드 실행 중 오류 발생:")
        print(f"   오류 타입: {type(e).__name__}")
        print(f"   오류 메시지: {str(e)}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시 기존 state 반환
        return state


def test_sequential_flow(use_run_graph_step: bool = False):
    """순차적으로 모든 노드를 테스트
    
    Args:
        use_run_graph_step: True면 run_graph_step 사용 (실제 웹과 동일), False면 노드 직접 호출
    """
    print("\n" + "="*70)
    print("🚀 LangGraph 노드 순차 실행 테스트 시작")
    if use_run_graph_step:
        print("📌 모드: run_graph_step 사용 (실제 웹과 동일)")
    else:
        print("📌 모드: 노드 직접 호출")
    print("="*70)
    
    # 1. 초기 State 생성 및 DB 세션 생성 (실제 웹과 동일하게)
    try:
        from src.services.session_manager import SessionManager
        # DB에 세션 생성
        session_id = SessionManager.create_session(channel="test")
        # 생성된 세션 ID로 State 생성
        state = create_initial_context(session_id)
        logger.info(f"테스트: DB 세션 생성 완료 (session_id: {session_id})")
    except Exception as e:
        logger.warning(f"테스트: DB 세션 생성 실패, 메모리에서만 테스트 진행: {str(e)}")
        # DB 세션 생성 실패 시 메모리에서만 테스트
        session_id = generate_session_id()
        state = create_initial_context(session_id)
    
    print(f"\n✅ 초기 State 생성 완료 (session_id: {session_id})")
    print_state_summary(state, "INITIAL")
    
    if use_run_graph_step:
        # run_graph_step을 사용하는 경우 (실제 웹과 동일)
        # 2. INIT 노드 테스트
        state["current_state"] = "INIT"
        state = test_node(run_graph_step, state, "INIT (run_graph_step)", expected_next_state="CASE_CLASSIFICATION")
        
        # INIT 노드가 CASE_CLASSIFICATION으로 전이하지 않으면 사용자 입력 시뮬레이션
        if state.get("current_state") == "INIT":
            state["last_user_input"] = "어제 음주운전 사고를 냈어요"
            state = test_node(run_graph_step, state, "INIT (사용자 입력 포함, run_graph_step)", expected_next_state="CASE_CLASSIFICATION")
        
        # 3. CASE_CLASSIFICATION 노드 테스트
        state["current_state"] = "CASE_CLASSIFICATION"
        state["last_user_input"] = "어제 음주운전 사고를 냈어요"
        state = test_node(run_graph_step, state, "CASE_CLASSIFICATION (run_graph_step)", expected_next_state="FACT_COLLECTION")
        
        # 4. FACT_COLLECTION 노드 테스트
        state["current_state"] = "FACT_COLLECTION"
        state["last_user_input"] = "음주운전을 하다가 전봇대를 박았어요. 피해금액은 약 500만원입니다."
        state = test_node(run_graph_step, state, "FACT_COLLECTION (run_graph_step)", expected_next_state="VALIDATION")
        
        # 5. VALIDATION 노드 테스트 (체인 실행 로직 테스트)
        state["current_state"] = "VALIDATION"
        state["last_user_input"] = "어제"
        # missing_fields를 강제로 설정하여 RE_QUESTION으로 전이하도록 함
        state["missing_fields"] = ["location", "counterparty"]  # 테스트용
        state = test_node(run_graph_step, state, "VALIDATION (run_graph_step, 체인 실행 테스트)", expected_next_state=None)
        
        # 6. RE_QUESTION 노드 테스트 (체인 실행으로 이미 실행되었을 수 있음)
        if state.get("current_state") == "RE_QUESTION":
            state["current_state"] = "RE_QUESTION"
            state["last_user_input"] = ""
            state = test_node(run_graph_step, state, "RE_QUESTION (run_graph_step)", expected_next_state=None)
        
        # 7. SUMMARY 노드 테스트
        if state.get("current_state") == "SUMMARY":
            state["current_state"] = "SUMMARY"
            state["last_user_input"] = ""
            state = test_node(run_graph_step, state, "SUMMARY (run_graph_step)", expected_next_state="COMPLETED")
        
        # 8. COMPLETED 노드 테스트
        if state.get("current_state") == "COMPLETED":
            state["current_state"] = "COMPLETED"
            state["last_user_input"] = ""
            state = test_node(run_graph_step, state, "COMPLETED (run_graph_step)", expected_next_state=None)
    else:
        # 노드를 직접 호출하는 경우 (기존 방식)
        # 2. INIT 노드 테스트
        state["current_state"] = "INIT"
        state = test_node(init_node, state, "INIT", expected_next_state="CASE_CLASSIFICATION")
        
        # INIT 노드가 CASE_CLASSIFICATION으로 전이하지 않으면 사용자 입력 시뮬레이션
        if state.get("current_state") == "INIT":
            state["last_user_input"] = "어제 음주운전 사고를 냈어요"
            state = test_node(init_node, state, "INIT (사용자 입력 포함)", expected_next_state="CASE_CLASSIFICATION")
        
        # 3. CASE_CLASSIFICATION 노드 테스트
        state["current_state"] = "CASE_CLASSIFICATION"
        state["last_user_input"] = "어제 음주운전 사고를 냈어요"
        state = test_node(case_classification_node, state, "CASE_CLASSIFICATION", expected_next_state="FACT_COLLECTION")
        
        # 4. FACT_COLLECTION 노드 테스트
        state["current_state"] = "FACT_COLLECTION"
        state["last_user_input"] = "음주운전을 하다가 전봇대를 박았어요. 피해금액은 약 500만원입니다."
        state = test_node(fact_collection_node, state, "FACT_COLLECTION", expected_next_state="VALIDATION")
        
        # 5. VALIDATION 노드 테스트
        state["current_state"] = "VALIDATION"
        state["last_user_input"] = "어제"
        state = test_node(validation_node, state, "VALIDATION", expected_next_state=None)  # RE_QUESTION 또는 SUMMARY
        
        next_state = state.get("next_state")
        
        # 6-1. RE_QUESTION 노드 테스트 (VALIDATION이 RE_QUESTION으로 전이한 경우)
        if next_state == "RE_QUESTION":
            state["current_state"] = "RE_QUESTION"
            state["last_user_input"] = ""  # RE_QUESTION은 추가 질문만 생성
            state = test_node(re_question_node, state, "RE_QUESTION", expected_next_state=None)
            
            # RE_QUESTION 후 다시 사용자 입력으로 VALIDATION으로 가는 시뮬레이션
            if state.get("next_state") != "SUMMARY":
                state["current_state"] = "VALIDATION"
                state["last_user_input"] = "2024년 1월 1일"
                state = test_node(validation_node, state, "VALIDATION (추가 입력)", expected_next_state=None)
        
        # 7. SUMMARY 노드 테스트
        state["current_state"] = "SUMMARY"
        state["last_user_input"] = ""
        state = test_node(summary_node, state, "SUMMARY", expected_next_state="COMPLETED")
        
        # 8. COMPLETED 노드 테스트
        state["current_state"] = "COMPLETED"
        state["last_user_input"] = ""
        state = test_node(completed_node, state, "COMPLETED", expected_next_state=None)
    
    # 최종 결과 출력
    print("\n" + "="*70)
    print("✅ 모든 노드 순차 실행 테스트 완료")
    print("="*70)
    
    # 최종 conversation_history DB 저장 확인
    final_session_id = state.get("session_id")
    if final_session_id and final_session_id.startswith("sess_"):
        try:
            # DB에서 최종 상태 로드하여 conversation_history 확인
            final_state = load_session_state(final_session_id)
            if final_state:
                db_conv_history = final_state.get("conversation_history", [])
                test_conv_history = state.get("conversation_history", [])
                print(f"\n📋 conversation_history 저장/복원 확인:")
                print(f"   테스트 State: {len(test_conv_history)}개 Q-A 쌍")
                print(f"   DB에서 복원: {len(db_conv_history)}개 Q-A 쌍")
                if len(db_conv_history) == len(test_conv_history):
                    print(f"   ✅ 저장/복원 일치")
                else:
                    print(f"   ⚠️  저장/복원 불일치")
        except Exception as e:
            logger.warning(f"최종 conversation_history 확인 실패: {str(e)}")
    
    print(f"\n최종 State:")
    print(json.dumps({
        "session_id": state.get("session_id"),
        "current_state": state.get("current_state"),
        "case_type": state.get("case_type"),
        "sub_case_type": state.get("sub_case_type"),
        "completion_rate": state.get("completion_rate"),
        "missing_fields_count": len(state.get("missing_fields", [])),
        "conversation_history_count": len(state.get("conversation_history", [])),
        "bot_message": state.get("bot_message", "")[:200] if state.get("bot_message") else None
    }, indent=2, ensure_ascii=False))
    print("="*70 + "\n")


def test_individual_nodes():
    """각 노드를 개별적으로 테스트"""
    print("\n" + "="*70)
    print("🔬 개별 노드 테스트 모드")
    print("="*70)
    
    # 각 노드별로 독립적인 테스트
    test_cases = [
        {
            "name": "INIT",
            "node": init_node,
            "setup": lambda: create_initial_context(generate_session_id())
        },
        {
            "name": "CASE_CLASSIFICATION",
            "node": case_classification_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "CASE_CLASSIFICATION",
                "last_user_input": "어제 음주운전 사고를 냈어요"
            }
        },
        {
            "name": "FACT_COLLECTION",
            "node": fact_collection_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "FACT_COLLECTION",
                "case_type": "CRIMINAL",
                "sub_case_type": "음주운전",
                "last_user_input": "음주운전을 하다가 전봇대를 박았어요",
                "initial_description": "어제 음주운전 사고를 냈어요",
                "skipped_fields": ["incident_date"],
                "missing_fields": ["location", "amount", "counterparty"]
            }
        },
        {
            "name": "VALIDATION",
            "node": validation_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "VALIDATION",
                "case_type": "CRIMINAL",
                "sub_case_type": "음주운전",
                "last_user_input": "어제",
                "conversation_history": [
                    {"field": "incident_date", "question": "사건이 발생한 날짜는?", "answer": "어제"}
                ],
                "skipped_fields": ["incident_date"],
                "missing_fields": ["location", "amount", "counterparty"]
            }
        },
        {
            "name": "RE_QUESTION",
            "node": re_question_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "RE_QUESTION",
                "case_type": "CRIMINAL",
                "sub_case_type": "음주운전",
                "missing_fields": ["location", "amount", "counterparty"],
                "asked_fields": ["incident_date"],
                "skipped_fields": ["incident_date"],
                "conversation_history": [
                    {"field": "incident_date", "question": "사건이 발생한 날짜는?", "answer": "어제"}
                ]
            }
        },
        {
            "name": "SUMMARY",
            "node": summary_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "SUMMARY",
                "case_type": "CRIMINAL",
                "sub_case_type": "음주운전",
                "facts": {"incident_date": "2024-01-01", "location": "서울", "amount": "5000000"},
                "conversation_history": [
                    {"field": "incident_date", "question": "사건이 발생한 날짜는?", "answer": "어제"},
                    {"field": "location", "question": "사건 발생 장소는?", "answer": "서울"},
                    {"field": "amount", "question": "피해금액은?", "answer": "500만원"}
                ],
                "completion_rate": 80
            }
        },
        {
            "name": "COMPLETED",
            "node": completed_node,
            "setup": lambda: {
                **create_initial_context(generate_session_id()),
                "current_state": "COMPLETED",
                "bot_message": "모든 정보 수집이 완료되었습니다."
            }
        }
    ]
    
    for test_case in test_cases:
        try:
            state = test_case["setup"]()
            test_node(test_case["node"], state, test_case["name"])
        except Exception as e:
            print(f"\n❌ [{test_case['name']}] 노드 테스트 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph 노드 순차 실행 테스트")
    parser.add_argument(
        "--mode",
        choices=["sequential", "individual", "both"],
        default="both",
        help="테스트 모드 선택: sequential (순차 실행), individual (개별 테스트), both (둘 다)"
    )
    parser.add_argument(
        "--use-graph-step",
        action="store_true",
        help="run_graph_step 사용 (실제 웹과 동일한 방식으로 테스트)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode in ["sequential", "both"]:
            test_sequential_flow(use_run_graph_step=args.use_graph_step)
        
        if args.mode in ["individual", "both"]:
            test_individual_nodes()
        
        print("\n✅ 모든 테스트 완료!\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 사용자에 의해 중단되었습니다.\n")
    except Exception as e:
        print(f"\n\n❌ 테스트 실행 중 치명적 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
