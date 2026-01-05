# Service Prompt Builder 검토 보고서

## 검토 대상
- 파일: `src/services/prompt_builder.py`
- 검토 일자: 2024년
- 검토 범위: 프롬프트 조합, 변수 치환

---

## ✅ 정상 동작 부분

### 1. 클래스 구조 (Lines 11-12)
- ✅ `PromptBuilder` 클래스 구조 명확
- ✅ 초기화 시 템플릿 디렉토리 경로 설정

### 2. 템플릿 디렉토리 초기화 (Lines 14-26)
- ✅ `__init__()`: 템플릿 디렉토리 경로 설정 로직 적절
- ✅ 기본 경로 자동 탐지 (`Path(__file__).parent.parent / "prompts"`)
- ✅ 초기화 시 템플릿 자동 로드

### 3. 템플릿 로드 (Lines 28-40, 42-52)
- ✅ `_load_templates()`: 템플릿 파일 로드 로직 적절
- ✅ UTF-8 인코딩 사용
- ✅ 에러 처리 및 로깅 구현됨
- ✅ `load_template()`: 템플릿 조회 로직 간단하고 명확

### 4. 프롬프트 빌드 (Lines 54-86)
- ✅ `build_prompt()`: 프롬프트 빌드 로직 적절
- ✅ 폴백 템플릿 지원
- ✅ 변수 치환 (`template.format(**variables)`)
- ✅ 에러 처리 구현됨

### 5. RAG 컨텍스트 주입 (Lines 88-128)
- ✅ `inject_rag_context()`: RAG 컨텍스트 주입 로직 적절
- ✅ 최대 컨텍스트 길이 제한
- ✅ 빈 결과 처리

### 6. 프롬프트 결합 (Lines 130-141)
- ✅ `combine_prompts()`: 프롬프트 결합 로직 간단하고 명확
- ✅ 빈 프롬프트 필터링

---

## ⚠️ 발견된 문제점

### 1. 🟡 **중요한 문제**: `_load_templates`에서 하위 디렉토리 미지원 (Line 34)

**문제**: `self.templates_dir.glob("*.txt")`는 루트 디렉토리의 `.txt` 파일만 로드합니다. `prompt_loader.py`와 달리 하위 디렉토리(`summary/`, `entity_extraction/` 등)의 템플릿을 로드하지 않습니다.

```python
for template_file in self.templates_dir.glob("*.txt"):  # ❌ 하위 디렉토리 미지원
    ...
```

**영향도**: 중간  
**수정 필요**: 하위 디렉토리도 포함하여 템플릿 로드

**수정 예시**:
```python
def _load_templates(self):
    """템플릿 파일 로드"""
    if not self.templates_dir.exists():
        logger.warning(f"템플릿 디렉토리를 찾을 수 없습니다: {self.templates_dir}")
        return
    
    # 하위 디렉토리 포함하여 모든 .txt 파일 로드
    for template_file in self.templates_dir.rglob("*.txt"):
        try:
            # 하위 디렉토리 경로를 키로 사용 (예: "summary/family_divorce")
            relative_path = template_file.relative_to(self.templates_dir)
            template_key = str(relative_path.with_suffix('')).replace('\\', '/')
            
            with open(template_file, 'r', encoding='utf-8') as f:
                self.templates[template_key] = f.read()
            logger.debug(f"템플릿 로드 완료: {template_key}")
        except Exception as e:
            logger.error(f"템플릿 로드 실패: {template_file} - {str(e)}")
```

---

### 2. 🟡 **중요한 문제**: `build_prompt`에서 변수 누락 시 원본 템플릿 반환 (Line 86)

**문제**: `KeyError`가 발생하면 원본 템플릿을 반환합니다. 이는 변수가 누락된 경우에도 빈 문자열이 아닌 템플릿을 반환하므로, 사용자가 변수 누락을 인지하지 못할 수 있습니다.

```python
except KeyError as e:
    logger.error(f"템플릿 변수 누락: {template_name} - {str(e)}")
    return template  # ❌ 변수 누락된 템플릿 반환
```

**영향도**: 중간  
**수정 권장**: 변수 누락 시 빈 문자열 반환 또는 명시적 오류 처리

**수정 예시**:
```python
except KeyError as e:
    logger.error(f"템플릿 변수 누락: {template_name} - {str(e)}")
    # 변수 누락 시 빈 문자열 반환 또는 예외 발생
    return ""  # 또는 raise ValueError(f"템플릿 변수 누락: {e}")
```

---

### 3. 🟢 **낮음**: `inject_rag_context`에서 길이 계산 부정확 (Lines 118-122)

