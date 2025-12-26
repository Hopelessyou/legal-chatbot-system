"""
K2 질문 엑셀 → YAML 자동 생성 스크립트

엑셀 파일: excel/knowledge_base.xlsx (시트: K2_Questions)
출력: rag/K2_required_fields/{level1}/{scenario}_required.yaml
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
SHEET_NAME = "K2_Questions"


def generate_k2_yaml(excel_file: str = None, sheet_name: str = None):
    """
    K2 질문 엑셀 시트를 읽어서 YAML 파일 생성
    
    Args:
        excel_file: 엑셀 파일명 (기본값: knowledge_base.xlsx)
        sheet_name: 시트 이름 (기본값: K2_Questions)
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
        "LEVEL1", "LEVEL2_CODE", "LEVEL3_SCENARIO_CODE",
        "QUESTION_ORDER", "FIELD_KEY", "QUESTION_TEXT",
        "ANSWER_TYPE", "REQUIRED"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"필수 컬럼이 없습니다: {missing_columns}")
        logger.info(f"현재 컬럼: {list(df.columns)}")
        return
    
    # 그룹화: LEVEL1, LEVEL2_CODE, LEVEL3_SCENARIO_CODE
    grouped = df.groupby(["LEVEL1", "LEVEL2_CODE", "LEVEL3_SCENARIO_CODE"])
    
    generated_count = 0
    
    for (level1, level2, scenario), rows in grouped:
        questions = []
        required_fields = []
        
        for _, r in rows.iterrows():
            # 질문 정보 추가
            question_data = {
                "order": int(r["QUESTION_ORDER"]),
                "field": str(r["FIELD_KEY"]),
                "question": str(r["QUESTION_TEXT"]),
                "answer_type": str(r["ANSWER_TYPE"]),
                "required": bool(r["REQUIRED"])
            }
            questions.append(question_data)
            
            # 필수 필드 목록에 추가
            if r["REQUIRED"]:
                field_key = str(r["FIELD_KEY"])
                if field_key not in required_fields:
                    required_fields.append(field_key)
        
        # YAML 데이터 구성
        yaml_data = {
            "doc_id": f"K2-{scenario}",
            "knowledge_type": "K2",
            "level1": str(level1),
            "level2": str(level2),
            "scenario": str(scenario),
            "required_fields": list(set(required_fields)),  # 중복 제거
            "questions": sorted(questions, key=lambda x: x["order"])
        }
        
        # 파일 경로 생성
        level1_lower = str(level1).lower()
        scenario_lower = str(scenario).lower()
        output_path = project_root / "data" / "rag" / "K2_required_fields" / level1_lower / f"{scenario_lower}_required.yaml"
        
        # YAML 저장
        save_yaml(yaml_data, str(output_path))
        logger.info(f"생성 완료: {output_path}")
        generated_count += 1
    
    logger.info(f"총 {generated_count}개의 K2 YAML 파일이 생성되었습니다.")


if __name__ == "__main__":
    generate_k2_yaml()

