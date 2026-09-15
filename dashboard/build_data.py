"""대시보드용 JSON 번들 생성 스크립트.

두 종류의 데이터를 합친다.

1) 신규 운영 데이터셋 (dashboard_*.csv, 4종) — data/processed/dashboard/
   화면 1~5의 주 데이터 소스가 될 예정이지만, 아직 팀에서 전달되지 않았다면
   각 데이터셋을 {"available": false, "rows": []}로 채워 프레임만 유지한다.
   즉, 이 파일이 없다고 에러를 내지 않고 "데이터 없음" 상태로 정상 동작해야 한다.
2) 레거시 EDA 데이터셋 (01~08, data/processed/1차 수정/eda/) — 화면 6(통계적 근거)의
   Kruskal-Wallis/사후검정/카이제곱 결과와, 품목분류 필터 목록(taxonomy)에만 사용한다.
   신규 운영 데이터셋의 수치 지표(중앙 소요일수, HHI 등)를 이 레거시 파일에서
   끌어와 대신 채우지 않는다 — 컬럼 정의가 다를 수 있어 임의로 채우면 왜곡이다.

Usage:
    python dashboard/build_data.py
"""

import json
import math
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
EDA_DIR = REPO_ROOT / "data" / "processed" / "1차 수정" / "eda"
NEW_DIR = REPO_ROOT / "data" / "processed" / "dashboard"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "dashboard_data.json"

NEW_DATASET_FILES = {
    "itemRisk": "dashboard_품목별_위험현황.csv",
    "monthlyTrend": "dashboard_품목별_월별추이.csv",
    "caseDetail": "dashboard_조달건별_상세내역.csv",
    "vendorConcentration": "dashboard_품목별_업체집중도.csv",
}


