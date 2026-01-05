# RAG Parser 검토 보고서

## 검토 대상
- 파일: `src/rag/parser.py`
- 검토 일자: 2024년
- 검토 범위: YAML/JSON 파싱, 문서 타입별 파싱 로직, 메타데이터 추출

---

## ✅ 정상 동작 부분

### 1. 파일 로드 메서드 (Lines 25-58)
```python
@staticmethod
def load_yaml(file_path: Path) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"YAML 파일 로드 실패: {file_path} - {str(e)}")
        raise
```
- ✅ `yaml.safe_load` 사용으로 보안 강화
- ✅ UTF-8 인코딩 명시
- ✅ 예외 로깅 및 재발생

### 2. 문서 타입별 파싱 메서드
- ✅ K1, K2, K3, K4, FACT 문서별 전용 파싱 메서드
- ✅ 메타데이터 추출 로직 공통화
- ✅ 기본값 처리 (`data.get(..., [])`)

### 3. 자동 파싱 메서드 (Lines 205-238)
```python
@staticmethod
def parse_document(file_path: Path) -> Any:
    if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
        data = RAGDocumentParser.load_yaml(file_path)
    elif file_path.suffix == '.json':
        data = RAGDocumentParser.load_json(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {file_path.suffix}")
```
- ✅ 파일 확장자에 따른 자동 분기
- ✅ knowledge_type에 따른 자동 파싱

### 4. required_fields 변환 로직 (Lines 128-132)
```python
required_fields = data.get("required_fields", [])
if required_fields and isinstance(required_fields[0], dict):
    required_fields = [field.get("field", field) if isinstance(field, dict) else field for field in required_fields]
```
- ✅ 딕셔너리 리스트와 문자열 리스트 모두 처리

---

## ⚠️ 발견된 문제점

### 1. Pydantic ValidationError 처리 없음 (Line 90)
**영향도**: 중간  
**문제**: 
- `extract_metadata`에서 `RAGDocumentMetadata(**metadata_dict)` 호출 시 Pydantic ValidationError 발생 가능
- ValidationError가 그대로 전파되어 사용자 친화적이지 않음

**현재 코드**:
```python
return RAGDocumentMetadata(**metadata_dict)
```

**권장 수정**:
```python
try:
    return RAGDocumentMetadata(**metadata_dict)
except ValidationError as e:
    logger.error(f"메타데이터 검증 실패: {metadata_dict} - {str(e)}")
    raise ValueError(f"문서 메타데이터가 유효하지 않습니다: {str(e)}") from e
```

### 2. datetime 파싱 에러 처리 부족 (Lines 81-88)
**영향도**: 중간  
**문제**: 
- `datetime.fromisoformat` 호출 시 잘못된 형식이면 ValueError 발생
- `replace('Z', '+00:00')`가 항상 안전하지 않음

**현재 코드**:
```python
if isinstance(data["last_updated"], str):
    metadata_dict["last_updated"] = datetime.fromisoformat(
        data["last_updated"].replace('Z', '+00:00')
    )
```

**권장 수정**:
```python
if isinstance(data["last_updated"], str):
    try:
        date_str = data["last_updated"]
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        metadata_dict["last_updated"] = datetime.fromisoformat(date_str)
    except (ValueError, AttributeError) as e:
        logger.warning(f"last_updated 파싱 실패: {data['last_updated']} - {str(e)}")
        # 기본값 사용 또는 None으로 설정
        metadata_dict["last_updated"] = datetime.now(timezone.utc)
```

### 3. knowledge_type None 체크 없음 (Line 222)
**영향도**: 중간  
**문제**: 
- `knowledge_type`이 None이면 모든 elif 조건이 False가 되어 `ValueError` 발생
- 에러 메시지가 명확하지 않음

**현재 코드**:
```python
knowledge_type = data.get("knowledge_type")

if knowledge_type == "K0":
    ...
elif knowledge_type == "K1":
    ...
else:
    raise ValueError(f"알 수 없는 knowledge_type: {knowledge_type}")
```

