import streamlit as st

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 접근 제한")
        pwd = st.text_input("비밀번호를 입력하세요", type="password")

        if pwd:
            if pwd == "NQ0716":   # ← 비밀번호 여기서 변경
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()

check_password()
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

st.set_page_config(layout="wide")
st.title("NQ6 신차 프로젝트 통합 대시보드")

# =========================
# 데이터 로드
# =========================
schedule = pd.read_excel("data/project_schedule.xlsx")
internal_schedule = pd.read_excel("data/internal_schedule.xlsx")

customer = pd.read_excel("data/customer_issue.xlsx")
internal = pd.read_excel("data/internal_issue.xlsx")
supplier = pd.read_excel("data/supplier_issue.xlsx")
design_review = pd.read_excel("data/design_review.xlsx")

Q_COLORS = {
    1: "#E3F2FD",
    2: "#E8F5E9",
    3: "#FFFDE7",
    4: "#FCE4EC"
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
    x = str(x)
    if "완료" in x: return "완료"
    if "진행" in x: return "진행중"
    return "미진행"

def compute_kpi(df):
    today = pd.Timestamp.today().normalize()
    d = df.copy()
    d["개선현황"] = d["개선현황"].apply(normalize_status)
    d["적용일"] = pd.to_datetime(d["적용일"], errors="coerce")

    total = len(d)
    done = (d["개선현황"]=="완료").sum()
    ing  = (d["개선현황"]=="진행중").sum()
    noty = (d["개선현황"]=="미진행").sum()
    delay = ((d["개선현황"]!="완료") & (d["적용일"] < today)).sum()
    rate = round(done/total*100,1) if total else 0
    return total, done, ing, noty, delay, rate

def render_kpi_summary(title, df):
    st.subheader(f"{title} KPI 요약")
    t,d,i,n,dl,r = compute_kpi(df)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("📦 전체", t)
    c2.metric("✅ 완료", d)
    c3.metric("🔄 진행중", i)
    c4.metric("⏸ 미진행", n)
    c5.metric("⚠️ 지연", dl)
    c6.metric("📊 완료율", f"{r}%")

def calc_dday(apply_date, status):
    if normalize_status(status) == "완료":
        return "—"
    if pd.isna(apply_date):
        return "—"

    today = pd.Timestamp.today().normalize()
    d = (pd.to_datetime(apply_date) - today).days

    if d > 0:
        return f"D-{d}"
    elif d == 0:
        return "D-DAY"
    else:
        return f"D+{abs(d)}"

def highlight_delay(row):
    status = normalize_status(row["개선현황"])
    apply_date = pd.to_datetime(row["적용일"], errors="coerce")
    today = pd.Timestamp.today().normalize()

    if status != "완료" and pd.notna(apply_date) and apply_date < today:
        return ["background-color: #FFE5E5"] * len(row)
    return [""] * len(row)

# =========================
# 일정 그래프 (좌우 이동 가능)
# =========================
def render_master_schedule(title, df):
    st.subheader(title)
    d = df.copy()
    d["일정"] = pd.to_datetime(d["일정"], errors="coerce")
    fig = go.Figure()

    if not d.empty:
        # 분기 배경
        q_range = pd.period_range(d["일정"].min(), d["일정"].max(), freq="Q")
        for q in q_range:
            fig.add_vrect(
                x0=q.start_time,
                x1=q.end_time,
                fillcolor=Q_COLORS[q.quarter],
                opacity=0.35,
                layer="below",
                line_width=0
            )
            fig.add_annotation(
                x=q.start_time + (q.end_time - q.start_time)/2,
                y=1.08,
                xref="x",
                yref="paper",
                text=f"{q.year} Q{q.quarter}",
                showarrow=False,
                font=dict(size=15)
            )

        # 일정 포인트
        for _, r in d.iterrows():
            stage = str(r.get("단계",""))
            is_sop = stage.upper() == "SOP"
            y_val = r.get("차종","")

            fig.add_trace(go.Scatter(
                x=[r["일정"]],
                y=[y_val],
                mode="markers",
                marker=dict(
                    size=14 if is_sop else 10,
                    color="red" if is_sop else "#1f77b4",
                    symbol="star" if is_sop else "circle"
                ),
                showlegend=False
            ))

            fig.add_annotation(
                x=r["일정"],
                y=y_val,
                text=stage,
                showarrow=False,
                yshift=18 if is_sop else 14,
                font=dict(
                    size=13 if is_sop else 11,
                    color="red" if is_sop else "black"
                )
            )

        # Now 기준선
        today = pd.to_datetime(date.today())
        fig.add_shape(
            type="line",
            x0=today, x1=today,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="red", dash="dash")
        )
        fig.add_annotation(
            x=today, y=1.05,
            xref="x", yref="paper",
            text="Now",
            showarrow=False,
            font=dict(color="red", size=14, family="Arial Black")
        )

        # 🔹 좌우 이동 + 슬라이더 추가
        fig.update_layout(
            height=520,
            dragmode="pan",
            hovermode="closest",
            xaxis=dict(
                dtick="M1",
                tickformat="%Y-%m",
                rangeslider=dict(
                    visible=True,
                    thickness=0.08
                )
            ),
            margin=dict(t=80)
        )

        st.plotly_chart(fig, use_container_width=True)

def render_issue_table(title, df):
    render_kpi_summary(title, df)
    st.markdown("---")

    d = df.copy()
    d["D-DAY"] = d.apply(lambda r: calc_dday(r["적용일"], r["개선현황"]), axis=1)

    cols = ["NO","발생일","차종","활동항목","개선현황","D-DAY","적용일"]
    cols = [c for c in cols if c in d.columns]

    styled = d[cols].style.apply(highlight_delay, axis=1)
    st.dataframe(styled, use_container_width=True)

# =========================
# 탭별 화면
# =========================
with tabs[0]:
    render_master_schedule("고객 대일정 (월·분기)", schedule)
    st.markdown("---")
    st.subheader("프로젝트 일정")
    st.dataframe(schedule, use_container_width=True)

with tabs[1]:
    render_master_schedule("사내 일정 (월·분기)", internal_schedule)
    st.markdown("---")
    st.subheader("사내 일정 상세")
    st.dataframe(internal_schedule, use_container_width=True)

with tabs[2]:
    render_kpi_summary("고객 이슈", customer)
    st.markdown("---")
    render_kpi_summary("사내 이슈", internal)
    st.markdown("---")
    render_kpi_summary("협력사 이슈", supplier)

with tabs[3]:
    render_issue_table("고객 이슈", customer)

with tabs[4]:
    render_issue_table("사내 이슈", internal)

with tabs[5]:
    render_issue_table("협력사 이슈", supplier)

with tabs[6]:
    render_issue_table("디자인리뷰", design_review)
