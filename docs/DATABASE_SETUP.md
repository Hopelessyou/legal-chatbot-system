# 데이터베이스 설정 가이드

## 개요

본 프로젝트는 MySQL 데이터베이스를 사용합니다. 이 문서는 데이터베이스 설정 및 초기화 방법을 설명합니다.

## 1. MySQL 설치

### Windows
1. [MySQL 공식 사이트](https://dev.mysql.com/downloads/installer/)에서 MySQL Installer 다운로드
2. 설치 시 root 사용자의 비밀번호 설정 (기억해두세요!)
3. MySQL 서버가 자동으로 시작되도록 설정

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

### macOS
```bash
brew install mysql
brew services start mysql
```

## 2. 데이터베이스 생성

### 방법 1: 스크립트 사용 (권장)

```bash
python scripts/create_db.py
```

### 방법 2: MySQL CLI 사용

```bash
# MySQL에 접속
mysql -u root -p

# 데이터베이스 생성
CREATE DATABASE legal_chatbot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 사용자 생성 (선택사항)
CREATE USER 'legal_user'@'localhost' IDENTIFIED BY 'your_password';

# 권한 부여
GRANT ALL PRIVILEGES ON legal_chatbot_db.* TO 'legal_user'@'localhost';
FLUSH PRIVILEGES;

# 접속 종료
EXIT;
```

## 3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 데이터베이스 설정
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/legal_chatbot_db

# 또는 사용자 지정 사용자 사용 시
# DATABASE_URL=mysql+pymysql://legal_user:your_password@localhost:3306/legal_chatbot_db
```

### DATABASE_URL 형식

```
mysql+pymysql://[user[:password]@][host][:port][/database]
```

예시:
- 로컬 MySQL: `mysql+pymysql://root:mypassword@localhost:3306/legal_chatbot_db`
- 원격 MySQL: `mysql+pymysql://user:pass@192.168.1.100:3306/legal_chatbot_db`

**참고**: `mysql+pymysql`은 SQLAlchemy에서 PyMySQL 드라이버를 사용한다는 의미입니다.

## 4. 데이터베이스 스키마 초기화

### 방법 1: SQL 스크립트 직접 실행

```bash
# MySQL에 접속
mysql -u root -p legal_chatbot_db

# SQL 파일 실행
source migrations/versions/001_initial_schema.sql

# 또는
mysql -u root -p legal_chatbot_db < migrations/versions/001_initial_schema.sql
```

### 방법 2: Alembic 사용 (권장)

```bash
# Alembic 초기화 (이미 완료된 경우 생략)
alembic init migrations

# 마이그레이션 실행
alembic upgrade head
```

### 방법 3: Python 스크립트 사용

```bash
python scripts/init_db.py
```

## 5. 데이터베이스 연결 확인

```bash
# Python 스크립트로 연결 테스트
python -c "from src.db.connection import db_manager; print('연결 성공!' if db_manager.health_check() else '연결 실패')"
```

또는 API 헬스 체크 엔드포인트 사용:

```bash
curl http://localhost:8000/health
```

## 6. 테이블 목록 확인

```bash
mysql -u root -p legal_chatbot_db -e "SHOW TABLES;"
```

생성된 테이블 목록:
- `chat_session` - 채팅 세션
- `chat_session_state_log` - 상태 전이 로그
- `case_master` - 사건 마스터
- `case_party` - 당사자 정보
- `case_fact` - 사실 정보
- `case_evidence` - 증거 정보
- `case_emotion` - 감정 정보
- `case_missing_field` - 누락 필드
- `case_summary` - 사건 요약
- `ai_process_log` - AI 처리 로그

## 7. 문제 해결

### 연결 오류: "could not connect to server"

**원인**: MySQL 서비스가 실행 중이 아닙니다.

**해결**:
- Windows: 
  ```powershell
  # 서비스 관리자에서 MySQL 서비스 시작
  # Win + R → services.msc → MySQL 서비스 찾아서 시작
  
  # 또는 명령줄에서
  net start MySQL80
  ```
- Linux: `sudo systemctl start mysql`
- macOS: `brew services start mysql`

### 인증 실패: "Access denied"

**원인**: 비밀번호가 잘못되었습니다.

**해결**:
1. `.env` 파일의 `DATABASE_URL`에서 비밀번호 확인
2. MySQL 비밀번호 재설정:
   ```bash
   mysql -u root -p
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
   ```

### 데이터베이스 없음: "Unknown database"

**원인**: 데이터베이스가 생성되지 않았습니다.

**해결**:
```bash
python scripts/create_db.py
```

### 권한 오류: "Access denied"

**원인**: 사용자에게 권한이 없습니다.

**해결**:
```sql
GRANT ALL PRIVILEGES ON legal_chatbot_db.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Windows에서 사용자 및 데이터베이스 수동 생성

MySQL 서버가 실행 중인 상태에서 다음 명령을 실행하세요:

```powershell
# MySQL에 접속 (비밀번호 입력 필요)
mysql -u root -p

# MySQL 프롬프트에서 다음 명령 실행:
CREATE DATABASE legal_chat_info_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'legal_chat_bot'@'localhost' IDENTIFIED BY '1qazxsw2';
GRANT ALL PRIVILEGES ON legal_chat_info_db.* TO 'legal_chat_bot'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 8. 개발 환경 vs 프로덕션 환경

### 개발 환경
- 로컬 MySQL 사용
- 간단한 비밀번호 사용 가능
- `DATABASE_URL`을 `.env`에 저장

### 프로덕션 환경
- 강력한 비밀번호 사용
- 환경 변수를 안전하게 관리 (Secret Manager 등)
- 연결 풀 설정 최적화
- 백업 전략 수립
- SSL/TLS 연결 사용 권장

## 9. 데이터베이스 백업 및 복원

### 백업
```bash
mysqldump -u root -p legal_chatbot_db > backup.sql
```

### 복원
```bash
mysql -u root -p legal_chatbot_db < backup.sql
```

## 10. MySQL과 PostgreSQL의 주요 차이점

### 문자 인코딩
- MySQL: `utf8mb4` 사용 (이모지 지원)
- PostgreSQL: `UTF8` 사용

### 데이터 타입
- MySQL: `TEXT`, `VARCHAR`, `INT`, `BIGINT`, `DATETIME`, `TIMESTAMP`
- PostgreSQL: `TEXT`, `VARCHAR`, `INTEGER`, `BIGINT`, `TIMESTAMP`

### 자동 증가
- MySQL: `AUTO_INCREMENT`
- PostgreSQL: `SERIAL` 또는 `GENERATED ALWAYS AS IDENTITY`

### 문자열 연결
- MySQL: `CONCAT()`
- PostgreSQL: `||` 또는 `CONCAT()`

## 11. 다음 단계

데이터베이스 설정이 완료되면:

1. RAG 문서 인덱싱: `python scripts/index_rag_documents.py`
2. 서버 실행: `uvicorn src.api.main:app --reload`
3. API 테스트: `http://localhost:8000/docs`
