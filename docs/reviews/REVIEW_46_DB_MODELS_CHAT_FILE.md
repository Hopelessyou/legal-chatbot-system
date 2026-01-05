# DB Model ChatFile 검토 보고서

## 검토 대상
- 파일: `src/db/models/chat_file.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름

### 2. 컬럼 정의 (Lines 15-25)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `session_id`: Foreign Key, NOT NULL
- ✅ `file_name`: NOT NULL, String(255)
- ✅ `file_path`: NOT NULL, String(500)
- ✅ `file_size`: NOT NULL, Integer (bytes)
- ✅ `file_type`: Nullable String(50) (MIME type)
- ✅ `file_extension`: Nullable String(10)
- ✅ `description`: Nullable Text
- ✅ `uploaded_at`, `created_at`, `updated_at`: `get_kst_now()` 사용

### 3. 관계 정의 (Lines 27-28)
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
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: SQL 스키마(`002_add_chat_file_table.sql`)에는 `idx_file_session`과 `idx_file_uploaded` 인덱스가 있지만 모델에는 정의되어 있지 않습니다. `session_id`와 `uploaded_at`은 자주 조회되는 컬럼이므로 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `session_id`와 `uploaded_at`에 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text, Index, CheckConstraint

__table_args__ = (
    Index('idx_file_session', 'session_id'),
    Index('idx_file_uploaded', 'uploaded_at'),
)
```

---

### 3. 🟢 **낮음**: `file_size` 제약조건 없음

**문제**: `file_size`는 파일 크기(bytes)를 저장하는데, 음수 값이 들어갈 수 있습니다. 파일 크기는 항상 0 이상이어야 합니다.

**영향도**: 낮음  
**수정 권장**: `file_size`에 `CheckConstraint` 추가

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("file_size >= 0", name="check_file_size"),
    Index('idx_file_session', 'session_id'),
    Index('idx_file_uploaded', 'uploaded_at'),
)
```

---

### 4. 🟢 **낮음**: `file_extension` 길이 제한

**문제**: `file_extension`이 `String(10)`으로 정의되어 있지만, 일부 확장자는 더 길 수 있습니다 (예: `.docx`, `.pptx`, `.xlsx` 등). 하지만 대부분의 확장자는 10자 이내이므로 큰 문제는 아닙니다.

**영향도**: 낮음 (현재는 문제가 없지만, 향후 일부 확장자에서 문제 발생 가능)  
**수정 권장**: 선택적 (필요시 `String(20)`으로 확장)

**참고**: 현재는 대부분의 확장자가 10자 이내이므로 수정하지 않아도 됩니다.

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 3개 (사용되지 않는 import, 인덱스 없음, file_size 제약조건 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `file_size` 제약조건 추가 (데이터 무결성)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거, 인덱스 및 제약조건 추가

```python
"""
ChatFile 모델 - 채팅 세션에 첨부된 파일 정보
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class ChatFile(BaseModel):
    """채팅 세션 파일 첨부 테이블"""
    __tablename__ = "chat_file"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="check_file_size"),
        Index('idx_file_session', 'session_id'),
        Index('idx_file_uploaded', 'uploaded_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_session.session_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    file_type = Column(String(50))  # MIME type
    file_extension = Column(String(10))  # .pdf, .jpg, etc.
    description = Column(Text)  # 사용자가 입력한 설명
    uploaded_at = Column(DateTime, nullable=False, default=get_kst_now)
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    updated_at = Column(DateTime, nullable=False, default=get_kst_now, onupdate=get_kst_now)
    
    # Relationships
    session = relationship("ChatSession", back_populates="files")
```

---

## ✅ 결론

`ChatFile` 모델은 전반적으로 잘 구현되어 있습니다. **사용되지 않는 import 제거**, **인덱스 추가**, **`file_size` 제약조건 추가**를 권장합니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `file_size` 제약조건 추가 (데이터 무결성)

