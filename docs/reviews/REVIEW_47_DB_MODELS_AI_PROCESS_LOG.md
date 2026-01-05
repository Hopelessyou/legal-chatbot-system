# DB Model AIProcessLog 검토 보고서

## 검토 대상
- 파일: `src/db/models/ai_process_log.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름

### 2. 컬럼 정의 (Lines 15-22)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `session_id`: Foreign Key, NOT NULL
- ✅ `node_name`: Nullable String(50)
- ✅ `model`: Nullable String(50)
- ✅ `token_input`: Nullable Integer
- ✅ `token_output`: Nullable Integer
- ✅ `latency_ms`: Nullable Integer
- ✅ `created_at`: `get_kst_now()` 사용

### 3. 관계 정의 (Lines 24-25)
- ✅ `session`: `ChatSession`와 N:1 관계
- ✅ `back_populates` 설정 적절

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 사용되지 않는 import (Line 6)

**문제**: `from datetime import datetime`를 import했지만 사용하지 않습니다. `get_kst_now()`를 사용하므로 불필요합니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는 import 제거

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: SQL 스키마(`001_initial_schema.sql`)에는 `idx_ai_log_session`과 `idx_ai_log_created` 인덱스가 있지만 모델에는 정의되어 있지 않습니다. `session_id`와 `created_at`은 자주 조회되는 컬럼이므로 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `session_id`와 `created_at`에 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index, CheckConstraint

__table_args__ = (
    Index('idx_ai_log_session', 'session_id'),
    Index('idx_ai_log_created', 'created_at'),
)
```

---

### 3. 🟢 **낮음**: 숫자 필드 제약조건 없음

**문제**: `token_input`, `token_output`, `latency_ms`는 음수 값이 들어갈 수 있습니다. 토큰 수와 지연 시간은 항상 0 이상이어야 합니다.

**영향도**: 낮음  
**수정 권장**: 숫자 필드에 `CheckConstraint` 추가

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("token_input IS NULL OR token_input >= 0", name="check_token_input"),
    CheckConstraint("token_output IS NULL OR token_output >= 0", name="check_token_output"),
    CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="check_latency_ms"),
    Index('idx_ai_log_session', 'session_id'),
    Index('idx_ai_log_created', 'created_at'),
)
```

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 3개 (사용되지 않는 import, 인덱스 없음, 숫자 필드 제약조건 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: 숫자 필드 제약조건 추가 (데이터 무결성)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거, 인덱스 및 제약조건 추가

```python
"""
AIProcessLog 모델
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class AIProcessLog(BaseModel):
    """GPT / RAG 호출 로그 테이블"""
    __tablename__ = "ai_process_log"
    __table_args__ = (
        CheckConstraint("token_input IS NULL OR token_input >= 0", name="check_token_input"),
        CheckConstraint("token_output IS NULL OR token_output >= 0", name="check_token_output"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="check_latency_ms"),
        Index('idx_ai_log_session', 'session_id'),
        Index('idx_ai_log_created', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    node_name = Column(String(50))
    model = Column(String(50))
    token_input = Column(Integer)
    token_output = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    session = relationship("ChatSession", back_populates="ai_logs")
```

---

## ✅ 결론

`AIProcessLog` 모델은 전반적으로 잘 구현되어 있습니다. **사용되지 않는 import 제거**, **인덱스 추가**, **숫자 필드 제약조건 추가**를 권장합니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: 숫자 필드 제약조건 추가 (데이터 무결성)

