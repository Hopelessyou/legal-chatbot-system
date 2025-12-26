"""
DATABASE_URL 디버깅 스크립트
"""
import sys
import os
from pathlib import Path
from urllib.parse import quote_plus, unquote

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def debug_database_url():
    """DATABASE_URL 디버깅"""
    env_file = Path(__file__).parent.parent / ".env"
    
    if not env_file.exists():
        print(f"[ERROR] .env 파일을 찾을 수 없습니다: {env_file}")
        return
    
    # 여러 인코딩으로 시도
    encodings = ['utf-8', 'cp949', 'euc-kr']
    
    for encoding in encodings:
        try:
            with open(env_file, 'r', encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('DATABASE_URL='):
                        db_url = line.split('=', 1)[1].strip()
                        db_url = db_url.strip('"').strip("'")
                        
                        print(f"[OK] {encoding.upper()} 인코딩으로 읽기 성공")
                        print(f"원본 URL: {db_url}")
                        print()
                        
                        # URL 파싱
                        if not db_url.startswith('postgresql://'):
                            print("[ERROR] postgresql://로 시작하지 않습니다")
                            return
                        
                        url_part = db_url[13:]
                        
                        if '@' not in url_part:
                            print("[ERROR] @ 기호가 없습니다")
                            return
                        
                        auth_part, rest_part = url_part.split('@', 1)
                        
                        if ':' not in auth_part:
                            username = auth_part
                            password = ""
                        else:
                            username, password = auth_part.split(':', 1)
                        
                        print(f"사용자명: {username}")
                        print(f"비밀번호 (원본): {password}")
                        print(f"비밀번호 길이: {len(password)}")
                        print(f"비밀번호 바이트: {password.encode('utf-8', errors='replace')}")
                        
                        # 각 바이트 확인
                        print("\n비밀번호 바이트 분석:")
                        for i, byte in enumerate(password.encode('utf-8', errors='replace')):
                            print(f"  위치 {i}: 0x{byte:02x} ({byte}) - '{chr(byte) if 32 <= byte < 127 else '?'}'")
                        
                        # URL 인코딩 시도
                        try:
                            password_decoded = unquote(password)
                            print(f"\n비밀번호 (디코딩 후): {password_decoded}")
                            password_encoded = quote_plus(password_decoded, safe='')
                            print(f"비밀번호 (인코딩 후): {password_encoded}")
                        except Exception as e:
                            print(f"\n[ERROR] 인코딩/디코딩 실패: {str(e)}")
                        
                        # ASCII 확인
                        try:
                            password.encode('ascii')
                            print("\n[OK] 비밀번호는 ASCII 문자만 포함합니다")
                        except UnicodeEncodeError as e:
                            print(f"\n[WARNING] 비밀번호에 비-ASCII 문자가 포함되어 있습니다: {str(e)}")
                            print("  -> URL 인코딩이 필요합니다")
                        
                        return
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"[ERROR] {encoding} 인코딩 오류: {str(e)}")
            continue
    
    print("[ERROR] 모든 인코딩으로 읽기 실패")


if __name__ == "__main__":
    debug_database_url()

