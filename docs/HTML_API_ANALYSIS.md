# chat_gpt.html API 통신 및 세션 관리 상세 분석

## 📋 목차
1. [전체 구조 개요](#전체-구조-개요)
2. [초기화 및 설정](#초기화-및-설정)
3. [API 세션 관리](#api-세션-관리)
4. [데이터 송수신 방식](#데이터-송수신-방식)
5. [에러 처리 및 복구](#에러-처리-및-복구)
6. [상태 관리](#상태-관리)

---

## 전체 구조 개요

### 핵심 변수
```javascript
const API_BASE_URL = window.location.origin;  // 동적 API 주소 (예: http://localhost:8000)
let API_KEY = localStorage.getItem('api_key'); // localStorage에서 API 키 로드
let sessionId = null;                          // 현재 세션 ID (메모리에만 저장)
let isProcessing = false;                      // 중복 요청 방지 플래그
let currentStep = 'greeting';                 // 현재 대화 단계
```

### 주요 특징
- **세션 복원 비활성화**: 새로고침 시 항상 새 세션 시작
- **캐시 완전 비활성화**: 모든 API 요청에 캐시 우회 설정
- **타임아웃 처리**: 5초 타임아웃으로 서버 응답 대기
- **Service Worker 해제**: 오프라인 캐시 방지

---

## 초기화 및 설정

### 1. 파일 프로토콜 체크 (1160-1182줄)
```javascript
if (window.location.protocol === 'file:') {
    // file:// 프로토콜로 직접 열면 에러 메시지 표시
    // 서버를 통해서만 접근 가능하도록 강제
}
```

**목적**: HTML 파일을 직접 열 수 없도록 방지

### 2. API Base URL 설정 (1184줄)
```javascript
const API_BASE_URL = window.location.origin;
// 예: http://localhost:8000
```

**특징**: 
- 동적으로 현재 호스트 사용
- 개발/프로덕션 환경 자동 대응

### 3. API 키 관리 (1187-1199줄)
```javascript
let API_KEY = localStorage.getItem('api_key');
if (!API_KEY) {
    API_KEY = prompt('API 키를 입력하세요...');
    if (API_KEY) {
        localStorage.setItem('api_key', API_KEY);
    }
}
```

**특징**:
- localStorage에 영구 저장
- 없으면 prompt로 입력받음
- 한 번 저장하면 자동 로드

### 4. 헤더 생성 함수 (1211-1220줄)
```javascript
function getHeaders() {
    const headers = {
        'Content-Type': 'application/json',
    };
    if (API_KEY) {
        headers['Authorization'] = `Bearer ${API_KEY}`;
    }
    return headers;
}
```

**특징**:
- 모든 요청에 `Content-Type: application/json` 포함
- API 키가 있으면 `Authorization: Bearer {API_KEY}` 추가
- Bearer 토큰 방식 사용

---

## API 세션 관리

### 1. 세션 시작 (`startSession` 함수, 1258-1481줄)

#### 1.1 Service Worker 해제 (1264-1275줄)
```javascript
if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (let registration of registrations) {
        await registration.unregister();
    }
}
```

**목적**: 오프라인 캐시로 인한 문제 방지

#### 1.2 API 연결 테스트 (1281-1290줄)
```javascript
try {
    const isConnected = await testApiConnection();
    if (!isConnected) {
        logWarn('API 연결 테스트 실패, 계속 진행');
    }
} catch (testError) {
    logWarn('API 연결 테스트 중 오류, 계속 진행');
    // 연결 테스트 실패해도 실제 API 호출은 시도
}
```

**특징**:
- 선택적 테스트 (실패해도 계속 진행)
- 실제 세션 시작은 별도로 시도

#### 1.3 세션 복원 비활성화 (1292-1298줄)
```javascript
const savedSessionId = localStorage.getItem('current_session_id');
if (savedSessionId) {
    logInfo('저장된 세션 ID 삭제 (새 세션 시작)');
    localStorage.removeItem('current_session_id');
}
```

**목적**: 새로고침 시 항상 새 세션 시작

#### 1.4 세션 시작 API 호출 (1307-1358줄)

**캐시 우회 설정**:
```javascript
const headers = {
    ...getHeaders(),
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
    'X-Request-ID': `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
};
```

**타임아웃 설정**:
```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);  // 5초

response = await fetch(`${API_BASE_URL}/chat/start?t=${Date.now()}&r=${Math.random()}`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(startRequestBody),
    cache: 'no-store',
    credentials: 'omit',
    signal: controller.signal
});
```

**요청 데이터**:
```javascript
{
    channel: 'web',
    user_id: `user_${Date.now()}`,
    device: 'desktop'
}
```

**응답 검증** (1362-1428줄):
```javascript
// 1. response 존재 확인
if (!response) {
    throw new Error('서버로부터 응답을 받을 수 없습니다...');
}

// 2. HTTP 상태 확인
if (!response.ok) {
    if (response.status === 401) {
        // API 키 오류 처리
        localStorage.removeItem('api_key');
        throw new Error('API 키가 유효하지 않습니다...');
    }
    // 기타 오류 처리
}

// 3. 응답 텍스트 읽기 (캐시 확인)
const responseText = await response.text();
if (!responseText || responseText.trim() === '') {
    throw new Error('서버로부터 빈 응답을 받았습니다...');
}

// 4. JSON 파싱
data = JSON.parse(responseText);

// 5. 응답 구조 검증
if (!data.success) {
    throw new Error(data.error?.message || '세션 시작 실패');
}
if (!data.data) {
    throw new Error('서버 응답에 데이터가 없습니다.');
}
if (!data.data.session_id) {
    throw new Error('서버 응답에 세션 ID가 없습니다.');
}
```

**성공 시 처리** (1430-1447줄):
```javascript
sessionId = data.data.session_id;
// 세션 ID 저장하지 않음 (새로고침 시 항상 새 세션 시작)

// 서버 응답의 bot_message만 표시
const botMessage = data.data.bot_message;
if (botMessage && botMessage.trim()) {
    addMessage('bot', botMessage);
}

// 입력 필드 활성화
chatInput.disabled = false;
sendButton.disabled = false;
```

---

## 데이터 송수신 방식

### 1. 메시지 전송 (`sendMessage` 함수, 1538-1592줄)

#### 요청 전송
```javascript
const response = await fetch(`${API_BASE_URL}/chat/message`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
        session_id: sessionId,
        user_message: message
    })
});
```

**요청 데이터 구조**:
```json
{
    "session_id": "sess_xxx",
    "user_message": "사용자 입력 메시지"
}
```

#### 응답 처리
```javascript
const data = await response.json();

