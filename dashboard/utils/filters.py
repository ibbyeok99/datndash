import pandas as pd


def filter_data(
    df,
    keyword="",
    period="전체",
    agency="전체",
    contract_type="전체"
):
    """검색 조건에 따라 조달 데이터를 필터링한다."""

    filtered_df = df.copy()

    # -------------------------
    # 품목코드 / 품명 검색
    # -------------------------
    if keyword:
        keyword = keyword.strip()

        mask = (
            filtered_df["item_code"]
            .astype(str)
            .str.contains(keyword, case=False, na=False)
            |
            filtered_df["item_name"]
            .astype(str)
            .str.contains(keyword, case=False, na=False)
        )

        filtered_df = filtered_df[mask]

    # -------------------------
    # 조회 기간
    # -------------------------
    if period != "전체":

        years = {
            "최근 1년": 1,
            "최근 3년": 3,
            "최근 5년": 5
        }

        selected_years = years[period]

        latest_date = df["contract_date"].max()
        start_date = latest_date - pd.DateOffset(years=selected_years)

        filtered_df = filtered_df[
            filtered_df["contract_date"] >= start_date
        ]

    # -------------------------
    # 수요기관
    # -------------------------
    if agency != "전체":
        filtered_df = filtered_df[
            filtered_df["agency"] == agency
        ]

    # -------------------------
    # 계약 방식
    # -------------------------
    if contract_type != "전체":
        filtered_df = filtered_df[
            filtered_df["contract_type"] == contract_type
        ]

    return filtered_df