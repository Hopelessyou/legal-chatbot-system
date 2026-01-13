"""
서버 시작 스크립트 (디버깅용)
"""
import uvicorn
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("="*70)
    print("서버 시작 중...")
    print("="*70)
    try:
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n서버 종료")
    except Exception as e:
        print(f"\n서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