if (data.success && data.data) {
    handleBotResponse(data.data);
} else {
    throw new Error(data.error?.message || '메시지 전송 실패');
}
```

**응답 데이터 구조**:
```json
{
    "success": true,
    "data": {
        "session_id": "sess_xxx",
        "current_state": "FACT_COLLECTION",
        "bot_message": "봇 응답 메시지",
        "completion_rate": 25,
        "expected_input": {...},
        "conversation_history": [...],
        "skipped_fields": [...],
        "initial_analysis": {...}
    }
}
```

### 2. 봇 응답 처리 (`handleBotResponse` 함수, 1650-1725줄)

#### 데이터 추출
```javascript
const botMessage = data.bot_message || '';
const state = data.current_state || data.state;
const previousState = currentStep;
```

#### 상태별 처리
```javascript
if (state === 'CASE_CLASSIFICATION') {
    // 유형 선택 버튼 표시
    if (botMessage && botMessage.trim()) {
        addMessage('bot', botMessage);
    }
    addButtonGroup('🧭 STEP 2. 어떤 유형에 가까운가요?', [...]);
}
else if (state === 'FACT_COLLECTION') {
    // 사실 수집 단계
    if (botMessage && botMessage.trim()) {
        addMessage('bot', botMessage);
    }
}
// ... 기타 상태 처리
else if (state === 'COMPLETED') {
    // 완료 단계
    if (botMessage && botMessage.trim()) {
        addMessage('bot', botMessage);
    }
    loadFinalSummary(sessionId);  // 최종 요약 로드
}
```

**특징**:
- 모든 상태에서 `bot_message`가 있으면 표시
- 상태별로 추가 UI 요소 표시 (버튼 등)
- 상태 전이 로깅

### 3. 최종 요약 로드 (`loadFinalSummary` 함수, 1727-1776줄)

```javascript
async function loadFinalSummary(sessionId) {
    const response = await fetch(`${API_BASE_URL}/chat/result?session_id=${sessionId}`, {
        method: 'GET',
        headers: getHeaders()
    });
    
    if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
            displayFinalSummary(data.data);
        }
    }
}
```

**요청**: `GET /chat/result?session_id={sessionId}`

**응답 구조**:
```json
{
    "success": true,
    "data": {
        "case_summary_text": "요약 텍스트",
        "structured_data": {
            "사건_유형": "...",
            "핵심_사실관계": "...",
            "금액_및_증거": "...",
            "특이사항": "..."
        },
        "completion_rate": 100
    }
}
```

---

## 에러 처리 및 복구

### 1. 네트워크 오류 처리

#### fetch 실패 시 (1340-1358줄)
```javascript
catch (fetchError) {
    // 즉시 에러 표시 및 입력 비활성화
    addErrorMessage(`API 서버에 연결할 수 없습니다...`);
    updateStatus('연결 실패', false);
    chatInput.disabled = true;
    sendButton.disabled = true;
    sessionId = null;
    throw fetchError;
}
```

#### 타임아웃 처리 (1333-1339줄)
```javascript
catch (fetchError) {
    clearTimeout(timeoutId);
    if (fetchError.name === 'AbortError') {
        throw new Error('서버 응답 시간이 초과되었습니다...');
    }
    throw fetchError;
}
```

### 2. HTTP 오류 처리

#### 401 Unauthorized (1369-1373줄, 1562-1567줄)
```javascript
if (response.status === 401) {
    localStorage.removeItem('api_key');
    throw new Error('API 키가 유효하지 않습니다...');
}
```

**처리 방식**:
- API 키 삭제
- 사용자에게 재입력 요청

#### 기타 HTTP 오류
```javascript
const errorData = await response.json().catch(() => ({
    error: { message: `HTTP ${response.status}: ${response.statusText}` }
}));
throw new Error(errorData.error?.message || ...);
```

### 3. JSON 파싱 오류 처리 (1397-1406줄)
```javascript
try {
    data = JSON.parse(responseText);
} catch (parseError) {
    logError('응답 JSON 파싱 실패', {
        error: parseError.message,
        responseText: responseText.substring(0, 500)
    });
    throw new Error(`서버 응답을 파싱할 수 없습니다...`);
}
```

### 4. 통합 에러 처리 (1448-1480줄)
```javascript
catch (error) {
    // 네트워크 오류 감지
    if (error.message.includes('Failed to fetch') || 
        error.message.includes('NetworkError') || ...) {
        errorMessage = `API 서버에 연결할 수 없습니다...`;
    }
    
    // 에러 메시지 표시 및 입력 비활성화
    addErrorMessage(`세션 시작 실패: ${errorMessage}`);
    updateStatus('연결 실패', false);
    chatInput.disabled = true;
    sendButton.disabled = true;
    sessionId = null;
}
```

---

## 상태 관리

### 1. 세션 상태 변수
```javascript
let sessionId = null;        // 현재 세션 ID (메모리만)
let isProcessing = false;    // 중복 요청 방지
let currentStep = 'greeting'; // 현재 대화 단계
```

### 2. 상태 전이 추적
```javascript
// handleBotResponse에서
const previousState = currentStep;
const state = data.current_state || data.state;