**권장 수정**:
```python
knowledge_type = data.get("knowledge_type")

if not knowledge_type:
    raise ValueError(f"knowledge_type이 없습니다: {file_path}")

if knowledge_type == "K0":
    ...
elif knowledge_type == "K1":
    ...
else:
    raise ValueError(f"알 수 없는 knowledge_type: {knowledge_type}")
```

### 4. required_fields 변환 로직 에러 처리 부족 (Lines 129-132)
**영향도**: 낮음  
**문제**: 
- `required_fields[0]` 접근 시 빈 리스트면 IndexError 발생
- `isinstance(field, dict)` 체크가 리스트 내 모든 항목에 대해 수행되지 않음

**현재 코드**:
```python
required_fields = data.get("required_fields", [])
if required_fields and isinstance(required_fields[0], dict):
    required_fields = [field.get("field", field) if isinstance(field, dict) else field for field in required_fields]
```

**권장 수정**:
```python
required_fields = data.get("required_fields", [])
if required_fields:
    # 첫 번째 항목이 딕셔너리인지 확인
    if isinstance(required_fields[0], dict):
        # 모든 항목이 딕셔너리인지 확인하고 변환
        try:
            required_fields = [
                field.get("field", field) if isinstance(field, dict) else field 
                for field in required_fields
            ]
        except (AttributeError, TypeError) as e:
            logger.warning(f"required_fields 변환 실패: {str(e)}")
            # 원본 유지 또는 빈 리스트
```

### 5. 파일 경로 검증 없음 (Line 205)
**영향도**: 낮음  
**문제**: 
- `file_path`가 존재하는지, 파일인지 확인하지 않음
- 디렉토리나 존재하지 않는 파일에 대한 에러 메시지가 명확하지 않음

**권장 수정**:
```python
@staticmethod
def parse_document(file_path: Path) -> Any:
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"파일이 아닙니다: {file_path}")
    
    if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
        data = RAGDocumentParser.load_yaml(file_path)
    ...
```

### 6. 빈 파일 처리 없음 (Lines 25-40, 43-58)
**영향도**: 낮음  
**문제**: 
- YAML/JSON 파일이 비어있으면 `yaml.safe_load`나 `json.load`가 None 반환 가능
- None에 대한 `data.get()` 호출 시 AttributeError 발생

**권장 수정**:
```python
@staticmethod
def load_yaml(file_path: Path) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None:
                logger.warning(f"YAML 파일이 비어있습니다: {file_path}")
                return {}
            if not isinstance(data, dict):
                raise ValueError(f"YAML 파일이 딕셔너리가 아닙니다: {file_path}")
            return data
    except Exception as e:
        logger.error(f"YAML 파일 로드 실패: {file_path} - {str(e)}")
        raise
```

### 7. 예외 타입이 너무 일반적 (Lines 38, 57)
**영향도**: 낮음  
**문제**: 
- `except Exception`이 너무 광범위함
- 구체적인 예외 타입으로 처리하는 것이 좋음

**권장 수정**:
```python
except (FileNotFoundError, PermissionError) as e:
    logger.error(f"파일 접근 실패: {file_path} - {str(e)}")
    raise
except (yaml.YAMLError, json.JSONDecodeError) as e:
    logger.error(f"파싱 실패: {file_path} - {str(e)}")
    raise
except Exception as e:
    logger.error(f"예상치 못한 오류: {file_path} - {str(e)}", exc_info=True)
    raise
```

### 8. K0 문서 스키마 검증 없음 (Line 226)
**영역도**: 낮음  
**문제**: 
- K0 문서가 딕셔너리 그대로 반환됨
- 스키마 검증 없이 반환

**현재 코드**:
```python
if knowledge_type == "K0":
    # K0는 간단한 구조이므로 그대로 반환
    return data
```

