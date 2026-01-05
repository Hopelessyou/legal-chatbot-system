# Scripts 검토 보고서

## 검토 대상
- 스크립트 디렉토리: `scripts/`
- 검토 일자: 2024년
- 검토 범위: DB 설정 스크립트, 데이터 생성 스크립트, 유틸리티 스크립트

---

## ✅ 정상 동작 부분

### 1. 스크립트 구조
- ✅ **Python 스크립트**: 17개 파일
- ✅ **PowerShell 스크립트**: 12개 파일
- ✅ **텍스트 파일**: 3개 파일 (설정 가이드)
- ✅ **utils.py**: 공통 유틸리티 함수 제공 (`save_yaml`)

### 2. DB 설정 스크립트
- ✅ **create_db.py**: PostgreSQL 데이터베이스 생성
- ✅ **create_db_mysql.py**: MySQL 데이터베이스 생성 (간단 버전)
- ✅ **create_db_mysql.py** (다른 버전): MySQL 데이터베이스 생성 (사용자 생성 포함)
- ✅ **init_db.py**: 데이터베이스 초기화 (DDL 실행)
- ✅ **check_db_setup.py**: 데이터베이스 설정 상태 확인

### 3. 데이터 생성 스크립트
- ✅ **generate_all_yaml.py**: 모든 엑셀 시트를 YAML로 변환하는 통합 스크립트
- ✅ **generate_k0_yaml.py**: K0 Intake 시트 → YAML
- ✅ **generate_k1_yaml.py**: K1 Classification 시트 → YAML
- ✅ **generate_k2_yaml.py**: K2 Questions 시트 → YAML
- ✅ **generate_k3_yaml.py**: K3 Risk Rules 시트 → YAML
- ✅ **generate_k4_yaml.py**: K4 Output Format 시트 → YAML
- ✅ **generate_fact_yaml.py**: LEVEL4 FACT 시트 → YAML

### 4. RAG 인덱싱 스크립트
- ✅ **index_rag_documents.py**: RAG 문서 인덱싱 스크립트
  - `--clear` 옵션으로 기존 인덱스 초기화 지원
  - 재귀적 디렉토리 인덱싱 지원

### 5. 디버깅/확인 스크립트
- ✅ **check_session_db.py**: 세션 DB 확인
- ✅ **check_summary.py**: 요약 확인
- ✅ **debug_db_url.py**: DB URL 디버깅

### 6. PowerShell 스크립트
- ✅ **create_db_mysql.ps1**: MySQL DB 생성 (PowerShell)
- ✅ **setup_db_commands.ps1**: DB 설정 명령어
- ✅ **test_mysql_connection.ps1**: MySQL 연결 테스트

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중간**: 스크립트 중복 및 일관성 부족

**문제**: 같은 기능을 수행하는 스크립트가 여러 개 존재합니다.

**영향도**: 중간  
**위험성**: 
- 사용자가 어떤 스크립트를 사용해야 할지 혼란
- 유지보수 어려움
- 버전 불일치 가능성

**현재 상황**:
- `create_db.py`: PostgreSQL용
- `create_db_mysql.py`: MySQL용 (2개 버전 존재)
- `create_db_mysql.ps1`: PowerShell 버전
- `create_db_simple.ps1`: 간단 버전
- `create_db_mysql_cli.ps1`: CLI 버전

**수정 권장**: 
1. **통합 스크립트 생성**: 데이터베이스 타입을 자동 감지하거나 인자로 받는 통합 스크립트
2. **README 문서화**: 각 스크립트의 용도와 사용 시나리오 명시
3. **Deprecated 표시**: 사용하지 않는 스크립트에 명시

