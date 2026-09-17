import streamlit as st
import pandas as pd
import altair as alt
import base64
import random
from pathlib import Path

from utils.data_loader import load_data
from utils.filters import filter_data
from utils.analysis import (calculate_kpis,
                            format_amount,
                            get_monthly_trend,
                            get_agency_share,
                            get_recent_history,
                            get_contract_size_distribution,
                            get_contract_type_share,
                            get_supplier_share,
                            get_market_summary)


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"


def get_judgment_icon(value):
    icon_map = {
        # 상태
        "높음": ASSETS_DIR / "icon_level_high.png",
        "낮음": ASSETS_DIR / "icon_level_low.png",
        "증가": ASSETS_DIR / "icon_trend_up.png",
        "감소": ASSETS_DIR / "icon_trend_down.png",

        # 계약 방식
        "일반경쟁": ASSETS_DIR / "icon_contract_open.png",
        "제한경쟁": ASSETS_DIR / "icon_contract_restricted.png",
        "수의계약": ASSETS_DIR / "icon_contract_private.png",
        "지명경쟁": ASSETS_DIR / "icon_contract_nominated.png",
    }

    return icon_map.get(value)

# =========================================================
# MOCK NOTICE DATA
# TODO: 실제 크롤링 구현 후 제거
# =========================================================

MOCK_NOTICES = [
    {
        "notice_id": "notice_001",
        "d_day": "D-12",
        "title": "레이더 장비 구매",
        "notice_no": "20260916-001",
        "agency": "방위사업청",
        "contract_type": "일반경쟁",
        "start_date": "2026.09.12",
        "end_date": "2026.09.28",
        "amount": "12.4억 원",
        "summary": (
            "레이더 장비 구매를 위한 일반경쟁 공고입니다. "
            "납품 일정과 규격 요건을 확인한 뒤 참여 여부를 검토할 수 있습니다."
        ),
    },
    {
        "notice_id": "notice_002",
        "d_day": "D-18",
        "title": "레이더 체계 구성품 구매",
        "notice_no": "20260916-002",
        "agency": "공군",
        "contract_type": "제한경쟁",
        "start_date": "2026.09.10",
        "end_date": "2026.10.04",
        "amount": "7.8억 원",
        "summary": (
            "레이더 체계 구성품 조달을 위한 제한경쟁 공고입니다. "
            "참가자격과 납품 규격 확인이 필요한 예시 공고입니다."
        ),
    },
    {
        "notice_id": "notice_003",
        "d_day": "D-7",
        "title": "감시 레이더 부품 조달",
        "notice_no": "20260916-003",
        "agency": "육군",
        "contract_type": "지명경쟁",
        "start_date": "2026.09.14",
        "end_date": "2026.09.23",
        "amount": "3.2억 원",
        "summary": (
            "감시 레이더 유지·운용에 필요한 부품 조달 예시 공고입니다. "
            "실제 크롤링 구현 후 원문 공고 데이터로 교체할 예정입니다."
        ),
    },
]


@st.dialog("공고 상세", width="large")
def show_notice_detail(notice):
    st.subheader(notice["title"])
    st.caption(f'공고번호 · {notice["notice_no"]}')

    detail_1, detail_2 = st.columns(2)

    with detail_1:
        st.markdown(f'**수요기관**  \n{notice["agency"]}')
        st.markdown(f'**계약방식**  \n{notice["contract_type"]}')

    with detail_2:
        st.markdown(
            f'**공고기간**  \n'
            f'{notice["start_date"]} ~ {notice["end_date"]}'
        )
        st.markdown(f'**추정금액**  \n{notice["amount"]}')

    st.divider()
    st.markdown("#### 공고 요약")
    st.write(notice["summary"])


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="국방 조달시장 분석",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 시장 현황 2개 + 경쟁 분석 2개 카드 공통 높이
ANALYSIS_CARD_HEIGHT = 430



