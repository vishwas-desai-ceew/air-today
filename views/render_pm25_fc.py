"""AQEWS 10-day PM2.5 forecast over CPCB PM2.5 bands.

The AQEWS series is 2-hourly; CPCB breakpoints are 24-hour averages, so the
daily mean is drawn (and coloured) against the bands, with the 2-hourly
series behind it for the diurnal shape.
"""
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import PM25_BANDS, band_for
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line
from views.render_aqi_fc import band_legend_html

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_pm25_error_html():
    return """
    <div class="aqi-pm25-error">
       <div class="aqi-forecast-error-title">PM₂.₅ AQEWS forecast temporarily unavailable</div>
        <ul class="custom-list1">
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>10 day PM₂.₅ forecast cannot be displayed at this time</li>
        </ul>
    </div>
    """


def load_pm25_forecast():
    df = pd.read_csv(DATA_DIR / "AQEWS_PM25_forecast.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df


def pm25_chart(df, daily, height=400):
    y_max = max(300, float(df["PM2.5"].max()) * 1.12)
    fig = go.Figure()
    add_bands(fig, PM25_BANDS, y_max)
    fig.add_scatter(
        x=df["time"], y=df["PM2.5"], name="2-hourly forecast", mode="lines",
        line=dict(color="rgba(10,61,122,0.55)", width=1.6),
        fill="tozeroy", fillcolor="rgba(10,61,122,0.06)",
        hovertemplate="2-hourly: %{y:.0f} µg/m³<extra></extra>",
    )
    cats = [band_for(v, PM25_BANDS) for v in daily["mean"]]
    fig.add_scatter(
        x=daily["noon"], y=daily["mean"], name="Daily mean (compare with bands)", mode="markers+text",
        marker=dict(size=16, color=[c for _, c in cats], line=dict(width=2, color="#ffffff"), symbol="circle"),
        text=[f"<b>{v:.0f}</b>" for v in daily["mean"]], textposition="top center",
        textfont=dict(size=12, color="#0d2440"), customdata=[n for n, _ in cats],
        hovertemplate="Daily mean: <b>%{y:.0f} µg/m³</b> · %{customdata}<extra></extra>",
    )
    base_layout(fig, height=height, y_title="PM2.5 (µg/m³)")
    fig.update_layout(margin=dict(r=86))
    fig.update_yaxes(range=[0, y_max])
    fig.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000)
    return fig


def render_pm25_fc(compact=False):
    try:
        df = load_pm25_forecast()
    except Exception:
        st.markdown(get_pm25_error_html(), unsafe_allow_html=True)
        return
    if "PM2.5" not in df.columns or df["PM2.5"].fillna(0).sum() == 0:
        st.markdown(get_pm25_error_html(), unsafe_allow_html=True)
        return

    df = df.dropna(subset=["PM2.5"]).sort_values("time")
    daily = df.groupby(df["time"].dt.normalize())["PM2.5"].agg(["mean", "count"]).reset_index()
    daily["noon"] = daily["time"] + pd.Timedelta(hours=12)
    peak = daily.loc[daily["mean"].idxmax()]
    peak_cat, peak_colour = band_for(peak["mean"], PM25_BANDS)
    over = int((daily["mean"] > 120).sum())

    st.markdown(
        f"<div class='fc-summary {'alert' if over else 'ok'}'>"
        f"<div class='fc-summary-main'>{over} of {len(daily)} days with mean PM2.5 above 120 µg/m³ "
        f"(CPCB <b>Very Poor</b> or worse)</div>"
        f"<div class='fc-summary-peak'>Highest daily mean <b style='color:{peak_colour}'>{peak['mean']:.0f} µg/m³</b> "
        f"({escape(peak_cat)}) on {peak['time']:%a %d %b}</div></div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True, key="fc-pm-card"):
        st.markdown(
            f"<div class='chart-title'>PM2.5 concentration, {df['time'].min():%d %b} – {df['time'].max():%d %b %Y}</div>"
            "<div class='chart-sub'>AQEWS 10 km model, 2-hourly. Dots are daily means, coloured by the CPCB 24-hour "
            "PM2.5 band they fall in.</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(pm25_chart(df, daily, height=320 if compact else 400), key="pm25_chart",
                        width="stretch", config=PLOT_CONFIG)
        st.markdown(band_legend_html(PM25_BANDS, " µg/m³"), unsafe_allow_html=True)
        source_line("iitm_aqews", "cpcb_aqi", note="bands from CPCB Table 3.11 (24-hour breakpoints)")
    partial = daily[daily["count"] < 12]
    if len(partial):
        st.caption("Days with fewer than 12 two-hourly values (usually the first and last day) have a partial-day mean.")