if (previousState !== state) {
    logStateTransition(previousState, state, sessionId);
}

currentStep = state ? state.toLowerCase() : currentStep;
```

### 3. 중복 요청 방지
```javascript
// sendMessage 시작 시
if (!message || isProcessing || !sessionId) return;

isProcessing = true;
// ... API 호출 ...
finally {
    isProcessing = false;
}
```

---

## 주요 특징 요약

### ✅ 강점
1. **캐시 완전 비활성화**: 타임스탬프 + 랜덤 값으로 캐시 우회
2. **타임아웃 처리**: 5초 타임아웃으로 무한 대기 방지
3. **Service Worker 해제**: 오프라인 캐시 방지
4. **상세한 에러 처리**: 네트워크, HTTP, JSON 파싱 오류 모두 처리
5. **응답 검증**: 다단계 검증으로 잘못된 응답 방지
6. **로깅 시스템**: 모든 API 요청/응답 로깅

### ⚠️ 주의사항
1. **세션 ID 저장 안 함**: 새로고침 시 항상 새 세션 시작
2. **API 키 localStorage 저장**: 보안 고려 필요
3. **타임아웃 5초**: 느린 네트워크 환경에서 짧을 수 있음

### 🔄 데이터 흐름
```
1. 페이지 로드
   ↓