df = load_data()

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
[data-testid="stLayoutWrapper"][height="{ANALYSIS_CARD_HEIGHT}px"][overflow="auto"],
[data-testid="stLayoutWrapper"][height="480px"][overflow="auto"],
[data-testid="stLayoutWrapper"][height="500px"][overflow="auto"] {{
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


.st-key-market_judgment_card [data-testid="stImage"] {{
    width: 46px !important;
    min-width: 46px !important;
}}

.st-key-market_judgment_card [data-testid="stImage"] img {{
    width: 46px !important;
    height: 46px !important;
    object-fit: contain !important;
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

    left: 5px !important;
    top: 0px !important;

    width: 55px !important;
    height: 55px !important;

    margin: 0 !important;
    padding: 0 !important;

    z-index: 2 !important;
}}


/* 실제 PNG 이미지 */

.st-key-kpi_contract_value [data-testid="stImage"] img,
.st-key-kpi_contract_count [data-testid="stImage"] img,
.st-key-kpi_avg_contract [data-testid="stImage"] img,
.st-key-kpi_suppliers [data-testid="stImage"] img {{
    width: 55px !important;
    height: 55px !important;

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

    left: 80px !important;
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

    font-size: 0.88rem !important;
    font-weight: 600 !important;

    white-space: nowrap !important;
}}


/* KPI 숫자 */

.st-key-kpi_contract_value [data-testid="stMetricValue"],
.st-key-kpi_contract_count [data-testid="stMetricValue"],
.st-key-kpi_avg_contract [data-testid="stMetricValue"],
.st-key-kpi_suppliers [data-testid="stMetricValue"] {{
    color: #0D47A1 !important;

    font-size: 1.65rem !important;
    font-weight: 700 !important;

    line-height: 1.1 !important;

    letter-spacing: -0.5px !important;

    white-space: nowrap !important;
}}


/* =========================================================
   SUMMARY
   ========================================================= */

.st-key-summary_card {{
    background: #EAF5FE !important;
    border: 1px solid #D5EAFB !important;
    border-radius: 10px !important;
    min-height: 83px !important;
    height: auto !important;
    padding: 14px 18px !important;
    margin-top: 8px !important;
    margin-bottom: 14px !important;
    overflow: visible !important;
    box-sizing: border-box !important;
}}

.st-key-summary_card [data-testid="stVerticalBlock"],
.st-key-summary_card [data-testid="stLayoutWrapper"] {{
    height: auto !important;
    min-height: fit-content !important;
    max-height: none !important;
    overflow: visible !important;
    background: transparent !important;
}}

.st-key-summary_card h3 {{
    color: #334155 !important;
    font-size: 0.86rem !important;
    font-weight: 700 !important;
    line-height: 1.35 !important;
    margin: 0 !important;
    padding: 0 !important;
}}

.st-key-summary_card p {{
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;
    margin: 0 !important;
    padding: 0 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: keep-all !important;
}}

.st-key-summary_card [data-testid="stElementContainer"]:has(h3)
+ [data-testid="stElementContainer"] {{
    margin-top: 3px !important;
}}


.st-key-summary_card [data-testid="stImage"] {{
    width: 42px !important;
    min-width: 42px !important;
}}

.st-key-summary_card [data-testid="stImage"] img {{
    width: 42px !important;
    height: 42px !important;
    object-fit: contain !important;
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
   DATE INPUT
   ========================================================= */

/* 위젯 전체 */
[data-testid="stDateInput"] {{
    width: 100% !important;
}}

/* Streamlit/BaseWeb 버전별 입력 박스 후보를 모두 커버 */
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="base-input"],
[data-testid="stDateInput"] [role="group"],
[data-testid="stDateInput"] div:has(> input[type="text"]) {{
    background-color: #FFFFFF !important;
    border: 1px solid var(--ui-border) !important;
    border-radius: 7px !important;
    min-height: 42px !important;
    box-shadow: none !important;
}}

/* 내부 입력 필드 */
[data-testid="stDateInput"] input {{
    color: #334155 !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
    min-height: 40px !important;
    background: transparent !important;
}}

/* YYYY / MM / DD 구분자 등 */
[data-testid="stDateInput"] span {{
    color: #475569 !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
}}

/* hover */
[data-testid="stDateInput"] [data-baseweb="input"]:hover,
[data-testid="stDateInput"] [data-baseweb="base-input"]:hover,
[data-testid="stDateInput"] [role="group"]:hover {{
    border-color: var(--ui-border-hover) !important;
}}

/* focus */
[data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
[data-testid="stDateInput"] [data-baseweb="base-input"]:focus-within,
[data-testid="stDateInput"] [role="group"]:focus-within {{
    border-color: var(--ui-border-focus) !important;
    box-shadow: 0 0 0 1px rgba(30, 136, 229, 0.12) !important;
}}

/* 라벨 */
[data-testid="stDateInput"] label p {{
    color: #334155 !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
}}

/* 달력 버튼/아이콘 */
[data-testid="stDateInput"] button {{
    color: var(--blue-dark) !important;
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

/* 주요 수요기관 - 기관별 항목 세로 간격 축소 */
[data-testid="stProgress"] {{
    margin-top: -8px !important;
    margin-bottom: -10px !important;
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
   SIDEBAR SEARCH
   ========================================================= */

[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid var(--card-border) !important;
}}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    background-color: #FFFFFF !important;
    padding-top: 1.25rem !important;
}}

[data-testid="stSidebar"] h2 {{
    color: var(--blue-deep) !important;
    font-size: 1.35rem !important;
    margin-bottom: 0.15rem !important;
}}

[data-testid="stSidebar"] h3 {{
    color: #334155 !important;
    font-size: 1rem !important;
}}

[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
    color: #334155 !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    color: var(--text-sub) !important;
    font-size: 0.78rem !important;
}}

[data-testid="stSidebar"] .stButton > button {{
    min-height: 42px !important;
    font-size: 0.95rem !important;
}}

[data-testid="stSidebar"] hr {{
    margin-top: 1.25rem !important;
    margin-bottom: 1.1rem !important;
    border-color: #E2E8F0 !important;
}}

/* 현재 조회 조건 */
.st-key-current_search_info h3 {{
    text-align: left !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: #334155 !important;
    margin-bottom: 0.35rem !important;
}}

.st-key-current_search_info [data-testid="stHorizontalBlock"] {{
    gap: 0.5rem !important;
}}

.st-key-current_search_info [data-testid="column"]:first-child p {{
    text-align: left !important;
    color: #94A3B8 !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
}}

.st-key-current_search_info [data-testid="column"]:last-child p {{
    text-align: right !important;
    color: #334155 !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
}}

.st-key-current_search_info [data-testid="stVerticalBlock"] {{
    gap: 0.28rem !important;
}}


/* 분석 기간: 라벨과 버튼을 같은 줄에 배치하므로 별도 이동 없음 */

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



/* 진행 공고 / 시장 현황 / 경쟁 분석 탭 글씨 크기 */
div[data-testid="stTab"] div[data-testid="stMarkdownContainer"] p {{
    font-size: 18px !important;
    font-weight: 600 !important;
}}
</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE

# =========================================================

if "analysis_page" not in st.session_state:
    st.session_state.analysis_page = "notice"


if "search_filters" not in st.session_state:
    st.session_state.search_filters = {
        "keyword": "",
        "notice_date": pd.Timestamp.today().date(),
        "agency": "전체",
        "contract_type": "전체"
    }

valid_analysis_periods = ["최근 1년", "최근 3년", "최근 5년", "전체"]

if (
    "analysis_period" not in st.session_state
    or st.session_state.analysis_period not in valid_analysis_periods
):
    st.session_state.analysis_period = "최근 3년"

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
# SIDEBAR SEARCH
# =========================================================

with st.sidebar:

    st.markdown("## 조회 조건")
    st.caption("조회할 품목과 조건을 설정하세요.")

    search_keyword = st.text_input(
        "물품코드 / 품명",
        value=st.session_state.search_filters["keyword"],
        placeholder="물품코드 또는 품명을 입력하세요"
    )


    agency_options = [
        "전체",
        "국방부",
        "육군",
        "해군",
        "공군"
    ]

    contract_type_options = [
        "전체",
        "일반경쟁",
        "제한경쟁",
        "수의계약",
        "지명경쟁"
    ]

    current_agency = st.session_state.search_filters["agency"]
    current_contract_type = st.session_state.search_filters["contract_type"]

    notice_date = st.date_input(
        "공고 기준일",
        value=st.session_state.search_filters["notice_date"],
        help="선택한 날짜에 진행 중인 공고를 조회합니다."
    )

    agency = st.selectbox(
        "수요기관",
        agency_options,
        index=agency_options.index(current_agency)
        if current_agency in agency_options else 0
    )

    contract_type = st.selectbox(
        "계약 방식",
        contract_type_options,
        index=contract_type_options.index(current_contract_type)
        if current_contract_type in contract_type_options else 0
    )

    search_clicked = st.button(
        "검색",
        type="primary",
        use_container_width=True,
        key="search"
    )

    if search_clicked:
        st.session_state.search_filters = {
            "keyword": search_keyword,
            "notice_date": notice_date,
            "agency": agency,
            "contract_type": contract_type
        }
        st.rerun()

    st.divider()

    with st.container(key="current_search_info"):

        st.markdown("### 현재 조회 조건")

        applied_filters = st.session_state.search_filters

        current_keyword_text = (
            applied_filters["keyword"]
            if applied_filters["keyword"]
            else "전체 품목"
        )

        label_col, value_col = st.columns([1, 2])

        with label_col:
            st.markdown("품목")
            st.markdown("기준일")
            st.markdown("기관")
            st.markdown("방식")

        with value_col:
            st.markdown(f"**{current_keyword_text}**")
            st.markdown(f'**{applied_filters["notice_date"].strftime("%Y.%m.%d")}**')
            st.markdown(f'**{applied_filters["agency"]}**')
            st.markdown(f'**{applied_filters["contract_type"]}**')

filters = st.session_state.search_filters

filtered_df = filter_data(
    df,
    keyword=filters["keyword"],
    period="전체",
    agency=filters["agency"],
    contract_type=filters["contract_type"]
)

analysis_df = filter_data(
    df,
    keyword=filters["keyword"],
    period=st.session_state.analysis_period,
    agency=filters["agency"],
    contract_type=filters["contract_type"]
)

kpis = calculate_kpis(analysis_df)

# 월별 계약 추이
monthly_trend = get_monthly_trend(analysis_df)

agency_data = get_agency_share(analysis_df)
contract_size_data = get_contract_size_distribution(analysis_df)
history_df = get_recent_history(analysis_df)
contract_type_data = get_contract_type_share(analysis_df)
supplier_data = get_supplier_share(analysis_df)
market_summary = get_market_summary(analysis_df)

# =========================================================
# KPI
# =========================================================

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
            format_amount(kpis["total_amount"])
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
            f'{kpis["contract_count"]:,}건'
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
            format_amount(kpis["avg_amount"])
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
            f'{kpis["supplier_count"]:,}개'
        )



# =========================================================
# SUMMARY
# =========================================================

with st.container(
    border=False,
    key="summary_card"
):
    summary_icon, summary_text = st.columns(
        [0.45, 9.55],
        gap="small",
        vertical_alignment="center"
    )

    with summary_icon:
        st.image("assets/icon_summary.png")

    with summary_text:
        st.markdown("### 한 줄 요약")
        st.write(market_summary)


# =========================================================
# ANALYSIS NAVIGATION
# =========================================================

st.markdown("## 조달 분석")

notice_tab, market_tab, competition_tab = st.tabs(
    ["진행 공고", "시장 현황", "경쟁 분석"]
)

# =========================================================
# NOTICE PAGE
# =========================================================

with notice_tab:

    selected_notice_date = filters["notice_date"]

    st.caption(
        f'{selected_notice_date.strftime("%Y.%m.%d")} 기준으로 '
        "현재 검색 품목과 관련된 진행 중 조달 공고를 표시합니다. "
        "현재는 화면 구성을 위한 예시 데이터입니다."
    )

    active_notices = []
    for notice in MOCK_NOTICES:
        start_date = pd.to_datetime(notice["start_date"]).date()
        end_date = pd.to_datetime(notice["end_date"]).date()

        if start_date <= selected_notice_date <= end_date:
            active_notices.append(notice)

    st.markdown(f"### 관련 진행 공고 {len(active_notices)}건")

    if not active_notices:
        st.info("선택한 공고 기준일에 진행 중인 예시 공고가 없습니다.")

    for i, notice in enumerate(active_notices):
        with st.container(border=True, key=f"notice_card_{i}"):

            info_col, button_col = st.columns(
                [8.5, 1.5],
                gap="medium",
                vertical_alignment="center"
            )

            with info_col:
                st.caption(
                    f'{notice["d_day"]} · {notice["agency"]} · '
                    f'{notice["contract_type"]}'
                )
                st.markdown(f'### {notice["title"]}')
                st.caption(
                    f'공고기간 {notice["start_date"]} ~ {notice["end_date"]} '
                    f'· 추정금액 {notice["amount"]}'
                )

            with button_col:
                if st.button(
                    "상세보기",
                    key=f'notice_detail_{notice["notice_id"]}',
                    use_container_width=True
                ):
                    show_notice_detail(notice)

    st.info(
        "공고 요약 · 현재는 예시 공고를 표시하고 있습니다. "
        "추후 크롤링 결과를 연결하면 검색 품목과 관련된 진행 공고와 "
        "핵심 요약 정보가 이 영역에 자동으로 표시됩니다."
    )


# =========================================================
# MARKET PAGE
# =========================================================

with market_tab:

    period_label_col, period_button_col = st.columns(
        [0.6, 8.4],
        gap="small",
        vertical_alignment="center"
    )

    with period_label_col:
        st.markdown("**분석 기간**")

    with period_button_col:
        st.segmented_control(
            "분석 기간",
            options=valid_analysis_periods,
            key="analysis_period",
            label_visibility="collapsed"
        )

    trend_col, agency_col = st.columns(
        [1, 1],
        gap="medium"
    )

    with trend_col:
        with st.container(
            border=True,
            height=ANALYSIS_CARD_HEIGHT
        ):
            st.markdown("### 월별 계약 추이")
            st.caption(
                f"{st.session_state.analysis_period} 월별 계약금액"
            )

            if monthly_trend.empty:
                st.info("조회된 계약 데이터가 없습니다.")
            else:
                chart_df = monthly_trend.copy()
                chart_df["계약금액(억원)"] = (
                    chart_df["contract_amount"] / 100_000_000
                )
                chart_df["계약금액 표시"] = (
                    chart_df["계약금액(억원)"]
                    .map(lambda x: f"{x:,.1f}억 원")
                )

                chart = (
                    alt.Chart(chart_df)
                    .mark_line()
                    .encode(
                        x=alt.X(
                            "month:T",
                            title=None,
                            axis=alt.Axis(
                                format="%y.%m",
                                labelAngle=0,
                                tickCount=8
                            )
                        ),
                        y=alt.Y(
                            "계약금액(억원):Q",
                            title=None
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "month:T",
                                title="계약 월",
                                format="%Y년 %m월"
                            ),
                            alt.Tooltip(
                                "계약금액 표시:N",
                                title="계약금액"
                            )
                        ]
                    )
                    .properties(height=270)
                )

                st.altair_chart(
                    chart,
                    width="stretch",
                    key="monthly_contract_trend_chart"
                )

    with agency_col:
        with st.container(
            border=True,
            height=ANALYSIS_CARD_HEIGHT
        ):
            if filters["agency"] == "전체":
                st.markdown("### 주요 수요기관")
                st.caption("계약금액 기준")

                if not agency_data:
                    st.info("조회된 데이터가 없습니다.")
                else:
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
            else:
                st.markdown("### 계약 규모 분포")
                st.caption(
                    f'{filters["agency"]} · 계약건수 기준'
                )

                if not contract_size_data:
                    st.info("조회된 데이터가 없습니다.")
                else:
                    for name, value in contract_size_data:
                        label_col, percent_col = st.columns(
                            [4, 1],
                            gap="small"
                        )
                        with label_col:
                            st.caption(name)
                        with percent_col:
                            st.caption(f"{value}%")
                        st.progress(value)

    with st.container(
        border=True,
        height=500
    ):
        st.markdown("### 최근 납품 이력")
        st.caption("최근 계약·납품 기록")
        st.dataframe(
            history_df,
            width="stretch",
            hide_index=True,
            row_height=36,
            height=390
        )


# =========================================================
# COMPETITION PAGE
# =========================================================

with competition_tab:

    period_label_col, period_button_col = st.columns(
        [0.6, 8.4],
        gap="small",
        vertical_alignment="center"
    )

    with period_label_col:
        st.markdown("**분석 기간**")

    with period_button_col:
        competition_period = st.segmented_control(
            "분석 기간",
            options=valid_analysis_periods,
            default="최근 3년",
            key="competition_analysis_period",
            label_visibility="collapsed"
        )
    contract_col, supplier_col = st.columns(
        [1, 1],
        gap="medium"
    )

    with contract_col:
        with st.container(
            border=True,
            height=ANALYSIS_CARD_HEIGHT
        ):
            st.markdown("### 계약 방식")
            st.caption("계약 방식별 비중")

            for name, value in contract_type_data:
                label_col, percent_col = st.columns(
                    [4, 1],
                    gap="small"
                )

                with label_col:
                    st.caption(name)

                with percent_col:
                    st.caption(f"{value}%")

                st.progress(value)

            st.caption("주요 계약 방식 · 경쟁입찰 52%")

    with supplier_col:
        with st.container(
            border=True,
            height=ANALYSIS_CARD_HEIGHT
        ):
            st.markdown("### 주요 납품업체 · 시장집중도")
            st.caption("업체별 계약금액 비중")

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

            st.caption("시장집중도 · 낮음")


# =========================================================
# MARKET JUDGMENT
# =========================================================

# TODO: 실제 분석 로직 연결 후 랜덤 테스트 코드 삭제
competition_level = random.choice(["높음", "낮음"])
market_concentration = random.choice(["높음", "낮음"])
contract_trend = random.choice(["증가", "감소"])

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
        value = competition_level
        icon = get_judgment_icon(value)

        icon_col, metric_col = st.columns(
            [1, 3],
            gap="small",
            vertical_alignment="center"
        )

        with icon_col:
            if icon:
                st.image(icon)

        with metric_col:
            st.metric(
                "경쟁 강도",
                value
            )

    with judgment_2:
        value = market_concentration
        icon = get_judgment_icon(value)

        icon_col, metric_col = st.columns(
            [1, 3],
            gap="small",
            vertical_alignment="center"
        )

        with icon_col:
            if icon:
                st.image(icon)

        with metric_col:
            st.metric(
                "시장 집중도",
                value
            )

    with judgment_3:
        value = contract_trend
        icon = get_judgment_icon(value)

        icon_col, metric_col = st.columns(
            [1, 3],
            gap="small",
            vertical_alignment="center"
        )

        with icon_col:
            if icon:
                st.image(icon)

        with metric_col:
            st.metric(
                "계약 추세",
                value
            )

    with judgment_4:
        contract_method = random.choice([
            "일반경쟁",
            "제한경쟁",
            "수의계약",
            "지명경쟁"
        ])

        icon = get_judgment_icon(contract_method)

        icon_col, metric_col = st.columns(
            [1, 3],
            gap="small",
            vertical_alignment="center"
        )

        with icon_col:
            if icon:
                st.image(icon)

        with metric_col:
            st.metric(
                "주요 계약 방식",
                contract_method
            )

    st.info(
        "현재 아이콘 전환 확인을 위해 경쟁 강도·시장 집중도·계약 추세를 "
        "임시 랜덤값으로 표시하고 있습니다."
    )
