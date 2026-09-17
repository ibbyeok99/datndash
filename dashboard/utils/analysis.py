import pandas as pd

def calculate_kpis(df):
    """필터링된 조달 데이터의 핵심 KPI를 계산한다."""

    # 검색 결과가 없는 경우
    if df.empty:
        return {
            "total_amount": 0,
            "contract_count": 0,
            "avg_amount": 0,
            "supplier_count": 0
        }

    total_amount = df["contract_amount"].sum()
    contract_count = len(df)
    avg_amount = df["contract_amount"].mean()
    supplier_count = df["supplier_name"].nunique()

    return {
        "total_amount": total_amount,
        "contract_count": contract_count,
        "avg_amount": avg_amount,
        "supplier_count": supplier_count
    }


def format_amount(amount):
    """계약금액을 억 원 단위 문자열로 변환한다."""

    amount_eok = amount / 100_000_000

    if amount_eok >= 100:
        return f"{amount_eok:,.0f}억 원"

    return f"{amount_eok:,.1f}억 원"

def get_yearly_trend(df):
    if df.empty:
        return pd.DataFrame(
            columns=["year", "contract_amount", "contract_count"]
        )

    yearly = (
        df.assign(year=df["contract_date"].dt.year)
        .groupby("year")
        .agg(
            contract_amount=("contract_amount", "sum"),
            contract_count=("contract_id", "count")
        )
        .reset_index()
        .sort_values("year")
    )

    return yearly

