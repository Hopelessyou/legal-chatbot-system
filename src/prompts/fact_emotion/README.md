# 사실/감정 분리 프롬프트

이 디렉토리에는 사용자 입력에서 사실과 감정을 분리하기 위한 프롬프트 템플릿이 저장됩니다.

## 파일
- `split.txt`: 사실/감정 분리 프롬프트

## 변수
- `{user_input}`: 사용자 입력 텍스트

## 출력 형식
JSON 형식:
```json
{
    "facts": "객관적 사실",
    "emotions": ["감정1", "감정2"]
}
```

## 사용 위치
- `src/services/fact_emotion_splitter.py`