**예제**:
```python
# scripts/create_db.py (통합 버전)
"""
데이터베이스 생성 통합 스크립트
PostgreSQL과 MySQL을 모두 지원
"""
import argparse
from urllib.parse import urlparse
from config.settings import settings

def create_database(db_type=None):
    """데이터베이스 생성 (타입 자동 감지 또는 명시)"""
    db_url = settings.database_url
    parsed = urlparse(db_url)
    
    # DB 타입 자동 감지
    if not db_type:
        if 'postgresql' in parsed.scheme:
            db_type = 'postgresql'
        elif 'mysql' in parsed.scheme:
            db_type = 'mysql'
        else:
            raise ValueError(f"지원하지 않는 데이터베이스 타입: {parsed.scheme}")
    
    if db_type == 'postgresql':
        from scripts.db.postgresql import create_postgresql_db
        create_postgresql_db()
    elif db_type == 'mysql':
        from scripts.db.mysql import create_mysql_db
        create_mysql_db()
    else:
        raise ValueError(f"지원하지 않는 데이터베이스 타입: {db_type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="데이터베이스 생성")
    parser.add_argument("--type", choices=["postgresql", "mysql"], help="데이터베이스 타입")
    args = parser.parse_args()
    create_database(args.type)
```

---

### 2. 🟡 **중간**: 에러 처리 및 로깅 일관성 부족

**문제**: 스크립트마다 에러 처리 방식이 다릅니다.

**영향도**: 중간  
**위험성**: 
- 일부 스크립트는 에러를 무시하고 계속 진행
- 일부 스크립트는 즉시 종료
- 디버깅 어려움

**현재 상황**:
- `init_db.py`: 일부 에러는 무시 (`already exists`), 나머지는 raise
- `create_db_mysql.py`: 모든 에러를 raise
- `index_rag_documents.py`: 에러 발생 시 raise

**수정 권장**: 
```python
# 공통 에러 처리 유틸리티
# scripts/utils.py 확장
import sys
from src.utils.logger import get_logger

logger = get_logger(__name__)

def handle_script_error(error: Exception, script_name: str, exit_code: int = 1):
    """
    스크립트 에러 처리 공통 함수
    
    Args:
        error: 발생한 예외
        script_name: 스크립트 이름
        exit_code: 종료 코드
    """
    logger.error(f"[{script_name}] 오류 발생: {str(error)}", exc_info=True)
    print(f"\n❌ {script_name} 실행 실패: {str(error)}")
    print("\n해결 방법:")
    print("1. 로그 파일 확인: logs/app.log")
    print("2. 환경 변수 확인: .env 파일")
    print("3. 데이터베이스 연결 확인")
    sys.exit(exit_code)

def safe_execute(func, script_name: str):
    """
    안전한 스크립트 실행 래퍼
    
    Args:
        func: 실행할 함수
        script_name: 스크립트 이름
    """
    try:
        return func()
    except Exception as e:
        handle_script_error(e, script_name)
```

---

### 3. 🟡 **중간**: 스크립트 실행 방법 문서화 부족

**문제**: 스크립트 실행 방법과 의존성이 명확히 문서화되어 있지 않습니다.

**영향도**: 중간  
**위험성**: 
- 사용자가 스크립트를 올바르게 실행하지 못함
- 필수 환경 변수나 의존성 누락

**수정 권장**: 
1. **README.md 생성**: `scripts/README.md`
2. **각 스크립트에 docstring 추가**: 사용법, 인자, 예제 포함

**예제**:
```markdown
# scripts/README.md

## 스크립트 목록

### 데이터베이스 설정

#### 1. 데이터베이스 생성
```bash
# PostgreSQL
python scripts/create_db.py

# MySQL
python scripts/create_db_mysql.py
```

#### 2. 데이터베이스 초기화 (테이블 생성)
```bash
python scripts/init_db.py
```

#### 3. 데이터베이스 설정 확인
```bash
python scripts/check_db_setup.py
```

### 데이터 생성

#### 엑셀 → YAML 변환
```bash
# 모든 시트 변환
python scripts/generate_all_yaml.py

