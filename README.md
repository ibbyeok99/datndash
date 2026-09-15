# 국방조달 절차 위험 스크리닝 대시보드

군수품 조달 데이터를 분석해 계약 체결이 오래 걸리거나 유찰·단독입찰·업체집중이 반복되는 품목을 조기에 선별하는 의사결정 지원 대시보드입니다. (국방·첨단산업 AI 솔루션 머신러닝 엔지니어 양성과정 1차 프로젝트)

## 배포

- 최신 배포판: https://claude.ai/artifact/L6nxxd2PykyyzqMn1dLa1J

## 로컬 실행

```bash
# 1. 데이터 번들 생성 (신규 대시보드 CSV 또는 레거시 EDA CSV가 로컬에 있어야 함)
python dashboard/build_data.py

# 2. 로컬 서버로 미리보기 (fetch로 JSON을 불러오므로 파일을 직접 여는 것보다 서버 구동 권장)
python -m http.server 8000 --directory dashboard
# 이후 브라우저에서 http://localhost:8000 접속
```

테스트: `pytest tests/`

## 데이터 구조

두 종류의 데이터 소스를 사용합니다.

1. **신규 운영 데이터셋** (`data/processed/dashboard/dashboard_*.csv`, 4종) — 화면 1~5(전체 현황/소요일수·추이/입찰경쟁/업체집중도/품목 상세)의 주 데이터 소스입니다. 아직 팀에서 전달되지 않아 현재는 비어 있으며, 각 화면은 "데이터 없음" 빈 상태로 표시됩니다. **파일이 도착하면 `data/processed/dashboard/`에 넣고 `python dashboard/build_data.py`를 다시 실행하면 자동으로 반영됩니다.** 각 파일의 정확한 컬럼 스펙은 `data/processed/dashboard/README.md`를 참고하세요.
2. **레거시 EDA 데이터셋** (`data/processed/1차 수정/eda/*.csv`, `docs/데이터_전달가이드.md` 기준) — 화면 6(통계적 근거)의 실제 통계 검정 결과와, 품목분류 필터 목록을 보조하는 데 사용됩니다.

CSV 원본 파일은 `.gitignore`에 의해 저장소에 포함되지 않습니다 (`dashboard/data/dashboard_data.json`은 작은 집계 파일이라 커밋됩니다).

## 위험점수 로드맵

조달절차 위험점수(리드타임점수/유찰점수/단독입찰점수/HHI점수/종합위험점수/위험등급)는 산식이 확정되어 `dashboard_품목별_위험현황.csv`에 실제 값으로 채워지기 전까지는 계산하지 않고 "데이터 없음"으로만 표시합니다. 관련 로직은 `dashboard/app.js`의 `renderDetail()` 내 위험점수 구성요소 렌더링 부분에 있습니다.

## 디렉터리

```
dashboard/            대시보드 소스 (index.html, app.js, style.css, build_data.py)
dashboard/data/       빌드된 JSON 번들 (커밋됨)
data/processed/dashboard/   신규 운영 CSV 4종이 도착할 위치 (README.md에 스펙 명시)
data/processed/1차 수정/eda/  레거시 EDA CSV 8종 (통계적 근거 화면용, gitignore 대상)
docs/                 데이터 전달 가이드, EDA 통계분석 보고서
project_guide/        프로젝트 목적 및 대시보드 설계안, 실행 가이드
tests/                pytest (데이터 파이프라인 검증)
```
