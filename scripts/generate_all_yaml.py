"""
모든 엑셀 시트를 YAML로 변환하는 통합 스크립트

엑셀 파일: excel/knowledge_base.xlsx
시트:
1. K0_Intake → YAML (초기 인입 질문)
2. K1_Classification → YAML (분류 기준)
3. K2_Questions → YAML (질문 및 필수 필드)
4. LEVEL4_FACT_Pattern → YAML (사실 패턴)
5. K3_Risk_Rules → YAML (리스크 규칙)
6. K4_Output_Format → YAML (출력 포맷)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logging, get_logger
from scripts.generate_k0_yaml import generate_k0_yaml
from scripts.generate_k1_yaml import generate_k1_yaml
from scripts.generate_k2_yaml import generate_k2_yaml
from scripts.generate_fact_yaml import generate_fact_yaml
from scripts.generate_k3_yaml import generate_k3_yaml
from scripts.generate_k4_yaml import generate_k4_yaml

setup_logging()
logger = get_logger(__name__)

# 엑셀 파일명 설정
EXCEL_FILE = "knowledge_base.xlsx"


def generate_all_yaml(excel_file: str = None):
    """
    모든 엑셀 시트를 YAML로 변환
    
    Args:
        excel_file: 엑셀 파일명 (기본값: knowledge_base.xlsx)
    """
    excel_file = excel_file or EXCEL_FILE
    
    excel_path = project_root / "excel" / excel_file
    
    if not excel_path.exists():
        logger.error(f"엑셀 파일을 찾을 수 없습니다: {excel_path}")
        logger.info("엑셀 파일을 excel/ 폴더에 배치해주세요.")
        return
    
    logger.info("=" * 60)
    logger.info(f"엑셀 → YAML 변환 시작: {excel_file}")
    logger.info("=" * 60)
    
    try:
        # 1. K0 Intake 시트 → YAML
        logger.info("\n[1/6] K0 Intake 시트 → YAML 변환 중...")
        generate_k0_yaml(excel_file=excel_file)
        
        # 2. K1 Classification 시트 → YAML
        logger.info("\n[2/6] K1 Classification 시트 → YAML 변환 중...")
        generate_k1_yaml(excel_file=excel_file)
        
        # 3. K2 질문 시트 → YAML
        logger.info("\n[3/6] K2 질문 시트 → YAML 변환 중...")
        generate_k2_yaml(excel_file=excel_file)
        
        # 4. LEVEL4 FACT 시트 → YAML
        logger.info("\n[4/6] LEVEL4 FACT 시트 → YAML 변환 중...")
        generate_fact_yaml(excel_file=excel_file)
        
        # 5. K3 리스크 규칙 시트 → YAML
        logger.info("\n[5/6] K3 리스크 규칙 시트 → YAML 변환 중...")
        generate_k3_yaml(excel_file=excel_file)
        
        # 6. K4 출력 포맷 시트 → YAML
        logger.info("\n[6/6] K4 출력 포맷 시트 → YAML 변환 중...")
        generate_k4_yaml(excel_file=excel_file)
        
        logger.info("\n" + "=" * 60)
        logger.info("모든 변환 완료!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"변환 중 오류 발생: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    generate_all_yaml()

