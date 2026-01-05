# 사건 분류 프롬프트

이 디렉토리에는 법률 사건 유형을 분류하기 위한 프롬프트 템플릿이 저장됩니다.

## 파일
- `case_classification.txt`: 사건 유형 분류 프롬프트

## 변수
- `{user_input}`: 사용자 입력 텍스트

## 출력 형식
JSON 형식:
```json
{
    "main_case_type": "민사/형사/가사/행정",
    "sub_case_type": "세부 유형"
}
```

## 사용 위치
- `src/langgraph/nodes/case_classification_node.py`

