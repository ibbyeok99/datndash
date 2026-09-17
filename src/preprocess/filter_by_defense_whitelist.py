"""
defense_institution_whitelist.csv(Y로 확정된 기관코드)를 기준으로, TRY01의
계약정보/입찰공고 원천 데이터(2020~2022년)에서 공고기관·수요기관·계약기관 중
하나라도 화이트리스트에 포함되는 행만 걸러서 같은 폴더에 CSV로 저장한다.

- 계약정보(getCntrctInfoListThng_YYYY.csv): 계약기관(cntrctInsttCd) 또는
  수요기관(dminsttList 안의 코드들) 중 하나라도 Y 목록에 있으면 포함.
- 입찰공고(bid_notice_YYYY.csv): 공고기관(ntceInsttCd) 또는 수요기관
  (dminsttCd) 중 하나라도 Y 목록에 있으면 포함.
- 외자계약은 2020~2022년 데이터가 없어 이번 범위에서 제외.

원본 행을 그대로(가공 없이) 출력하며, 헤더도 원본 그대로 유지한다.
"""
import csv
import glob
import os
import re
import sys

BASE = r"C:\frontline_data\data\whitelist\TRY01\data"
WHITELIST = r"C:\frontline_data\data\whitelist\TRY01\result\defense_institution_whitelist.csv"
YEARS = ["2020", "2021", "2022"]

DMINSTT_BRACKET_RE = re.compile(r"\[[^\[\]]*\]")


def load_defense_codes():
    codes = set()
    with open(WHITELIST, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["is_defense"] == "Y":
                codes.add(row["institution_code"].strip())
    return codes


def parse_dminstt_codes(raw):
    out = []
    if not raw:
        return out
    for bracket in DMINSTT_BRACKET_RE.findall(raw):
        parts = bracket[1:-1].split("^")
        if len(parts) >= 2:
            out.append(parts[1])
    return out


def filter_contract_file(path, out_path, defense_codes, stats):
    n_rows = 0
    n_matched = 0
    n_mismatch = 0
    with open(path, encoding="utf-8-sig", newline="") as fin, \
         open(out_path, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header = next(reader)
        writer.writerow(header)
        expected_len = len(header)
        idx = {h: i for i, h in enumerate(header)}
        i_code = idx["cntrctInsttCd"]
        i_dmi = idx["dminsttList"]
        for row in reader:
            n_rows += 1
            if len(row) != expected_len:
                n_mismatch += 1
                continue
            hit = row[i_code] in defense_codes
            if not hit:
                for dcode in parse_dminstt_codes(row[i_dmi]):
                    if dcode in defense_codes:
                        hit = True
                        break
            if hit:
                n_matched += 1
                writer.writerow(row)
    stats.append({"file": path, "rows": n_rows, "matched": n_matched, "mismatched": n_mismatch})
    print(f"[contract] {os.path.basename(path)}: rows={n_rows} matched={n_matched} mismatched={n_mismatch}", file=sys.stderr)


def filter_bid_file(path, out_path, defense_codes, stats):
    n_rows = 0
    n_matched = 0
    n_mismatch = 0
    with open(path, encoding="utf-8-sig", newline="") as fin, \
         open(out_path, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header = next(reader)
        writer.writerow(header)
        NTCE_CODE, DM_CODE = 9, 11
        MIN_LEN = 13
        for row in reader:
            n_rows += 1
            if len(row) < MIN_LEN:
                n_mismatch += 1
                continue
            hit = row[NTCE_CODE] in defense_codes or row[DM_CODE] in defense_codes
            if hit:
                n_matched += 1
                writer.writerow(row)
    stats.append({"file": path, "rows": n_rows, "matched": n_matched, "mismatched": n_mismatch})
    print(f"[bid] {os.path.basename(path)}: rows={n_rows} matched={n_matched} mismatched={n_mismatch}", file=sys.stderr)


def main():
    defense_codes = load_defense_codes()
    print(f"Loaded {len(defense_codes)} defense institution codes (is_defense=Y)", file=sys.stderr)

    stats = []

    contract_dir = os.path.join(BASE, "계약정보서비스 1번_물품 계약현황")
    for year in YEARS:
        path = os.path.join(contract_dir, f"getCntrctInfoListThng_{year}.csv")
        out_path = os.path.join(contract_dir, f"getCntrctInfoListThng_{year}_defense_filtered.csv")
        filter_contract_file(path, out_path, defense_codes, stats)

    bid_dir = os.path.join(BASE, "입찰공고정보서비스 4번_물품 입찰공고")
    for year in YEARS:
        path = os.path.join(bid_dir, f"bid_notice_{year}.csv")
        out_path = os.path.join(bid_dir, f"bid_notice_{year}_defense_filtered.csv")
        filter_bid_file(path, out_path, defense_codes, stats)

    total_matched = sum(s["matched"] for s in stats)
    total_mismatch = sum(s["mismatched"] for s in stats)
    print(f"\nTotal matched rows across all files: {total_matched}", file=sys.stderr)
    print(f"Total mismatched(skipped) rows: {total_mismatch}", file=sys.stderr)


if __name__ == "__main__":
    main()
