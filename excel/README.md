# 엑셀 파일 위치

이 폴더에 **단일 엑셀 파일**을 배치하세요:

## 필수 엑셀 파일

**knowledge_base.xlsx** - 모든 지식 베이스 데이터를 포함하는 단일 엑셀 파일

이 파일에는 다음 시트들이 포함되어야 합니다:

1. **K0_Intake** - 초기 인입 질문/디스클레이머/긴급체크
2. **K1_Classification** - LEVEL2/LEVEL3 분류 기준
3. **K2_Questions** - 질문 및 필수 필드 정의
4. **LEVEL4_FACT_Pattern** - 사실 패턴 정의
5. **K3_Risk_Rules** - 리스크 규칙 정의
6. **K4_Output_Format** - 출력 포맷 정의

## 선택적 시트

- **LEVEL3_Scenario** - 시나리오 정의 (현재 미사용)

## 사용 방법

엑셀 파일을 이 폴더에 배치한 후:

```bash
python scripts/generate_all_yaml.py
```

자세한 내용은 `docs/EXCEL_TO_YAML.md`를 참고하세요.

## 장점

단일 엑셀 파일 방식의 장점:
- ✅ 파일 관리가 간편함
- ✅ 모든 데이터를 한 곳에서 관리
- ✅ 버전 관리가 쉬움
- ✅ 시트 간 데이터 일관성 유지 용이

