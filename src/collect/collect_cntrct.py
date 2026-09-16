"""나라장터 계약정보서비스(CntrctInfoService) 물품계약 데이터 월별 수집 스크립트.

- 대상 오퍼레이션: getCntrctInfoListThng(물품조회), ...Detail(세부조회),
  ...ChgHstry(변경이력), ...DltHstry(삭제이력)
- 대상 기간: 2020-01 ~ API에서 조회 가능한 최신 월(실행 시점 기준으로 매번 갱신), 오퍼레이션별로 월 단위 조회
- data.go.kr 개발계정 트래픽 제한(1,000건/일)에 걸리지 않도록 소프트 캡을 두고,
  제한에 걸리면 진행 상황을 저장하고 즉시 종료한다 (다음 실행 시 이어받기).
- 특정 월 수집이 실패하면 그 월은 스킵하고 다음 월로 넘어가되, 원인 불명 오류가
  연속으로 반복되면 안전을 위해 전체 수집을 중단하고 progress 파일에 사유를 남긴다.
- 매 월 시작 시점에 progress 파일에 "현재 작업 위치"를 먼저 기록하므로, 프로세스가
  강제 종료되어도 다음 실행 시 어디서 멈췄는지 정확히 알 수 있다.

Usage:
    python src/collect/collect_cntrct.py             # 이어받기 실행
    python src/collect/collect_cntrct.py --status     # 진행 현황만 출력
    python src/collect/collect_cntrct.py --preflight  # 파라미터 검증용 소량 호출만
    python src/collect/collect_cntrct.py --verify      # 완료 구간의 파일/기록 정합성 검증
"""

import argparse
import calendar
import csv
import json
import re
import sys
import time
from datetime import datetime, date
from pathlib import Path
from urllib.parse import unquote

import requests

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = REPO_ROOT / ".env"
RAW_DIR = REPO_ROOT / "data" / "raw" / "cntrct"
PROGRESS_PATH = RAW_DIR / "_progress.json"
LOG_PATH = RAW_DIR / "_collect.log"

BASE_URL = "https://apis.data.go.kr/1230000/ao/CntrctInfoService"
OPERATIONS = [
    "getCntrctInfoListThng",
    "getCntrctInfoListFrgcpt",      # 외자 계약현황 - 별도 한도라 ThngDetail보다 먼저 수집
    "getCntrctInfoListThngDetail",  # 위 Frgcpt 완료 후 이어서 재개
    # ThngChgHstry, ThngDltHstry: 더 이상 필요 없어 수집 대상에서 제외
]

START_YM = "2020-01"


def current_end_ym() -> str:
    """조회 종료월(항상 실행 시점의 현재 월). 미래월은 API가 정상 0건으로 응답하므로
    실행 시점 기준으로 매번 새로 계산해 '최신 데이터까지' 자동으로 범위를 넓힌다."""
    return date.today().strftime("%Y-%m")

NUM_OF_ROWS = 999
REQUEST_DELAY_SEC = 0.4
RETRY_DELAY_SEC = 3
MAX_PAGE_RETRY = 2
DAILY_CALL_SOFT_LIMIT = 2900  # 주+서브1+서브2 키(각 1,000/일) 합산 한도에 여유를 둔 최종 안전장치.
# 실제 중단은 각 키가 트래픽 제한 응답(코드 22 등)을 받을 때 자동 전환/중단되는 로직이 담당한다.
MAX_CONSECUTIVE_UNKNOWN_FAILURES = 3  # 원인 불명 오류가 연속으로 이만큼 나면 전체 중단(무한 스킵 방지).

