# DB Model CaseParty 검토 보고서

## 검토 대상
- 파일: `src/db/models/case_party.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름
- ✅ `__table_args__`: 제약조건 정의 적절

### 2. 제약조건 (Lines 14-17)
- ✅ `CheckConstraint`로 `party_role` 값 검증: `의뢰인`, `상대방`
- ✅ `CheckConstraint`로 `party_type` 값 검증: `개인`, `법인`

### 3. 컬럼 정의 (Lines 19-24)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `case_id`: Foreign Key, NOT NULL
- ✅ `party_role`: NOT NULL, String(20)
- ✅ `party_type`: Nullable String(20)
- ✅ `party_description`: Nullable String(255)
- ✅ `created_at`: `get_kst_now()` 사용

### 4. 관계 정의 (Lines 26-27)
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
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: SQL 스키마에는 `idx_case_party_case` 인덱스가 있지만 모델에는 정의되어 있지 않습니다. `case_id`는 자주 조회되는 컬럼이므로 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `case_id`에 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index

__table_args__ = (
    CheckConstraint("party_role IN ('의뢰인', '상대방')", name="check_party_role"),
    CheckConstraint("party_type IN ('개인', '법인')", name="check_party_type"),
    Index('idx_case_party_case', 'case_id'),
)
```

---

### 3. 🟢 **낮음**: `party_type`이 Nullable이지만 제약조건이 있음

**문제**: `party_type`이 Nullable이지만 `CheckConstraint`가 있어서 NULL이 아닌 경우에만 값 검증이 됩니다. 이는 의도된 동작일 수 있지만, 일관성을 위해 확인이 필요합니다.

**영향도**: 낮음  
**수정 권장**: 현재 구현이 적절하므로 변경 불필요 (NULL 허용은 정상)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 2개 (사용되지 않는 import, 인덱스 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 인덱스 추가

```python
"""
CaseParty 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseParty(BaseModel):
    """사건 당사자 정보 테이블"""
    __tablename__ = "case_party"
    __table_args__ = (
        CheckConstraint("party_role IN ('의뢰인', '상대방')", name="check_party_role"),
        CheckConstraint("party_type IN ('개인', '법인')", name="check_party_type"),
        Index('idx_case_party_case', 'case_id'),
    )
```

---

## ✅ 결론

`CaseParty` 모델은 전반적으로 잘 구현되어 있으며, 제약조건도 적절하게 설정되어 있습니다. **인덱스 추가**와 **사용되지 않는 import 제거**를 권장합니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)

