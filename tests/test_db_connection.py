"""
DB 연결 상태 및 테이블 존재 여부 확인 테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from src.db.connection import db_manager
from src.db.models import (
    ChatSession,
    ChatSessionStateLog,
    CaseMaster,
    CaseParty,
    CaseFact,
    CaseEvidence,
    CaseEmotion,
    CaseMissingField,
    CaseSummary,
    AIProcessLog
)
from src.utils.logger import setup_logging, get_logger
from typing import Dict, List, Any
import json

setup_logging()
logger = get_logger(__name__)


class DatabaseHealthChecker:
    """데이터베이스 상태 확인 클래스"""
    
    def __init__(self):
        self.engine = db_manager.engine
        self.inspector = inspect(self.engine)
        self.results = {
            "connection": False,
            "tables": {},
            "errors": []
        }
    
    def check_connection(self) -> bool:
        """DB 연결 상태 확인"""
        try:
            result = db_manager.health_check()
            self.results["connection"] = result
            return result
        except Exception as e:
            self.results["errors"].append(f"연결 확인 실패: {str(e)}")
            return False
    
    def get_table_list(self) -> List[str]:
        """데이터베이스의 모든 테이블 목록 조회"""
        try:
            return self.inspector.get_table_names()
        except Exception as e:
            self.results["errors"].append(f"테이블 목록 조회 실패: {str(e)}")
            return []
    
    def check_table_exists(self, table_name: str) -> bool:
        """특정 테이블 존재 여부 확인"""
        try:
            tables = self.get_table_list()
            return table_name in tables
        except Exception as e:
            self.results["errors"].append(f"테이블 존재 확인 실패 ({table_name}): {str(e)}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블의 컬럼 정보 조회"""
        try:
            columns = self.inspector.get_columns(table_name)
            return [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col.get("default", "")),
                    "primary_key": col.get("primary_key", False)
                }
                for col in columns
            ]
        except Exception as e:
            self.results["errors"].append(f"컬럼 정보 조회 실패 ({table_name}): {str(e)}")
            return []
    
    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블의 인덱스 정보 조회"""
        try:
            indexes = self.inspector.get_indexes(table_name)
            return [
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx.get("unique", False)
                }
                for idx in indexes
            ]
        except Exception as e:
            self.results["errors"].append(f"인덱스 정보 조회 실패 ({table_name}): {str(e)}")
            return []
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블의 외래키 정보 조회"""
        try:
            fks = self.inspector.get_foreign_keys(table_name)
            return [
                {
                    "name": fk.get("name", ""),
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                }
                for fk in fks
            ]
        except Exception as e:
            self.results["errors"].append(f"외래키 정보 조회 실패 ({table_name}): {str(e)}")
            return []
    
    def get_table_row_count(self, table_name: str) -> int:
        """테이블의 행 개수 조회"""
        try:
            with db_manager.get_db_session() as session:
                result = session.execute(text(f"SELECT COUNT(*) as cnt FROM {table_name}"))
                row = result.fetchone()
                return row[0] if row else 0
        except Exception as e:
            self.results["errors"].append(f"행 개수 조회 실패 ({table_name}): {str(e)}")
            return -1
    
    def check_all_tables(self) -> Dict[str, Any]:
        """모든 모델 테이블 확인"""
        # 모델과 테이블명 매핑
        model_table_map = {
            "chat_session": ChatSession,
            "chat_session_state_log": ChatSessionStateLog,
            "case_master": CaseMaster,
            "case_party": CaseParty,
            "case_fact": CaseFact,
            "case_evidence": CaseEvidence,
            "case_emotion": CaseEmotion,
            "case_missing_field": CaseMissingField,
            "case_summary": CaseSummary,
            "ai_process_log": AIProcessLog
        }
        
        for table_name, model in model_table_map.items():
            exists = self.check_table_exists(table_name)
            table_info = {
                "exists": exists,
                "model": model.__name__,
                "columns": [],
                "indexes": [],
                "foreign_keys": [],
                "row_count": 0
            }
            
            if exists:
                table_info["columns"] = self.get_table_columns(table_name)
                table_info["indexes"] = self.get_table_indexes(table_name)
                table_info["foreign_keys"] = self.get_foreign_keys(table_name)
                table_info["row_count"] = self.get_table_row_count(table_name)
            
            self.results["tables"][table_name] = table_info
        
        return self.results
    
    def print_report(self):
        """상태 보고서 출력"""
        print("\n" + "="*80)
        print("데이터베이스 연결 상태 및 테이블 확인 보고서")
        print("="*80)
        
        # 연결 상태
        print(f"\n[연결 상태]")
        if self.results["connection"]:
            print("✅ 데이터베이스 연결: 정상")
        else:
            print("❌ 데이터베이스 연결: 실패")
        
        # 테이블 목록
        all_tables = self.get_table_list()
        print(f"\n[전체 테이블 목록] ({len(all_tables)}개)")
        for table in sorted(all_tables):
            print(f"  - {table}")
        
        # 모델 테이블 상세 정보
        print(f"\n[모델 테이블 상세 정보]")
        print("-"*80)
        
        for table_name, info in sorted(self.results["tables"].items()):
            status = "✅" if info["exists"] else "❌"
            print(f"\n{status} {table_name} (Model: {info['model']})")
            
            if not info["exists"]:
                print("  ⚠️  테이블이 존재하지 않습니다!")
                continue
            
            # 행 개수
            row_count = info["row_count"]
            if row_count >= 0:
                print(f"  📊 행 개수: {row_count:,}개")
            
            # 컬럼 정보
            columns = info["columns"]
            if columns:
                print(f"  📋 컬럼 ({len(columns)}개):")
                for col in columns:
                    pk_mark = " [PK]" if col["primary_key"] else ""
                    null_mark = " [NULL]" if col["nullable"] else " [NOT NULL]"
                    print(f"    - {col['name']}: {col['type']}{pk_mark}{null_mark}")
            
            # 인덱스 정보
            indexes = info["indexes"]
            if indexes:
                print(f"  🔍 인덱스 ({len(indexes)}개):")
                for idx in indexes:
                    unique_mark = " [UNIQUE]" if idx["unique"] else ""
                    print(f"    - {idx['name']}: ({', '.join(idx['columns'])}){unique_mark}")
            
            # 외래키 정보
            fks = info["foreign_keys"]
            if fks:
                print(f"  🔗 외래키 ({len(fks)}개):")
                for fk in fks:
                    print(f"    - {fk['name']}: {', '.join(fk['constrained_columns'])} → {fk['referred_table']}.{', '.join(fk['referred_columns'])}")
        
        # 오류 정보
        if self.results["errors"]:
            print(f"\n[오류 정보] ({len(self.results['errors'])}개)")
            for error in self.results["errors"]:
                print(f"  ⚠️  {error}")
        
        print("\n" + "="*80)
    
    def run_all_checks(self) -> Dict[str, Any]:
        """모든 확인 작업 실행"""
        print("데이터베이스 상태 확인 중...")
        
        # 연결 확인
        self.check_connection()
        
        # 테이블 확인
        self.check_all_tables()
        
        # 보고서 출력
        self.print_report()
        
        return self.results


def main():
    """메인 실행 함수"""
    try:
        checker = DatabaseHealthChecker()
        results = checker.run_all_checks()
        
        # 요약
        total_tables = len(results["tables"])
        existing_tables = sum(1 for info in results["tables"].values() if info["exists"])
        missing_tables = total_tables - existing_tables
        
        print(f"\n[요약]")
        print(f"  - 연결 상태: {'✅ 정상' if results['connection'] else '❌ 실패'}")
        print(f"  - 전체 모델 테이블: {total_tables}개")
        print(f"  - 존재하는 테이블: {existing_tables}개")
        print(f"  - 누락된 테이블: {missing_tables}개")
        print(f"  - 오류 개수: {len(results['errors'])}개")
        
        # JSON 출력 옵션
        if len(sys.argv) > 1 and sys.argv[1] == "--json":
            print("\n[JSON 출력]")
            print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        
        # 종료 코드
        if not results["connection"] or missing_tables > 0 or len(results["errors"]) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"테스트 실행 실패: {str(e)}", exc_info=True)
        print(f"\n❌ 테스트 실행 실패: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