# 이전 실행에서 이미 완료된 것으로 확인된 항목 (최초 실행 시, 진행상황 파일이 없을 때만 시딩)
KNOWN_DONE = {
    "getCntrctInfoListThng": [
        "2024-01", "2024-02", "2024-03", "2024-04", "2024-11", "2024-12",
        "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    ],
    "getCntrctInfoListThngDetail": ["2024-01"],
    "getCntrctInfoListThngChgHstry": ["2024-01", "2024-02"],
    "getCntrctInfoListThngDltHstry": [],
}

# data.go.kr 공공데이터포털 공통 에러코드 (일부)
CODE_QUOTA_EXCEEDED = {"22", "20", "21", "30", "31", "32"}  # 트래픽/서비스 제한 + 키별 등록·만료·IP 오류 -> 키 전환
CODE_PARAM_ERROR = {"06", "10", "11", "12", "33"}  # 요청 자체의 파라미터 오류 -> 키를 바꿔도 소용없어 즉시 중단
CODE_NODATA = {"03"}                            # 정상, 데이터 없음
CODE_OK = {"00", "0"}


def log(msg: str):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env() -> dict:
    env = {}
    if not ENV_PATH.exists():
        return env
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        v = re.split(r"\s+#", v, maxsplit=1)[0]  # 값 뒤에 붙은 인라인 주석(예: "키값 # 메모") 제거
        env[k.strip()] = v.strip()
    return env


def month_range(start_ym: str, end_ym: str) -> list[str]:
    y, m = map(int, start_ym.split("-"))
    ey, em = map(int, end_ym.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def month_bounds(ym: str) -> tuple[str, str]:
    """월의 시작/끝을 YYYYMMDDHHMM 형식으로 반환한다 (이 API는 분 단위까지 요구함)."""
    y, m = map(int, ym.split("-"))
    last_day = calendar.monthrange(y, m)[1]
    bgn = date(y, m, 1).strftime("%Y%m%d") + "0000"
    end = date(y, m, last_day).strftime("%Y%m%d") + "2359"
    return bgn, end


class QuotaExhausted(Exception):
    pass


class ParamError(Exception):
    pass


class KeyRing:
    """서비스키를 순서대로 시도하다가 트래픽 제한에 걸리면 다음 키로 전환한다.

    전환이 일어날 때마다 시점/사유/당시 작업 위치(context)를 progress 파일의
    key_switch_log에 남긴다. 키 값 자체는 절대 기록하지 않는다.
    """

    def __init__(self, keys: list[str], progress: dict | None = None):
        # .env에는 URL-encoding된 키가 저장되어 있어, requests가 다시 encoding하면
        # 이중 인코딩되어 SERVICE_KEY_IS_NOT_REGISTERED_ERROR가 난다. 미리 decode해둔다.
        self.keys = [unquote(k) for k in keys if k]
        self.idx = 0
        self.progress = progress

    def current(self) -> str:
        if self.idx >= len(self.keys):
            raise QuotaExhausted("사용 가능한 서비스키가 모두 트래픽 제한에 걸렸습니다")
        return self.keys[self.idx]

    def rotate(self, code: str = "", msg: str = "", context: str = ""):
        from_idx = self.idx
        self.idx += 1
        event = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "from_idx": from_idx,
            "to_idx": self.idx,
            "code": code,
            "msg": msg,
            "context": context,
        }
        if self.progress is not None:
            self.progress.setdefault("key_switch_log", []).append(event)
            save_progress(self.progress)
        if self.idx >= len(self.keys):
            log(f"키 전환 실패: 다음 키 없음 (context={context}, code={code}, msg={msg})")
            raise QuotaExhausted("사용 가능한 서비스키가 모두 트래픽 제한에 걸렸습니다")
        log(f"서비스키 전환: index={from_idx} -> {self.idx} (context={context}, code={code}, msg={msg})")


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    else:
        progress = {"operations": {}, "calls_used_this_run": 0}
        for op in OPERATIONS:
            progress["operations"][op] = {
                "done": {ym: {"rows": None, "note": "이전 실행에서 완료 확인"} for ym in KNOWN_DONE.get(op, [])},
                "failed": {},
            }
    # 이전 버전의 progress 파일에는 없을 수 있는 키들을 보강한다.
    progress.setdefault("current", None)
    progress.setdefault("halted", None)
    progress.setdefault("key_switch_log", [])
    for op in OPERATIONS:
        progress["operations"].setdefault(op, {"done": {}, "failed": {}})
    return progress


def save_progress(progress: dict):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def pending_months(progress: dict, op: str) -> list[str]:
    done = set(progress["operations"][op]["done"].keys())
    return [ym for ym in month_range(START_YM, current_end_ym()) if ym not in done]


def call_api(op: str, params: dict, keyring: KeyRing, call_counter: list[int], context: str = "") -> dict:
    """단일 페이지 호출. 성공 시 response body dict 반환, 실패 시 예외."""
    context = context or op
    last_err = None
    for attempt in range(MAX_PAGE_RETRY + 1):
        params_with_key = dict(params)
        params_with_key["serviceKey"] = keyring.current()
        try:
            resp = requests.get(f"{BASE_URL}/{op}", params=params_with_key, timeout=20)
            call_counter[0] += 1
        except requests.RequestException as e:
            last_err = e
            log(f"  [{context}] 네트워크 오류 (재시도 {attempt+1}/{MAX_PAGE_RETRY}): {e}")
            time.sleep(RETRY_DELAY_SEC)
            continue

        try:
            data = resp.json()
        except ValueError:
            last_err = RuntimeError(f"JSON 파싱 실패: status={resp.status_code} body[:300]={resp.text[:300]!r}")
            log(f"  {last_err}")
            time.sleep(RETRY_DELAY_SEC)
            continue

        # 이 API는 상황에 따라 응답 래퍼가 3가지로 다르게 온다:
        # 1) {"response": {"header": {resultCode,resultMsg}, "body": ...}}            (정상/데이터없음)
        # 2) {"nkoneps.com.response.ResponseError": {"header": {resultCode,resultMsg}}} (업무 로직 검증 오류)
        # 3) {"OpenAPI_ServiceResponse": {"cmmMsgHeader": {returnReasonCode,errMsg}}}   (게이트웨이 레벨 오류: 인증/트래픽 제한)
        if "response" in data:
            header = data.get("response", {}).get("header", {})
            code = str(header.get("resultCode", ""))
            msg = header.get("resultMsg", "")
        elif "nkoneps.com.response.ResponseError" in data:
            header = data["nkoneps.com.response.ResponseError"].get("header", {})
            code = str(header.get("resultCode", ""))
            msg = header.get("resultMsg", "")
        elif "OpenAPI_ServiceResponse" in data:
            header = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {})
            code = str(header.get("returnReasonCode", ""))
            msg = header.get("errMsg", "")
        else:
            code, msg = "", f"알 수 없는 응답 형식: {str(data)[:200]}"

        if code in CODE_OK or code in CODE_NODATA:
            return data.get("response", {}).get("body", {}), code

        if code in CODE_QUOTA_EXCEEDED:
            log(f"  [{context}] 트래픽/서비스 제한 코드 {code} ({msg}) -> 다음 키로 전환 시도")
            keyring.rotate(code=code, msg=msg, context=context)
            continue

        if code in CODE_PARAM_ERROR:
            raise ParamError(f"파라미터/인증 오류 resultCode={code} resultMsg={msg} params={params}")

        # 알려지지 않은 코드: 한 번 더 재시도 후 실패 처리
        last_err = RuntimeError(f"알 수 없는 resultCode={code} resultMsg={msg}")
        log(f"  [{context}] {last_err} (재시도 {attempt+1}/{MAX_PAGE_RETRY})")
        time.sleep(RETRY_DELAY_SEC)

    raise RuntimeError(f"페이지 호출 반복 실패: {last_err}")


