# DB Model CaseMissingField 검토 보고서

## 검토 대상
- 파일: `src/db/models/case_missing_field.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름

### 2. 컬럼 정의 (Lines 15-21)
- ✅ `id`: Primary Key, BigInteger, autoincrement
- ✅ `case_id`: Foreign Key, NOT NULL
- ✅ `field_key`: NOT NULL, String(50)
- ✅ `required`: NOT NULL, Boolean, 기본값 True
- ✅ `resolved`: NOT NULL, Boolean, 기본값 False
- ✅ `resolved_at`: Nullable DateTime
- ✅ `created_at`: `get_kst_now()` 사용

### 3. 관계 정의 (Lines 23-24)
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
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
# from datetime import datetime  # 제거
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now
```

---

### 2. 🟢 **낮음**: 인덱스 정의 없음

**문제**: SQL 스키마에는 `idx_missing_unresolved` 인덱스가 있지만 모델에는 정의되어 있지 않습니다. `case_id`와 `resolved`는 자주 조회되는 컬럼이므로 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: `case_id`와 `resolved`에 복합 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index, CheckConstraint

__table_args__ = (
    Index('idx_missing_unresolved', 'case_id', 'resolved'),
)
```

---

### 3. 🟢 **낮음**: `resolved_at`과 `resolved`의 일관성 검증 없음

**문제**: `resolved=True`일 때 `resolved_at`이 NULL이면 안 되고, `resolved=False`일 때 `resolved_at`이 NULL이어야 합니다. 하지만 현재는 제약조건이 없어서 일관성이 깨질 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `CheckConstraint` 추가 (선택적)

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("(resolved = 1 AND resolved_at IS NOT NULL) OR (resolved = 0 AND resolved_at IS NULL)", name="check_resolved_consistency"),
    Index('idx_missing_unresolved', 'case_id', 'resolved'),
)
```

**참고**: MySQL에서는 Boolean이 TINYINT(1)로 저장되므로 `resolved = 1` 또는 `resolved = 0`으로 비교해야 합니다.

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 3개 (사용되지 않는 import, 인덱스 없음, resolved/resolved_at 일관성 검증 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `resolved`와 `resolved_at` 일관성 검증 추가 (선택적)

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 인덱스 추가

```python
"""
CaseMissingField 모델
"""
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseMissingField(BaseModel):
    """누락 정보 관리 테이블"""
    __tablename__ = "case_missing_field"
    __table_args__ = (
        CheckConstraint("(resolved = 1 AND resolved_at IS NOT NULL) OR (resolved = 0 AND resolved_at IS NULL)", name="check_resolved_consistency"),
        Index('idx_missing_unresolved', 'case_id', 'resolved'),
    )
```

---

## ✅ 결론

`CaseMissingField` 모델은 전반적으로 잘 구현되어 있습니다. **인덱스 추가**와 **사용되지 않는 import 제거**를 권장합니다. 또한 `resolved`와 `resolved_at`의 일관성 검증을 추가하는 것도 고려할 수 있습니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `resolved`와 `resolved_at` 일관성 검증 추가 (선택적)

