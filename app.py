"""
Streamlit dashboard — System Capacity & Care Load Analytics for
Unaccompanied Children.

Run locally with:
    streamlit run app/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Allow importing src/ when run as `streamlit run app/app.py` from repo root
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.data_pipeline import load_and_process, compute_kpis  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "uac_daily_data.csv"

st.set_page_config(
    page_title="UAC System Capacity & Care Load Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def get_data(path):
    return load_and_process(path)


def kpi_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def main():
    st.title("System Capacity & Care Load Analytics")
    st.caption("Unaccompanied Children (UAC) Program — CBP & HHS care pipeline monitoring")

    df, anomalies = get_data(DATA_PATH)

    # ---------------- Sidebar controls ----------------
    st.sidebar.header("Filters")

    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    granularity = st.sidebar.selectbox("Time granularity", ["Daily", "Weekly", "Monthly"], index=0)

    metric_options = {
        "Total System Load": "total_system_load",
        "CBP Custody": "cbp_custody",
        "HHS Care": "hhs_care",
        "Net Daily Intake": "net_daily_intake",
        "Care Load Growth Rate (%)": "care_load_growth_rate",
    }
    selected_metrics = st.sidebar.multiselect(
        "Metrics to plot", list(metric_options.keys()),
        default=["Total System Load", "CBP Custody", "HHS Care"],
    )

    show_ma = st.sidebar.checkbox("Overlay 7-day rolling average", value=True)

    st.sidebar.divider()
    if not anomalies.empty:
        st.sidebar.warning(f"{len(anomalies)} data quality flags detected")
        with st.sidebar.expander("View flagged anomalies"):
            st.dataframe(anomalies, use_container_width=True, hide_index=True)
    else:
        st.sidebar.success("No data quality anomalies detected")

    # ---------------- Filter data ----------------
    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    fdf = df.loc[mask].copy()

    if granularity != "Daily":
        rule = "W" if granularity == "Weekly" else "M"
        fdf = (
            fdf.set_index("date")
            .resample(rule)
            .agg({
                "apprehended": "sum",
                "transferred_out": "sum",
                "discharged": "sum",
                "cbp_custody": "last",
                "hhs_care": "last",
                "total_system_load": "last",
                "net_daily_intake": "sum",
                "care_load_growth_rate": "mean",
            })
            .reset_index()
        )

    # ---------------- KPI summary cards ----------------
    kpis = compute_kpis(df.loc[mask] if len(df.loc[mask]) > 1 else df)
    st.subheader("KPI Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Children Under Care", f"{kpis['total_children_under_care']:,}")
    with c2:
        kpi_card("Net Intake Pressure (30d avg)", kpis["net_intake_pressure_30d_avg"],
                  "Transfers in minus discharges out, averaged over the last 30 days")
    with c3:
        kpi_card("Care Load Volatility Index", kpis["care_load_volatility_index_30d"],
                  "7-day rolling std. dev. of total system load, averaged over 30 days")
    with c4:
        kpi_card("Backlog Accumulation Rate", f"{kpis['backlog_accumulation_rate_30d']}%",
                  "% of the last 30 days with a sustained (3+ day) positive net intake streak")
    with c5:
        kpi_card("Discharge Offset Ratio", kpis["discharge_offset_ratio_30d_avg"],
                  "Discharges / transfers-in — above 1.0 means the system is relieving backlog")

    st.divider()

    # ---------------- System Load Overview ----------------
    st.subheader("System Load Overview")
    fig = go.Figure()
    for label in selected_metrics:
        col = metric_options[label]
        fig.add_trace(go.Scatter(x=fdf["date"], y=fdf[col], mode="lines", name=label))
        if show_ma and granularity == "Daily" and f"{col}_ma7" in df.columns:
            fig.add_trace(go.Scatter(
                x=fdf["date"], y=df.loc[mask, f"{col}_ma7"] if f"{col}_ma7" in df.columns else None,
                mode="lines", name=f"{label} (7d MA)", line=dict(dash="dot"),
            ))
    fig.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02),
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------------- CBP vs HHS comparison ----------------
    st.subheader("CBP vs HHS Load Comparison")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=fdf["date"], y=fdf["cbp_custody"], name="CBP Custody"))
    fig2.add_trace(go.Bar(x=fdf["date"], y=fdf["hhs_care"], name="HHS Care"))
    fig2.update_layout(barmode="stack", height=400,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    # ---------------- Net intake & backlog ----------------
    st.subheader("Net Intake & Backlog Trends")
    fig3 = go.Figure()
    colors = ["crimson" if v > 0 else "seagreen" for v in fdf["net_daily_intake"]]
    fig3.add_trace(go.Bar(x=fdf["date"], y=fdf["net_daily_intake"], name="Net Daily Intake",
                           marker_color=colors))
    fig3.add_hline(y=0, line_dash="dash", line_color="gray")
    fig3.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Red bars = net inflow (system load growing) · Green bars = net outflow (system load relieving)")

    with st.expander("View underlying data table"):
        st.dataframe(fdf, use_container_width=True)


if __name__ == "__main__":
    main()