def extract_rows(body: dict) -> tuple[list[dict], int]:
    total = int(body.get("totalCount", 0) or 0)
    items = body.get("items")
    if items in (None, "", []):
        return [], total
    if isinstance(items, dict):
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item], total
        return list(item), total
    if isinstance(items, list):
        return items, total
    return [], total


def fetch_month(op: str, ym: str, keyring: KeyRing, call_counter: list[int]) -> list[dict]:
    bgn, end = month_bounds(ym)
    context = f"{op}/{ym}"
    all_rows: list[dict] = []
    page = 1
    while True:
        params = {
            "pageNo": page,
            "numOfRows": NUM_OF_ROWS,
            "type": "json",
            "inqryDiv": "1",
            "inqryBgnDt": bgn,
            "inqryEndDt": end,
        }
        body, code = call_api(op, params, keyring, call_counter, context=context)
        if code in CODE_NODATA:
            break
        rows, total = extract_rows(body)
        all_rows.extend(rows)
        time.sleep(REQUEST_DELAY_SEC)
        if not rows or len(all_rows) >= total:
            break
        page += 1
    return all_rows


def write_csv(op: str, ym: str, rows: list[dict]):
    out_dir = RAW_DIR / op
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ym}.csv"
    if not rows:
        out_path.write_text("", encoding="utf-8-sig")
        return
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_status(progress: dict):
    end_ym = current_end_ym()
    total_months = len(month_range(START_YM, end_ym))
    for op in OPERATIONS:
        done = progress["operations"][op]["done"]
        failed = progress["operations"][op]["failed"]
        total_rows = sum((v.get("rows") or 0) for v in done.values())
        print(f"{op}: 완료 {len(done)}/{total_months} (실패 {len(failed)}), 누적 행수 {total_rows:,}")
    if progress.get("current"):
        print(f"진행 중(중단 시 이어받을 위치): {progress['current']}")
    if progress.get("halted"):
        print(f"중단 상태: {progress['halted']}")