# 개별 시트 변환
python scripts/generate_k0_yaml.py
python scripts/generate_k1_yaml.py
# ...
```

### RAG 인덱싱

```bash
# RAG 문서 인덱싱
python scripts/index_rag_documents.py

# 기존 인덱스 초기화 후 재인덱싱
python scripts/index_rag_documents.py --clear
```

## 필수 환경 변수

- `DATABASE_URL`: 데이터베이스 연결 URL
- `OPENAI_API_KEY`: OpenAI API 키 (RAG 인덱싱 시)
```

---

### 4. 🟢 **낮음**: 스크립트 실행 권한 확인 없음

**문제**: 스크립트가 실행 권한이나 필수 조건을 확인하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```python
# scripts/utils.py 확장
import os
import sys
from pathlib import Path
from config.settings import settings

def check_prerequisites():
    """스크립트 실행 전 필수 조건 확인"""
    errors = []
    
    # 1. 환경 변수 확인
    if not settings.database_url:
        errors.append("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    # 2. 디렉토리 확인
    required_dirs = [
        Path("data/rag"),
        Path("migrations"),
    ]
    for dir_path in required_dirs:
        if not dir_path.exists():
            errors.append(f"필수 디렉토리가 없습니다: {dir_path}")
    
    # 3. 파일 확인
    required_files = [
        Path("migrations/versions/001_initial_schema.sql"),
    ]
    for file_path in required_files:
        if not file_path.exists():
            errors.append(f"필수 파일이 없습니다: {file_path}")
    
    if errors:
        print("❌ 스크립트 실행 전 필수 조건을 확인하세요:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    return True
```

---

### 5. 🟢 **낮음**: PowerShell 스크립트 실행 정책 확인 없음

**문제**: PowerShell 스크립트가 실행 정책을 확인하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 
```powershell
# scripts/create_db_mysql.ps1 시작 부분에 추가
#Requires -Version 5.1

# 실행 정책 확인
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "❌ PowerShell 실행 정책이 'Restricted'로 설정되어 있습니다." -ForegroundColor Red
    Write-Host "다음 명령어로 실행 정책을 변경하세요:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
    exit 1
}
```

---

### 6. 🟢 **낮음**: 스크립트 테스트 부족

**문제**: 스크립트에 대한 테스트가 없습니다.

**영향도**: 낮음  
**수정 권장**: 
```python
# tests/scripts/test_create_db.py
import pytest
from unittest.mock import patch, MagicMock
from scripts.create_db import create_database

@pytest.mark.unit
def test_create_database_success():
    """데이터베이스 생성 성공 테스트"""
    with patch('scripts.create_db.create_engine') as mock_engine:
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = None  # DB 없음
        
        create_database()
        
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()
```

---

### 7. 🟢 **낮음**: 스크립트 버전 관리 부족

**문제**: 스크립트에 버전 정보나 변경 이력이 없습니다.

**영향도**: 낮음  
**수정 권장**: 
```python
# 각 스크립트에 버전 정보 추가
"""
데이터베이스 생성 스크립트

Version: 1.0.0
Last Updated: 2024-01-01
Author: Your Name

Changelog:
- 1.0.0: 초기 버전
"""
```

---

## 📊 검토 요약

### 스크립트 현황
- **Python 스크립트**: 17개
- **PowerShell 스크립트**: 12개
- **텍스트 파일**: 3개
- **총 스크립트**: 32개

### 스크립트 분류
1. **DB 설정**: 8개 (create_db.py, init_db.py, check_db_setup.py 등)
2. **데이터 생성**: 7개 (generate_*.py)
3. **RAG 인덱싱**: 1개 (index_rag_documents.py)
4. **디버깅/확인**: 3개 (check_*.py, debug_*.py)
5. **PowerShell 유틸리티**: 12개
6. **공통 유틸리티**: 1개 (utils.py)

