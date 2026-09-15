"""dashboard/build_data.py의 출력(JSON 번들)에 대한 회귀 테스트.

신규 dashboard_*.csv 4종은 아직 팀에서 전달되지 않은 상태일 수 있으므로,
"파일이 없을 때도 정상적으로 빈 프레임을 만든다"는 것 자체가 핵심 테스트 대상이다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NEW_DIR = REPO_ROOT / "data" / "processed" / "dashboard"
JSON_PATH = REPO_ROOT / "dashboard" / "data" / "dashboard_data.json"

NEW_DATASET_KEYS = ["itemRisk", "monthlyTrend", "caseDetail", "vendorConcentration"]


@pytest.fixture(scope="module")
def bundle():
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "dashboard" / "build_data.py")],
        check=True,
        cwd=REPO_ROOT,
    )
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_required_top_level_keys_present(bundle):
    for key in ["itemCategories", "itemCategoriesSource", "stats", "qualitySummary", *NEW_DATASET_KEYS]:
        assert key in bundle


def test_new_datasets_have_available_flag_and_rows(bundle):
    for key in NEW_DATASET_KEYS:
        ds = bundle[key]
        assert "available" in ds
        assert "rows" in ds
        assert isinstance(ds["rows"], list)
        if not ds["available"]:
            # 파일이 없을 때 강제로 값을 채워넣지 않고 빈 프레임이어야 한다
            assert ds["rows"] == []


def test_missing_new_files_do_not_crash_build(bundle):
    # 이 시점에는 신규 CSV가 아직 도착하지 않았을 수 있음 — 그래도 빌드는 성공해야 함
    for key in NEW_DATASET_KEYS:
        assert key in bundle  # 존재 자체가 "크래시 없이 빈 프레임 생성"의 증거


def test_item_categories_source_is_labeled(bundle):
    assert bundle["itemCategoriesSource"] in ("itemRisk", "legacy_07", "none")
    if bundle["itemCategoriesSource"] == "none":
        assert bundle["itemCategories"] == []


def test_item_risk_ratio_columns_within_unit_range_if_available(bundle):
    if not bundle["itemRisk"]["available"]:
        pytest.skip("dashboard_품목별_위험현황.csv 아직 없음")
    for row in bundle["itemRisk"]["rows"]:
        for col in ("유찰률", "단독입찰률", "재공고율", "상위1개사_계약금액점유율", "상위3개사_계약금액점유율"):
            v = row.get(col)
            if v is not None:
                assert 0 <= v <= 1, f"{col}={v}"
        if row.get("HHI") is not None:
            assert 0 <= row["HHI"] <= 10000


def test_stats_block_present_when_legacy_files_exist(bundle):
    if bundle["stats"]["available"]:
        assert bundle["stats"]["d2bOverallTest"] is not None
        assert bundle["stats"]["g2bChi2"] is not None
        assert isinstance(bundle["stats"]["d2bPosthoc"], list)


def test_h1_block_present_when_legacy_files_exist(bundle):
    if bundle["stats"]["h1Available"]:
        t = bundle["stats"]["h1Test"]
        assert t is not None
        assert 0 <= t["단독입찰_재절차발생률"] <= 1
        assert 0 <= t["다수입찰_재절차발생률"] <= 1
        assert isinstance(bundle["stats"]["h1Sensitivity"], list) and len(bundle["stats"]["h1Sensitivity"]) > 0
        assert isinstance(bundle["stats"]["h1CrossTab"], list)
