"""
TRY01 원천 데이터(계약정보/입찰공고/외자계약)에서 기관(공고/수요/계약기관)을
추출하고, 기관코드 단위로 이름 버전을 분리해 각 버전이 데이터상 처음
관측된 날짜(first_observed_date)를 기록한다.

역할 구분(공고/수요/계약기관)은 저장하지 않는다 - 코드값을 단일 네임스페이스로
병합한다.
"""
import csv
import glob
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

BASE = r"C:\frontline_data\data\whitelist\TRY01\data"
SCRATCH = r"C:\Users\acorn2\AppData\Local\Temp\claude\C--frontline-data\b72a18fe-7b29-42dc-95ec-27e84574f402\scratchpad"
OUT_DIR = r"C:\frontline_data\data\whitelist\TRY01\result"

CONTRACT_GLOB = os.path.join(BASE, "계약정보서비스 1번_물품 계약현황", "getCntrctInfoListThng_[0-9][0-9][0-9][0-9].csv")
BID_GLOB = os.path.join(BASE, "입찰공고정보서비스 4번_물품 입찰공고", "bid_notice_[0-9][0-9][0-9][0-9].csv")
FRGCPT_GLOB = os.path.join(BASE, "계약정보서비스 17번_외자 계약현황", "getCntrctInfoListFrgcpt_[0-9][0-9][0-9][0-9].csv")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_MIN = "2020-01-01"
VALID_MAX = "2026-12-31"
DMINSTT_BRACKET_RE = re.compile(r"\[[^\[\]]*\]")
PLACEHOLDER_CODES = {"ZZ99999"}

# occurrences[code][raw_name] = list of (date_or_None, source_tag)
occurrences = defaultdict(lambda: defaultdict(list))
row_length_report = []
malformed_rows_log = []


def clean_date(s):
    """Return a validated YYYY-MM-DD string, or None if missing/invalid/out-of-range."""
    if not s:
        return None
    s = s.strip()[:10]
    if not DATE_RE.match(s):
        return None
    if not (VALID_MIN <= s <= VALID_MAX):
        return None
    return s


def add_occurrence(code, name, date, role):
    code = (code or "").strip()
    name = (name or "").strip()
    if not code or not name or code in PLACEHOLDER_CODES:
        return
    occurrences[code][name].append((date, role))


def parse_dminstt_list(raw):
    """[seq^code^name^type^^^],[seq^code^name^type^^^] -> [(code, name), ...]"""
    out = []
    if not raw:
        return out
    for bracket in DMINSTT_BRACKET_RE.findall(raw):
        parts = bracket[1:-1].split("^")
        if len(parts) >= 3:
            out.append((parts[1], parts[2]))
    return out


def process_contract_file(path, col):
    """col: dict with keys code,name,dminstt_list,date_primary,date_fallback,date_fallback_dt"""
    n_rows = 0
    n_mismatch = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        expected_len = len(header)
        for i, row in enumerate(reader):
            n_rows += 1
            L = len(row)
            if L == col["len_full"]:
                idx = col["full"]
            elif "len_shifted" in col and L == col["len_shifted"]:
                idx = col["shifted"]
            else:
                n_mismatch += 1
                if len(malformed_rows_log) < 200:
                    malformed_rows_log.append(
                        {"file": path, "row": i, "len": L, "sample": row[:5]}
                    )
                continue

            code = row[idx["code"]]
            name = row[idx["name"]]
            date = (
                clean_date(row[idx["date_primary"]])
                or clean_date(row[idx["date_fallback"]])
                or clean_date(row[idx["date_fallback_dt"]][:10] if row[idx["date_fallback_dt"]] else "")
            )
            add_occurrence(code, name, date, "계약기관")

            dm_raw = row[idx["dminstt_list"]]
            for dcode, dname in parse_dminstt_list(dm_raw):
                add_occurrence(dcode, dname, date, "수요기관")
    row_length_report.append(
        {"file": path, "expected_len": expected_len, "rows": n_rows, "mismatched": n_mismatch}
    )
    print(f"[contract] {path}: rows={n_rows} mismatched={n_mismatch}", file=sys.stderr)


def process_bid_file(path):
    n_rows = 0
    n_mismatch = 0
    # standard bid_notice column positions (0-based)
    NTCE_CODE, NTCE_NAME = 9, 10
    DM_CODE, DM_NAME = 11, 12
    DATE_COL = 6
    MIN_LEN = 13  # need at least through dminsttNm
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        expected_len = len(header)
        for i, row in enumerate(reader):
            n_rows += 1
            if len(row) < MIN_LEN:
                n_mismatch += 1
                if len(malformed_rows_log) < 200:
                    malformed_rows_log.append(
                        {"file": path, "row": i, "len": len(row), "sample": row[:5]}
                    )
                continue
            if len(row) != expected_len:
                n_mismatch += 1  # usable but logged
            date = clean_date(row[DATE_COL][:10] if row[DATE_COL] else "")
            add_occurrence(row[NTCE_CODE], row[NTCE_NAME], date, "공고기관")
            add_occurrence(row[DM_CODE], row[DM_NAME], date, "수요기관")
    row_length_report.append(
        {"file": path, "expected_len": expected_len, "rows": n_rows, "mismatched": n_mismatch}
    )
    print(f"[bid] {path}: rows={n_rows} mismatched={n_mismatch}", file=sys.stderr)


