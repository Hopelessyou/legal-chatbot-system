# 엔티티 추출 프롬프트

이 디렉토리에는 텍스트에서 엔티티(날짜, 금액, 당사자, 행위 등)를 추출하기 위한 프롬프트 템플릿이 저장됩니다.

## 파일
- `date.txt`: 날짜 추출 프롬프트
- `amount.txt`: 금액 추출 프롬프트
- `party.txt`: 당사자 추출 프롬프트
- `action.txt`: 행위 추출 프롬프트
- `all_entities.txt`: 모든 엔티티를 한 번에 추출하는 프롬프트

## 변수
- `{text}`: 분석할 텍스트

## 출력 형식
각 프롬프트마다 다른 형식:
- `date.txt`: YYYY-MM-DD 형식 또는 "null"
- `amount.txt`: 숫자 또는 "null"
- `party.txt`: 당사자 정보 JSON
- `action.txt`: 행위 정보 JSON
- `all_entities.txt`: 모든 엔티티를 포함한 JSON

## 사용 위치
- `src/services/entity_extractor.py`