**문제**: `current_length`는 `context_line`의 길이만 더하지만, 실제로는 `"\n\n참고 문서:\n"`와 `"\n".join()`으로 인한 개행 문자도 포함됩니다. 또한 마지막에 추가되는 구분자도 고려하지 않습니다.

```python
if current_length + len(context_line) > max_context_length:
    break

context_parts.append(context_line)
current_length += len(context_line)  # ❌ 개행 문자 미고려
```

**영향도**: 낮음  
**수정 권장**: 실제 최종 문자열 길이를 정확히 계산

**수정 예시**:
```python
# RAG 컨텍스트 구성
context_parts = []
header = "\n\n참고 문서:\n"
separator = "\n"
current_length = len(header)  # 헤더 길이 포함

for result in rag_results:
    content = result.get("content", "")
    metadata = result.get("metadata", {})
    
    context_line = f"[{metadata.get('doc_id', '')}] {content}"
    
    # 실제 추가될 길이 계산 (구분자 포함)
    line_with_separator = context_line + separator
    if current_length + len(line_with_separator) > max_context_length:
        break
    
    context_parts.append(context_line)
    current_length += len(line_with_separator)
```

---

### 4. 🟢 **낮음**: `_load_templates`에서 중복 템플릿 이름 처리 없음 (Line 37)

**문제**: 같은 이름의 템플릿 파일이 여러 디렉토리에 있으면 나중에 로드된 것이 이전 것을 덮어씁니다. 경고나 에러 로그가 없습니다.

**영향도**: 낮음  
**수정 권장**: 중복 템플릿 이름 감지 및 경고

**수정 예시**:
```python
def _load_templates(self):
    """템플릿 파일 로드"""
    if not self.templates_dir.exists():
        logger.warning(f"템플릿 디렉토리를 찾을 수 없습니다: {self.templates_dir}")
        return
    
    for template_file in self.templates_dir.rglob("*.txt"):
        try:
            template_key = template_file.stem  # 또는 하위 디렉토리 경로 포함
            
            if template_key in self.templates:
                logger.warning(f"중복 템플릿 이름 감지: {template_key} (기존: {self.templates[template_key][:50]}..., 새: {template_file})")
            
            with open(template_file, 'r', encoding='utf-8') as f:
                self.templates[template_key] = f.read()
            logger.debug(f"템플릿 로드 완료: {template_key}")
        except Exception as e:
            logger.error(f"템플릿 로드 실패: {template_file} - {str(e)}")
```

---

### 5. 🟢 **낮음**: `build_prompt`에서 `template.format()` 예외 처리 부족

**문제**: `KeyError` 외에도 `ValueError`, `IndexError` 등이 발생할 수 있지만 `KeyError`만 처리합니다.

**영향도**: 낮음  
**수정 권장**: 더 포괄적인 예외 처리

**수정 예시**:
```python
# 변수 치환
try:
    prompt = template.format(**variables)
    return prompt
except (KeyError, ValueError, IndexError) as e:
    logger.error(f"템플릿 변수 치환 실패: {template_name} - {str(e)}")
    return ""  # 또는 예외 발생
except Exception as e:
    logger.error(f"템플릿 처리 중 예상치 못한 오류: {template_name} - {str(e)}")
    return ""
```

---

### 6. 🟢 **낮음**: `combine_prompts`에서 공백만 있는 프롬프트 필터링 없음 (Line 141)

**문제**: `if p` 조건은 빈 문자열만 필터링하지만, 공백만 있는 프롬프트는 필터링하지 않습니다.

**영향도**: 낮음  
**수정 권장**: 공백만 있는 프롬프트도 필터링

**수정 예시**:
```python
def combine_prompts(self, prompts: List[str], separator: str = "\n\n") -> str:
    """
    여러 프롬프트 결합
    
    Args:
        prompts: 프롬프트 리스트
        separator: 구분자
    
    Returns:
        결합된 프롬프트
    """
    return separator.join([p for p in prompts if p and p.strip()])
```

---

### 7. 🟢 **낮음**: 전역 인스턴스 사용 (Line 145)

**문제**: 전역 인스턴스 `prompt_builder`를 사용하면 테스트나 다중 인스턴스 사용이 어려울 수 있습니다.

**영향도**: 낮음  
**수정 권장**: 싱글톤 패턴 또는 팩토리 함수 사용 (선택적)

---

### 8. 🟢 **낮음**: 실제 사용 여부 불명확