def clean_value(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def df_to_records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean_value(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def load_new_dataset(key: str, filename: str) -> dict:
    """신규 dashboard_*.csv 하나를 읽는다. 없으면 available=False로 빈 프레임 반환."""
    path = NEW_DIR / filename
    if not path.exists():
        return {"available": False, "bridged": False, "sourceFile": filename, "rows": []}
    df = pd.read_csv(path, encoding="utf-8-sig")
    return {"available": True, "bridged": False, "sourceFile": filename, "rows": df_to_records(df)}


def bridge_item_risk_from_legacy(df_07: pd.DataFrame) -> dict:
    """dashboard_품목별_위험현황.csv 가 아직 없을 때, 실제 값이 존재하는 지표에 한해
    레거시 07 통합지표에서 같은 의미의 컬럼만 옮겨온다.

    위험점수 구성요소(리드타임점수/유찰점수/단독입찰점수/HHI점수/종합위험점수/위험등급)는
    레거시 데이터에 대응 항목이 전혀 없으므로 null로 남긴다 — 절대 임의 계산하지 않는다.
    유효공고건수/계약성립건수/분석가능건수/계약금액합계는 정의가 정확히 같지 않은
    근사 매핑이라 "bridged": true 로 표시해 프런트에서 안내 배너를 띄운다.
    """
    rows = []
    for row in df_to_records(df_07):
        insufficient = "Y" if "Y" in (
            row.get("D2B_표본부족여부"),
            row.get("G2B_입찰표본부족여부"),
            row.get("G2B_HHI표본부족여부"),
        ) else "N"
        rows.append({
            "품목분류": row.get("품목분류"),
            "유효공고건수": row.get("G2B_공고품목수"),
            "계약성립건수": row.get("G2B_계약수"),
            "분석가능건수": row.get("D2B_분석표본수"),
            "중앙_계약성립소요일수": row.get("중앙_계약성립소요일수"),
            "평균_계약성립소요일수": row.get("평균_계약성립소요일수"),
            "p90_계약성립소요일수": row.get("P90_계약성립소요일수"),
            "유찰률": row.get("유찰률"),
            "단독입찰률": row.get("단독입찰률"),
            "재공고율": row.get("재공고율"),
            "계약금액합계": row.get("G2B_계약금액"),
            "상위1개사_계약금액점유율": row.get("상위1개사_계약금액비중"),
            "상위3개사_계약금액점유율": row.get("상위3개사_계약금액비중"),
            "HHI": row.get("HHI"),
            "리드타임점수": None,
            "유찰점수": None,
            "단독입찰점수": None,
            "HHI점수": None,
            "종합위험점수": None,
            "위험등급": None,
            "표본부족여부": insufficient,
        })
    return {
        "available": True,
        "bridged": True,
        "sourceFile": "07_품목별_조달절차_경쟁구조_통합지표.csv (레거시 임시 매핑)",
        "rows": rows,
    }


def read_legacy_csv(filename: str) -> pd.DataFrame | None:
    path = EDA_DIR / filename
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def main():
    # ---- 신규 운영 데이터셋 (4종, 아직 미도착 가능) --------------------------------
    new_datasets = {key: load_new_dataset(key, fname) for key, fname in NEW_DATASET_FILES.items()}

    # itemRisk 파일이 아직 없으면, 실제 값이 있는 레거시 07 통합지표로 임시 연결한다
    # (월별추이·조달건별상세·업체집중도는 레거시에 대응 데이터가 전혀 없어 브릿지하지 않음)
    if not new_datasets["itemRisk"]["available"]:
        df_07_for_bridge = read_legacy_csv("07_품목별_조달절차_경쟁구조_통합지표.csv")
        if df_07_for_bridge is not None:
            new_datasets["itemRisk"] = bridge_item_risk_from_legacy(df_07_for_bridge)

    # itemRisk가 도착했다면(또는 브릿지되었다면) 값 범위를 검증(있는 컬럼에 한해서만)
    if new_datasets["itemRisk"]["available"]:
        rows = new_datasets["itemRisk"]["rows"]
        for row in rows:
            for col in ("유찰률", "단독입찰률", "재공고율", "상위1개사_계약금액점유율", "상위3개사_계약금액점유율"):
                v = row.get(col)
                if v is not None and not (0 <= v <= 1):
                    raise ValueError(f"itemRisk.{col}={v} 가 0~1 범위를 벗어났습니다")
            hhi = row.get("HHI")
            if hhi is not None and not (0 <= hhi <= 10000):
                raise ValueError(f"itemRisk.HHI={hhi} 가 0~10000 범위를 벗어났습니다")

    # ---- 레거시 EDA 데이터셋: 통계적 근거(화면6) + 품목분류 taxonomy -----------------
    df_02 = read_legacy_csv("02_D2B_가설2_전체검정요약.csv")
    df_03 = read_legacy_csv("03_D2B_가설2_사후검정.csv")
    df_05 = read_legacy_csv("05_G2B_단독입찰_낙찰성공_검정.csv")
    df_07 = read_legacy_csv("07_품목별_조달절차_경쟁구조_통합지표.csv")
    df_08 = read_legacy_csv("08_품목분류_품질요약.csv")

    legacy_available = df_07 is not None

    # 품목분류 taxonomy: 신규 itemRisk가 있으면 그쪽을, 없으면 레거시 07에서 derive.
    # (필터 칩/품목 상세 드롭다운을 채우기 위한 "분류 목록"일 뿐, 지표값을 끌어오는 게 아니므로
    #  레거시를 보조로 쓰는 것은 §데이터 왜곡 금지 원칙에 저촉되지 않는다.)
    if new_datasets["itemRisk"]["available"]:
        item_categories = sorted({r["품목분류"] for r in new_datasets["itemRisk"]["rows"] if r.get("품목분류")})
    elif legacy_available:
        item_categories = sorted(df_07["품목분류"].dropna().unique().tolist())
    else:
        item_categories = []

    stats = {
        "available": df_02 is not None and df_03 is not None and df_05 is not None,
        "d2bOverallTest": df_to_records(df_02)[0] if df_02 is not None else None,
        "d2bPosthoc": df_to_records(df_03) if df_03 is not None else [],
        "g2bChi2": df_to_records(df_05)[0] if df_05 is not None else None,
    }
    quality_summary = df_to_records(df_08) if df_08 is not None else []

    bundle = {
        "itemCategories": item_categories,
        "itemCategoriesSource": "itemRisk" if new_datasets["itemRisk"]["available"] else ("legacy_07" if legacy_available else "none"),
        **new_datasets,
        "stats": stats,
        "qualitySummary": quality_summary,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    missing = [fname for key, fname in NEW_DATASET_FILES.items() if not new_datasets[key]["available"]]
    print(f"완료: {OUTPUT_PATH}")
    print(f"품목분류 {len(item_categories)}개 (출처: {bundle['itemCategoriesSource']})")
    if missing:
        print("아직 없는 신규 데이터셋 (프레임만 생성됨, '데이터 없음'으로 표시됨):")
        for m in missing:
            print(f"  - data/processed/dashboard/{m}")


if __name__ == "__main__":
    main()