def verify(progress: dict) -> list[str]:
    """완료로 기록된 구간의 실제 파일/기록 정합성을 점검하고, 오퍼레이션 x 기간 기준
    누락 여부도 함께 확인한다. 데이터를 수정하지 않고 문제 목록만 보고한다."""
    problems: list[str] = []
    end_ym = current_end_ym()
    all_months = month_range(START_YM, end_ym)

    for op in OPERATIONS:
        done = progress["operations"][op]["done"]
        failed = progress["operations"][op]["failed"]
        attempted = set(done) | set(failed)
        missing = [ym for ym in all_months if ym not in attempted]
        if missing:
            shown = missing[:6]
            suffix = " ..." if len(missing) > 6 else ""
            problems.append(f"{op}: 미시도 구간 {len(missing)}개 -> {shown}{suffix}")

        for ym, info in done.items():
            path = RAW_DIR / op / f"{ym}.csv"
            rows = info.get("rows")
            if not path.exists():
                problems.append(f"{op}/{ym}: 완료 기록은 있으나 파일이 없음 ({path})")
                continue
            size = path.stat().st_size
            if rows and rows > 0 and size == 0:
                problems.append(f"{op}/{ym}: rows={rows}로 기록됐는데 파일 크기가 0 (불완전 저장 의심)")
            elif (rows in (0, None)) and size > 0:
                problems.append(f"{op}/{ym}: rows={rows}로 기록됐는데 파일 크기가 {size} (불일치)")
            elif rows and rows > 0:
                with open(path, encoding="utf-8-sig") as f:
                    line_count = sum(1 for _ in f) - 1  # 헤더 제외
                if line_count != rows:
                    problems.append(f"{op}/{ym}: 기록된 rows={rows}, 실제 파일 행수={line_count} 불일치")

        for ym, info in failed.items():
            problems.append(f"{op}/{ym}: 실패 상태로 남아있음 -> {str(info.get('reason',''))[:120]}")

    if progress.get("current"):
        problems.append(f"진행 중 표시가 남아있음(비정상 종료 의심) -> {progress['current']}")
    if progress.get("halted"):
        problems.append(f"중단 상태로 남아있음 -> {progress['halted']}")

    log(f"=== 검증 시작 (대상 기간 {START_YM} ~ {end_ym}) ===")
    if not problems:
        log("문제 없음: 모든 오퍼레이션 x 기간이 완료 상태이며 파일 검증을 통과했습니다.")
    else:
        for p in problems:
            log(f"[검증 경고] {p}")
        log(f"=== 검증 종료: 문제 {len(problems)}건 ===")
    return problems