**권장 수정**: K0Document 스키마 추가 후 검증 (schema.py 수정 필요)

### 9. 로깅 레벨 개선 필요
**영역도**: 낮음  
**문제**: 
- 모든 에러가 `logger.error`로 로깅
- 일부는 `logger.warning`이 적절할 수 있음

---

## 🔍 추가 검토 사항

### 1. 성능 최적화
- 대용량 YAML/JSON 파일 처리 시 메모리 사용량
- 파일 캐싱 전략

### 2. 스키마 버전 호환성
- 버전별 스키마 마이그레이션 로직
- 하위 호환성 처리

### 3. 문서 검증
- 파싱 후 문서 구조 검증
- 필수 필드 존재 여부 확인

---

## 📊 종합 평가

### 강점
1. ✅ `yaml.safe_load` 사용으로 보안 강화
2. ✅ 문서 타입별 명확한 파싱 메서드
3. ✅ 메타데이터 추출 로직 공통화
4. ✅ 자동 파싱 메서드로 편의성 제공
5. ✅ UTF-8 인코딩 명시

### 개선 필요
1. 🟡 **중간**: Pydantic ValidationError 처리
2. 🟡 **중간**: datetime 파싱 에러 처리
3. 🟡 **중간**: knowledge_type None 체크
4. 🟢 **낮음**: required_fields 변환 로직 에러 처리
5. 🟢 **낮음**: 파일 경로 검증
6. 🟢 **낮음**: 빈 파일 처리
7. 🟢 **낮음**: 예외 타입 구체화
8. 🟢 **낮음**: K0 문서 스키마 검증

### 우선순위
- **중간**: Pydantic ValidationError 처리, datetime 파싱 에러 처리, knowledge_type None 체크
- **낮음**: 나머지 개선 사항

---

## 📝 권장 수정 사항

### 수정 1: Pydantic ValidationError 처리
```python
from pydantic import ValidationError

@staticmethod
def extract_metadata(data: Dict[str, Any]) -> RAGDocumentMetadata:
    ...
    try:
        return RAGDocumentMetadata(**metadata_dict)
    except ValidationError as e:
        logger.error(f"메타데이터 검증 실패: {metadata_dict} - {str(e)}")
        raise ValueError(f"문서 메타데이터가 유효하지 않습니다: {str(e)}") from e
```

### 수정 2: datetime 파싱 에러 처리
```python
from datetime import datetime, timezone

if isinstance(data["last_updated"], str):
    try:
        date_str = data["last_updated"]
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        metadata_dict["last_updated"] = datetime.fromisoformat(date_str)
    except (ValueError, AttributeError) as e:
        logger.warning(f"last_updated 파싱 실패: {data['last_updated']} - {str(e)}")
        metadata_dict["last_updated"] = datetime.now(timezone.utc)
```

### 수정 3: knowledge_type None 체크
```python
knowledge_type = data.get("knowledge_type")

if not knowledge_type:
    raise ValueError(f"knowledge_type이 없습니다: {file_path}")

if knowledge_type == "K0":
    ...
```

### 수정 4: 파일 경로 검증
```python
@staticmethod
def parse_document(file_path: Path) -> Any:
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"파일이 아닙니다: {file_path}")
    
    ...
```

### 수정 5: 빈 파일 처리
```python
@staticmethod
def load_yaml(file_path: Path) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None:
                logger.warning(f"YAML 파일이 비어있습니다: {file_path}")
                return {}
            if not isinstance(data, dict):
                raise ValueError(f"YAML 파일이 딕셔너리가 아닙니다: {file_path}")
            return data
    except Exception as e:
        logger.error(f"YAML 파일 로드 실패: {file_path} - {str(e)}")
        raise
```

---

## ✅ 검토 완료

**검토 항목**: `review_19_rag_parser`  
**상태**: 완료  
**다음 항목**: `review_20_rag_chunker`