**문제**: 코드베이스에서 `prompt_builder`를 실제로 사용하는 곳이 거의 없습니다. `prompt_loader`는 사용되지만 `prompt_builder`는 사용되지 않는 것 같습니다.

**영향도**: 낮음  
**수정 권장**: 사용되지 않는다면 제거하거나, 사용하도록 통합

---

## 📊 검토 요약

### 발견된 문제
- 🟡 **중요한 문제**: 2개 (하위 디렉토리 미지원, 변수 누락 시 원본 템플릿 반환)
- 🟢 **낮음**: 6개 (길이 계산, 중복 처리, 예외 처리, 공백 필터링, 전역 인스턴스, 사용 여부)

### 우선순위별 수정 권장
1. 🟡 **중요**: `_load_templates`에서 하위 디렉토리 지원 추가
2. 🟡 **중요**: `build_prompt`에서 변수 누락 시 처리 개선
3. 🟢 **낮음**: `inject_rag_context`에서 길이 계산 정확도 개선, 중복 템플릿 감지, 예외 처리 개선

---

## 🔧 수정 제안

### 수정 1: 하위 디렉토리 지원 추가

```python
def _load_templates(self):
    """템플릿 파일 로드"""
    if not self.templates_dir.exists():
        logger.warning(f"템플릿 디렉토리를 찾을 수 없습니다: {self.templates_dir}")
        return
    
    # 하위 디렉토리 포함하여 모든 .txt 파일 로드
    for template_file in self.templates_dir.rglob("*.txt"):
        try:
            # 하위 디렉토리 경로를 키로 사용 (예: "summary/family_divorce")
            relative_path = template_file.relative_to(self.templates_dir)
            template_key = str(relative_path.with_suffix('')).replace('\\', '/')
            
            if template_key in self.templates:
                logger.warning(f"중복 템플릿 이름 감지: {template_key}")
            
            with open(template_file, 'r', encoding='utf-8') as f:
                self.templates[template_key] = f.read()
            logger.debug(f"템플릿 로드 완료: {template_key}")
        except Exception as e:
            logger.error(f"템플릿 로드 실패: {template_file} - {str(e)}")
```

### 수정 2: 변수 누락 시 처리 개선

```python
# 변수 치환
try:
    prompt = template.format(**variables)
    return prompt
except KeyError as e:
    logger.error(f"템플릿 변수 누락: {template_name} - {str(e)}")
    return ""  # 빈 문자열 반환
except (ValueError, IndexError) as e:
    logger.error(f"템플릿 변수 치환 실패: {template_name} - {str(e)}")
    return ""
```

### 수정 3: 길이 계산 정확도 개선

```python
def inject_rag_context(
    self,
    prompt: str,
    rag_results: List[Dict[str, Any]],
    max_context_length: int = 2000
) -> str:
    if not rag_results:
        return prompt
    
    # RAG 컨텍스트 구성
    context_parts = []
    header = "\n\n참고 문서:\n"
    separator = "\n"
    current_length = len(header)
    
    for result in rag_results:
        content = result.get("content", "")
        metadata = result.get("metadata", {})
        
        context_line = f"[{metadata.get('doc_id', '')}] {content}"
        
        # 실제 추가될 길이 계산 (구분자 포함)
        line_with_separator = context_line + separator
        if current_length + len(line_with_separator) > max_context_length:
            break
        
        context_parts.append(context_line)
        current_length += len(line_with_separator)
    
    if context_parts:
        rag_context = header + separator.join(context_parts)
        return prompt + rag_context
    
    return prompt
```

### 수정 4: 공백 필터링 개선

```python
def combine_prompts(self, prompts: List[str], separator: str = "\n\n") -> str:
    """
    여러 프롬프트 결합
    
    Args:
        prompts: 프롬프트 리스트
        separator: 구분자
    
    Returns:
        결합된 프롬프트
    """
    return separator.join([p for p in prompts if p and p.strip()])
```

---

## ✅ 결론

`PromptBuilder` 클래스는 전반적으로 잘 구현되어 있으나, **하위 디렉토리 미지원**과 **변수 누락 시 원본 템플릿 반환** 문제가 있습니다. 또한 실제로 코드베이스에서 사용되지 않는 것 같으므로, 사용 여부를 확인하고 필요시 통합하거나 제거하는 것을 권장합니다.

**우선순위**:
1. 🟡 **중요**: `_load_templates`에서 하위 디렉토리 지원 추가
2. 🟡 **중요**: `build_prompt`에서 변수 누락 시 처리 개선
3. 🟢 **낮음**: 길이 계산 정확도 개선, 중복 템플릿 감지, 예외 처리 개선, 공백 필터링 개선

