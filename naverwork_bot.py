"""
Naver Works 봇 메시지 전송 스크립트 (서비스 계정 인증 - JWT 방식)

필수 라이브러리 설치:
    pip install requests PyJWT

Naver Works 개발자 콘솔에서 확인 필요:
    1. Service Account 생성 및 ID 확인
    2. Private Key 다운로드 (서비스 계정 인증에 필요)
    3. 봇 앱의 Client ID 확인
    4. 봇 ID 및 사용자 ID 확인

서비스 계정 인증 (JWT):
    - Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용
    - Private Key는 개발자 콘솔의 '서비스 계정' 메뉴에서 다운로드
    - Private Key는 재발행 가능하며, 재발행하면 이전 키는 사용 불가
    - 대안으로 CLIENT_SECRET을 사용할 수도 있음 (일부 구현)

API 규격 준수:
    - 엔드포인트: https://www.worksapis.com/v1.0/...
    - 인증: Authorization: Bearer {Access Token} (공백 필수)
    - Content-Type: application/json; charset=UTF-8
    - HTTP 메서드: POST (메시지 전송)
    - Request Body: JSON 형식 (UTF-8)
    - HTTP 상태 코드 처리: 2xx(성공), 4xx(클라이언트 오류), 5xx(서버 오류)
    
참고 문서:
    - API 공통 규격: https://developers.worksmobile.com/docs/api-common
    - 인증 가이드: https://developers.worksmobile.com/docs/auth-oauth
    - Access Token 발급: 서비스 계정으로 인증(JWT) 방식
"""
import requests
import json
import time
try:
    import jwt
except ImportError:
    print("❌ PyJWT 라이브러리가 설치되지 않았습니다.")
    print("   다음 명령어로 설치하세요: pip install PyJWT")
    raise

# 설정 정보
CLIENT_ID = 'FCfZT2AnOAVJodPjbPoT'
CLIENT_SECRET = '06xJaKX_CO'  # 참고: 일부 구현에서는 CLIENT_SECRET을 사용할 수 있음
BOT_ID = '11012551'
USER_ID = 'dhk@ibslaw.co.kr' # 메시지를 받을 사용자의 ID

# ⚠️ 중요: Naver Works 개발자 콘솔에서 서비스 계정 정보 확인
# 
# 서비스 계정 인증 (JWT)에 필요한 정보:
# 1. Service Account: 가상 관리자 계정 (서비스 계정 ID)
# 2. Private Key: Service Account와 함께 사용되는 개인 키
# 
# 확인 방법:
# 1. https://developers.worksmobile.com 접속 및 로그인
# 2. 상단 메뉴에서 "내 앱" 또는 "앱 관리" 클릭
# 3. 해당 봇 앱 선택
# 4. 좌측 메뉴에서 "서비스 계정" 또는 "Service Account" 메뉴 클릭
# 5. 서비스 계정이 없으면 "생성" 버튼으로 새로 생성
# 6. 서비스 계정 정보 확인:
#    - Service Account: 계정 ID (예: 'bot@yourdomain.com' 또는 이메일 형식)
#    - Private Key: 개인 키 (다운로드 또는 복사)
# 
# 주의: Private Key는 재발행 가능하며, 재발행하면 이전 키는 사용 불가
SERVICE_ACCOUNT = '29jda.serviceaccount@ibslaw.co.kr'  # Service Account ID (이메일 형식 또는 계정 ID)

