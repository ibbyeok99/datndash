import streamlit as st
import pandas as pd
import base64


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="국방 조달시장 분석",
    layout="wide"
)


# =========================================================
# HEADER IMAGE
# =========================================================

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except (FileNotFoundError, OSError):
        return None


radar_header = get_base64_image("assets/radar_header.png")

if radar_header:
    hero_background = f"""
        background-image:
            url("data:image/png;base64,{radar_header}") !important;
    """
else:
    hero_background = """
        background:
            linear-gradient(
                90deg,
                #EAF5FF 0%,
                #D9EEFF 55%,
                #BBDDFB 100%
            ) !important;
    """


# =========================================================
# CSS
# =========================================================

st.markdown(
    f"""
<style>

/* =========================================================
   COLOR SYSTEM
   ========================================================= */

:root {{
    --page-bg: #F4F9FD;
    --card-bg: #FFFFFF;

    --blue-soft: #E3F2FF;
    --blue-light: #BBDDFB;
    --blue-main: #1E88E5;
    --blue-dark: #1565C0;
    --blue-deep: #0D47A1;

    --text-main: #1F2937;
    --text-sub: #64748B;
    --text-light: #94A3B8;

    --card-border: #D8E1EA;

    --ui-border: #B8D4EA;
    --ui-border-hover: #6FB2EA;
    --ui-border-focus: #1E88E5;
}}


/* =========================================================
   PAGE
   ========================================================= */

html,
body,
.stApp,
[data-testid="stAppViewContainer"] {{
    background-color: var(--page-bg) !important;
}}

[data-testid="stMain"] {{
    background-color: transparent !important;
}}

[data-testid="stHeader"] {{
    background-color: var(--page-bg) !important;
}}

.block-container {{
    max-width: 1250px;

    padding-top: 3rem;
    padding-bottom: 3rem;

    padding-left: 2rem;
    padding-right: 2rem;
}}


/* =========================================================
   HERO HEADER
   ========================================================= */

.st-key-hero_header {{
    {hero_background}

    background-size: cover !important;
    background-position: center center !important;
    background-repeat: no-repeat !important;

    min-height: 120px;

    padding: 18px 24px !important;

    border-radius: 10px;
    overflow: hidden;
}}

.st-key-hero_header [data-testid="stVerticalBlock"],
.st-key-hero_header [data-testid="stHorizontalBlock"],
.st-key-hero_header [data-testid="stColumn"] {{
    background-color: transparent !important;
}}

.st-key-item_title h3 {{
    color: var(--blue-deep) !important;
}}


/* =========================================================
   PDF DOWNLOAD
   ========================================================= */

.st-key-header_pdf {{
    position: fixed !important;

    top: 15px !important;
    right: 120px !important;

    width: 90px !important;

    z-index: 999999 !important;
}}

.st-key-header_pdf button {{
    min-height: 28px !important;
    height: 28px !important;

    padding: 0 10px !important;

    border-radius: 7px !important;
}}

.st-key-header_pdf button p {{
    font-size: 11px !important;
    white-space: nowrap !important;
}}


/* =========================================================
   FIXED HEIGHT CARDS
   ========================================================= */

[data-testid="stLayoutWrapper"][height="100px"][overflow="auto"],
[data-testid="stLayoutWrapper"][height="420px"][overflow="auto"] {{
    background-color: #FFFFFF !important;
}}


/* =========================================================
   AUTO HEIGHT CARDS
   ========================================================= */

.st-key-search_card,
.st-key-market_judgment_card {{
    background-color: #FFFFFF !important;
}}

.st-key-search_card [data-testid="stLayoutWrapper"],
.st-key-market_judgment_card [data-testid="stLayoutWrapper"],
.st-key-search_card [data-testid="stVerticalBlock"],
.st-key-market_judgment_card [data-testid="stVerticalBlock"] {{
    background-color: #FFFFFF !important;
}}


/* =========================================================
   BASIC TEXT
   ========================================================= */

p,
label {{
    color: var(--text-main);
}}

h1,
h2 {{
    color: var(--blue-deep) !important;
    font-weight: 700 !important;
}}

h3,
h4 {{
    color: var(--text-main) !important;
    font-weight: 700 !important;
}}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {{
    color: var(--text-sub) !important;
}}


/* =========================================================
   METRIC GLOBAL
   ========================================================= */

[data-testid="stMetricLabel"] p {{
    color: #475569 !important;

    font-size: 0.76rem !important;
    font-weight: 500 !important;
}}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] p {{
    color: var(--blue-deep) !important;

    font-size: 1.45rem !important;
    font-weight: 700 !important;

    line-height: 1.15 !important;
}}


/* =========================================================
   KPI CARD
   ========================================================= */

.st-key-kpi_contract_value,
.st-key-kpi_contract_count,
.st-key-kpi_avg_contract,
.st-key-kpi_suppliers {{
    position: relative !important;
}}


/* =========================================================
   KPI ICON
   ========================================================= */

.st-key-kpi_contract_value [data-testid="stImage"],
.st-key-kpi_contract_count [data-testid="stImage"],
.st-key-kpi_avg_contract [data-testid="stImage"],
.st-key-kpi_suppliers [data-testid="stImage"] {{
    position: absolute !important;

    left: -2px !important;
    top: 0px !important;

    width: 44px !important;
    height: 44px !important;

    margin: 0 !important;
    padding: 0 !important;

    z-index: 2 !important;
}}


/* 실제 PNG 이미지 */

.st-key-kpi_contract_value [data-testid="stImage"] img,
.st-key-kpi_contract_count [data-testid="stImage"] img,
.st-key-kpi_avg_contract [data-testid="stImage"] img,
.st-key-kpi_suppliers [data-testid="stImage"] img {{
    width: 44px !important;
    height: 44px !important;

    max-width: none !important;

    object-fit: contain !important;
}}


/* =========================================================
   KPI TEXT
   ========================================================= */

.st-key-kpi_contract_value [data-testid="stMetric"],
.st-key-kpi_contract_count [data-testid="stMetric"],
.st-key-kpi_avg_contract [data-testid="stMetric"],
.st-key-kpi_suppliers [data-testid="stMetric"] {{
    position: absolute !important;

    left: 53px !important;
    top: -5px !important;

    width: calc(100% - 57px) !important;

    margin: 0 !important;
    padding: 0 !important;
}}


/* KPI 제목 */

.st-key-kpi_contract_value [data-testid="stMetricLabel"] p,
.st-key-kpi_contract_count [data-testid="stMetricLabel"] p,
.st-key-kpi_avg_contract [data-testid="stMetricLabel"] p,
.st-key-kpi_suppliers [data-testid="stMetricLabel"] p {{
    color: #334155 !important;

    font-size: 0.72rem !important;
    font-weight: 500 !important;

    white-space: nowrap !important;
}}


/* KPI 숫자 */

.st-key-kpi_contract_value [data-testid="stMetricValue"],
.st-key-kpi_contract_count [data-testid="stMetricValue"],
.st-key-kpi_avg_contract [data-testid="stMetricValue"],
.st-key-kpi_suppliers [data-testid="stMetricValue"] {{
    color: #0D47A1 !important;

    font-size: 1.30rem !important;
    font-weight: 700 !important;

    line-height: 1.1 !important;

    letter-spacing: -0.5px !important;

    white-space: nowrap !important;
}}


/* =========================================================
   SUMMARY
   ========================================================= */

/* 한 줄 요약 제목 */

.st-key-summary_card h3 {{
    color: #334155 !important;

    font-size: 1.15rem !important;
    font-weight: 700 !important;
    line-height: 1.4 !important;

    margin: 0 !important;
    padding: 0 !important;
}}


/* 한 줄 요약 본문 */

.st-key-summary_card p {{
    color: #475569 !important;

    font-size: 0.8rem !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;

    margin: 0 !important;
    padding: 0 !important;
}}


/* 한 줄 요약 제목 다음 본문 위치 */

.st-key-summary_card [data-testid="stElementContainer"]:has(h3)
+ [data-testid="stElementContainer"] {{
    margin-top: 5px !important;
}}


/* =========================================================
   NORMAL BUTTON
   ========================================================= */

.stButton > button {{
    background-color: #FFFFFF !important;

    border: 1px solid var(--blue-light) !important;
    border-radius: 8px !important;

    color: var(--blue-dark) !important;

    font-weight: 500 !important;

    box-shadow: none !important;
}}

.stButton > button p {{
    color: var(--blue-dark) !important;
}}

.stButton > button:hover {{
    background-color: #F1F8FE !important;

    border-color: var(--blue-main) !important;

    box-shadow:
        0 1px 4px rgba(30, 136, 229, 0.10) !important;
}}

.stButton > button:hover p {{
    color: var(--blue-dark) !important;
}}


/* =========================================================
   PRIMARY BUTTON
   ========================================================= */

.stButton > button[kind="primary"] {{
    background-color: var(--blue-main) !important;

    border-color: var(--blue-main) !important;

    color: #FFFFFF !important;

    font-weight: 600 !important;

    box-shadow:
        0 2px 5px rgba(30, 136, 229, 0.15) !important;
}}

.stButton > button[kind="primary"] p {{
    color: #FFFFFF !important;
}}

.stButton > button[kind="primary"]:hover {{
    background-color: var(--blue-dark) !important;
    border-color: var(--blue-dark) !important;
}}

.stButton > button[kind="primary"]:hover p {{
    color: #FFFFFF !important;
}}


/* =========================================================
   DOWNLOAD BUTTON
   ========================================================= */

.stDownloadButton > button {{
    background-color: var(--blue-main) !important;

    border: 1px solid var(--blue-main) !important;
    border-radius: 8px !important;

    color: #FFFFFF !important;

    font-weight: 600 !important;
}}

.stDownloadButton > button p {{
    color: #FFFFFF !important;
}}

.stDownloadButton > button:hover {{
    background-color: var(--blue-dark) !important;
    border-color: var(--blue-dark) !important;
}}

.stDownloadButton > button:hover p {{
    color: #FFFFFF !important;
}}


/* =========================================================
   TEXT INPUT
   ========================================================= */

[data-testid="stTextInput"] input {{
    background-color: #FFFFFF !important;

    border: 1px solid var(--ui-border) !important;
    border-radius: 7px !important;

    color: var(--text-main) !important;
}}

[data-testid="stTextInput"] input::placeholder {{
    color: var(--text-light) !important;
}}

[data-testid="stTextInput"] input:hover {{
    border-color: var(--ui-border-hover) !important;
}}

[data-testid="stTextInput"] input:focus {{
    border-color: var(--ui-border-focus) !important;

    box-shadow:
        0 0 0 1px rgba(30, 136, 229, 0.12) !important;
}}

[data-testid="stTextInput"] label p {{
    color: #334155 !important;
    font-weight: 500 !important;
}}


/* =========================================================
   SELECTBOX
   ========================================================= */

[data-testid="stSelectbox"] [role="group"] {{
    background-color: #FFFFFF !important;

    border: 1px solid var(--ui-border) !important;
    border-radius: 7px !important;
}}

[data-testid="stSelectbox"] [role="group"]:hover {{
    border-color: var(--ui-border-hover) !important;
}}

[data-testid="stSelectbox"] [role="group"]:focus-within {{
    border-color: var(--ui-border-focus) !important;

    box-shadow:
        0 0 0 1px rgba(30, 136, 229, 0.12) !important;
}}

[data-testid="stSelectbox"] input {{
    background-color: transparent !important;

    color: var(--text-main) !important;

    font-weight: 500 !important;
}}

[data-testid="stSelectbox"] label p {{
    color: #334155 !important;
    font-weight: 500 !important;
}}

[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;

    border-color: var(--ui-border) !important;

    color: var(--text-main) !important;
}}

[data-baseweb="select"] span {{
    color: var(--text-main) !important;
}}


/* =========================================================
   PROGRESS
   ========================================================= */

[data-testid="stProgressBarTrack"] {{
    background-color: #EDF5FC !important;
}}


/* =========================================================
   DATAFRAME
   ========================================================= */

[data-testid="stDataFrame"] {{
    width: 100% !important;

    background-color: #FFFFFF !important;

    border: none !important;
    border-radius: 0 !important;

    overflow: hidden !important;
}}


/* =========================================================
   INFO
   ========================================================= */

[data-testid="stAlert"] {{
    background-color: #EAF5FF !important;

    border: none !important;
    border-radius: 7px !important;
}}

[data-testid="stAlert"] p {{
    color: #334155 !important;
}}


/* =========================================================
   MOBILE
   ========================================================= */

@media (max-width: 900px) {{

    .block-container {{
        padding-left: 1rem;
        padding-right: 1rem;
    }}

    .st-key-hero_header {{
        min-height: 110px;

        padding: 14px 18px !important;

        background-position: 65% center !important;
    }}

    .st-key-header_pdf {{
        top: 8px !important;
        right: 95px !important;

        width: 100px !important;
    }}
}}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "analysis_page" not in st.session_state:
    st.session_state.analysis_page = "market"

if "search_open" not in st.session_state:
    st.session_state.search_open = True


# =========================================================
# HEADER
# =========================================================

with st.container(key="hero_header"):

    with st.container(key="item_title"):
        st.subheader("레이더 장비")

    st.caption(
        "전자장비 > 탐지장비 > 레이더 > 레이더 장비"
    )


# =========================================================
# PDF DOWNLOAD
# =========================================================

st.download_button(
    "PDF 다운로드",
    data=b"",
    file_name="radar_market_report.pdf",
    use_container_width=False,
    key="header_pdf"
)


# =========================================================
# SEARCH
# =========================================================

if st.session_state.search_open:

    with st.container(
        border=True,
        key="search_card"
    ):

        st.markdown("### 품목 검색")

        search_input_col, search_button_col = st.columns(
            [8, 2],
            gap="medium",
            vertical_alignment="bottom"
        )

        with search_input_col:

            search_keyword = st.text_input(
                "물품코드 / 품명",
                placeholder="물품코드 또는 품명을 입력하세요"
            )

        with search_button_col:

            st.button(
                "검색",
                type="primary",
                use_container_width=True,
                key="search"
            )

        filter_period, filter_agency, filter_contract = st.columns(
            3,
            gap="medium"
        )

        with filter_period:

            period = st.selectbox(
                "조회 기간",
                [
                    "최근 3년",
                    "최근 5년",
                    "최근 10년",
                    "전체"
                ]
            )

        with filter_agency:

            agency = st.selectbox(
                "수요기관",
                [
                    "전체",
                    "국방부",
                    "육군",
                    "해군",
                    "공군"
                ]
            )

        with filter_contract:

            contract_type = st.selectbox(
                "계약 방식",
                [
                    "전체",
                    "일반경쟁",
                    "제한경쟁",
                    "수의계약",
                    "지명경쟁"
                ]
            )


# =========================================================
# SEARCH TOGGLE
# =========================================================

toggle_left, toggle_button, toggle_right = st.columns(
    [5, 0.45, 5]
)

with toggle_button:

    toggle_text = (
        "△"
        if st.session_state.search_open
        else "▽"
    )

    if st.button(
        toggle_text,
        use_container_width=True,
        key="toggle_search"
    ):

        st.session_state.search_open = (
            not st.session_state.search_open
        )

        st.rerun()


# =========================================================
# KPI + SUMMARY
# =========================================================

kpi_area, summary_area = st.columns(
    [2.5, 1],
    gap="medium"
)


# =========================================================
# KPI
# =========================================================

with kpi_area:

    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(
        4,
        gap="small"
    )


    with kpi_1:

        with st.container(
            border=True,
            height=100,
            key="kpi_contract_value"
        ):

            st.image(
                "assets/icon_contract_value.png"
            )

            st.metric(
                "계약금액",
                "1,284억 원"
            )


    with kpi_2:

        with st.container(
            border=True,
            height=100,
            key="kpi_contract_count"
        ):

            st.image(
                "assets/icon_contract_count.png"
            )

            st.metric(
                "계약건수",
                "186건"
            )


    with kpi_3:

        with st.container(
            border=True,
            height=100,
            key="kpi_avg_contract"
        ):

            st.image(
                "assets/icon_avg_contract.png"
            )

            st.metric(
                "평균 계약금액",
                "6.9억 원"
            )


    with kpi_4:

        with st.container(
            border=True,
            height=100,
            key="kpi_suppliers"
        ):

            st.image(
                "assets/icon_suppliers.png"
            )

            st.metric(
                "납품업체 수",
                "42개"
            )


# =========================================================
# SUMMARY
# =========================================================

with summary_area:

    with st.container(
        border=True,
        height=100,
        key="summary_card"
    ):

        st.markdown("### 한 줄 요약")

        st.write(
            "다수 업체가 참여하는 경쟁시장으로 "
            "최근 계약 규모가 증가하고 있습니다."
        )


# =========================================================
# ANALYSIS NAVIGATION
# =========================================================

title_area, nav_area = st.columns(
    [6, 4],
    gap="medium",
    vertical_alignment="center"
)

with title_area:

    if st.session_state.analysis_page == "market":
        st.markdown("## 시장 현황")

    else:
        st.markdown("## 경쟁 분석")


with nav_area:

    market_button, competition_button = st.columns(
        2,
        gap="small"
    )

    with market_button:

        if st.button(
            "시장 현황",
            type=(
                "primary"
                if st.session_state.analysis_page == "market"
                else "secondary"
            ),
            use_container_width=True,
            key="market_button"
        ):

            st.session_state.analysis_page = "market"
            st.rerun()

    with competition_button:

        if st.button(
            "경쟁 분석",
            type=(
                "primary"
                if st.session_state.analysis_page == "competition"
                else "secondary"
            ),
            use_container_width=True,
            key="competition_button"
        ):

            st.session_state.analysis_page = "competition"
            st.rerun()


# =========================================================
# MARKET PAGE
# =========================================================

if st.session_state.analysis_page == "market":

    trend_col, agency_col, history_col = st.columns(
        [1, 1, 1],
        gap="medium"
    )


    with trend_col:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 연도별 계약 추이"
            )

            st.caption(
                "최근 5년 계약금액 및 계약건수"
            )


    with agency_col:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 주요 수요기관"
            )

            st.caption(
                "계약금액 기준"
            )

            agency_data = [
                ("국방부", 38),
                ("육군", 27),
                ("공군", 18),
                ("해군", 12),
                ("기타", 5),
            ]

            for name, value in agency_data:

                label_col, percent_col = st.columns(
                    [4, 1],
                    gap="small"
                )

                with label_col:
                    st.caption(name)

                with percent_col:
                    st.caption(f"{value}%")

                st.progress(value)


    with history_col:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 최근 납품 이력"
            )

            st.caption(
                "최근 계약·납품 기록"
            )

            history_df = pd.DataFrame({
                "시기": [
                    "2025-06",
                    "2024-11",
                    "2024-06",
                    "2023-12",
                    "2023-09"
                ],
                "기관": [
                    "육군",
                    "공군",
                    "해군",
                    "국방부",
                    "육군"
                ],
                "방식": [
                    "경쟁",
                    "수의",
                    "경쟁",
                    "제한",
                    "수의"
                ],
                "금액": [
                    "120억",
                    "95억",
                    "80억",
                    "65억",
                    "58억"
                ]
            })

            st.dataframe(
                history_df,
                width="stretch",
                hide_index=True,
                row_height=36
            )


# =========================================================
# COMPETITION PAGE
# =========================================================

else:

    contract_col, supplier_col = st.columns(
        [1, 1],
        gap="medium"
    )


    with contract_col:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 계약 방식"
            )

            st.caption(
                "계약 방식별 비중"
            )

            contract_data = [
                ("경쟁입찰", 52),
                ("수의계약", 30),
                ("제한경쟁", 15),
                ("기타", 3),
            ]

            for name, value in contract_data:

                label_col, percent_col = st.columns(
                    [4, 1],
                    gap="small"
                )

                with label_col:
                    st.caption(name)

                with percent_col:
                    st.caption(f"{value}%")

                st.progress(value)

            st.caption(
                "주요 계약 방식 · 경쟁입찰 52%"
            )


    with supplier_col:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 주요 납품업체 · 시장집중도"
            )

            st.caption(
                "업체별 계약금액 비중"
            )

            supplier_data = [
                ("A업체", 31),
                ("B업체", 24),
                ("C업체", 18),
                ("D업체", 11),
                ("기타", 16),
            ]

            for name, value in supplier_data:

                label_col, percent_col = st.columns(
                    [4, 1],
                    gap="small"
                )

                with label_col:
                    st.caption(name)

                with percent_col:
                    st.caption(f"{value}%")

                st.progress(value)

            st.caption(
                "시장집중도 · 낮음"
            )


# =========================================================
# MARKET JUDGMENT
# =========================================================

with st.container(
    border=True,
    key="market_judgment_card"
):

    st.markdown(
        "### 업체 관점 시장 판단"
    )

    judgment_1, judgment_2, judgment_3, judgment_4 = st.columns(
        4,
        gap="medium"
    )

    with judgment_1:

        st.metric(
            "경쟁 강도",
            "높음"
        )

    with judgment_2:

        st.metric(
            "시장 집중도",
            "낮음"
        )

    with judgment_3:

        st.metric(
            "계약 추세",
            "증가"
        )

    with judgment_4:

        st.metric(
            "주요 계약 방식",
            "경쟁입찰"
        )

    st.info(
        "다수 업체가 참여하고 시장 집중도가 낮은 편이며, "
        "최근 계약 규모가 증가하고 있어 신규 업체의 "
        "시장 진입 가능성을 검토할 수 있습니다."
    )