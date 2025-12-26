"""
K1 Classification 엑셀 → YAML 자동 생성 스크립트

엑셀 파일: excel/knowledge_base.xlsx (시트: K1_Classification)
출력: rag/K1_case_type/{level1}/{level2_code}_classification.yaml
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
SHEET_NAME = "K1_Classification"


def generate_k1_yaml(excel_file: str = None, sheet_name: str = None):
    """
    K1 Classification 엑셀 시트를 읽어서 YAML 파일 생성
    
    Args:
        excel_file: 엑셀 파일명 (기본값: knowledge_base.xlsx)
        sheet_name: 시트 이름 (기본값: K1_Classification)
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
        "LEVEL1", "LEVEL2_CODE", "LEVEL2_NAME",
        "LEVEL3_SCENARIO_CODE", "LEVEL3_SCENARIO_NAME"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"필수 컬럼이 없습니다: {missing_columns}")
        logger.info(f"현재 컬럼: {list(df.columns)}")
        return
    
    # 그룹화: LEVEL1, LEVEL2_CODE
    grouped = df.groupby(["LEVEL1", "LEVEL2_CODE"])
    
    generated_count = 0
    
    for (level1, level2_code), rows in grouped:
        scenarios = []
        
        for _, r in rows.iterrows():
            scenario_data = {
                "scenario_code": str(r["LEVEL3_SCENARIO_CODE"]),
                "scenario_name": str(r["LEVEL3_SCENARIO_NAME"])
            }
            
            # 키워드 처리
            if "KEYWORDS" in df.columns and pd.notna(r.get("KEYWORDS")):
                keywords_str = str(r["KEYWORDS"])
                scenario_data["keywords"] = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
            
            # 전형적 표현 처리
            if "TYPICAL_EXPRESSIONS" in df.columns and pd.notna(r.get("TYPICAL_EXPRESSIONS")):
                expressions_str = str(r["TYPICAL_EXPRESSIONS"])
                scenario_data["typical_expressions"] = [exp.strip() for exp in expressions_str.split(",") if exp.strip()]
            
            # 애매할 때 확인 질문
            if "DISAMBIGUATION_QUESTION" in df.columns and pd.notna(r.get("DISAMBIGUATION_QUESTION")):
                scenario_data["disambiguation_question"] = str(r["DISAMBIGUATION_QUESTION"])
            
            # 확인 질문 선택지
            if "DISAMBIGUATION_OPTIONS" in df.columns and pd.notna(r.get("DISAMBIGUATION_OPTIONS")):
                options_str = str(r["DISAMBIGUATION_OPTIONS"])
                scenario_data["disambiguation_options"] = [opt.strip() for opt in options_str.split(",") if opt.strip()]
            
            scenarios.append(scenario_data)
        
        # YAML 데이터 구성
        level2_name = str(rows.iloc[0]["LEVEL2_NAME"])
        
        yaml_data = {
            "doc_id": f"K1-{level1}-{level2_code}",
            "knowledge_type": "K1",
            "level1": str(level1),
            "level2_code": str(level2_code),
            "level2_name": level2_name,
            "node_scope": ["CASE_CLASSIFICATION"],
            "version": "v1.0",
            "scenarios": scenarios
        }
        
        # 키워드 통합 (모든 시나리오의 키워드를 모음)
        all_keywords = []
        all_expressions = []
        for scenario in scenarios:
            if "keywords" in scenario:
                all_keywords.extend(scenario["keywords"])
            if "typical_expressions" in scenario:
                all_expressions.extend(scenario["typical_expressions"])
        
        if all_keywords:
            yaml_data["typical_keywords"] = list(set(all_keywords))  # 중복 제거
        
        if all_expressions:
            yaml_data["typical_expressions"] = list(set(all_expressions))  # 중복 제거
        
        # 파일 경로 생성
        level1_lower = str(level1).lower()
        level2_lower = str(level2_code).lower()
        output_path = project_root / "data" / "rag" / "K1_case_type" / level1_lower / f"{level2_lower}_classification.yaml"
        
        # YAML 저장
        save_yaml(yaml_data, str(output_path))
        logger.info(f"생성 완료: {output_path}")
        generated_count += 1
    
    logger.info(f"총 {generated_count}개의 K1 YAML 파일이 생성되었습니다.")


if __name__ == "__main__":
    generate_k1_yaml()

