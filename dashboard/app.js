/* ========================================================================
   국방조달 절차 위험 스크리닝 대시보드 — app.js
   데이터: dashboard/data/dashboard_data.json (dashboard/build_data.py로 생성)

   데이터 소스 2종:
   1) 신규 운영 데이터셋(dashboard_*.csv 4종) — 화면 1~5의 주 소스. 아직 파일이 없으면
      {available:false}로 내려오며, 해당 영역은 "데이터 없음" 빈 상태로 표시한다.
      절대 다른 데이터로 대신 채우지 않는다.
   2) 레거시 EDA 데이터셋 — 화면 6(통계적 근거)의 실제 통계 결과, 그리고 품목분류
      taxonomy(필터용 목록) 보조 자료로만 사용한다.
   ======================================================================== */

let DATA = null;
let selectedItems = null; // Set<string>
let currentTab = "overview";
let lastDetailItem = null;

/* ------------------------------------------------------------------------
   포맷팅 유틸 — 결측은 항상 "자료 없음", 0으로 치환하지 않음
   ------------------------------------------------------------------------ */
function isMissing(v) {
  return v === null || v === undefined || (typeof v === "string" && v.trim() === "");
}
function formatRatio(v) {
  return isMissing(v) ? "자료 없음" : `${(v * 100).toFixed(1)}%`;
}
function formatHHI(v) {
  return isMissing(v) ? "자료 없음" : Math.round(v).toLocaleString("ko-KR");
}
function formatWon(v) {
  return isMissing(v) ? "자료 없음" : `${Math.round(v).toLocaleString("ko-KR")}원`;
}
function formatDays(v) {
  return isMissing(v) ? "자료 없음" : `${Number(v).toFixed(1)}일`;
}
function formatCount(v) {
  return isMissing(v) ? "자료 없음" : Math.round(v).toLocaleString("ko-KR");
}
function formatScore(v) {
  return isMissing(v) ? "자료 없음" : Number(v).toFixed(1);
}
function flagBadgeHTML(v, labelY = "⚠ 표본부족", labelN = "충분") {
  if (v === "Y") return `<span class="badge badge-warning">⚠ ${labelY.replace("⚠ ", "")}</span>`;
  if (v === "N") return `<span class="badge badge-ok">${labelN}</span>`;
  return `<span class="badge badge-muted">자료 없음</span>`;
}
function gradeBadgeHTML(grade) {
  if (isMissing(grade)) return `<span class="badge badge-muted">자료 없음</span>`;
  if (grade === "고위험") return `<span class="badge badge-critical">⛔ 고위험</span>`;
  if (grade === "주의") return `<span class="badge badge-warning">⚠ 주의</span>`;
  return `<span class="badge badge-ok">${grade}</span>`;
}
function yesNoBadgeHTML(v) {
  if (v === true || v === "Y" || v === "y") return `<span class="badge badge-warning">Y</span>`;
  if (v === false || v === "N" || v === "n") return `<span class="badge badge-muted">N</span>`;
  return `<span class="badge badge-muted">자료 없음</span>`;
}

/* ------------------------------------------------------------------------
   빈 상태(데이터 없음) 공용 컴포넌트
   ------------------------------------------------------------------------ */