### 발견된 문제
- 🟡 **중간**: 3개 (스크립트 중복, 에러 처리 일관성, 문서화 부족)
- 🟢 **낮음**: 4개 (실행 권한 확인, PowerShell 실행 정책, 테스트, 버전 관리)

### 우선순위별 수정 권장
1. 🟡 **중간**: 스크립트 중복 정리 및 통합 (권장)
2. 🟡 **중간**: 에러 처리 일관성 개선 (권장)
3. 🟡 **중간**: 스크립트 실행 방법 문서화 (권장)
4. 🟢 **낮음**: 실행 권한 확인 추가 (선택적)
5. 🟢 **낮음**: PowerShell 실행 정책 확인 (선택적)
6. 🟢 **낮음**: 스크립트 테스트 추가 (선택적)
7. 🟢 **낮음**: 버전 관리 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: 스크립트 통합 및 구조 개선

#### `scripts/README.md` 생성
```markdown
# Scripts 디렉토리 가이드

## 개요
이 디렉토리에는 데이터베이스 설정, 데이터 생성, RAG 인덱싱 등의 유틸리티 스크립트가 포함되어 있습니다.

## 스크립트 분류

### 데이터베이스 설정
- `create_db.py`: PostgreSQL 데이터베이스 생성
- `create_db_mysql.py`: MySQL 데이터베이스 생성
- `init_db.py`: 데이터베이스 초기화 (테이블 생성)
- `check_db_setup.py`: 데이터베이스 설정 확인

### 데이터 생성
- `generate_all_yaml.py`: 모든 엑셀 시트를 YAML로 변환
- `generate_k0_yaml.py`: K0 Intake 시트 변환
- `generate_k1_yaml.py`: K1 Classification 시트 변환
- `generate_k2_yaml.py`: K2 Questions 시트 변환
- `generate_k3_yaml.py`: K3 Risk Rules 시트 변환
- `generate_k4_yaml.py`: K4 Output Format 시트 변환
- `generate_fact_yaml.py`: LEVEL4 FACT 시트 변환

### RAG 인덱싱
- `index_rag_documents.py`: RAG 문서 인덱싱

### 디버깅/확인
- `check_session_db.py`: 세션 DB 확인
- `check_summary.py`: 요약 확인
- `debug_db_url.py`: DB URL 디버깅

## 사용 방법

### 1. 데이터베이스 설정
```bash
# 1. 데이터베이스 생성
python scripts/create_db.py  # PostgreSQL
# 또는
python scripts/create_db_mysql.py  # MySQL

# 2. 데이터베이스 초기화
python scripts/init_db.py

# 3. 설정 확인
python scripts/check_db_setup.py
```

### 2. 데이터 생성
```bash
# 모든 시트 변환
python scripts/generate_all_yaml.py

# 개별 시트 변환
python scripts/generate_k0_yaml.py
```

### 3. RAG 인덱싱
```bash
# 인덱싱
python scripts/index_rag_documents.py

# 기존 인덱스 초기화 후 재인덱싱
python scripts/index_rag_documents.py --clear
```

## 필수 환경 변수
- `DATABASE_URL`: 데이터베이스 연결 URL
- `OPENAI_API_KEY`: OpenAI API 키 (RAG 인덱싱 시)
```

---

### 수정 2: 공통 유틸리티 확장

