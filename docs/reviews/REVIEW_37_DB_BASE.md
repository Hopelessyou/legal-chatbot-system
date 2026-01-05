# DB Base 검토 보고서

## 검토 대상
- 파일: `src/db/base.py`
- 검토 일자: 2024년
- 검토 범위: SQLAlchemy Base, BaseModel, 공통 메서드

---

## ✅ 정상 동작 부분

### 1. Base 클래스 (Lines 9-11)
- ✅ `DeclarativeBase` 사용: SQLAlchemy 2.x 스타일 적절
- ✅ 클래스 구조 명확

### 2. BaseModel 클래스 (Lines 14-16)
- ✅ `__abstract__ = True`: 추상 클래스로 올바르게 설정
- ✅ `Base` 상속: 올바른 상속 구조

### 3. to_dict 메서드 (Lines 18-23)
- ✅ 모델을 딕셔너리로 변환하는 기본 로직 구현
- ✅ 모든 컬럼을 포함하는 로직 적절

### 4. to_json 메서드 (Lines 25-34)
- ✅ JSON 직렬화 가능한 딕셔너리로 변환
- ✅ `datetime` 타입을 `isoformat()`으로 변환하는 로직 적절

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중요한 문제**: `to_dict`와 `to_json`에서 관계(relationship) 필드 미처리

**문제**: `to_dict()`와 `to_json()` 메서드는 테이블 컬럼만 처리하고 관계(relationship) 필드는 처리하지 않습니다. 관계 데이터가 필요한 경우 이를 포함할 수 없습니다.

```python
def to_dict(self):
    """모델을 딕셔너리로 변환"""
    return {
        column.name: getattr(self, column.name)
        for column in self.__table__.columns  # ❌ 관계 필드 미포함
    }
```

**영향도**: 중간  
**수정 권장**: 관계 필드 포함 옵션 추가 또는 별도 메서드 제공

**수정 예시**:
```python
def to_dict(self, include_relationships: bool = False):
    """모델을 딕셔너리로 변환"""
    result = {
        column.name: getattr(self, column.name)
        for column in self.__table__.columns
    }
    
    if include_relationships:
        for key, relationship in self.__mapper__.relationships.items():
            rel_value = getattr(self, key)
            if rel_value is None:
                result[key] = None
            elif isinstance(rel_value, list):
                result[key] = [item.to_dict() if hasattr(item, 'to_dict') else str(item) for item in rel_value]
            else:
                result[key] = rel_value.to_dict() if hasattr(rel_value, 'to_dict') else str(rel_value)
    
    return result
```

---

### 2. 🟡 **중요한 문제**: `to_json`에서 다른 타입 처리 부족

**문제**: `to_json()` 메서드는 `datetime`만 처리하고, `UUID`, `Decimal`, `date`, `time` 등 다른 타입은 처리하지 않습니다.

```python
if isinstance(value, datetime):
    result[column.name] = value.isoformat()
else:
    result[column.name] = value  # ❌ UUID, Decimal 등 미처리
```

**영향도**: 중간  
**수정 권장**: 더 많은 타입 처리 추가

**수정 예시**:
```python
def to_json(self):
    """모델을 JSON 직렬화 가능한 딕셔너리로 변환"""
    import json
    from decimal import Decimal
    from uuid import UUID
    from datetime import date, time
    
    result = {}
    for column in self.__table__.columns:
        value = getattr(self, column.name)
        if value is None:
            result[column.name] = None
        elif isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, date):
            result[column.name] = value.isoformat()
        elif isinstance(value, time):
            result[column.name] = value.isoformat()
        elif isinstance(value, UUID):
            result[column.name] = str(value)
        elif isinstance(value, Decimal):
            result[column.name] = float(value)
        else:
            result[column.name] = value
    return result
```

---

### 3. 🟢 **낮음**: `to_dict`와 `to_json`에서 `None` 값 처리 명시적이지 않음

**문제**: `getattr(self, column.name)`이 `None`을 반환할 수 있지만, 명시적으로 처리하지 않습니다. 일반적으로는 문제없지만, 일부 경우에 예상치 못한 동작을 할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: `None` 값 명시적 처리 (선택적)

---

