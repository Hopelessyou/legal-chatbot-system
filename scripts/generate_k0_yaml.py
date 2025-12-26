"""
K0 Intake 엑셀 → YAML 자동 생성 스크립트

엑셀 파일: excel/knowledge_base.xlsx (시트: K0_Intake)
출력: rag/K0_intake/intake_messages.yaml
"""
import sys
import os
import pandas as pd
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils import save_yaml
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# 엑셀 파일명 및 시트명 설정
EXCEL_FILE = "knowledge_base.xlsx"
SHEET_NAME = "K0_Intake"


def generate_k0_yaml(excel_file: str = None, sheet_name: str = None):
    """
    K0 Intake 엑셀 시트를 읽어서 YAML 파일 생성
    
    Args:
        excel_file: 엑셀 파일명 (기본값: knowledge_base.xlsx)
        sheet_name: 시트 이름 (기본값: K0_Intake)
    """
    excel_file = excel_file or EXCEL_FILE
    sheet_name = sheet_name or SHEET_NAME
    
    excel_path = project_root / "excel" / excel_file
    
    if not excel_path.exists():
        logger.error(f"엑셀 파일을 찾을 수 없습니다: {excel_path}")
        logger.info("엑셀 파일을 excel/ 폴더에 배치해주세요.")
        return
    
    logger.info(f"엑셀 파일 읽기: {excel_path} (시트: {sheet_name})")
    
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except ValueError as e:
        logger.error(f"시트 '{sheet_name}'를 찾을 수 없습니다.")
        logger.info(f"사용 가능한 시트 목록을 확인 중...")
        try:
            xl_file = pd.ExcelFile(excel_path)
            logger.info(f"사용 가능한 시트: {xl_file.sheet_names}")
        except:
            pass
        return
    
    # 필수 컬럼 확인
    required_columns = [
        "STEP_CODE", "MESSAGE_ORDER", "MESSAGE_TEXT",
        "ANSWER_TYPE", "NEXT_ACTION"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"필수 컬럼이 없습니다: {missing_columns}")
        logger.info(f"현재 컬럼: {list(df.columns)}")
        return
    
    # MESSAGE_ORDER로 정렬
    df = df.sort_values("MESSAGE_ORDER")
    
    # 메시지 목록 구성
    messages = []
    
    for _, r in df.iterrows():
        message_data = {
            "step_code": str(r["STEP_CODE"]),
            "order": int(r["MESSAGE_ORDER"]),
            "message_text": str(r["MESSAGE_TEXT"]),
            "answer_type": str(r["ANSWER_TYPE"]).lower() if pd.notna(r["ANSWER_TYPE"]) else "none",
            "next_action": str(r["NEXT_ACTION"]).upper() if pd.notna(r["NEXT_ACTION"]) else "CLASSIFY"
        }
        
        # 선택지가 있는 경우 추가 (DISAMBIGUATION_OPTIONS 컬럼이 있다면)
        if "DISAMBIGUATION_OPTIONS" in df.columns and pd.notna(r.get("DISAMBIGUATION_OPTIONS")):
            options_str = str(r["DISAMBIGUATION_OPTIONS"])
            message_data["options"] = [opt.strip() for opt in options_str.split(",") if opt.strip()]
        
        messages.append(message_data)
    
    # YAML 데이터 구성
    yaml_data = {
        "doc_id": "K0-INTAKE-001",
        "knowledge_type": "K0",
        "node_scope": ["INIT", "INTAKE"],
        "version": "v1.0",
        "messages": sorted(messages, key=lambda x: x["order"])
    }
    
    # 파일 경로 생성
    output_path = project_root / "data" / "rag" / "K0_intake" / "intake_messages.yaml"
    
    # YAML 저장
    save_yaml(yaml_data, str(output_path))
    logger.info(f"생성 완료: {output_path}")
    logger.info(f"총 {len(messages)}개의 K0 메시지가 생성되었습니다.")


if __name__ == "__main__":
    generate_k0_yaml()