function emptyStateHTML(desc, filename) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">🗂️</div>
      <div class="empty-state-title">데이터 없음</div>
      <div class="empty-state-desc">${desc}${
    filename ? `<br/><code>data/processed/dashboard/${filename}</code> 를 추가한 뒤 <code>python dashboard/build_data.py</code> 를 다시 실행하면 표시됩니다.` : ""
  }</div>
    </div>`;
}

/* ------------------------------------------------------------------------
   Plotly 공통 테마
   ------------------------------------------------------------------------ */
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
const PLOTLY_CONFIG = { displayModeBar: false, responsive: true };

function baseLayout(extra) {
  return Object.assign(
    {
      paper_bgcolor: cssVar("--surface"),
      plot_bgcolor: cssVar("--surface"),
      font: { family: "'Noto Sans KR', sans-serif", color: cssVar("--text-secondary"), size: 12 },
      margin: { l: 150, r: 30, t: 10, b: 40 },
      legend: { orientation: "h", y: -0.18, font: { size: 11 } },
      xaxis: { gridcolor: cssVar("--gridline"), zeroline: false },
      yaxis: { gridcolor: cssVar("--gridline"), zeroline: false, automargin: true },
      hoverlabel: { bgcolor: cssVar("--surface"), font: { family: "'Noto Sans KR', sans-serif" } },
    },
    extra
  );
}

function muteMarker(colorVar, flags) {
  const base = cssVar(colorVar);
  return {
    color: base,
    opacity: flags.map((f) => (f === "Y" ? 0.4 : 1)),
    pattern: { shape: flags.map((f) => (f === "Y" ? "/" : "")), size: 6, solidity: 0.25 },
  };
}
function sortDesc(rows, key) {
  return [...rows].filter((r) => !isMissing(r[key])).sort((a, b) => b[key] - a[key]);
}

/* ------------------------------------------------------------------------
   데이터 접근 헬퍼
   ------------------------------------------------------------------------ */
function itemRiskRows() {
  const rows = DATA.itemRisk.rows;
  if (!selectedItems || selectedItems.size === DATA.itemCategories.length) return rows;
  return rows.filter((r) => selectedItems.has(r.품목분류));
}
function caseDetailRowsFor(item) {
  return DATA.caseDetail.rows.filter((r) => r.최종품목분류 === item);
}
function vendorRowsFor(item) {
  return DATA.vendorConcentration.rows.filter((r) => r.품목분류 === item);
}
function monthlyTrendRowsFor(items) {
  const set = new Set(items);
  return DATA.monthlyTrend.rows.filter((r) => set.has(r.품목분류));
}

/* ------------------------------------------------------------------------
   범용 정렬/검색 테이블
   ------------------------------------------------------------------------ */
function renderDataTable(containerEl, rows, columns, opts = {}) {
  let sortKey = opts.defaultSortKey || columns[0].key;
  let sortDir = -1;
  let query = "";

  function draw() {
    const filtered = query ? rows.filter((r) => String(r[opts.searchKey || "품목분류"] || "").includes(query)) : rows;
    const sorted = [...filtered].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (isMissing(av)) return 1;
      if (isMissing(bv)) return -1;
      if (typeof av === "string") return sortDir * av.localeCompare(bv, "ko");
      return sortDir * (av - bv);
    });

    const headHTML = columns
      .map((c) => `<th data-key="${c.key}" style="cursor:pointer">${c.label}${sortKey === c.key ? (sortDir === -1 ? " ▼" : " ▲") : ""}</th>`)
      .join("");
    const bodyHTML = sorted
      .map((r) => {
        const cells = columns.map((c) => `<td>${c.format ? c.format(r[c.key], r) : (r[c.key] ?? "자료 없음")}</td>`).join("");
        return `<tr data-item="${r.품목분류 || ""}">${cells}</tr>`;
      })
      .join("");

    containerEl.innerHTML = `
      ${opts.searchable ? `<div style="margin-bottom:10px"><input class="search-input" type="text" placeholder="검색" value="${query}" data-role="table-search" /></div>` : ""}
      <div class="table-wrap">
        <table class="data-table tabular">
          <thead><tr>${headHTML}</tr></thead>
          <tbody>${bodyHTML || `<tr><td colspan="${columns.length}" style="text-align:center;color:var(--text-muted)">데이터 없음</td></tr>`}</tbody>
        </table>
      </div>`;

    containerEl.querySelectorAll("th[data-key]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (key === sortKey) sortDir *= -1;
        else { sortKey = key; sortDir = -1; }
        draw();
      });
    });
    const searchInput = containerEl.querySelector('[data-role="table-search"]');
    if (searchInput) searchInput.addEventListener("input", (e) => { query = e.target.value; draw(); });
    if (opts.onRowClick) {
      containerEl.querySelectorAll("tbody tr[data-item]").forEach((tr) => {
        if (tr.dataset.item) tr.addEventListener("click", () => opts.onRowClick(tr.dataset.item));
      });
    }
  }
  draw();
}

/* ------------------------------------------------------------------------
   필터 칩
   ------------------------------------------------------------------------ */
function renderFilterChips() {
  const el = document.getElementById("filter-chip-container");
  if (DATA.itemCategories.length === 0) {
    el.innerHTML = `<span class="kpi-help">품목분류 목록을 아직 확인할 수 없습니다.</span>`;
    document.getElementById("filter-count").textContent = "";
    return;
  }
  el.innerHTML = DATA.itemCategories
    .map((item) => `<button class="chip ${selectedItems.has(item) ? "active" : ""}" data-item="${item}">${item}</button>`)
    .join("");
  el.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const item = chip.dataset.item;
      if (selectedItems.has(item)) selectedItems.delete(item);
      else selectedItems.add(item);
      if (selectedItems.size === 0) selectedItems = new Set(DATA.itemCategories);
      renderFilterChips();
      renderCurrentTab();
    });
  });
  document.getElementById("filter-count").textContent = `${selectedItems.size} / ${DATA.itemCategories.length} 선택됨`;
}

/* ========================================================================
   화면 1 — 전체 현황
   ======================================================================== */
function renderOverview() {
  const wrap = document.getElementById("overview-body");
  if (!DATA.itemRisk.available) {
    wrap.innerHTML = emptyStateHTML(
      "품목별 위험현황 데이터가 아직 연결되지 않았습니다. 이 화면의 KPI와 차트는 해당 파일이 도착하면 자동으로 채워집니다.",
      "dashboard_품목별_위험현황.csv"
    );
    return;
  }
  const rows = itemRiskRows();
  const highRisk = rows.filter((r) => r.위험등급 === "고위험").length;
  const insufficient = rows.filter((r) => r.표본부족여부 === "Y").length;

  wrap.innerHTML = `
    <div class="grid grid-kpi" id="overview-kpis"></div>
    <div class="card" style="margin-top:18px">
      <h2>품목별 계약성립건수</h2>
      <div id="chart-overview-sample" style="width:100%"></div>
    </div>`;

  document.getElementById("overview-kpis").innerHTML = `
    <div class="kpi-card"><div class="kpi-label">분석 품목군 수</div><div class="kpi-value">${rows.length}</div></div>
    <div class="kpi-card"><div class="kpi-label">유효공고건수 합계</div><div class="kpi-value">${formatCount(sum(rows, "유효공고건수"))}</div></div>
    <div class="kpi-card"><div class="kpi-label">계약성립건수 합계</div><div class="kpi-value">${formatCount(sum(rows, "계약성립건수"))}</div></div>
    <div class="kpi-card"><div class="kpi-label">계약금액 합계</div><div class="kpi-value" style="font-size:19px">${formatWon(sum(rows, "계약금액합계"))}</div></div>
    <div class="kpi-card"><div class="kpi-label">고위험 품목 수</div><div class="kpi-value" style="color:var(--status-critical)">${highRisk}</div></div>
    <div class="kpi-card"><div class="kpi-label">표본부족 품목 수</div><div class="kpi-value">${insufficient}</div></div>`;

  const sorted = sortDesc(rows, "계약성립건수");
  Plotly.newPlot(
    "chart-overview-sample",
    [{ type: "bar", orientation: "h", x: sorted.map((r) => r.계약성립건수), y: sorted.map((r) => r.품목분류), marker: { color: cssVar("--accent") }, hovertemplate: "%{y}<br>계약성립건수: %{x:,}<extra></extra>" }],
    baseLayout({ yaxis: { autorange: "reversed", gridcolor: cssVar("--gridline") }, height: Math.max(280, sorted.length * 26) }),
    PLOTLY_CONFIG
  );
}
function sum(rows, key) {
  return rows.reduce((s, r) => s + (isMissing(r[key]) ? 0 : r[key]), 0);
}

/* ========================================================================
   화면 2 — 품목별 소요일수 + 월별 추이
   ======================================================================== */
function renderLeadTime() {
  const wrapA = document.getElementById("leadtime-item-body");
  if (!DATA.itemRisk.available) {
    wrapA.innerHTML = emptyStateHTML("품목별 소요일수 데이터가 아직 없습니다.", "dashboard_품목별_위험현황.csv");
  } else {
    const rows = itemRiskRows();
    wrapA.innerHTML = `
      <div class="grid grid-2">
        <div><h3>중앙 계약성립소요일수</h3><div id="chart-leadtime-median"></div></div>
        <div><h3>P90 계약성립소요일수</h3><div id="chart-leadtime-p90"></div></div>
      </div>
      <h3 style="margin-top:22px">중앙값 vs P90 비교</h3>
      <div id="chart-leadtime-compare"></div>
      <h3 style="margin-top:22px">상세 표</h3>
      <div id="leadtime-table-container"></div>`;

    const byMedian = sortDesc(rows, "중앙_계약성립소요일수");
    Plotly.newPlot("chart-leadtime-median",
      [{ type: "bar", orientation: "h", x: byMedian.map((r) => r.중앙_계약성립소요일수), y: byMedian.map((r) => r.품목분류),
        marker: muteMarker("--accent", byMedian.map((r) => r.표본부족여부)),
        hovertemplate: "%{y}<br>중앙값: %{x:.1f}일<extra></extra>" }],
      baseLayout({ yaxis: { autorange: "reversed" }, height: Math.max(260, byMedian.length * 26) }), PLOTLY_CONFIG);

    const byP90 = sortDesc(rows, "p90_계약성립소요일수");
    Plotly.newPlot("chart-leadtime-p90",
      [{ type: "bar", orientation: "h", x: byP90.map((r) => r.p90_계약성립소요일수), y: byP90.map((r) => r.품목분류),
        marker: muteMarker("--accent-2", byP90.map((r) => r.표본부족여부)),
        hovertemplate: "%{y}<br>P90: %{x:.1f}일<extra></extra>" }],
      baseLayout({ yaxis: { autorange: "reversed" }, height: Math.max(260, byP90.length * 26) }), PLOTLY_CONFIG);

    const byCompare = sortDesc(rows, "중앙_계약성립소요일수");
    Plotly.newPlot("chart-leadtime-compare",
      [
        { type: "bar", orientation: "h", name: "중앙값", x: byCompare.map((r) => r.중앙_계약성립소요일수), y: byCompare.map((r) => r.품목분류), marker: { color: cssVar("--accent") } },
        { type: "bar", orientation: "h", name: "P90", x: byCompare.map((r) => r.p90_계약성립소요일수), y: byCompare.map((r) => r.품목분류), marker: { color: cssVar("--accent-2") } },
      ],
      baseLayout({ yaxis: { autorange: "reversed" }, barmode: "group", height: Math.max(300, byCompare.length * 42) }), PLOTLY_CONFIG);

    renderDataTable(document.getElementById("leadtime-table-container"), rows,
      [
        { key: "품목분류", label: "품목분류" },
        { key: "분석가능건수", label: "분석가능건수", format: formatCount },
        { key: "중앙_계약성립소요일수", label: "중앙값", format: formatDays },
        { key: "p90_계약성립소요일수", label: "P90", format: formatDays },
        { key: "표본부족여부", label: "표본상태", format: (v) => flagBadgeHTML(v) },
      ],
      { searchable: true, defaultSortKey: "중앙_계약성립소요일수", onRowClick: goToDetail });
  }

  // ---- 월별 추이 (신규 스키마 전용 — 이전 프레임에서는 만들 수 없던 화면) ----
  const wrapB = document.getElementById("leadtime-trend-body");
  if (!DATA.monthlyTrend.available) {
    wrapB.innerHTML = emptyStateHTML("월별 추이 데이터가 아직 없습니다. 연결되면 품목별 월별 소요일수·유찰률·단독입찰률 추이를 확인할 수 있습니다.", "dashboard_품목별_월별추이.csv");
    return;
  }
  const activeItems = selectedItems && selectedItems.size <= 3 ? [...selectedItems] : DATA.itemCategories.slice(0, 3);
  wrapB.innerHTML = `
    ${selectedItems && selectedItems.size > 3 ? `<div class="banner">현재 ${selectedItems.size}개 품목이 선택되어 있습니다. 추이 비교는 앞 3개 품목만 표시합니다: ${activeItems.join(", ")} — 상단 필터에서 3개 이하로 선택하면 원하는 품목을 비교할 수 있습니다.</div>` : ""}
    <div id="chart-trend-median"></div>`;
  const trendColors = ["--accent", "--accent-2", "--accent-3"];
  const traces = activeItems.map((item, i) => {
    const rows = DATA.monthlyTrend.rows.filter((r) => r.품목분류 === item).sort((a, b) => String(a.기준연월).localeCompare(String(b.기준연월)));
    return { type: "scatter", mode: "lines+markers", name: item, x: rows.map((r) => r.기준연월), y: rows.map((r) => r.중앙_계약성립소요일수), line: { color: cssVar(trendColors[i]) } };
  });
  Plotly.newPlot("chart-trend-median", traces, baseLayout({ margin: { l: 60, r: 30, t: 10, b: 50 }, xaxis: { title: "기준연월", gridcolor: cssVar("--gridline") }, yaxis: { title: "중앙 계약성립소요일수(일)", gridcolor: cssVar("--gridline") }, height: 360 }), PLOTLY_CONFIG);
}

/* ========================================================================
   화면 3 — 품목별 입찰경쟁
   ======================================================================== */
function renderBidding() {
  const wrap = document.getElementById("bidding-body");
  if (!DATA.itemRisk.available) {
    wrap.innerHTML = emptyStateHTML("품목별 입찰경쟁 데이터가 아직 없습니다.", "dashboard_품목별_위험현황.csv");
    return;
  }
  const rows = itemRiskRows();
  wrap.innerHTML = `
    <p class="section-intro">새 데이터셋에는 반복입찰률·낙찰성공률·참가업체수 필드가 없어 이번 프레임에서는 단독입찰률·유찰률만 제공합니다. 해당 필드가 추가되면 이 화면에 지표를 더 연결할 수 있습니다.</p>
    <div class="grid grid-2">
      <div><h3>단독입찰률</h3><div id="chart-bidding-solo"></div></div>
      <div><h3>유찰률</h3><div id="chart-bidding-fail"></div></div>
    </div>
    <h3 style="margin-top:22px">단독입찰률 × 유찰률</h3>
    <div id="chart-bidding-scatter"></div>`;

  const bySolo = sortDesc(rows, "단독입찰률");
  Plotly.newPlot("chart-bidding-solo",
    [{ type: "bar", orientation: "h", x: bySolo.map((r) => r.단독입찰률 * 100), y: bySolo.map((r) => r.품목분류), marker: muteMarker("--accent", bySolo.map((r) => r.표본부족여부)), hovertemplate: "%{y}<br>단독입찰률: %{x:.1f}%<extra></extra>" }],
    baseLayout({ yaxis: { autorange: "reversed" }, xaxis: { ticksuffix: "%", gridcolor: cssVar("--gridline") }, height: Math.max(260, bySolo.length * 26) }), PLOTLY_CONFIG);

  const byFail = sortDesc(rows, "유찰률");
  Plotly.newPlot("chart-bidding-fail",
    [{ type: "bar", orientation: "h", x: byFail.map((r) => r.유찰률 * 100), y: byFail.map((r) => r.품목분류), marker: muteMarker("--accent-3", byFail.map((r) => r.표본부족여부)), hovertemplate: "%{y}<br>유찰률: %{x:.1f}%<extra></extra>" }],
    baseLayout({ yaxis: { autorange: "reversed" }, xaxis: { ticksuffix: "%", gridcolor: cssVar("--gridline") }, height: Math.max(260, byFail.length * 26) }), PLOTLY_CONFIG);

  const bubbleBase = rows.filter((r) => !isMissing(r.계약금액합계) && r.계약금액합계 > 0);
  const maxAmt = Math.max(1, ...bubbleBase.map((r) => r.계약금액합계));
  Plotly.newPlot("chart-bidding-scatter",
    [{ type: "scatter", mode: "markers+text", x: rows.map((r) => r.단독입찰률 * 100), y: rows.map((r) => r.유찰률 * 100), text: rows.map((r) => r.품목분류), textposition: "top center", textfont: { size: 10, color: cssVar("--text-muted") },
      marker: { color: cssVar("--accent"), opacity: 0.75, size: rows.map((r) => (isMissing(r.계약금액합계) ? 1 : r.계약금액합계)), sizemode: "area", sizeref: (2.0 * maxAmt) / 40 ** 2, sizemin: 6 },
      hovertemplate: "%{text}<br>단독입찰률: %{x:.1f}%<br>유찰률: %{y:.1f}%<extra></extra>" }],
    baseLayout({ xaxis: { title: "단독입찰률(%)", gridcolor: cssVar("--gridline") }, yaxis: { title: "유찰률(%)", automargin: true, gridcolor: cssVar("--gridline") }, margin: { l: 60, r: 30, t: 10, b: 50 }, height: 420 }), PLOTLY_CONFIG);
}

/* ========================================================================
   화면 4 — 품목별 업체집중도
   ======================================================================== */
function renderConcentration() {
  const wrap = document.getElementById("concentration-body");
  if (!DATA.itemRisk.available) {
    wrap.innerHTML = emptyStateHTML("품목별 업체집중도 데이터가 아직 없습니다.", "dashboard_품목별_위험현황.csv");
    return;
  }
  const rows = itemRiskRows();
  wrap.innerHTML = `
    <h3>HHI</h3><div id="chart-hhi-bar"></div>
    <h3 style="margin-top:22px">상위1개사 vs 상위3개사 점유율</h3><div id="chart-share-compare"></div>
    <h3 style="margin-top:22px">HHI × 상위1개사 점유율</h3><div id="chart-hhi-scatter"></div>`;

  const byHhi = sortDesc(rows, "HHI");
  Plotly.newPlot("chart-hhi-bar",
    [{ type: "bar", orientation: "h", x: byHhi.map((r) => r.HHI), y: byHhi.map((r) => r.품목분류), marker: muteMarker("--accent", byHhi.map((r) => r.표본부족여부)), hovertemplate: "%{y}<br>HHI: %{x:,.0f}<extra></extra>" }],
    baseLayout({ yaxis: { autorange: "reversed" }, height: Math.max(260, byHhi.length * 26) }), PLOTLY_CONFIG);

  const byShare = sortDesc(rows, "상위1개사_계약금액점유율");
  Plotly.newPlot("chart-share-compare",
    [
      { type: "bar", orientation: "h", name: "상위1개사", x: byShare.map((r) => r.상위1개사_계약금액점유율 * 100), y: byShare.map((r) => r.품목분류), marker: { color: cssVar("--accent") } },
      { type: "bar", orientation: "h", name: "상위3개사", x: byShare.map((r) => r.상위3개사_계약금액점유율 * 100), y: byShare.map((r) => r.품목분류), marker: { color: cssVar("--accent-2") } },
    ],
    baseLayout({ yaxis: { autorange: "reversed" }, xaxis: { ticksuffix: "%", gridcolor: cssVar("--gridline") }, barmode: "group", height: Math.max(300, byShare.length * 42) }), PLOTLY_CONFIG);

  Plotly.newPlot("chart-hhi-scatter",
    [{ type: "scatter", mode: "markers", x: rows.map((r) => r.HHI), y: rows.map((r) => r.상위1개사_계약금액점유율 * 100), text: rows.map((r) => r.품목분류), marker: { color: cssVar("--accent"), opacity: 0.8, size: 11 }, hovertemplate: "%{text}<br>HHI: %{x:,.0f}<br>상위1개사: %{y:.1f}%<extra></extra>" }],
    baseLayout({ xaxis: { title: "HHI", gridcolor: cssVar("--gridline") }, yaxis: { title: "상위1개사 점유율(%)", automargin: true, gridcolor: cssVar("--gridline") }, margin: { l: 60, r: 30, t: 10, b: 50 }, height: 400 }), PLOTLY_CONFIG);
}

/* ========================================================================
   화면 5 — 품목 상세
   ======================================================================== */
function renderDetailSelect() {
  const sel = document.getElementById("detail-select");
  if (DATA.itemCategories.length === 0) {
    sel.innerHTML = `<option>품목 없음</option>`;
    sel.disabled = true;
    return;
  }
  sel.innerHTML = DATA.itemCategories.map((i) => `<option value="${i}">${i}</option>`).join("");
  sel.value = lastDetailItem || DATA.itemCategories[0];
  sel.addEventListener("change", () => renderDetail(sel.value));
}
function goToDetail(item) {
  lastDetailItem = item;
  switchTab("detail");
}

function renderDetail(item) {
  if (DATA.itemCategories.length === 0) return;
  const target = item || lastDetailItem || DATA.itemCategories[0];
  lastDetailItem = target;
  const sel = document.getElementById("detail-select");
  if (sel) sel.value = target;

  const r = DATA.itemRisk.available ? DATA.itemRisk.rows.find((row) => row.품목분류 === target) : null;

  // ---- 위험현황 요약 ----
  const summaryEl = document.getElementById("detail-summary");
  if (!r) {
    summaryEl.innerHTML = emptyStateHTML(`"${target}" 품목의 위험현황 데이터가 아직 없습니다.`, "dashboard_품목별_위험현황.csv");
  } else {
    summaryEl.innerHTML = `
      <div class="detail-flags">${flagBadgeHTML(r.표본부족여부)} ${gradeBadgeHTML(r.위험등급)}</div>
      <div class="grid grid-2" style="margin-top:14px">
        <div class="card"><h3>조달 규모</h3><ul class="detail-list">
          <li>유효공고건수: <strong>${formatCount(r.유효공고건수)}</strong></li>
          <li>계약성립건수: <strong>${formatCount(r.계약성립건수)}</strong></li>
          <li>분석가능건수: <strong>${formatCount(r.분석가능건수)}</strong></li>
          <li>계약금액합계: <strong>${formatWon(r.계약금액합계)}</strong></li>
        </ul></div>
        <div class="card"><h3>절차·경쟁 지표</h3><ul class="detail-list">
          <li>중앙 / 평균 / P90 소요일수: <strong>${formatDays(r.중앙_계약성립소요일수)} / ${formatDays(r.평균_계약성립소요일수)} / ${formatDays(r.p90_계약성립소요일수)}</strong></li>
          <li>유찰률: <strong>${formatRatio(r.유찰률)}</strong></li>
          <li>단독입찰률: <strong>${formatRatio(r.단독입찰률)}</strong></li>
          <li>재공고율: <strong>${formatRatio(r.재공고율)}</strong></li>
          <li>상위1개사 / 상위3개사 점유율: <strong>${formatRatio(r.상위1개사_계약금액점유율)} / ${formatRatio(r.상위3개사_계약금액점유율)}</strong></li>
          <li>HHI: <strong>${formatHHI(r.HHI)}</strong></li>
        </ul></div>
      </div>`;
  }

  // ---- 위험점수 구성요소 (실제 값이 있으면 표시, 없으면 데이터 없음) ----
  const riskEl = document.getElementById("detail-risk");
  const hasScore = r && !isMissing(r.종합위험점수);
  if (!r) {
    riskEl.innerHTML = "";
  } else if (!hasScore) {
    riskEl.innerHTML = `<div class="card"><h3>조달절차 위험점수</h3>${emptyStateHTML("이 품목의 위험점수가 아직 산정되지 않았습니다.")}</div>`;
  } else {
    const components = [
      { label: "리드타임점수", value: r.리드타임점수 },
      { label: "유찰점수", value: r.유찰점수 },
      { label: "단독입찰점수", value: r.단독입찰점수 },
      { label: "HHI점수", value: r.HHI점수 },
    ];
    riskEl.innerHTML = `
      <div class="card">
        <h3>조달절차 위험점수</h3>
        <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:12px">
          <span class="kpi-value" style="font-size:32px">${formatScore(r.종합위험점수)}</span>
          ${gradeBadgeHTML(r.위험등급)}
        </div>
        <div id="chart-risk-components"></div>
      </div>`;
    Plotly.newPlot("chart-risk-components",
      [{ type: "bar", x: components.map((c) => c.value ?? 0), y: components.map((c) => c.label), orientation: "h",
        marker: { color: [cssVar("--accent"), cssVar("--accent-2"), cssVar("--accent-3"), cssVar("--status-warning")] },
        text: components.map((c) => formatScore(c.value)), textposition: "auto" }],
      baseLayout({ yaxis: { autorange: "reversed" }, height: 220, margin: { l: 120, r: 30, t: 10, b: 30 } }), PLOTLY_CONFIG);
  }

  // ---- 업체별 계약 현황 (3.4, 선택) ----
  const vendorEl = document.getElementById("detail-vendors");
  if (!DATA.vendorConcentration.available) {
    vendorEl.innerHTML = `<div class="card"><h3>업체별 계약 현황</h3>${emptyStateHTML("업체별 상세 데이터는 아직 제공되지 않았습니다 (선택 항목).", "dashboard_품목별_업체집중도.csv")}</div>`;
  } else {
    const vendorRows = vendorRowsFor(target);
    vendorEl.innerHTML = `<div class="card"><h3>업체별 계약 현황</h3><div id="detail-vendor-table"></div></div>`;
    renderDataTable(document.getElementById("detail-vendor-table"), vendorRows,
      [
        { key: "업체명", label: "업체명" },
        { key: "계약건수", label: "계약건수", format: formatCount },
        { key: "배분계약금액", label: "배분계약금액", format: formatWon },
        { key: "계약금액점유율", label: "점유율", format: formatRatio },
        { key: "품목내업체순위", label: "순위" },
      ],
      { searchable: false, defaultSortKey: "계약금액점유율", searchKey: "업체명" });
  }

  // ---- 조달건별 상세내역 (3.3) ----
  const caseEl = document.getElementById("detail-cases");
  if (!DATA.caseDetail.available) {
    caseEl.innerHTML = emptyStateHTML(`"${target}" 품목의 개별 공고·계약 이력이 아직 연결되지 않았습니다. 연결되면 공고→유찰→재공고→계약 단위까지 조회할 수 있습니다.`, "dashboard_조달건별_상세내역.csv");
  } else {
    const caseRows = caseDetailRowsFor(target);
    caseEl.innerHTML = `<div id="detail-case-count" class="kpi-help" style="margin-bottom:8px"></div><div id="detail-case-table"></div>`;
    document.getElementById("detail-case-count").textContent = `${caseRows.length}건`;
    renderDataTable(document.getElementById("detail-case-table"), caseRows,
      [
        { key: "공고명", label: "공고명" },
        { key: "계약명", label: "계약명" },
        { key: "최초공고일", label: "최초공고일" },
        { key: "계약체결일", label: "계약체결일" },
        { key: "계약성립소요일수", label: "소요일수", format: formatDays },
        { key: "유찰여부", label: "유찰", format: yesNoBadgeHTML },
        { key: "단독입찰여부", label: "단독입찰", format: yesNoBadgeHTML },
        { key: "재공고여부", label: "재공고", format: yesNoBadgeHTML },
        { key: "계약금액", label: "계약금액", format: formatWon },
        { key: "위험등급", label: "위험등급", format: gradeBadgeHTML },
      ],
      { searchable: true, defaultSortKey: "계약성립소요일수", searchKey: "공고명" });
  }
}

/* ========================================================================
   화면 6 — 통계적 근거 (레거시 EDA 데이터셋 기준)
   ======================================================================== */
function kwInterpretation(t) {
  const sig = t.귀무가설기각 === true;
  const eff = t.효과크기;
  if (!sig) return "품목분류 간 계약성립 소요일수 차이가 통계적으로 유의하지 않았습니다.";
  if (eff < 0.06) return "품목분류별 계약성립 소요일수에는 통계적으로 유의한 차이가 나타났습니다. 다만 효과크기가 작으므로 품목분류만으로 소요일수 차이 전체를 설명할 수는 없습니다.";
  if (eff < 0.14) return "품목분류별 계약성립 소요일수에는 통계적으로 유의한 차이가 나타났으며, 효과크기는 중간 수준입니다.";
  return "품목분류별 계약성립 소요일수에는 통계적으로 유의한 차이가 나타났으며, 효과크기도 상당히 큰 편입니다.";
}

function renderStats() {
  const wrap = document.getElementById("stats-body");
  if (!DATA.stats.available) {
    wrap.innerHTML = emptyStateHTML("통계 검정 결과(레거시 EDA 데이터셋)를 찾을 수 없습니다.");
    return;
  }
  const t02 = DATA.stats.d2bOverallTest;
  const t05 = DATA.stats.g2bChi2;
  const posthocSig = DATA.stats.d2bPosthoc.filter((r) => r.유의함 === true);

  wrap.innerHTML = `
    <p class="kpi-help" style="margin-bottom:16px">이 화면은 레거시 EDA 데이터셋(품목분류 조달절차 통계분석) 기준이며, 위의 신규 운영 대시보드 데이터셋과는 별도 자료입니다.</p>
    <div class="grid grid-2">
      <div class="card"><h3>Kruskal-Wallis 검정 (품목별 소요일수 차이)</h3>
        <ul class="detail-list">
          <li>검정명: <strong>${t02.검정명}</strong> · 분석표본수 ${formatCount(t02.분석표본수)} · 품목군수 ${t02.품목군수}</li>
          <li>통계량 H: <strong>${t02.통계량_H.toFixed(2)}</strong> (자유도 ${t02.자유도})</li>
          <li>p-value: <strong>${t02.p_value.toExponential(2)}</strong></li>
          <li>효과크기 (${t02.효과크기명}): <strong>${t02.효과크기.toFixed(4)}</strong></li>
        </ul>
        <p class="section-intro">${kwInterpretation(t02)}</p>
      </div>
      <div class="card"><h3>카이제곱 검정 (단독입찰 × 낙찰성공)</h3>
        <ul class="detail-list">
          <li>전체표본수: <strong>${formatCount(t05.전체표본수)}</strong> (단독입찰 ${formatCount(t05.단독입찰수)} / 비단독입찰 ${formatCount(t05.비단독입찰수)})</li>
          <li>카이제곱통계량: <strong>${t05.카이제곱통계량.toFixed(2)}</strong> (자유도 ${t05.자유도})</li>
          <li>p-value: <strong>${t05.p_value.toExponential(2)}</strong></li>
        </ul>
        <p class="section-intro">단독입찰 여부와 낙찰성공 여부 사이에는 통계적 관련성이 확인되었습니다. 이는 인과관계를 의미하지 않으며 G2B 국방기관 표본 범위에서 해석해야 합니다.</p>
      </div>
    </div>
    <div class="card" style="margin-top:18px">
      <h3>품목 쌍별 사후검정</h3>
      <label class="kpi-help"><input type="checkbox" id="stats-posthoc-toggle" /> 전체 ${DATA.stats.d2bPosthoc.length}개 조합 보기 (기본: 유의한 ${posthocSig.length}개)</label>
      <div id="stats-posthoc-table-container" style="margin-top:10px"></div>
    </div>`;

  function drawPosthoc(showAll) {
    renderDataTable(document.getElementById("stats-posthoc-table-container"), showAll ? DATA.stats.d2bPosthoc : posthocSig,
      [
        { key: "품목A", label: "품목A" },
        { key: "품목B", label: "품목B" },
        { key: "중앙값차이_A-B", label: "중앙값차이(A-B)", format: (v) => (isMissing(v) ? "자료 없음" : `${v.toFixed(1)}일`) },
        { key: "p_holm", label: "p (Holm 보정)", format: (v) => v.toExponential(2) },
        { key: "유의함", label: "유의함", format: (v) => (v ? '<span class="badge badge-warning">유의함</span>' : '<span class="badge badge-muted">해당없음</span>') },
      ],
      { searchable: false, defaultSortKey: "p_holm", searchKey: "품목A" });
  }
  drawPosthoc(false);
  document.getElementById("stats-posthoc-toggle").addEventListener("change", (e) => drawPosthoc(e.target.checked));
}

/* ========================================================================
   탭 라우팅
   ======================================================================== */
const RENDERERS = {
  overview: renderOverview,
  leadtime: renderLeadTime,
  bidding: renderBidding,
  concentration: renderConcentration,
  detail: () => renderDetail(lastDetailItem),
  stats: renderStats,
};

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tab}`));
  window.location.hash = tab;
  renderCurrentTab();
}
function renderCurrentTab() {
  RENDERERS[currentTab] && RENDERERS[currentTab]();
}

/* ------------------------------------------------------------------------
   테마 토글
   ------------------------------------------------------------------------ */
function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("procurement-dashboard-theme"); } catch (e) {}
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);

  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const next = cur === "dark" ? "light" : cur === "light" ? null : "dark";
    if (next) document.documentElement.setAttribute("data-theme", next);
    else document.documentElement.removeAttribute("data-theme");
    try {
      if (next) localStorage.setItem("procurement-dashboard-theme", next);
      else localStorage.removeItem("procurement-dashboard-theme");
    } catch (e) {}
    renderCurrentTab();
  });
}

/* ========================================================================
   초기화
   ======================================================================== */
async function init() {
  const res = await fetch("data/dashboard_data.json");
  DATA = await res.json();
  selectedItems = new Set(DATA.itemCategories);

  renderFilterChips();
  document.getElementById("chip-reset-btn").addEventListener("click", () => {
    selectedItems = new Set(DATA.itemCategories);
    renderFilterChips();
    renderCurrentTab();
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

  renderDetailSelect();
  initTheme();

  const hashTab = window.location.hash.replace("#", "");
  switchTab(RENDERERS[hashTab] ? hashTab : "overview");
}

document.addEventListener("DOMContentLoaded", init);