def main():
    # --- 1. domestic contract files (39-col standard, 2024 file mixes 43/39) ---
    # 39-col header: cntrctInsttCd=17, cntrctInsttNm=18, dminsttList=24,
    # cntrctCnclsDate=7, cntrctDate=37, rgstDt=30.
    contract_full = {
        "code": 17, "name": 18, "dminstt_list": 24,
        "date_primary": 7, "date_fallback": 37, "date_fallback_dt": 30,
    }
    contract_shifted = {k: v + 4 for k, v in contract_full.items()}
    col_contract = {
        "len_full": 39, "full": contract_full,
        "len_shifted": 43, "shifted": contract_shifted,
    }
    for path in sorted(glob.glob(CONTRACT_GLOB)):
        process_contract_file(path, col_contract)

    # --- 2. bid notice files (101-col standard) ---
    for path in sorted(glob.glob(BID_GLOB)):
        process_bid_file(path)

    # --- 3. foreign-currency (외자) contract files (35-col, different layout) ---
    frgcpt_full = {
        "code": 19, "name": 20, "dminstt_list": 26,
        "date_primary": 7, "date_fallback": 34, "date_fallback_dt": 32,
    }
    col_frgcpt = {"len_full": 35, "full": frgcpt_full}
    for path in sorted(glob.glob(FRGCPT_GLOB)):
        process_contract_file(path, col_frgcpt)

    print(f"Total distinct institution codes: {len(occurrences)}", file=sys.stderr)

    os.makedirs(SCRATCH, exist_ok=True)
    with open(os.path.join(SCRATCH, "row_length_report.json"), "w", encoding="utf-8") as f:
        json.dump(row_length_report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(SCRATCH, "malformed_rows_sample.json"), "w", encoding="utf-8") as f:
        json.dump(malformed_rows_log, f, ensure_ascii=False, indent=2)

    # --- normalize + build SCD versions ---
    def normalize_name(raw):
        s = raw.strip()
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("（", "(").replace("）", ")")
        s = re.sub(r"\s+", " ", s)
        s = s.strip(" .")
        s = s.replace("㈜", "(주)")
        return s

    os.makedirs(OUT_DIR, exist_ok=True)
    rows_out = []
    multi_version_codes = []

    ROLE_ORDER = ["공고기관", "수요기관", "계약기관"]

    for code, raw_name_map in occurrences.items():
        groups = defaultdict(list)  # std_name -> list of (raw_name, date_or_None, role)
        for raw_name, occ_list in raw_name_map.items():
            std = normalize_name(raw_name)
            for date, role in occ_list:
                groups[std].append((raw_name, date, role))

        def sort_key(item):
            _std, occ = item
            dated = [d for _, d, _ in occ if d]
            return min(dated) if dated else "9999-99-99"

        ordered = sorted(groups.items(), key=sort_key)

        if len(ordered) > 1:
            multi_version_codes.append(code)

        for idx, (std_name, occ) in enumerate(ordered):
            dated = sorted(d for _, d, _ in occ if d)
            first_observed_date = dated[0] if dated else ""
            raw_counter = Counter(r for r, _, _ in occ)
            institution_name_raw = raw_counter.most_common(1)[0][0]
            roles_seen = {role for _, _, role in occ}
            institution_roles = "|".join(r for r in ROLE_ORDER if r in roles_seen)
            rows_out.append(
                {
                    "institution_code": code,
                    "institution_name_raw": institution_name_raw,
                    "institution_name_std": std_name,
                    "institution_roles": institution_roles,
                    "first_observed_date": first_observed_date,
                }
            )

    print(f"Total output rows (code+version): {len(rows_out)}", file=sys.stderr)
    print(f"Codes with >1 name version: {len(multi_version_codes)}", file=sys.stderr)
    with open(os.path.join(SCRATCH, "multi_version_codes.json"), "w", encoding="utf-8") as f:
        json.dump(multi_version_codes, f, ensure_ascii=False, indent=2)

    stage1_out = os.path.join(SCRATCH, "stage1_institutions.csv")
    with open(stage1_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "institution_code",
                "institution_name_raw",
                "institution_name_std",
                "institution_roles",
                "first_observed_date",
            ],
        )
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote {stage1_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