2. API 키 확인/입력
   ↓
3. startSession() 호출
   ↓
4. Service Worker 해제
   ↓
5. API 연결 테스트 (선택적)
   ↓
6. POST /chat/start 요청
   ↓
7. 세션 ID 받음
   ↓
8. bot_message 표시
   ↓
9. 사용자 입력 대기
   ↓
10. POST /chat/message 요청
    ↓
11. handleBotResponse() 처리
    ↓
12. 상태별 UI 업데이트
    ↓
13. 반복 (9-12)
    ↓
14. COMPLETED 상태 도달
    ↓
15. GET /chat/result 요청
    ↓
16. 최종 요약 표시
```

---

## API 엔드포인트 요약

### POST /chat/start
- **목적**: 새 세션 시작
- **요청**: `{ channel, user_id, device }`
- **응답**: `{ success, data: { session_id, state, bot_message } }`

### POST /chat/message
- **목적**: 사용자 메시지 전송
- **요청**: `{ session_id, user_message }`
- **응답**: `{ success, data: { current_state, bot_message, completion_rate, ... } }`

### GET /chat/result
- **목적**: 최종 요약 정보 조회
- **요청**: `?session_id={sessionId}`
- **응답**: `{ success, data: { case_summary_text, structured_data, completion_rate } }`

---

## 보안 고려사항

1. **API 키 관리**
   - localStorage에 평문 저장 (개선 필요)
   - Bearer 토큰 방식 사용

2. **세션 관리**
   - 세션 ID는 메모리에만 저장
   - 새로고침 시 자동으로 새 세션 시작

3. **캐시 방지**
   - 모든 요청에 캐시 비활성화 헤더
   - URL에 타임스탬프 추가

---

## 디버깅 기능

### 로깅 시스템
- 모든 API 요청/응답 로깅
- 상태 전이 로깅
- 에러 상세 로깅

### 디버그 패널
- F12 개발자 도구 또는 헤더 버튼으로 접근
- 최대 100개 로그 저장
- 로그 레벨별 색상 구분

---

## 개선 제안

1. **API 키 암호화**: localStorage에 평문 저장 대신 암호화
2. **재시도 로직**: 네트워크 오류 시 자동 재시도
3. **오프라인 감지**: 네트워크 상태 확인 및 사용자 알림
4. **세션 복원 옵션**: 선택적으로 세션 복원 가능하도록
5. **타임아웃 조정**: 환경에 따라 동적 조정


