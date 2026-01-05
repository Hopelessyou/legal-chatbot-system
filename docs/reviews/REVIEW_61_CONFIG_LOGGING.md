# Config Logging 검토 보고서

## 검토 대상
- 파일: `config/logging.yaml`
- 검토 일자: 2024년
- 검토 범위: 로깅 설정, 핸들러, 포맷터

---

## ✅ 정상 동작 부분

### 1. 파일 구조 (Lines 1-2)
- ✅ `version: 1` 명시 (Python logging 설정 버전)
- ✅ `disable_existing_loggers: false` 설정

### 2. Formatters (Lines 4-11)
- ✅ `standard` 포맷터: 표준 텍스트 포맷
- ✅ `json` 포맷터: JSON 포맷 (구조화 로깅)
- ✅ 적절한 날짜 포맷 설정

### 3. Handlers (Lines 13-36)
- ✅ `console`: 콘솔 출력 핸들러
- ✅ `file`: 파일 로테이션 핸들러 (10MB, 5개 백업)
- ✅ `error_file`: 에러 전용 파일 핸들러
- ✅ 적절한 로그 레벨 설정
- ✅ UTF-8 인코딩 명시

### 4. Loggers (Lines 38-62)
- ✅ 모듈별 로거 정의: `api`, `langgraph`, `rag`, `gpt`, `db`
- ✅ 적절한 로그 레벨 설정
- ✅ `propagate: false` 설정으로 중복 로깅 방지

### 5. Root Logger (Lines 64-66)
- ✅ 루트 로거 설정

---

## ⚠️ 발견된 문제점

### 1. 🟢 **낮음**: JSON 포맷터 의존성 확인 필요

**문제**: `json` 포맷터에서 `pythonjsonlogger.jsonlogger.JsonFormatter`를 사용하는데, 이 패키지가 `requirements.txt`에 포함되어 있는지 확인이 필요합니다.

**영향도**: 낮음  
**수정 권장**: `requirements.txt`에 `python-json-logger` 패키지 포함 확인 (선택적)

---

### 2. 🟢 **낮음**: 로그 파일 경로 상대 경로

**문제**: `filename: logs/app.log`와 `filename: logs/error.log`가 상대 경로로 설정되어 있습니다. 실행 위치에 따라 로그 파일이 다른 위치에 생성될 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 절대 경로 사용 또는 프로젝트 루트 기준 경로 명확화 (선택적)

**수정 예시**:
```yaml
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: standard
    filename: ./logs/app.log  # 명시적으로 상대 경로 표시
    maxBytes: 10485760
    backupCount: 5
    encoding: utf8
```

---

### 3. 🟢 **낮음**: 로그 레벨 일관성

**문제**: 
- `console` 핸들러는 `DEBUG` 레벨
- `file` 핸들러는 `INFO` 레벨
- `error_file` 핸들러는 `ERROR` 레벨

이는 의도된 설정일 수 있지만, 일관성을 위해 확인이 필요합니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재 설정도 합리적)

---

### 4. 🟢 **낮음**: 로거별 세부 설정 부족

**문제**: 각 로거(`api`, `langgraph`, `rag`, `gpt`, `db`)가 모두 동일한 설정을 사용합니다. 모듈별로 다른 로그 레벨이나 핸들러를 사용할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재 설정도 충분히 합리적)

**수정 예시 (선택적)**:
```yaml
loggers:
  api:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  langgraph:
    level: DEBUG  # 개발 시 더 상세한 로깅
    handlers: [console, file, error_file]
    propagate: false
  
  gpt:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
    # GPT API 호출은 민감한 정보가 포함될 수 있으므로 별도 처리 가능
```

---

### 5. 🟢 **낮음**: 로그 파일 크기 및 백업 설정

**문제**: `maxBytes: 10485760` (10MB)와 `backupCount: 5`는 합리적이지만, 프로덕션 환경에서는 더 큰 값이 필요할 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 선택적 (현재 설정도 충분히 합리적)

---

