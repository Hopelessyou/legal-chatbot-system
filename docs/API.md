# API 명세서

## 개요

본 API는 RAG + LangGraph 기반 법률 상담문의 수집 챗봇 시스템의 REST API입니다.

**Base URL**: `http://localhost:8000`

**인증**: Bearer Token (선택사항)

## 공통 응답 형식

### 성공 응답
```json
{
  "success": true,
  "data": {
    // 응답 데이터
  },
  "error": null
}
```

### 에러 응답
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": {}
  }
}
```

## 엔드포인트

### 1. POST /chat/start

상담 세션을 시작합니다.

**Request Body:**
```json
{
  "channel": "web",
  "user_meta": {
    "device": "desktop",
    "locale": "ko-KR"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "state": "INIT",
    "bot_message": "안녕하세요. 법률 상담을 도와드리겠습니다. 사건이 언제 발생했는지 알려주세요.",
    "expected_input": {
      "type": "date",
      "field": "incident_date"
    }
  }
}
```

### 2. POST /chat/message

사용자 메시지를 처리하고 LangGraph를 1 step 실행합니다.

**Request Body:**
```json
{
  "session_id": "sess_abc123",
  "user_message": "작년 10월쯤 계약을 했어요."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "current_state": "FACT_COLLECTION",
    "completion_rate": 35,
    "bot_message": "계약 상대방은 개인인가요, 법인인가요?",
    "expected_input": {
      "type": "choice",
      "field": "counterparty_type",
      "options": ["개인", "법인"]
    }
  }
}
```

### 3. POST /chat/end

상담을 종료하고 최종 요약을 생성합니다.

**Request Body:**
```json
{
  "session_id": "sess_abc123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "final_state": "COMPLETED",
    "completion_rate": 92,
    "summary": {
      "summary_text": "2023년 10월 개인과 계약을 체결하였으나 대금 미지급 문제가 발생한 사안입니다.",
      "structured_data": {
        "사건_유형": "민사 / 계약 분쟁",
        "핵심_사실관계": "...",
        "금액_및_증거": "...",
        "특이사항": "..."
      }
    }
  }
}
```

### 4. GET /chat/status

현재 상담 상태를 조회합니다.

**Query Parameters:**
- `session_id` (required): 세션 ID

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "state": "FACT_COLLECTION",
    "completion_rate": 35,
    "filled_fields": ["incident_date", "contract_type"],
    "missing_fields": ["counterparty", "amount"]
  }
}
```

### 5. GET /chat/result

최종 상담 결과를 조회합니다.

**Query Parameters:**
- `session_id` (required): 세션 ID

**Response:**
```json
{
  "success": true,
  "data": {
    "case_summary_text": "2023년 10월 개인과 계약을 체결하였으나 대금 미지급 문제가 발생한 사안입니다.",
    "structured_data": {
      "case_type": "민사",
      "sub_type": "대여금/계약",
      "amount": 50000000,
      "evidence": true
    },
    "completion_rate": 92
  }
}
```

## 에러 코드

| 코드 | 설명 | HTTP 상태 코드 |
|------|------|----------------|
| SESSION_NOT_FOUND | 세션을 찾을 수 없음 | 404 |
| INVALID_INPUT | 잘못된 입력 | 400 |
| VALIDATION_ERROR | 요청 데이터 검증 실패 | 422 |
| GPT_API_ERROR | GPT API 호출 오류 | 500 |
| RAG_SEARCH_ERROR | RAG 검색 오류 | 500 |
| DATABASE_ERROR | 데이터베이스 오류 | 500 |
| INTERNAL_SERVER_ERROR | 서버 내부 오류 | 500 |

## 사용 예시

### Python
```python
import requests

# 1. 상담 시작
response = requests.post(
    "http://localhost:8000/chat/start",
    json={"channel": "web"}
)
session_id = response.json()["data"]["session_id"]

# 2. 메시지 전송
response = requests.post(
    "http://localhost:8000/chat/message",
    json={
        "session_id": session_id,
        "user_message": "작년 10월에 계약을 했는데 대금을 받지 못했습니다."
    }
)
print(response.json()["data"]["bot_message"])

# 3. 상담 종료
response = requests.post(
    "http://localhost:8000/chat/end",
    json={"session_id": session_id}
)
print(response.json()["data"]["summary"])
```

### cURL
```bash
# 상담 시작
curl -X POST "http://localhost:8000/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"channel": "web"}'

# 메시지 전송
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_xxx",
    "user_message": "테스트 메시지"
  }'
```

