# 설치 및 실행 가이드

## 필수 요구사항

- Python 3.10 이상
- PostgreSQL 14 이상
- OpenAI API Key

## 설치 단계

### 1. 가상환경 생성 및 활성화

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 설정하세요:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/legal_chatbot_db
OPENAI_API_KEY=your_openai_api_key_here
API_SECRET_KEY=your_secret_key_here
```

### 4. 데이터베이스 설정

**상세 가이드는 `docs/DATABASE_SETUP.md`를 참고하세요.**

#### 빠른 설정 (PostgreSQL이 이미 설치된 경우)

1. PostgreSQL에 접속하여 데이터베이스 생성:
```bash
# 방법 1: 스크립트 사용 (권장)
python scripts/create_db.py

# 방법 2: 직접 생성
psql -U postgres
CREATE DATABASE legal_chatbot_db;
\q
```

2. `.env` 파일에 DATABASE_URL 설정:
```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/legal_chatbot_db
```

3. 스키마 초기화:
```bash
# 방법 1: SQL 스크립트 직접 실행
psql -U postgres -d legal_chatbot_db -f migrations/versions/001_initial_schema.sql

# 방법 2: Python 스크립트 사용
python scripts/init_db.py
```

4. 연결 확인:
```bash
curl http://localhost:8000/health
```

### 5. RAG 문서 인덱싱

```bash
# RAG 문서 인덱싱
python scripts/index_rag_documents.py
```

### 6. 서버 실행

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## API 테스트

서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI를 통해 API를 테스트할 수 있습니다.

### 예시 요청

#### 1. 상담 시작
```bash
curl -X POST "http://localhost:8000/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"channel": "web"}'
```

#### 2. 메시지 전송
```bash
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xxx",
    "user_message": "작년 10월에 계약을 했는데 대금을 받지 못했습니다."
  }'
```

## 문제 해결

### 데이터베이스 연결 오류
- PostgreSQL이 실행 중인지 확인
- DATABASE_URL이 올바른지 확인

### OpenAI API 오류
- OPENAI_API_KEY가 올바른지 확인
- API 할당량 확인

### RAG 검색 오류
- RAG 문서가 인덱싱되었는지 확인
- 벡터 DB 경로 확인

