import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="국방 조달시장 분석",
    layout="wide"
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

/* ---------------------------------------------------------
   전체 페이지 너비
--------------------------------------------------------- */

.block-container {
    max-width: 1250px;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 3rem;
}


/* ---------------------------------------------------------
   컨테이너
--------------------------------------------------------- */

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px;
}


/* ---------------------------------------------------------
   Metric
--------------------------------------------------------- */

[data-testid="stMetricValue"] {
    font-size: 1.8rem;
}


/* ---------------------------------------------------------
   버튼
--------------------------------------------------------- */

.stButton > button {
    border-radius: 8px;
    transition:
        background-color 0.2s ease,
        border-color 0.2s ease,
        transform 0.15s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
}


/* ---------------------------------------------------------
   분석 화면 등장 애니메이션
--------------------------------------------------------- */

@keyframes dashboardFadeIn {

    0% {
        opacity: 0;
        transform: translateY(6px);
    }

    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

.analysis-transition {
    animation: dashboardFadeIn 0.25s ease-out;
}


/* 모션 감소 설정 사용자 */
@media (prefers-reduced-motion: reduce) {

    .analysis-transition {
        animation: none;
    }

    .stButton > button {
        transition: none;
    }
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "analysis_page" not in st.session_state:
    st.session_state.analysis_page = 1


# ============================================================
# ① HEADER
# ============================================================

with st.container():

    header_left, header_right = st.columns(
        [8, 2],
        vertical_alignment="center"
    )

    with header_left:

        st.subheader("레이더 장비")

        st.caption(
            "전자장비 > 탐지장비 > 레이더 > 레이더 장비"
        )

    with header_right:

        st.download_button(
            "PDF 다운로드",
            data=b"",
            file_name="report.pdf",
            use_container_width=True
        )


# ============================================================
# ② 검색 영역
# ============================================================

with st.container(border=True):

    st.markdown("### 품목 검색")

    search_col, button_col = st.columns(
        [8, 2],
        gap="medium",
        vertical_alignment="bottom"
    )

    with search_col:

        search_keyword = st.text_input(
            "물품코드 / 품명",
            placeholder="물품코드 또는 품명을 입력하세요"
        )

    with button_col:

        search_button = st.button(
            "검색",
            use_container_width=True
        )


    # --------------------------------------------------------
    # 필터
    # --------------------------------------------------------

    filter1, filter2, filter3 = st.columns(
        [1, 1, 1],
        gap="medium"
    )

    with filter1:

        period = st.selectbox(
            "조회 기간",
            [
                "최근 3년",
                "최근 5년",
                "최근 10년",
                "전체"
            ]
        )

    with filter2:

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

    with filter3:

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


# ============================================================
# ③ KPI + 한 줄 요약
# ============================================================

kpi_area, summary_area = st.columns(
    [2, 1],
    gap="medium"
)


# ------------------------------------------------------------
# KPI
# ------------------------------------------------------------

with kpi_area:

    with st.container(
        border=True,
        height=155
    ):

        # KPI가 세로 중앙에 가깝게 위치하도록 여백
        st.markdown(
            "<div style='height:18px'></div>",
            unsafe_allow_html=True
        )

        k1, k2, k3, k4 = st.columns(
            [1, 1, 1, 1],
            vertical_alignment="center"
        )

        with k1:

            st.metric(
                "계약금액",
                "1,284억 원"
            )

        with k2:

            st.metric(
                "계약건수",
                "186건"
            )

        with k3:

            st.metric(
                "평균 계약금액",
                "6.9억 원"
            )

        with k4:

            st.metric(
                "납품업체 수",
                "42개"
            )


# ------------------------------------------------------------
# 한 줄 요약
# ------------------------------------------------------------

with summary_area:

    with st.container(
        border=True,
        height=155
    ):

        # 내용이 적으므로 중앙에 가깝게 배치
        st.markdown(
            "<div style='height:13px'></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "#### 한 줄 요약"
        )

        st.write(
            "다수 업체가 참여하는 경쟁시장으로 "
            "최근 계약 규모가 증가하고 있습니다."
        )


# ============================================================
# ④ 분석 영역 제목 + 페이지 전환
# ============================================================

analysis_title, page_buttons = st.columns(
    [6, 4],
    gap="medium",
    vertical_alignment="center"
)


# ------------------------------------------------------------
# 현재 페이지 제목
# ------------------------------------------------------------

with analysis_title:

    if st.session_state.analysis_page == 1:

        st.markdown(
            "## 시장 현황"
        )

    else:

        st.markdown(
            "## 경쟁 분석"
        )


# ------------------------------------------------------------
# 페이지 전환 버튼
# ------------------------------------------------------------

with page_buttons:

    page1, page2 = st.columns(
        [1, 1],
        gap="small"
    )

    with page1:

        if st.button(
            "시장 현황",
            type=(
                "primary"
                if st.session_state.analysis_page == 1
                else "secondary"
            ),
            use_container_width=True,
            key="market_page_button"
        ):

            st.session_state.analysis_page = 1
            st.rerun()

    with page2:

        if st.button(
            "경쟁 분석",
            type=(
                "primary"
                if st.session_state.analysis_page == 2
                else "secondary"
            ),
            use_container_width=True,
            key="competition_page_button"
        ):

            st.session_state.analysis_page = 2
            st.rerun()


# ============================================================
#
# PAGE 1
#
# 시장 현황
#
# ============================================================

if st.session_state.analysis_page == 1:

    # 화면 전환 효과용
    st.markdown(
        '<div class="analysis-transition"></div>',
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # 3단 구성
    # --------------------------------------------------------

    trend_area, agency_area, history_area = st.columns(
        [1, 1, 1],
        gap="medium"
    )


    # ========================================================
    # 연도별 계약 추이
    # ========================================================

    with trend_area:

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


            # ------------------------------------------------
            # 실제 그래프 위치
            # ------------------------------------------------

            st.info(
                "연도별 계약금액 / 계약건수 그래프"
            )


            # 실제 Plotly 그래프 연결 예시
            #
            # st.plotly_chart(
            #     fig_trend,
            #     use_container_width=True
            # )


    # ========================================================
    # 주요 수요기관
    # ========================================================

    with agency_area:

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


            st.write(
                "**국방부 · 38%**"
            )

            st.progress(38)


            st.write(
                "**육군 · 27%**"
            )

            st.progress(27)


            st.write(
                "**공군 · 18%**"
            )

            st.progress(18)


            st.write(
                "**해군 · 12%**"
            )

            st.progress(12)


            st.write(
                "**기타 · 5%**"
            )

            st.progress(5)


    # ========================================================
    # 최근 납품 이력
    # ========================================================

    with history_area:

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


            st.markdown("""
| 날짜 | 기관 | 방식 | 금액 |
|---|---|---|---:|
| 2025-06 | 육군 | 경쟁 | 120억 |
| 2024-11 | 공군 | 수의 | 95억 |
| 2024-06 | 해군 | 경쟁 | 80억 |
| 2023-12 | 국방부 | 제한 | 65억 |
| 2023-09 | 육군 | 수의 | 58억 |
""")


            # 실제 DataFrame 연결 예시
            #
            # st.dataframe(
            #     history_df,
            #     use_container_width=True,
            #     hide_index=True,
            #     height=280
            # )


# ============================================================
#
# PAGE 2
#
# 경쟁 분석
#
# ============================================================

elif st.session_state.analysis_page == 2:

    # 화면 전환 효과용
    st.markdown(
        '<div class="analysis-transition"></div>',
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # 2단 구성
    # --------------------------------------------------------

    contract_area, supplier_area = st.columns(
        [1, 1],
        gap="medium"
    )


    # ========================================================
    # 계약 방식
    # ========================================================

    with contract_area:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 계약 방식"
            )

            st.caption(
                "해당 품목의 과거 계약방식 비중"
            )


            # ------------------------------------------------
            # 경쟁입찰
            # ------------------------------------------------

            st.write(
                "**경쟁입찰 · 52%**"
            )

            st.progress(52)


            # ------------------------------------------------
            # 수의계약
            # ------------------------------------------------

            st.write(
                "**수의계약 · 30%**"
            )

            st.progress(30)


            # ------------------------------------------------
            # 제한경쟁
            # ------------------------------------------------

            st.write(
                "**제한경쟁 · 15%**"
            )

            st.progress(15)


            # ------------------------------------------------
            # 기타
            # ------------------------------------------------

            st.write(
                "**기타 · 3%**"
            )

            st.progress(3)


            st.divider()


            st.markdown(
                "**주요 계약 방식: 경쟁입찰**"
            )

            st.caption(
                "과거 계약 건수를 기준으로 계산"
            )


    # ========================================================
    # 주요 납품업체 / 시장집중도
    # ========================================================

    with supplier_area:

        with st.container(
            border=True,
            height=420
        ):

            st.markdown(
                "### 주요 납품업체 · 시장집중도"
            )

            st.caption(
                "계약금액 기준 업체별 시장 점유율"
            )


            # ------------------------------------------------
            # 업체별 점유율
            # ------------------------------------------------

            st.write(
                "**A업체 · 31%**"
            )

            st.progress(31)


            st.write(
                "**B업체 · 24%**"
            )

            st.progress(24)


            st.write(
                "**C업체 · 18%**"
            )

            st.progress(18)


            st.write(
                "**D업체 · 11%**"
            )

            st.progress(11)


            st.write(
                "**기타 · 16%**"
            )

            st.progress(16)


# ============================================================
# ⑤ 업체 관점 시장 판단
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 업체 관점 시장 판단"
    )


    decision1, decision2, decision3, decision4 = st.columns(
        [1, 1, 1, 1]
    )


    # --------------------------------------------------------
    # 경쟁 강도
    # --------------------------------------------------------

    with decision1:

        st.metric(
            "경쟁 강도",
            "높음"
        )


    # --------------------------------------------------------
    # 시장 집중도
    # --------------------------------------------------------

    with decision2:

        st.metric(
            "시장 집중도",
            "낮음"
        )


    # --------------------------------------------------------
    # 계약 추세
    # --------------------------------------------------------

    with decision3:

        st.metric(
            "계약 추세",
            "증가"
        )


    # --------------------------------------------------------
    # 주요 계약 방식
    # --------------------------------------------------------

    with decision4:

        st.metric(
            "주요 계약 방식",
            "경쟁입찰"
        )


    # --------------------------------------------------------
    # 최종 요약
    # --------------------------------------------------------

    st.info(
        "다수 업체가 참여하고 있으며 특정 업체에 계약이 "
        "과도하게 집중되지 않은 시장입니다. "
        "최근 계약 규모도 증가하고 있어 신규 업체의 "
        "시장 진입을 검토할 수 있습니다."
    )