# DB Model CaseMaster 검토 보고서

## 검토 대상
- 파일: `src/db/models/case_master.py`
- 검토 일자: 2024년
- 검토 범위: 모델 정의, 관계, 제약조건

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-13)
- ✅ `BaseModel` 상속: 올바른 상속 구조
- ✅ `__tablename__` 정의: 명확한 테이블 이름
- ✅ `__table_args__`: 제약조건 정의 적절

### 2. 제약조건 (Lines 14-16)
- ✅ `CheckConstraint`로 `urgency_level` 값 검증: `LOW`, `MID`, `HIGH`

### 3. 컬럼 정의 (Lines 18-26)
- ✅ `case_id`: Primary Key, BigInteger, autoincrement
- ✅ `session_id`: Foreign Key, NOT NULL, UNIQUE (1:1 관계)
- ✅ `main_case_type`, `sub_case_type`: Nullable String
- ✅ `case_stage`: 기본값 "상담전"
- ✅ `urgency_level`: Nullable String
- ✅ `estimated_value`: Nullable BigInteger
- ✅ `created_at`, `updated_at`: `get_kst_now()` 사용

### 4. 관계 정의 (Lines 28-35)
- ✅ `session`: `ChatSession`와 1:1 관계
- ✅ `parties`, `facts`, `evidences`, `emotions`, `missing_fields`: 1:N 관계, cascade 설정 적절
- ✅ `summary`: 1:1 관계, cascade 설정 적절
- ✅ `cascade="all, delete-orphan"`: 부모 삭제 시 자식도 삭제

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: 사용되지 않는 import (Lines 4, 6)

**문제**: 
- `Integer`를 import했지만 사용하지 않습니다.
- `UniqueConstraint`를 import했지만 사용하지 않습니다 (UNIQUE는 Column 정의에서 처리).
- `datetime`을 import했지만 사용하지 않습니다 (`get_kst_now()` 사용).

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

**문제**: SQL 스키마에는 인덱스가 있지만 모델에는 정의되어 있지 않습니다. 자주 조회되는 컬럼(`main_case_type`, `sub_case_type`, `estimated_value`, `session_id`)에 인덱스가 필요합니다.

**영향도**: 낮음 (현재는 데이터가 적을 수 있지만, 향후 성능 이슈 가능)  
**수정 권장**: 자주 조회되는 컬럼에 인덱스 추가

**수정 예시**:
```python
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index

__table_args__ = (
    CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
    Index('idx_case_type', 'main_case_type', 'sub_case_type'),
    Index('idx_case_value', 'estimated_value'),
    Index('idx_case_session', 'session_id'),
)
```

---

### 3. 🟢 **낮음**: `case_stage` 값 검증 없음

**문제**: `case_stage` 컬럼에 제약조건이 없어서 임의의 값이 들어갈 수 있습니다. 문서에 따르면 "상담전", "상담중" 등 특정 값만 허용해야 합니다.

**영향도**: 낮음  
**수정 권장**: `CheckConstraint` 추가

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
    CheckConstraint("case_stage IN ('상담전', '상담중', '상담완료', '수임', '거절')", name="check_case_stage"),
)
```

---

### 4. 🟢 **낮음**: `estimated_value` 음수 검증 없음

**문제**: `estimated_value`가 음수일 수 있습니다. 금액이므로 0 이상이어야 합니다.

**영향도**: 낮음  
**수정 권장**: `CheckConstraint` 추가

**수정 예시**:
```python
__table_args__ = (
    CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
    CheckConstraint("estimated_value IS NULL OR estimated_value >= 0", name="check_estimated_value"),
)
```

---

### 5. 🟢 **낮음**: `main_case_type`, `sub_case_type` 값 검증 없음

**문제**: `main_case_type`과 `sub_case_type`에 제약조건이 없어서 임의의 값이 들어갈 수 있습니다. 하지만 이는 동적으로 변할 수 있는 값이므로 제약조건 추가는 선택적입니다.

**영향도**: 낮음  
**수정 권장**: 필요시 ENUM 타입 사용 또는 CheckConstraint 추가 (선택적)

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 5개 (사용되지 않는 import, 인덱스 없음, case_stage/estimated_value 검증 없음, main_case_type/sub_case_type 검증 없음)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `case_stage` 및 `estimated_value` 값 검증 추가

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거 및 인덱스 추가

```python
"""
CaseMaster 모델
"""
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from src.db.base import BaseModel
from src.utils.helpers import get_kst_now


class CaseMaster(BaseModel):
    """법률 사건 마스터 테이블"""
    __tablename__ = "case_master"
    __table_args__ = (
        CheckConstraint("urgency_level IN ('LOW', 'MID', 'HIGH')", name="check_urgency_level"),
        CheckConstraint("case_stage IN ('상담전', '상담중', '상담완료', '수임', '거절')", name="check_case_stage"),
        CheckConstraint("estimated_value IS NULL OR estimated_value >= 0", name="check_estimated_value"),
        Index('idx_case_type', 'main_case_type', 'sub_case_type'),
        Index('idx_case_value', 'estimated_value'),
        Index('idx_case_session', 'session_id'),
    )
```

---

## ✅ 결론

`CaseMaster` 모델은 전반적으로 잘 구현되어 있으나, **인덱스 추가**와 **값 검증 강화**를 권장합니다. 또한 사용되지 않는 import를 제거하는 것이 좋습니다.

**우선순위**:
1. 🟢 **낮음**: 사용되지 않는 import 제거
2. 🟢 **낮음**: 인덱스 추가 (성능 최적화)
3. 🟢 **낮음**: `case_stage` 및 `estimated_value` 값 검증 추가

