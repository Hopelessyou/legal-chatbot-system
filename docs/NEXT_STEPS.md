# 다음 단계 가이드

## ✅ 완료된 작업
- [x] 데이터베이스 생성 (MySQL)
- [x] 테이블 생성 (10개 테이블)
- [x] 인덱스 및 외래 키 설정

## 📋 다음 단계

### 1. 환경 변수 확인
`.env` 파일이 올바르게 설정되었는지 확인하세요:

```env
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/legal_chat_info_db
OPENAI_API_KEY=your_openai_api_key_here
API_SECRET_KEY=your_secret_key_here
```

**중요**: 
- `OPENAI_API_KEY`는 실제 OpenAI API 키로 설정해야 합니다
- `API_SECRET_KEY`는 임의의 긴 문자열로 생성하세요 (예: `openssl rand -hex 32`)

### 2. RAG 문서 인덱싱
법률 문서를 벡터 데이터베이스에 인덱싱합니다:

```powershell
python scripts/index_rag_documents.py
```

**참고**: 
- RAG 문서는 `data/rag/` 디렉토리에 있어야 합니다
- 문서가 없으면 스크립트가 경고를 표시합니다

### 3. 서버 실행
FastAPI 서버를 시작합니다:

```powershell
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

또는:

```powershell
python -m uvicorn src.api.main:app --reload
```

### 4. API 테스트
서버가 실행되면 브라우저에서 다음 URL을 열어보세요:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 5. API 사용 예시

#### 상담 세션 시작
```powershell
curl -X POST "http://localhost:8000/chat/start" `
  -H "Content-Type: application/json" `
  -d '{\"channel\": \"web\"}'
```

#### 메시지 전송
```powershell
curl -X POST "http://localhost:8000/chat/message" `
  -H "Content-Type: application/json" `
  -d '{\"session_id\": \"sess_xxx\", \"user_message\": \"작년 10월에 계약을 했는데 대금을 받지 못했습니다.\"}'
```

## 🔍 문제 해결

### RAG 문서 인덱싱 오류
- `data/rag/` 디렉토리가 존재하는지 확인
- OpenAI API 키가 올바른지 확인
- 벡터 DB 경로 권한 확인

### 서버 실행 오류
- 포트 8000이 이미 사용 중인지 확인
- `.env` 파일의 모든 필수 변수가 설정되었는지 확인
- 데이터베이스 연결 확인: `python scripts/check_db_setup.py`

### API 오류
- 서버 로그 확인
- 데이터베이스 연결 상태 확인
- OpenAI API 할당량 확인

## 📚 추가 문서
- `docs/DATABASE_SETUP.md` - 데이터베이스 설정 상세 가이드
- `docs/RAG.md` - RAG 시스템 문서
- `README.md` - 프로젝트 개요

