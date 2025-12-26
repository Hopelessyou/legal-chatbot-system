# 요약 프롬프트 템플릿

이 디렉토리에는 케이스 타입별 요약 프롬프트 템플릿이 저장됩니다.

## 파일 구조

### 기본 프롬프트
- `default.txt`: 기본 요약 프롬프트 (케이스 타입별 파일이 없을 때 사용)

### 가족법 (FAMILY)
- `family_divorce.txt`: 이혼 사건 요약 프롬프트
- `family_inheritance.txt`: 상속 사건 요약 프롬프트
- `family_default.txt`: 가족법 기본 프롬프트

### 민사 (CIVIL)
- `civil_loan.txt`: 대여금 사건 요약 프롬프트
- `civil_contract.txt`: 계약 분쟁 사건 요약 프롬프트
- `civil_damages.txt`: 손해배상 사건 요약 프롬프트
- `civil_default.txt`: 민사 기본 프롬프트

### 형사 (CRIMINAL)
- `criminal_fraud.txt`: 사기 사건 요약 프롬프트
- `criminal_assault.txt`: 폭행 사건 요약 프롬프트
- `criminal_theft.txt`: 절도 사건 요약 프롬프트
- `criminal_sex_crime.txt`: 성범죄 사건 요약 프롬프트
- `criminal_default.txt`: 형사 기본 프롬프트

### 행정 (ADMIN)
- `admin_default.txt`: 행정처분 기본 프롬프트

## 파일명 규칙

파일명은 `{main_case_type}_{sub_case_type}.txt` 형식을 따릅니다:
- `family_divorce.txt`: FAMILY / 이혼
- `civil_loan.txt`: CIVIL / 대여금
- `civil_contract.txt`: CIVIL / 계약
- `criminal_fraud.txt`: CRIMINAL / 사기

## 템플릿 변수

프롬프트 템플릿에서 사용 가능한 변수:
- `{case_type}`: 사건 유형 (예: "FAMILY / 이혼")
- `{facts}`: 수집된 사실 딕셔너리
- `{emotions}`: 감정 정보 리스트
- `{completion_rate}`: 완성도 (%)
- `{user_inputs_section}`: 사용자 입력 내용 섹션 (자동 생성)
- `{sections_info}`: 요약 섹션 구성 정보 (자동 생성)
- `{important_info_guide_first}`: 중요 정보 가이드 첫 줄 (자동 생성)

## 사용 방법

1. 프롬프트 파일을 수정하여 원하는 내용으로 변경
2. 서버 재시작 없이도 변경사항이 자동으로 반영됨 (파일 읽기 시마다 로드)
3. 케이스 타입별로 다른 프롬프트를 사용하려면 해당 파일명으로 생성