# Private Key 설정
# ⚠️ 중요: Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용해야 합니다
# CLIENT_SECRET은 구성원 계정 인증에 사용되며, 서비스 계정 인증에는 사용할 수 없습니다
# 
# Naver Works 개발자 콘솔에서 다운로드한 Private Key를 여기에 설정
# 
# 설정 방법 1: 직접 문자열로 설정
# PRIVATE_KEY = '''-----BEGIN PRIVATE KEY-----
# MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
# -----END PRIVATE KEY-----'''
#
# 설정 방법 2: 파일에서 읽기 (보안상 권장)
# import os
# PRIVATE_KEY_PATH = 'private_key.pem'  # Private Key 파일 경로
# if os.path.exists(PRIVATE_KEY_PATH):
#     with open(PRIVATE_KEY_PATH, 'r', encoding='utf-8') as f:
#         PRIVATE_KEY = f.read()
# else:
#     PRIVATE_KEY = None
#
# ⚠️ Private Key 확인 방법:
# 1. Naver Works 개발자 콘솔(https://developers.worksmobile.com) 접속
# 2. 봇 앱 선택
# 3. 좌측 메뉴에서 "서비스 계정" 클릭
# 4. "Private Key" 다운로드 버튼 클릭 또는 복사
# 5. 다운로드한 파일의 내용을 PRIVATE_KEY에 설정
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCv3bybhGNGnDav
zz/6SpxYSLOyu7HPwh+lCX8GNbaKhtsNqP9imZ/2EZ81ccQZCs0y+HwwcR4uDRpF
+mEI0FWoJV7AXbDdwqa8lt1LJweCvfgsjpFKVCvMXa6IAr/Bs5rqbwuYQtO+UOVY
Ncc4XD5dDl5HuwUqomSFb2crxLMtZZsHK4W/D0Ltq1AVJvEv0JlcycX00yZmK0Ir
CuCh14ijUYrTwXpLFe6h3kXyp77RRWI4WAqCJfsoO+1bwLkDl9BSNTGgFfagvCiO
lbpDP7ahndLzrj/kEGWjaox6oRUbt+YC077QrVhy8QrWo7GfQZr+PCYsqC7i4vfc
cY1ubv2fAgMBAAECggEACYaKfOBfjGrtxHl4cNFK9u8wtr7JEbZW+FZlSDaoPmvO
DpyFyDrOSBDmnVC6kIzlK2qmb9CYsH3422R3OOmaGTxDm/UznTA6CIn3I/VR8uE2
QX6vlV6RMzBkeoJ11MpVIgXiE2Qiy88W5s26ci3GNr4ANkxMxrqQBkZsZRmrFURc
NqK8ZHXVt/k6SLJURVLdGSHOAtrFEyDroSrKvgcuA6G+qjW81SYPL1nO+lEEfPK9
7d3LPgS/hC55wW7PnZcGu6C386bjPSiftopeVbftWnyBbKZR77o5csy8EqEnRVVs
AO2yVG3XU/eS/hfuzFLeKMUAcvnM0NuKHzuvGGiJnQKBgQC+0hIAk9EZ0O5t26g6
if4+zW7sc84MVCg/rCG18rWiS6ynFYan0i6iYhEKv6clE2T3fl5E+K2AHxsgnMbV
0hUh19EvPdxqTPaU1MgSbJxAPFtbEMUUiW25D9QlAbO1WBZrF3mNdvw/7M1ieLpU
ruKVsjzzMHBZKy2Z06HdciI4xQKBgQDr8AGH4yLa25ART7D1T8E7NXdl7UkK2krt
3RQ2PXKQqMtqW/SfuadNA1CegEsiBhUg0kiStgthDNKgyNLP1z17FCNt/E0XkoVG
3B8soUnDG42IrLt550ttI4GmvOocpaG2VemoVR+9IseBYf/pblRy1a3dsN9faYO8
QNx4AMgbEwKBgQCBel82vxYSM1+lcXeMCRhYGuMaVFXKrcwFsFHLeN3gOwLy+Ls+
4nI8QtiXd4X9tVQ8TyW+HRL1LaYlkdulOICYTy2kpZALHR/vyxXa0pGPUKUYfJ+N
mNa3zNLBLY94DEZh8jLLV6I/6flOyOZ+EZCzzJZo2URSbObrStu5O/mWlQKBgQC1
5olXmd+CeqrdHeKhjsa8fmE6XTHmQxxnvP3bP463RtvleVXlWz5IGtkqCmFiruvV
LSq0qdOmFDvDqHEXuqt027bhEhbhqJ5GXmlOgF8dJH3/NKUpvBAj6a8IvTeFtJEz
wZLurApXSJwl/UdPUjebfXCZrcbZicD9/8e6YWflrwKBgCPpZi8vnBlZlGt4P5Ed
Q8JPrPE6D8xgze/eKvWIbHy+/KevBftvvU4FXwXCezCxPEYxgH8yhiDwTw9awHst
BEJTgPfSktlSVPqp3L/34dyBLdrU+7phDbXjPf9QL/zdqcZ/IUOyjR32YdoZC7qG
ISEenrHeFop+A0nvAfSX68ig
-----END PRIVATE KEY-----
"""  # Private Key 문자열 (필수) - 위 방법 중 하나로 설정하세요

# Private Key 사용 여부 결정
# ⚠️ 서비스 계정 인증에는 반드시 Private Key를 사용해야 합니다
# True: Private Key 사용 (문서 권장 방식, 필수)
# False: CLIENT_SECRET 사용 (구성원 계정 인증용, 서비스 계정 인증에는 사용 불가)
USE_PRIVATE_KEY = True  # 서비스 계정 인증에는 True로 설정 (필수)

def get_access_token_via_id_token():
    """
    Naver Works API 액세스 토큰을 서비스 계정 인증(JWT) 방식으로 가져옵니다.
    
    서비스 계정 인증은 JWT(JSON Web Token)를 생성하여 Access Token을 발급받는 방식입니다.
    Naver Works API 문서에 따르면 서비스 계정 인증에는 반드시 Private Key를 사용해야 합니다.
    CLIENT_SECRET은 구성원 계정 인증에만 사용됩니다.
    
    참고 문서: https://developers.worksmobile.com/docs/auth-oauth
    """
    # SERVICE_ACCOUNT가 설정되지 않았으면 에러
    if SERVICE_ACCOUNT == 'YOUR_SERVICE_ACCOUNT' or not SERVICE_ACCOUNT:
        print("❌ SERVICE_ACCOUNT가 설정되지 않았습니다.")
        print("   Naver Works 개발자 콘솔에서 서비스 계정을 생성하고 ID를 설정하세요.")
        return None
    
    # Private Key 검증 (서비스 계정 인증에는 필수)
    if USE_PRIVATE_KEY:
        if not PRIVATE_KEY:
            print("❌ Private Key가 설정되지 않았습니다.")
            print("\n   ⚠️ 중요: Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용해야 합니다.")
            print("   CLIENT_SECRET은 구성원 계정 인증에만 사용되며, 서비스 계정 인증에는 사용할 수 없습니다.")
            print("\n   해결 방법:")
            print("   1. Naver Works 개발자 콘솔(https://developers.worksmobile.com) 접속")
            print("   2. 봇 앱 선택")
            print("   3. '서비스 계정' 메뉴 클릭")
            print("   4. Private Key 다운로드 또는 복사")
            print("   5. 코드의 PRIVATE_KEY 변수에 Private Key 값 설정")
            print("\n   Private Key 형식 예시:")
            print("   PRIVATE_KEY = '''-----BEGIN PRIVATE KEY-----")
            print("   MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...")
            print("   -----END PRIVATE KEY-----'''")
            return None
    else:
        print("⚠️ 경고: CLIENT_SECRET을 사용하고 있습니다.")
        print("   Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용해야 합니다.")
        print("   CLIENT_SECRET은 구성원 계정 인증에만 사용됩니다.")
        print("   Private Key를 사용하려면 USE_PRIVATE_KEY = True로 설정하고 PRIVATE_KEY를 설정하세요.")
    
    try:
        now = int(time.time())
        
        # 1. JWT 페이로드 작성 (ID Token 생성용)
        # Naver Works API 규격에 맞는 JWT 페이로드
        # CLIENT_ID와 CLIENT_SECRET의 공백 제거 (복사/붙여넣기 시 발생할 수 있는 문제 방지)
        client_id_clean = CLIENT_ID.strip()
        client_secret_clean = CLIENT_SECRET.strip()
        
        if client_id_clean != CLIENT_ID:
            print(f"   ⚠️ CLIENT_ID에 공백이 있어 제거했습니다.")
        if client_secret_clean != CLIENT_SECRET:
            print(f"   ⚠️ CLIENT_SECRET에 공백이 있어 제거했습니다.")
        
        payload = {
            "iss": client_id_clean,  # Issuer: 클라이언트 ID (공백 제거된 값)
            "sub": SERVICE_ACCOUNT,  # Subject: 서비스 계정 (이메일 형식 또는 서비스 계정 ID)
            "aud": "https://auth.worksmobile.com/oauth2/v2.0/token",  # Audience: 토큰 발급 엔드포인트
            "iat": now,  # Issued At: 발급 시간
            "exp": now + 3600  # Expiration: 만료 시간 (1시간)
        }
        
        # 디버깅: JWT 페이로드 확인
        print("🔐 JWT 토큰 생성 중...")
        print(f"   페이로드: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print(f"   CLIENT_ID: '{client_id_clean}' (길이: {len(client_id_clean)})")
        print(f"   SERVICE_ACCOUNT: '{SERVICE_ACCOUNT}'")
        
        # 2. JWT 서명
        # Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용
        # 하지만 일부 구현에서는 CLIENT_SECRET을 사용할 수도 있음
        try:
            if USE_PRIVATE_KEY and PRIVATE_KEY:
                # Private Key 사용 (문서 권장 방식)
                print("   🔑 Private Key 사용 (서비스 계정 인증)")
                private_key_clean = PRIVATE_KEY.strip()
                
                # Private Key 형식 확인 (PEM 형식인지 확인)
                if "BEGIN" in private_key_clean.upper() or "PRIVATE KEY" in private_key_clean.upper():
                    # PEM 형식의 RSA Private Key (RS256 알고리즘 사용)
                    print("   알고리즘: RS256 (RSA Private Key)")
                    try:
                        id_token = jwt.encode(payload, private_key_clean, algorithm="RS256")
                    except Exception as e:
                        print(f"   ⚠️ RS256 실패, HS256 시도: {e}")
                        # RS256 실패 시 HS256으로 시도
                        id_token = jwt.encode(payload, private_key_clean, algorithm="HS256")
                else:
                    # 문자열 형식의 Private Key (HS256 알고리즘 사용)
                    print("   알고리즘: HS256 (문자열 Private Key)")
                    id_token = jwt.encode(payload, private_key_clean, algorithm="HS256")
            else:
                # CLIENT_SECRET 사용 (구성원 계정 인증용, 서비스 계정 인증에는 사용 불가)
                print("   ⚠️ CLIENT_SECRET 사용 (구성원 계정 인증용)")
                print("   ⚠️ 경고: Naver Works API 문서에 따르면 서비스 계정 인증에는 Private Key를 사용해야 합니다.")
                print("   ⚠️ CLIENT_SECRET은 구성원 계정 인증에만 사용되며, 서비스 계정 인증에는 사용할 수 없습니다.")
                print(f"   CLIENT_SECRET 길이: {len(client_secret_clean)}")
                secret_key = client_secret_clean
                
                # 디버깅: CLIENT_SECRET 검증 (실제 값은 마스킹)
                print(f"   CLIENT_SECRET 검증: 길이={len(secret_key)}, 첫글자='{secret_key[0] if secret_key else 'N/A'}', 마지막글자='{secret_key[-1] if secret_key else 'N/A'}'")
                print("   알고리즘: HS256")
                print("   ⚠️ 이 방식은 서비스 계정 인증에서 작동하지 않을 수 있습니다.")
                
                id_token = jwt.encode(payload, secret_key, algorithm="HS256")
        except Exception as e:
            print(f"   ❌ JWT 인코딩 오류: {e}")
            raise
        
        # 디버깅: 생성된 JWT 토큰 확인 (디코딩하여 검증)
        try:
            # 서명 검증 없이 페이로드만 디코딩하여 내용 확인
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            print(f"   ✅ JWT 토큰 생성 완료")
            print(f"   토큰 길이: {len(id_token)} 문자")
            print(f"   디코딩된 페이로드:")
            print(f"     - iss (CLIENT_ID): {decoded.get('iss')}")
            print(f"     - sub (SERVICE_ACCOUNT): {decoded.get('sub')}")
            print(f"     - aud: {decoded.get('aud')}")
            print(f"     - iat: {decoded.get('iat')} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(decoded.get('iat')))})")
            print(f"     - exp: {decoded.get('exp')} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(decoded.get('exp')))})")
            
            # CLIENT_ID와 SERVICE_ACCOUNT 확인
            if decoded.get('iss') != client_id_clean:
                print(f"   ⚠️ 경고: JWT의 'iss' 필드({decoded.get('iss')})가 CLIENT_ID({client_id_clean})와 일치하지 않습니다.")
            if decoded.get('sub') != SERVICE_ACCOUNT:
                print(f"   ⚠️ 경고: JWT의 'sub' 필드({decoded.get('sub')})가 SERVICE_ACCOUNT({SERVICE_ACCOUNT})와 일치하지 않습니다.")
        except Exception as e:
            print(f"   ⚠️ JWT 토큰 디코딩 중 경고: {e}")
        
        # 3. Access Token 요청
        # 인증 엔드포인트 (OAuth 2.0 토큰 발급)
        auth_url = "https://auth.worksmobile.com/oauth2/v2.0/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": id_token,
            "scope": "bot"  # 필요한 권한 범위
        }
        
        # 디버깅: 요청 데이터 확인 (assertion은 일부만 표시)
        print("📤 Access Token 요청 중...")
        print(f"   URL: {auth_url}")
        print(f"   grant_type: {data['grant_type']}")
        print(f"   assertion (처음 50자): {id_token[:50]}...")
        print(f"   scope: {data['scope']}")
        
        response = requests.post(auth_url, data=data, headers=headers)
        
        # HTTP 상태 코드 확인
        status_code = response.status_code
        print(f"📋 응답 상태 코드: {status_code}")
        
        # 성공 상태 코드 처리
        if status_code == 200:
            try:
                result = response.json()
                access_token = result.get("access_token")
                
                if not access_token:
                    print(f"❌ 토큰 획득 실패: 응답에 access_token이 없습니다")
                    print(f"   응답 내용: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return None
                
                # 토큰 만료 시간 정보 출력 (있는 경우)
                expires_in = result.get("expires_in")
                if expires_in:
                    print(f"⏰ 토큰 유효 기간: {expires_in}초 ({expires_in // 60}분)")
                
                return access_token
            except json.JSONDecodeError as e:
                print(f"❌ 응답 파싱 오류: {e}")
                print(f"   응답 내용: {response.text}")
                return None
        else:
            # 에러 상태 코드 처리
            print(f"❌ HTTP 에러 발생: {status_code}")
            
            # 에러 응답 파싱
            error_info = None
            if response.text:
                try:
                    error_info = response.json()
                    print(f"❌ 에러 상세: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
                except:
                    print(f"❌ 에러 응답: {response.text}")
            
            # 에러 코드별 구체적인 안내
            error_code = error_info.get("error") if error_info else None
            error_description = error_info.get("error_description") if error_info else None
            
            if status_code == 400:
                print("\n🔍 원인 분석:")
                if error_code == "invalid_request":
                    if "client_id or client_secret is not valid" in (error_description or ""):
                        print("   ❌ CLIENT_ID 또는 인증 키가 유효하지 않습니다.")
                        print("\n   ⚠️ 중요: 이 에러는 JWT 서명 검증 실패를 의미합니다.")
                        print("   Naver Works 서버가 JWT의 서명을 검증할 때 인증 정보가 맞지 않는다고 판단했습니다.")
                        print("\n   📚 Naver Works API 문서에 따르면:")
                        print("   - 서비스 계정 인증에는 반드시 Private Key를 사용해야 합니다")
                        print("   - CLIENT_SECRET은 구성원 계정 인증에만 사용되며, 서비스 계정 인증에는 사용할 수 없습니다")
                        print("   - Private Key는 개발자 콘솔의 '서비스 계정' 메뉴에서 다운로드할 수 있습니다")
                        print("   - Private Key는 재발행 가능하며, 재발행하면 이전 키는 사용 불가")
                        print("\n   가능한 원인:")
                        if USE_PRIVATE_KEY and PRIVATE_KEY:
                            print("   1. ❗ CLIENT_ID와 Private Key가 서로 다른 앱의 것일 수 있음")
                            print("      → 같은 봇 앱에서 발급받은 CLIENT_ID와 Private Key를 사용해야 합니다")
                            print("   2. ❗ CLIENT_ID 값이 잘못됨 (JWT의 'iss' 필드와 일치하지 않음)")
                            print("      → 개발자 콘솔의 '앱 설정' → '인증 정보'에서 정확한 Client ID 확인")
                            print("   3. ❗ Private Key 값이 잘못됨 (JWT 서명 검증 실패)")
                            print("      → 같은 봇 앱의 '서비스 계정' 메뉴에서 다운로드한 Private Key 사용")
                            print("   4. Private Key 형식이 올바르지 않음 (PEM 형식 확인)")
                            print("      → Private Key에 앞뒤 공백이나 줄바꿈 문제가 있을 수 있음")
                            print("   5. Private Key가 재발행되어 이전 키 사용 불가")
                            print("      → Private Key를 재발행했다면 새 키로 업데이트 필요")
                        else:
                            print("   1. ❗ CLIENT_SECRET은 서비스 계정 인증에 사용할 수 없습니다")
                            print("      → Private Key를 사용해야 합니다 (USE_PRIVATE_KEY = True, PRIVATE_KEY 설정)")
                            print("   2. ❗ CLIENT_ID 값이 잘못됨 (JWT의 'iss' 필드와 일치하지 않음)")
                            print("   3. ❗ CLIENT_SECRET은 구성원 계정 인증에만 사용됩니다")
                            print("   4. CLIENT_SECRET에 보이지 않는 공백이나 특수문자 포함")
                        print("   5. 다른 봇 앱의 인증 정보를 사용 중")
                        print("   6. 개발자 콘솔에서 확인한 값과 코드의 값이 정확히 일치하지 않음")
                        print("\n   🔍 확인 사항:")
                        print("   1. Naver Works 개발자 콘솔(https://developers.worksmobile.com) 접속")
                        print("   2. 봇 앱(BOT_ID: 11012551) 선택")
                        print("   3. '서비스 계정' 메뉴 확인:")
                        print("      - Service Account ID 확인 (현재: " + SERVICE_ACCOUNT + ")")
                        print("      - Private Key 다운로드 또는 복사")
                        print("      ⚠️ 중요: 같은 봇 앱에서 다운로드한 Private Key를 사용해야 합니다")
                        print("   4. '앱 설정' → '인증 정보' 메뉴에서 Client ID 확인")
                        print("      - 현재 CLIENT_ID: " + CLIENT_ID)
                        print("      ⚠️ 중요: CLIENT_ID와 Private Key가 같은 봇 앱의 것인지 확인")
                        print("   5. 코드 설정 확인:")
                        if not USE_PRIVATE_KEY or not PRIVATE_KEY:
                            print("      ⚠️ 필수: USE_PRIVATE_KEY = True로 변경")
                            print("      ⚠️ 필수: PRIVATE_KEY에 Private Key 값 설정")
                            print("      ⚠️ 중요: CLIENT_SECRET은 서비스 계정 인증에 사용할 수 없습니다")
                            print("      → Private Key를 반드시 사용해야 합니다")
                        else:
                            print("      - PRIVATE_KEY 값이 정확한지 확인")
                            print("      - Private Key 형식 확인 (PEM 형식 또는 문자열 형식)")
                            print("      - Private Key가 재발행되지 않았는지 확인")
                        print("   6. 값 정확히 일치하는지 확인:")
                        print("      - 대소문자 구분")
                        print("      - 앞뒤 공백 없음")
                        print("      - 특수문자 정확히 일치")
                        print("\n   💡 필수 사항:")
                        print("   - ⚠️ 서비스 계정 인증에는 반드시 Private Key를 사용해야 합니다")
                        print("   - ⚠️ CLIENT_SECRET은 구성원 계정 인증에만 사용되며, 서비스 계정 인증에는 사용할 수 없습니다")
                        print("   - Private Key는 '서비스 계정' 메뉴에서 다운로드")
                        print("   - Private Key가 재발행되었다면 새 키로 업데이트")
                        print("   - USE_PRIVATE_KEY = True로 설정하고 PRIVATE_KEY에 Private Key 값 설정")
                        print(f"\n   현재 설정:")
                        print(f"   - CLIENT_ID: '{CLIENT_ID}' (길이: {len(CLIENT_ID)})")
                        if USE_PRIVATE_KEY and PRIVATE_KEY:
                            print(f"   - Private Key 사용: ✅ (길이: {len(PRIVATE_KEY)})")
                        else:
                            print(f"   - CLIENT_SECRET 사용: {'*' * len(CLIENT_SECRET)} (길이: {len(CLIENT_SECRET)})")
                            print(f"   - Private Key 사용: ❌ (USE_PRIVATE_KEY = {USE_PRIVATE_KEY})")
                        print(f"   - SERVICE_ACCOUNT: '{SERVICE_ACCOUNT}'")
                        print(f"   - BOT_ID: {BOT_ID}")
                        print("\n   ⚠️ SERVICE_ACCOUNT는 이 에러와 무관할 수 있습니다.")
                        print("   'client_id or client_secret is not valid' 에러는 인증 키 문제입니다.")
                    elif "assertion" in (error_description or "").lower():
                        print("   ❌ JWT assertion이 유효하지 않습니다.")
                        print("   - SERVICE_ACCOUNT 값 확인 필요")
                        print(f"   - 현재 SERVICE_ACCOUNT: {SERVICE_ACCOUNT}")
                    else:
                        print("   ❌ 요청 파라미터 오류")
                        print("   - grant_type, assertion, scope 확인 필요")
                else:
                    print("   ❌ Bad Request - 요청 파라미터 오류")
            elif status_code == 401:
                print("\n🔍 원인 분석:")
                print("   ❌ Unauthorized - 인증 실패")
                print("\n   해결 방법:")
                print("   1. CLIENT_ID, CLIENT_SECRET 확인")
                print("   2. SERVICE_ACCOUNT 확인")
                print("   3. JWT 토큰 생성 과정 확인")
            elif status_code == 403:
                print("\n🔍 원인 분석:")
                print("   ❌ Forbidden - 권한 없음")
                print("   - 봇 앱의 권한 설정 확인 필요")
            elif status_code == 429:
                print("\n🔍 원인 분석:")
                print("   ❌ Too Many Requests - API 호출 제한 초과 (Rate Limit)")
                print("   - 잠시 후 다시 시도하세요")
            elif status_code >= 500:
                print("\n🔍 원인 분석:")
                print("   ❌ Server Error - 서버 오류")
                print("   - Naver Works 서버 문제일 수 있으니 잠시 후 다시 시도하세요")
            
            return None
        
    except jwt.InvalidTokenError as e:
        print(f"❌ JWT 토큰 생성 오류: {e}")
        print("   CLIENT_SECRET과 알고리즘(HS256)을 확인하세요.")
        return None
    except requests.exceptions.Timeout as e:
        print(f"❌ 요청 시간 초과: {e}")
        print("   네트워크 연결을 확인하세요.")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 연결 오류: {e}")
        print("   인터넷 연결을 확인하세요.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 토큰 요청 중 네트워크 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        import traceback
        print(f"   상세 오류:\n{traceback.format_exc()}")
        return None

# 기존 함수명과의 호환성을 위한 별칭
get_access_token = get_access_token_via_id_token

def send_message(token, message):
    """
    Naver Works 봇을 통해 메시지를 전송합니다.
    
    API 규격 준수:
    - 엔드포인트: https://www.worksapis.com/v1.0/bots/{botId}/users/{userId}/messages
    - HTTP 메서드: POST
    - Authorization: Bearer {Access Token} (공백 포함)
    - Content-Type: application/json; charset=UTF-8
    - Request Body: JSON 형식 (UTF-8)
    """
    # API 엔드포인트 (Naver Works API 규격 준수)
    url = f"https://www.worksapis.com/v1.0/bots/{BOT_ID}/users/{USER_ID}/messages"
    
    # 헤더 설정 (API 규격 준수)
    headers = {
        "Authorization": f"Bearer {token}",  # Bearer와 토큰 사이 공백 필수
        "Content-Type": "application/json; charset=UTF-8"  # charset=UTF-8 명시
    }
    
    # Request Body (JSON 형식, UTF-8)
    payload = {
        "content": {
            "type": "text",
            "text": message
        }
    }
    
    try:
        print(f"📤 메시지 전송 요청: {url}")
        response = requests.post(url, headers=headers, json=payload)
        
        # HTTP 상태 코드 확인
        status_code = response.status_code
        print(f"📋 응답 상태 코드: {status_code}")
        
        # 성공 상태 코드 (2xx, 3xx)
        if 200 <= status_code < 300:
            # 202 Accepted: 요청이 수락되었지만 아직 처리 중
            if status_code == 202:
                print("✅ 메시지 전송 요청이 수락되었습니다 (처리 중)")
            # 204 No Content: 성공했지만 응답 본문 없음
            elif status_code == 204:
                print("✅ 메시지 전송 성공 (응답 본문 없음)")
            # 200 OK: 성공
            else:
                print("✅ 메시지 전송 성공")
            
            # 응답 본문이 있으면 출력
            if response.text:
                try:
                    result = response.json()
                    print(f"📋 응답 내용: {json.dumps(result, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📋 응답 내용: {response.text}")
            
            return status_code
        
        # 에러 상태 코드 처리
        else:
            print(f"❌ HTTP 에러 발생: {status_code}")
            
            # 에러 응답 파싱
            error_info = None
            if response.text:
                try:
                    error_info = response.json()
                    print(f"❌ 에러 상세: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
                except:
                    print(f"❌ 에러 응답: {response.text}")
            
            # 주요 HTTP 상태 코드별 처리
            if status_code == 400:
                print("   원인: Bad Request - 요청 파라미터 오류")
            elif status_code == 401:
                print("   원인: Unauthorized - 인증 실패 (토큰 확인 필요)")
            elif status_code == 403:
                print("   원인: Forbidden - 권한 없음")
            elif status_code == 404:
                print("   원인: Not Found - 리소스를 찾을 수 없음 (BOT_ID 또는 USER_ID 확인)")
            elif status_code == 409:
                print("   원인: Conflict - 리소스 충돌")
            elif status_code == 429:
                print("   원인: Too Many Requests - API 호출 제한 초과 (Rate Limit)")
            elif status_code >= 500:
                print("   원인: Server Error - 서버 오류")
            
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 메시지 전송 중 네트워크 오류 발생: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ 응답 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return None

# 실행
if __name__ == "__main__":
    print("🔑 액세스 토큰 획득 중...")
    token = get_access_token()
    if token:
        print("✅ 토큰 획득 성공")
        print("📤 메시지 전송 중...")
        status = send_message(token, "🔔 프로그램에서 보낸 자동 알림입니다!")
        if status:
            print(f"✅ 전송 성공: HTTP {status}")
        else:
            print("❌ 메시지 전송 실패")
    else:
        print("❌ 토큰 획득 실패로 인해 메시지를 전송할 수 없습니다.")