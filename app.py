import streamlit as st

# =========================
# 비밀번호 체크
# =========================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 접근 제한")
        pwd = st.text_input("비밀번호를 입력하세요", type="password")
        if pwd:
            if pwd == "NQ0716":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()

check_password()

# =========================
# 라이브러리
# =========================
import pandas as pd
import plotly.graph_objects as go
from datetime import date

st.set_page_config(layout="wide")
st.title("KMC NQ6 AIR VENT PROJECT")

# =========================
# 데이터 로드
# =========================
schedule = pd.read_excel("data/project_schedule.xlsx")
internal_schedule = pd.read_excel("data/internal_schedule.xlsx")

customer = pd.read_excel("data/customer_issue.xlsx")
internal = pd.read_excel("data/internal_issue.xlsx")
supplier = pd.read_excel("data/supplier_issue.xlsx")
design_review = pd.read_excel("data/design_review.xlsx")

# =========================
# 날짜 컬럼 정리 (datetime 유지)
# =========================
for df in [schedule, internal_schedule]:
    if "일정" in df.columns:
        df["일정"] = pd.to_datetime(df["일정"], errors="coerce").dt.normalize()

for df in [customer, internal, supplier, design_review]:
    for c in ["발생일", "적용일"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.normalize()

# =========================
# 분기 색상
# =========================
Q_COLORS = {
    1: "#E3F2FD",
    2: "#E8F5E9",
    3: "#FFFDE7",
    4: "#FCE4EC",
}

# =========================
# 탭 구성
# =========================
tabs = st.tabs([
    "🗓 고객·프로젝트 일정",
    "🏢 사내 일정",
    "📊 대시보드",
    "📣 고객 이슈",
    "🏭 사내 이슈",
    "🤝 협력사 이슈",
    "🎨 디자인리뷰",
])

# =========================
# 공통 함수
# =========================
def normalize_status(x):
    return "완료" if "완료" in str(x) else "진행중"

def calc_schedule_dday(d):
    if pd.isna(d):
        return ""
    today = pd.Timestamp.today().normalize()
    diff = (d - today).days
    if diff < 0:
        return ""
    if diff == 0:
        return "D-DAY"
    return f"D-{diff}"

def format_date_col(df, cols):
    d = df.copy()
    for c in cols:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce").dt.strftime("%y.%m.%d")
    return d

def nl_to_br(x):
    if pd.isna(x):
        return ""
    return str(x).replace("\n", "<br>")

# =========================
# 다가오는 일정 강조
# =========================
def highlight_next_schedule(display_df, original_df, date_col="일정"):
    today = pd.Timestamp.today().normalize()
    dt = original_df[date_col]
    valid = original_df.loc[(dt.notna()) & (dt >= today)]

    if valid.empty:
        return display_df.style

    next_idx = valid.loc[dt.loc[valid.index].idxmin()].name

    def style_row(row):
        if row.name == next_idx:
            return ["background-color:#E3F2FD"] * len(row)
        return [""] * len(row)

    return display_df.style.apply(style_row, axis=1)

# =========================
# 일정 그래프
# =========================
def render_master_schedule(title, df):
    st.subheader(title)
    d = df.dropna(subset=["일정"]).copy()
    fig = go.Figure()

    q_range = pd.period_range(d["일정"].min(), d["일정"].max(), freq="Q")
    for q in q_range:
        fig.add_vrect(
            x0=q.start_time, x1=q.end_time,
            fillcolor=Q_COLORS[q.quarter],
            opacity=0.35, layer="below", line_width=0
        )
        fig.add_annotation(
            x=q.start_time + (q.end_time - q.start_time) / 2,
            y=1.10, xref="x", yref="paper",
            text=f"{q.year} Q{q.quarter}",
            showarrow=False,
            font=dict(size=18, family="Arial Black")
        )

    for _, r in d.iterrows():
        fig.add_trace(go.Scatter(
            x=[r["일정"]],
            y=[r.get("차종", "")],
            mode="markers",
            marker=dict(size=12),
            showlegend=False
        ))
        fig.add_annotation(
            x=r["일정"],
            y=r.get("차종", ""),
            text=str(r.get("단계", "")),
            showarrow=False,
            yshift=18,
            font=dict(size=14)
        )

    today = pd.to_datetime(date.today())
    fig.add_vline(x=today, line_dash="dash", line_color="red")
    fig.add_annotation(
        x=today, y=1.08, xref="x", yref="paper",
        text="NOW", showarrow=False,
        font=dict(color="red", size=18, family="Arial Black")
    )

    fig.update_layout(
        height=560,
        xaxis=dict(
            dtick="M1",
            tickformat="%Y-%m",
            rangeslider=dict(visible=True, thickness=0.08)
        ),
        margin=dict(t=110)
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# KPI
# =========================
def compute_kpi(df):
    today = pd.Timestamp.today().normalize()
    d = df.copy()
    d["개선현황"] = d["개선현황"].apply(normalize_status)
    d["_적용일_dt"] = pd.to_datetime(d["적용일"], errors="coerce")

    total = len(d)
    done = (d["개선현황"] == "완료").sum()
    overdue = ((d["개선현황"] != "완료") &
               pd.notna(d["_적용일_dt"]) &
               (d["_적용일_dt"] < today)).sum()
    ing = total - done - overdue
    rate = round(done / total * 100, 1) if total else 0
    return total, done, ing, overdue, rate

def render_kpi_summary(title, df):
    st.subheader(f"{title} KPI 요약")
    t, d, i, o, r = compute_kpi(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 전체", t)
    c2.metric("✅ 완료", d)
    c3.metric("🟡 진행중", i)
    c4.metric("🔴 기한초과", o)
    c5.metric("📊 완료율", f"{r}%")

# =========================
# 🔥 이슈 테이블 (글 안 짤림 수정)
# =========================
def render_issue_table(title, df):
    render_kpi_summary(title, df)
    st.markdown("---")

    d = df.copy()
    d["개선현황_raw"] = d["개선현황"].apply(normalize_status)
    d["_적용일_dt"] = pd.to_datetime(d["적용일"], errors="coerce")
    today = pd.Timestamp.today().normalize()

    def status(row):
        if row["개선현황_raw"] == "완료":
            return "완료 🟢"
        if pd.notna(row["_적용일_dt"]) and row["_적용일_dt"] < today:
            return "진행중 🔴"
        return "진행중 🟡"

    d["개선현황"] = d.apply(status, axis=1)
    d = format_date_col(d, ["발생일", "적용일"])

    for c in ["문제점", "개선안"]:
        if c in d.columns:
            d[c] = d[c].apply(nl_to_br)

    cols = [
        "NO","활동항목","발생일","차종",
        "발행부서","대응부서",
        "문제점","개선안",
        "적용일","개선현황"
    ]
    cols = [c for c in cols if c in d.columns]

    html = "<table style='width:100%; border-collapse:collapse; font-size:14px;'>"
    html += "<thead><tr>"
    for c in cols:
        html += f"<th style='border:1px solid #ccc; padding:6px; background:#f5f5f5'>{c}</th>"
    html += "</tr></thead><tbody>"

    for _, r in d.iterrows():
        html += "<tr>"
        for c in cols:
            bg = "#FFE5E5" if r["개선현황"] == "진행중 🔴" else ""
            html += (
                "<td style='"
                "border:1px solid #ddd;"
                "padding:6px;"
                f"background:{bg};"
                "white-space:pre-wrap;"
                "word-break:break-word;"
                "overflow-wrap:break-word;"
                "'>"
                f"{r[c]}"
                "</td>"
            )
        html += "</tr>"

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

# =========================
# 탭별 화면
# =========================
with tabs[0]:
    render_master_schedule("고객 대일정 (월·분기)", schedule)
    st.markdown("---")
    d_tbl = schedule.copy()
    d_tbl["D-DAY"] = d_tbl["일정"].apply(calc_schedule_dday)
    d_tbl["일정"] = d_tbl["일정"].dt.strftime("%y.%m.%d")
    st.dataframe(highlight_next_schedule(d_tbl, schedule), use_container_width=True)

with tabs[1]:
    render_master_schedule("사내 일정 (월·분기)", internal_schedule)
    st.markdown("---")
    d_tbl = internal_schedule.copy()
    d_tbl["D-DAY"] = d_tbl["일정"].apply(calc_schedule_dday)
    d_tbl["일정"] = d_tbl["일정"].dt.strftime("%y.%m.%d")
    st.dataframe(highlight_next_schedule(d_tbl, internal_schedule), use_container_width=True)

with tabs[2]:
    render_kpi_summary("고객 이슈", customer)
    render_kpi_summary("사내 이슈", internal)
    render_kpi_summary("협력사 이슈", supplier)

with tabs[3]:
    render_issue_table("고객 이슈", customer)

with tabs[4]:
    render_issue_table("사내 이슈", internal)

with tabs[5]:
    render_issue_table("협력사 이슈", supplier)

with tabs[6]:
    render_issue_table("디자인리뷰", design_review)