def run(preflight_only: bool = False):
    env = load_env()
    primary_key = env.get("G2B_CNTRCT_SERVICE_KEY", "")
    sub_key = env.get("SUB_SERVICE_KEY", "")
    sub_key2 = env.get("SUB_SERVICE_KEY2", "")

    progress = load_progress()
    call_counter = [0]

    if preflight_only:
        keyring = KeyRing([primary_key, sub_key, sub_key2])
        log("=== preflight 시작: 각 오퍼레이션 미완료 첫 달을 numOfRows=1로 검증 ===")
        for op in OPERATIONS:
            pending = pending_months(progress, op)
            if not pending:
                log(f"{op}: 미완료 월 없음, preflight 스킵")
                continue
            ym = pending[0]
            bgn, end = month_bounds(ym)
            params = {"pageNo": 1, "numOfRows": 1, "type": "json", "inqryDiv": "1",
                      "inqryBgnDt": bgn, "inqryEndDt": end}
            try:
                body, code = call_api(op, params, keyring, call_counter, context=f"{op}/{ym}")
                rows, total = extract_rows(body)
                log(f"{op} / {ym}: resultCode={code}, totalCount={total}, sample_keys={list(rows[0].keys()) if rows else '(없음)'}")
            except (ParamError, QuotaExhausted) as e:
                log(f"{op} / {ym}: 검증 실패 -> {e}")
                return
        log(f"=== preflight 종료 (호출 {call_counter[0]}건 사용) ===")
        return

    keyring = KeyRing([primary_key, sub_key, sub_key2], progress=progress)

    leftover = progress.get("current")
    if leftover:
        log(f"이전 실행이 {leftover['op']} / {leftover['ym']} 수집 중 비정상 종료된 것으로 보입니다"
            f"(시작 시각 {leftover.get('started_at', '?')}). 해당 구간부터 다시 수집합니다.")
    if progress.get("halted"):
        log(f"이전 실행이 다음 사유로 중단된 상태였습니다: {progress['halted']}. 이어서 재시도합니다.")
        progress["halted"] = None
        save_progress(progress)

    end_ym = current_end_ym()
    log(f"=== 이어받기 수집 시작 (대상 기간 {START_YM} ~ {end_ym}) ===")
    print_status(progress)

    consecutive_unknown_failures = 0

    try:
        for op in OPERATIONS:
            for ym in pending_months(progress, op):
                if call_counter[0] >= DAILY_CALL_SOFT_LIMIT:
                    log(f"자체 소프트 캡({DAILY_CALL_SOFT_LIMIT}건) 도달 -> 저장 후 종료")
                    progress["current"] = None
                    save_progress(progress)
                    log("오늘은 여기서 중단합니다. 내일(또는 트래픽 리셋 후) 다시 실행하면 이어받습니다.")
                    return

                progress["current"] = {
                    "op": op, "ym": ym, "started_at": datetime.now().isoformat(timespec="seconds"),
                }
                save_progress(progress)

                log(f"{op} / {ym} 수집 시작...")
                try:
                    rows = fetch_month(op, ym, keyring, call_counter)
                except ParamError as e:
                    log(f"{op} / {ym}: 파라미터 오류로 전체 중단 -> {e}")
                    progress["halted"] = {
                        "reason": "param_error", "detail": str(e), "op": op, "ym": ym,
                        "at": datetime.now().isoformat(timespec="seconds"),
                    }
                    progress["current"] = None
                    save_progress(progress)
                    return
                except QuotaExhausted as e:
                    log(f"{op} / {ym}: 트래픽 제한으로 전체 중단 -> {e}")
                    progress["halted"] = {
                        "reason": "quota_exhausted", "detail": str(e), "op": op, "ym": ym,
                        "at": datetime.now().isoformat(timespec="seconds"),
                    }
                    progress["current"] = None
                    save_progress(progress)
                    return
                except Exception as e:
                    consecutive_unknown_failures += 1
                    log(f"{op} / {ym}: 수집 실패 ({consecutive_unknown_failures}/{MAX_CONSECUTIVE_UNKNOWN_FAILURES}), 스킵하고 다음으로 -> {e}")
                    progress["operations"][op]["failed"][ym] = {
                        "reason": str(e), "at": datetime.now().isoformat(timespec="seconds"),
                    }
                    progress["current"] = None
                    save_progress(progress)
                    if consecutive_unknown_failures >= MAX_CONSECUTIVE_UNKNOWN_FAILURES:
                        log(f"원인 불명 오류가 {MAX_CONSECUTIVE_UNKNOWN_FAILURES}회 연속 발생 -> 안전을 위해 전체 수집을 중단합니다.")
                        progress["halted"] = {
                            "reason": "repeated_unknown_errors", "op": op, "ym": ym,
                            "at": datetime.now().isoformat(timespec="seconds"),
                        }
                        save_progress(progress)
                        return
                    continue

                consecutive_unknown_failures = 0
                write_csv(op, ym, rows)
                done_entry = {"rows": len(rows), "collected_at": datetime.now().isoformat(timespec="seconds")}
                if len(rows) == 0:
                    done_entry["note"] = "정상 조회 결과 0건(수집 실패 아님)"
                progress["operations"][op]["done"][ym] = done_entry
                progress["operations"][op]["failed"].pop(ym, None)
                progress["current"] = None
                save_progress(progress)
                log(f"{op} / {ym} 완료: {len(rows):,}행 (누적 호출 {call_counter[0]}건)")

        log("=== 대상 기간 전체 수집 완료, 검증을 실행합니다 ===")
        verify(progress)
    finally:
        save_progress(progress)
        log("=== 이번 실행 종료 ===")
        print_status(progress)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="진행 현황만 출력")
    parser.add_argument("--preflight", action="store_true", help="파라미터 검증용 소량 호출만 수행")
    parser.add_argument("--verify", action="store_true", help="완료 구간의 파일/기록 정합성 검증")
    args = parser.parse_args()

    if args.status:
        print_status(load_progress())
        return

    if args.verify:
        verify(load_progress())
        return

    run(preflight_only=args.preflight)


if __name__ == "__main__":
    main()
