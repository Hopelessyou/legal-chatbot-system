"""
데이터베이스 Base 클래스
"""
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    """SQLAlchemy 2.x 스타일 Base 클래스"""
    pass


class BaseModel(Base):
    """기본 모델 클래스"""
    __abstract__ = True
    
    def to_dict(self):
        """모델을 딕셔너리로 변환"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
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

