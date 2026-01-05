# DB Constants 검토 보고서

## 검토 대상
- 파일: `src/db/constants.py`
- 검토 일자: 2024년
- 검토 범위: DB 관련 상수, 열거형

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 7-27)
- ✅ `FieldLength` 클래스: DB 필드 길이 상수 정의
- ✅ 명확한 상수 이름과 값 정의
- ✅ 주석으로 용도 설명

### 2. 상수 정의 (Lines 9-27)
- ✅ 주요 DB 필드 길이 상수들이 모두 정의됨
- ✅ 일관된 네이밍 컨벤션 (UPPER_SNAKE_CASE)

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 사용되지 않는 import (Line 4)

**문제**: `from typing import Dict`를 import했지만 사용하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는 import 제거

**수정 예시**:
```python
"""
DB 관련 상수 정의
"""
# from typing import Dict  # 제거


class FieldLength:
    """DB 필드 길이 상수"""
    ...
```

---

### 2. 🟡 **중간**: 상수 사용되지 않음

**문제**: `FieldLength` 클래스의 상수들이 정의되어 있지만, 실제 DB 모델에서는 하드코딩된 값들을 사용하고 있습니다. 예를 들어:
- `chat_session.py`: `Column(String(50))` 대신 `Column(String(FieldLength.SESSION_ID))` 사용 가능
- `chat_file.py`: `Column(String(255))` 대신 `Column(String(FieldLength.FILE_NAME))` 사용 가능

**영향도**: 중간 (유지보수성 저하, 일관성 부족)  
**수정 권장**: DB 모델에서 `FieldLength` 상수 사용 (선택적, 대규모 리팩토링 필요)

**수정 예시**:
```python
# chat_session.py
from src.db.constants import FieldLength

session_id = Column(String(FieldLength.SESSION_ID), primary_key=True)
```

**참고**: 이는 대규모 리팩토링 작업이므로, 현재는 상수 정의만 유지하고 향후 개선 사항으로 남겨두는 것이 좋습니다.

---

### 3. 🟢 **낮음**: 누락된 상수

**문제**: 일부 DB 모델에서 사용되는 필드 길이가 `FieldLength`에 정의되어 있지 않습니다. 예를 들어:
- `user_hash`: 64 (ChatSession)
- `current_state`: 30 (ChatSession, ChatSessionStateLog)
- `risk_level`: 20 (CaseSummary)
- `ai_version`: 20 (CaseSummary)

**영향도**: 낮음  
**수정 권장**: 누락된 상수 추가 (선택적)

**수정 예시**:
```python
class FieldLength:
    """DB 필드 길이 상수"""
    SESSION_ID = 50
    FILE_NAME = 255
    FILE_PATH = 500
    PARTY_DESCRIPTION = 255
    CASE_TYPE = 50
    SUB_CASE_TYPE = 50
    CASE_STAGE = 30
    STATUS = 20
    EVIDENCE_TYPE = 50
    EVIDENCE_DESCRIPTION = 255
    FACT_TYPE = 50
    FACT_LOCATION = 255
    EMOTION_TYPE = 50
    MISSING_FIELD_KEY = 50
    NODE_NAME = 50
    MODEL_NAME = 50
    CONDITION_KEY = 50
    FILE_TYPE = 50
    FILE_EXTENSION = 10
    # 추가
    USER_HASH = 64
    CURRENT_STATE = 30
    RISK_LEVEL = 20
    AI_VERSION = 20
```

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 2개 (사용되지 않는 import, 누락된 상수)
- 🟡 **중간**: 1개 (상수 사용되지 않음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 누락된 상수 추가 (선택적)
3. 🟡 **중간**: DB 모델에서 `FieldLength` 상수 사용 (대규모 리팩토링, 선택적)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 누락된 상수 추가

```python
"""
DB 관련 상수 정의
"""


class FieldLength:
    """DB 필드 길이 상수"""
    SESSION_ID = 50
    FILE_NAME = 255
    FILE_PATH = 500
    PARTY_DESCRIPTION = 255
    CASE_TYPE = 50
    SUB_CASE_TYPE = 50
    CASE_STAGE = 30
    STATUS = 20
    EVIDENCE_TYPE = 50
    EVIDENCE_DESCRIPTION = 255
    FACT_TYPE = 50
    FACT_LOCATION = 255
    EMOTION_TYPE = 50
    MISSING_FIELD_KEY = 50
    NODE_NAME = 50
    MODEL_NAME = 50
    CONDITION_KEY = 50
    FILE_TYPE = 50
    FILE_EXTENSION = 10
    # 추가 상수
    USER_HASH = 64
    CURRENT_STATE = 30
    RISK_LEVEL = 20
    AI_VERSION = 20
```

---

## ✅ 결론

`db/constants.py` 파일은 `FieldLength` 클래스를 통해 DB 필드 길이 상수를 정의하고 있습니다. **사용되지 않는 import 제거**를 권장합니다. 누락된 상수 추가는 선택적이며, DB 모델에서 상수 사용은 향후 대규모 리팩토링 작업으로 고려할 수 있습니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 누락된 상수 추가 (선택적)
3. 🟡 **중간**: DB 모델에서 `FieldLength` 상수 사용 (대규모 리팩토링, 선택적)