#### `scripts/utils.py` 확장
```python
"""
YAML 저장 공통 유틸 함수
"""
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


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


def check_prerequisites(required_dirs: Optional[List[Path]] = None, 
                       required_files: Optional[List[Path]] = None) -> bool:
    """
    스크립트 실행 전 필수 조건 확인
    
    Args:
        required_dirs: 필수 디렉토리 목록
        required_files: 필수 파일 목록
    
    Returns:
        모든 조건이 충족되면 True, 아니면 False
    """
    errors = []
    
    required_dirs = required_dirs or []
    required_files = required_files or []
    
    # 디렉토리 확인
    for dir_path in required_dirs:
        if not dir_path.exists():
            errors.append(f"필수 디렉토리가 없습니다: {dir_path}")
    
    # 파일 확인
    for file_path in required_files:
        if not file_path.exists():
            errors.append(f"필수 파일이 없습니다: {file_path}")
    
    if errors:
        logger.error("스크립트 실행 전 필수 조건을 확인하세요:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    return True


def handle_script_error(error: Exception, script_name: str, exit_code: int = 1):
    """
    스크립트 에러 처리 공통 함수
    
    Args:
        error: 발생한 예외
        script_name: 스크립트 이름
        exit_code: 종료 코드
    """
    logger.error(f"[{script_name}] 오류 발생: {str(error)}", exc_info=True)
    print(f"\n❌ {script_name} 실행 실패: {str(error)}")
    print("\n해결 방법:")
    print("1. 로그 파일 확인: logs/app.log")
    print("2. 환경 변수 확인: .env 파일")
    print("3. 데이터베이스 연결 확인")
    sys.exit(exit_code)


def safe_execute(func, script_name: str):
    """
    안전한 스크립트 실행 래퍼
    
    Args:
        func: 실행할 함수
        script_name: 스크립트 이름
    
    Returns:
        함수 실행 결과
    """
    try:
        return func()
    except Exception as e:
        handle_script_error(e, script_name)
```

---

### 수정 3: 스크립트 docstring 개선

#### `scripts/init_db.py` 개선 예제
```python
"""
데이터베이스 초기화 스크립트 (DDL 실행)

이 스크립트는 migrations/versions/001_initial_schema.sql 파일을 읽어서
데이터베이스에 테이블을 생성합니다.

사용법:
    python scripts/init_db.py

필수 조건:
    - DATABASE_URL 환경 변수가 설정되어 있어야 함
    - migrations/versions/001_initial_schema.sql 파일이 존재해야 함
    - 데이터베이스가 이미 생성되어 있어야 함

에러 처리:
    - 이미 존재하는 테이블은 경고만 출력하고 계속 진행
    - 기타 에러는 즉시 종료

예제:
    # PostgreSQL
    export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
    python scripts/init_db.py
    
    # MySQL
    export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/dbname"
    python scripts/init_db.py
"""
```

---

## 📋 스크립트 실행 체크리스트

### 데이터베이스 설정
- [ ] 환경 변수 확인 (`.env` 파일)
- [ ] 데이터베이스 서버 실행 확인
- [ ] 데이터베이스 생성 (`create_db.py` 또는 `create_db_mysql.py`)
- [ ] 데이터베이스 초기화 (`init_db.py`)
- [ ] 설정 확인 (`check_db_setup.py`)

### 데이터 생성
- [ ] 엑셀 파일 확인 (`excel/knowledge_base.xlsx`)
- [ ] YAML 변환 (`generate_all_yaml.py`)

### RAG 인덱싱
- [ ] RAG 문서 확인 (`data/rag/` 디렉토리)
- [ ] OpenAI API 키 확인
- [ ] RAG 인덱싱 (`index_rag_documents.py`)

---

## ✅ 결론

스크립트 구조는 잘 구성되어 있지만, **스크립트 중복 정리**, **에러 처리 일관성**, **문서화** 측면에서 개선이 필요합니다.

**우선순위**:
1. 🟡 **중간**: 스크립트 중복 정리 및 통합 (권장)
2. 🟡 **중간**: 에러 처리 일관성 개선 (권장)
3. 🟡 **중간**: 스크립트 실행 방법 문서화 (권장)
4. 🟢 **낮음**: 실행 권한 확인, PowerShell 실행 정책, 테스트, 버전 관리 (선택적)

**참고**: 
- 스크립트가 다양한 용도로 잘 분류되어 있음
- 공통 유틸리티 함수가 존재함
- 로깅이 적절히 사용됨
- PowerShell 스크립트도 제공되어 Windows 환경 지원