### 6. 🟢 **낮음**: 주석 부족

**문제**: YAML 파일에 각 섹션에 대한 설명 주석이 부족합니다.

**영향도**: 낮음  
**수정 권장**: 주석 추가 (선택적)

**수정 예시**:
```yaml
version: 1
disable_existing_loggers: false

# 로그 포맷터 정의
formatters:
  # 표준 텍스트 포맷
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: "%Y-%m-%d %H:%M:%S"
  
  # JSON 포맷 (구조화 로깅)
  json:
    format: "%(asctime)s %(levelname)s %(name)s %(message)s"
    class: pythonjsonlogger.jsonlogger.JsonFormatter

# 로그 핸들러 정의
handlers:
  # 콘솔 출력 (개발 환경용)
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: standard
    stream: ext://sys.stdout
  
  # 일반 로그 파일 (로테이션)
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: standard
    filename: logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf8
  
  # 에러 전용 로그 파일
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: standard
    filename: logs/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf8

# 모듈별 로거 설정
loggers:
  api:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  langgraph:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  rag:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  gpt:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  db:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false

# 루트 로거 설정
root:
  level: INFO
  handlers: [console, file, error_file]
```

---

## 📊 검토 요약

### 발견된 문제
- 🟢 **낮음**: 6개 (JSON 포맷터 의존성, 로그 파일 경로, 로그 레벨 일관성, 로거별 세부 설정, 로그 파일 크기, 주석 부족)

### 우선순위별 수정 권장
1. 🟢 **낮음**: 주석 추가 (선택적)
2. 🟢 **낮음**: JSON 포맷터 의존성 확인 (선택적)
3. 🟢 **낮음**: 로그 파일 경로 명확화 (선택적)
4. 🟢 **낮음**: 로거별 세부 설정 (선택적)
5. 🟢 **낮음**: 로그 레벨 일관성 검토 (선택적)
6. 🟢 **낮음**: 로그 파일 크기 조정 (선택적)

---

## 🔧 수정 제안

### 수정 1: 주석 추가 및 경로 명확화

```yaml
version: 1
disable_existing_loggers: false

# 로그 포맷터 정의
formatters:
  # 표준 텍스트 포맷
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: "%Y-%m-%d %H:%M:%S"
  
  # JSON 포맷 (구조화 로깅, python-json-logger 패키지 필요)
  json:
    format: "%(asctime)s %(levelname)s %(name)s %(message)s"
    class: pythonjsonlogger.jsonlogger.JsonFormatter

# 로그 핸들러 정의
handlers:
  # 콘솔 출력 (개발 환경용)
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: standard
    stream: ext://sys.stdout
  
  # 일반 로그 파일 (로테이션)
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: standard
    filename: ./logs/app.log  # 프로젝트 루트 기준 상대 경로
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf8
  
  # 에러 전용 로그 파일
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: standard
    filename: ./logs/error.log  # 프로젝트 루트 기준 상대 경로
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf8

# 모듈별 로거 설정
loggers:
  api:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  langgraph:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  rag:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  gpt:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false
  
  db:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false

# 루트 로거 설정
root:
  level: INFO
  handlers: [console, file, error_file]
```

---

## ✅ 결론

`config/logging.yaml` 파일은 전반적으로 잘 구성되어 있습니다. **주석 추가**와 **로그 파일 경로 명확화**를 권장합니다.

**우선순위**:
1. 🟢 **낮음**: 주석 추가 (선택적)
2. 🟢 **낮음**: JSON 포맷터 의존성 확인 (선택적)
3. 🟢 **낮음**: 로그 파일 경로 명확화 (선택적)
4. 🟢 **낮음**: 로거별 세부 설정 (선택적)
5. 🟢 **낮음**: 로그 레벨 일관성 검토 (선택적)
6. 🟢 **낮음**: 로그 파일 크기 조정 (선택적)

**참고**: 현재 설정은 개발 및 프로덕션 환경 모두에서 충분히 사용 가능합니다. 추가 개선은 선택 사항입니다.