### 4. 🟢 **낮음**: 사용되지 않는 import (Line 5)

**문제**: `Column, Integer, DateTime`을 import했지만 사용하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 사용하지 않는 import 제거

**수정 예시**:
```python
from sqlalchemy.orm import DeclarativeBase
# Column, Integer, DateTime 제거
from datetime import datetime
```

---

### 5. 🟢 **낮음**: `to_dict`와 `to_json`에서 순환 참조 처리 없음

**문제**: 관계 필드를 포함할 때 순환 참조가 발생할 수 있습니다. 예를 들어, `CaseMaster`가 `CaseParty`를 포함하고, `CaseParty`가 다시 `CaseMaster`를 참조하는 경우입니다.

**영향도**: 낮음  
**수정 권장**: 순환 참조 방지 로직 추가 (관계 필드 포함 시)

---

### 6. 🟢 **낮음**: `to_dict`와 `to_json`에서 lazy loading 문제 가능

**문제**: 관계 필드에 접근할 때 lazy loading이 발생할 수 있으며, 세션이 이미 닫힌 경우 `DetachedInstanceError`가 발생할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 세션 상태 확인 또는 eager loading 사용 권장 (문서화)

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중요한 문제**: 2개 (관계 필드 미처리, 타입 처리 부족)
- 🟢 **낮음**: 4개 (None 처리, 사용되지 않는 import, 순환 참조, lazy loading)

### 우선순위별 수정 권장
1. 🟡 **중요**: `to_json`에서 더 많은 타입 처리 추가
2. 🟡 **중요**: 관계 필드 포함 옵션 추가 (선택적)
3. 🟢 **낮음**: 사용되지 않는 import 제거

---

## 🔧 수정 제안

### 수정 1: 사용되지 않는 import 제거

```python
"""
데이터베이스 Base 클래스
"""
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    """SQLAlchemy 2.x 스타일 Base 클래스"""
    pass
```

### 수정 2: to_json에서 더 많은 타입 처리 추가

```python
def to_json(self):
    """모델을 JSON 직렬화 가능한 딕셔너리로 변환"""
    from decimal import Decimal
    from uuid import UUID
    from datetime import date, time
    
    result = {}
    for column in self.__table__.columns:
        value = getattr(self, column.name)
        if value is None:
            result[column.name] = None
        elif isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, date):
            result[column.name] = value.isoformat()
        elif isinstance(value, time):
            result[column.name] = value.isoformat()
        elif isinstance(value, UUID):
            result[column.name] = str(value)
        elif isinstance(value, Decimal):
            result[column.name] = float(value)
        else:
            result[column.name] = value
    return result
```

### 수정 3: to_dict에 관계 필드 포함 옵션 추가 (선택적)

```python
def to_dict(self, include_relationships: bool = False):
    """모델을 딕셔너리로 변환"""
    result = {
        column.name: getattr(self, column.name)
        for column in self.__table__.columns
    }
    
    if include_relationships:
        for key, relationship in self.__mapper__.relationships.items():
            try:
                rel_value = getattr(self, key)
                if rel_value is None:
                    result[key] = None
                elif isinstance(rel_value, list):
                    result[key] = [
                        item.to_dict(include_relationships=False) 
                        if hasattr(item, 'to_dict') 
                        else str(item) 
                        for item in rel_value
                    ]
                else:
                    result[key] = (
                        rel_value.to_dict(include_relationships=False) 
                        if hasattr(rel_value, 'to_dict') 
                        else str(rel_value)
                    )
            except Exception as e:
                # Lazy loading 실패 시 스킵
                result[key] = None
    
    return result
```

---

## ✅ 결론

`BaseModel` 클래스는 전반적으로 잘 구현되어 있으나, **타입 처리 개선**과 **관계 필드 포함 옵션** 추가를 권장합니다. 또한 사용되지 않는 import를 제거하는 것이 좋습니다.

**우선순위**:
1. 🟡 **중요**: `to_json`에서 더 많은 타입 처리 추가 (`UUID`, `Decimal`, `date`, `time`)
2. 🟡 **중요**: 관계 필드 포함 옵션 추가 (선택적)
3. 🟢 **낮음**: 사용되지 않는 import 제거