def get_monthly_trend(df):
    if df.empty:
        return pd.DataFrame(
            columns=["month", "contract_amount", "contract_count"]
        )

    monthly = (
        df.assign(
            month=df["contract_date"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("month")
        .agg(
            contract_amount=("contract_amount", "sum"),
            contract_count=("contract_id", "count")
        )
        .reset_index()
        .sort_values("month")
    )

    return monthly


def get_agency_share(df, top_n=5):
    """수요기관별 계약금액 비중을 계산한다."""

    if df.empty:
        return []

    agency = (
        df.groupby("agency", as_index=False)["contract_amount"]
        .sum()
        .sort_values("contract_amount", ascending=False)
    )

    total_amount = agency["contract_amount"].sum()

    agency["share"] = (
        agency["contract_amount"] / total_amount * 100
    )

    return [
        (row["agency"], round(row["share"]))
        for _, row in agency.head(top_n).iterrows()
    ]


def get_recent_history(df, n=5):
    """최근 계약·납품 이력을 반환한다."""

    if df.empty:
        return pd.DataFrame(
            columns=["시기", "기관", "방식", "금액"]
        )

    recent = (
        df.sort_values("delivery_date", ascending=False)
        .head(n)
        .copy()
    )

    recent["시기"] = recent["delivery_date"].dt.strftime("%Y-%m")
    recent["기관"] = recent["agency"]
    recent["방식"] = recent["contract_type"]
    recent["금액"] = recent["contract_amount"].apply(format_amount)

    return recent[
        ["시기", "기관", "방식", "금액"]
    ].reset_index(drop=True)


def get_contract_size_distribution(df):
    """계약금액 구간별 계약건수 비중을 계산한다."""

    if df.empty:
        return []

    bins = [
        0,
        100_000_000,
        500_000_000,
        1_000_000_000,
        5_000_000_000,
        float("inf")
    ]

    labels = [
        "1억 미만",
        "1억 ~ 5억",
        "5억 ~ 10억",
        "10억 ~ 50억",
        "50억 이상"
    ]

    size_group = pd.cut(
        df["contract_amount"],
        bins=bins,
        labels=labels,
        right=False
    )

    counts = (
        size_group
        .value_counts()
        .reindex(labels, fill_value=0)
    )

    total_count = counts.sum()

    if total_count == 0:
        return []

    return [
        (label, round(count / total_count * 100))
        for label, count in counts.items()
    ]


def get_contract_type_share(df):
    """계약 방식별 계약건수 비중을 계산한다."""

    if df.empty:
        return []

    counts = (
        df["contract_type"]
        .value_counts()
    )

    total_count = counts.sum()

    return [
        (contract_type, round(count / total_count * 100))
        for contract_type, count in counts.items()
    ]


def get_supplier_share(df, top_n=4):
    """주요 납품업체의 계약금액 점유율을 계산한다."""

    if df.empty:
        return []

    supplier = (
        df.groupby("supplier_name", as_index=False)["contract_amount"]
        .sum()
        .sort_values("contract_amount", ascending=False)
    )

    total_amount = supplier["contract_amount"].sum()

    top_suppliers = supplier.head(top_n)

    result = [
        (
            row["supplier_name"],
            round(row["contract_amount"] / total_amount * 100)
        )
        for _, row in top_suppliers.iterrows()
    ]

    # TOP N 이외 업체는 '기타'로 합산
    if len(supplier) > top_n:

        other_amount = supplier.iloc[top_n:]["contract_amount"].sum()
        other_share = round(other_amount / total_amount * 100)

        result.append(("기타", other_share))

    return result

def get_market_summary(df):
    """공급업체 관점에서 시장의 최근 변화와 경쟁환경을 요약한다."""

    if df.empty:
        return "조회된 데이터가 없어 시장 흐름을 판단하기 어렵습니다."

    yearly = get_yearly_trend(df)

    # 연도 비교가 불가능한 경우
    if len(yearly) < 2:
        return "비교 가능한 연도 데이터가 부족해 시장 변화 추세를 판단하기 어렵습니다."

    current = yearly.iloc[-1]
    previous = yearly.iloc[-2]

    prev_amount = previous["contract_amount"]
    prev_count = previous["contract_count"]

    amount_change = (
        (current["contract_amount"] - prev_amount)
        / prev_amount * 100
        if prev_amount > 0 else 0
    )

    count_change = (
        (current["contract_count"] - prev_count)
        / prev_count * 100
        if prev_count > 0 else 0
    )

    # 경쟁성 계약 비중
    competitive_types = [
        "일반경쟁",
        "제한경쟁",
        "지명경쟁"
    ]

    competitive_count = df[
        df["contract_type"].isin(competitive_types)
    ].shape[0]

    competitive_share = (
        competitive_count / len(df) * 100
        if len(df) > 0 else 0
    )

    # -------------------------
    # 시장 변화 판단
    # -------------------------

    if amount_change >= 10 and count_change >= 10:
        market_signal = (
            "계약금액과 계약건수가 함께 증가해 "
            "신규 수주 기회가 확대되는 흐름입니다."
        )

    elif amount_change >= 10 and count_change <= -10:
        market_signal = (
            "계약건수는 감소했지만 계약금액은 증가해 "
            "소수의 대형 계약 중심으로 이동하는 흐름입니다."
        )

    elif amount_change <= -10 and count_change >= 10:
        market_signal = (
            "계약건수는 늘었지만 전체 계약금액은 감소해 "
            "소규모 계약 비중이 확대되는 흐름입니다."
        )

    elif amount_change <= -10 and count_change <= -10:
        market_signal = (
            "계약금액과 계약건수가 함께 감소해 "
            "최근 수주 기회가 축소되는 흐름입니다."
        )

    else:
        market_signal = (
            "최근 계약 규모와 건수의 변동이 크지 않아 "
            "비교적 안정적인 수요 흐름을 보이고 있습니다."
        )

    # -------------------------
    # 경쟁환경 추가 해석
    # -------------------------

    if competitive_share >= 70:
        competition_signal = (
            " 경쟁성 계약 비중이 높아 입찰 경쟁력 확보가 중요합니다."
        )

    elif competitive_share <= 30:
        competition_signal = (
            " 수의계약 비중이 상대적으로 높아 기존 거래관계와 "
            "기관별 발주 특성을 함께 확인할 필요가 있습니다."
        )

    else:
        competition_signal = ""

    return market_signal + competition_signal