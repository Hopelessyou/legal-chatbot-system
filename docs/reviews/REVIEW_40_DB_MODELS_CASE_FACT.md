# DB Model CaseFact 검토 보고서

## 검토 대상
- 파일: `src/db/models/case_fact.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름
- ✅ `__table_args__`: 제약조건 정의 적절

### 2. 제약조건 (Lines 14-16)
- ✅ `CheckConstraint`로 `confidence_score` 범위 검증: 0~100

### 3. 컬럼 정의 (Lines 18-27)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `case_id`: Foreign Key, NOT NULL
- ✅ `fact_type`, `location`, `description`, `source_text`: Nullable String/Text
- ✅ `incident_date`: Nullable Date
- ✅ `amount`: Nullable BigInteger
- ✅ `confidence_score`: Nullable Integer
- ✅ `created_at`: `get_kst_now()` 사용

### 4. 관계 정의 (Lines 29-30)
- ✅ `case`: `CaseMaster`와 N:1 관계
- ✅ `back_populates` 설정 적절

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 사용되지 않는 import (Line 6)

**문제**: `from datetime import datetime`를 import했지만 사용하지 않습니다. `get_kst_now()`를 사용하므로 불필요합니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는 import 제거

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Date, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: SQL 스키마에는 `idx_case_fact_case` 인덱스가 있지만 모델에는 정의되어 있지 않습니다. `case_id`는 자주 조회되는 컬럼이므로 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `case_id`에 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Date, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index

__table_args__ = (
    CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="check_confidence_score"),
    Index('idx_case_fact_case', 'case_id'),
)
```

---

### 3. 🟢 **낮음**: `amount` 음수 검증 없음

**문제**: `amount`가 음수일 수 있습니다. 금액이므로 0 이상이어야 합니다.

**영향도**: 낮음  
**수정 권장**: `CheckConstraint` 추가

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="check_confidence_score"),
    CheckConstraint("amount IS NULL OR amount >= 0", name="check_amount"),
    Index('idx_case_fact_case', 'case_id'),
)
```

---

### 4. 🟢 **낮음**: `fact_type` 값 검증 없음

**문제**: `fact_type`에 제약조건이 없어서 임의의 값이 들어갈 수 있습니다. 하지만 이는 동적으로 변할 수 있는 값이므로 제약조건 추가는 선택적입니다.

**영향도**: 낮음  
**수정 권장**: 필요시 ENUM 타입 사용 또는 CheckConstraint 추가 (선택적)

---

### 5. 🟢 **낮음**: `incident_date` 미래 날짜 검증 없음

**문제**: `incident_date`가 미래 날짜일 수 있습니다. 사건 발생일은 일반적으로 현재보다 과거여야 합니다.

**영향도**: 낮음  
**수정 권장**: 필요시 `CheckConstraint` 추가 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 5개 (사용되지 않는 import, 인덱스 없음, amount/incident_date 검증 없음, fact_type 검증 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `amount` 음수 검증 추가

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 인덱스 추가

```python
"""
CaseFact 모델
"""
from sqlalchemy import Column, BigInteger, String, Date, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseFact(BaseModel):
    """핵심 사실관계 테이블"""
    __tablename__ = "case_fact"
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="check_confidence_score"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="check_amount"),
        Index('idx_case_fact_case', 'case_id'),
    )
```

---

## ✅ 결론

`CaseFact` 모델은 전반적으로 잘 구현되어 있으나, **인덱스 추가**와 **값 검증 강화**를 권장합니다. 또한 사용되지 않는 import를 제거하는 것이 좋습니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `amount` 음수 검증 추가

