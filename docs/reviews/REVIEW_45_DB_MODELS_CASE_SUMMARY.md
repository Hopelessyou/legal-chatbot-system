# DB Model CaseSummary 검토 보고서

## 검토 대상
- 파일: `src/db/models/case_summary.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름

### 2. 컬럼 정의 (Lines 15-21)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `case_id`: Foreign Key, NOT NULL, UNIQUE (1:1 관계)
- ✅ `summary_text`: NOT NULL, Text
- ✅ `structured_json`: Nullable JSON
- ✅ `risk_level`: Nullable String(20)
- ✅ `ai_version`: Nullable String(20)
- ✅ `created_at`: `get_kst_now()` 사용

### 3. 관계 정의 (Lines 23-24)
- ✅ `case`: `CaseMaster`와 1:1 관계 (`uselist=False`)
- ✅ `back_populates` 설정 적절

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 사용되지 않는 import (Line 6)

**문제**: `from datetime import datetime`를 import했지만 사용하지 않습니다. `get_kst_now()`를 사용하므로 불필요합니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는 import 제거

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: `case_id`는 `unique=True`이므로 자동으로 인덱스가 생성되지만, 다른 컬럼들(`risk_level`, `ai_version`, `created_at`)에 대한 인덱스가 없습니다. `risk_level`은 자주 조회될 수 있으므로 인덱스가 유용할 수 있습니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `risk_level`에 인덱스 추가 (선택적)

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, JSON, Index

__table_args__ = (
    Index('idx_summary_risk_level', 'risk_level'),
)
```

**참고**: `case_id`는 `unique=True`이므로 자동으로 인덱스가 생성됩니다. `created_at`은 자주 조회되지 않을 수 있으므로 인덱스 추가는 선택적입니다.

---

### 3. 🟢 **낮음**: `risk_level` 제약조건 없음

**문제**: `risk_level`은 K4 문서에서 "HIGH 우선"이라고 언급되어 있지만, 정확한 값 목록이 명시되어 있지 않습니다. `CaseMaster`의 `urgency_level`과 유사하게 제약조건을 추가할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `risk_level` 제약조건 추가 (선택적, 값 목록이 명확해지면)

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, JSON, Index, CheckConstraint

__table_args__ = (
    CheckConstraint("risk_level IS NULL OR risk_level IN ('LOW', 'MID', 'HIGH')", name="check_risk_level"),
    Index('idx_summary_risk_level', 'risk_level'),
)
```

**참고**: `risk_level`의 정확한 값 목록이 명확하지 않으므로, 이는 선택적 개선 사항입니다.

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 3개 (사용되지 않는 import, 인덱스 없음, risk_level 제약조건 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: `risk_level` 인덱스 추가 (성능 최적화, 선택적)
3. 🟢 **낮음**: `risk_level` 제약조건 추가 (선택적, 값 목록이 명확해지면)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 인덱스 추가

```python
"""
CaseSummary 모델
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseSummary(BaseModel):
    """최종 요약 테이블"""
    __tablename__ = "case_summary"
    __table_args__ = (
        Index('idx_summary_risk_level', 'risk_level'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("case_master.case_id", ondelete="CASCADE"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    structured_json = Column(JSON)
    risk_level = Column(String(20))
    ai_version = Column(String(20))
    created_at = Column(DateTime, nullable=False, default=get_kst_now)
    
    # Relationships
    case = relationship("CaseMaster", back_populates="summary")
```

---

## ✅ 결론

`CaseSummary` 모델은 전반적으로 잘 구현되어 있습니다. **사용되지 않는 import 제거**를 권장합니다. `risk_level` 인덱스 추가는 성능 최적화를 위해 고려할 수 있지만, 현재 데이터 규모에서는 선택적입니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: `risk_level` 인덱스 추가 (성능 최적화, 선택적)
3. 🟢 **낮음**: `risk_level` 제약조건 추가 (선택적, 값 목록이 명확해지면)

