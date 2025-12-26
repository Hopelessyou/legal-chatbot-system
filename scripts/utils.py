"""
YAML 저장 공통 유틸 함수
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any


def save_yaml(data: Dict[str, Any], path: str):
    """
    YAML 파일 저장 (UTF-8 인코딩, 한글 지원)
    
    Args:
        data: 저장할 데이터 (딕셔너리)
        path: 저장할 파일 경로
    """
    # 디렉토리 생성
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # YAML 파일 저장
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2
        )

