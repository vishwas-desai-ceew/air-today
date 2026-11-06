"""AQEWS 10-day PM2.5 and PM10 forecasts over the CPCB 24-hour bands.

The AQEWS series are 2-hourly; CPCB breakpoints are 24-hour averages, so the
daily mean is drawn (and coloured) against the bands, with the 2-hourly
series behind it for the diurnal shape.
"""
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import PM10_BANDS, PM25_BANDS, band_for
from config.settings import AQEWS_PM10_CSV, AQEWS_PM25_CSV
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line
from views.render_aqi_fc import band_legend_html

# column, label, bands, file, y floor, "Very Poor" lower bound, chart key
POLLUTANTS = {
    "PM2.5": dict(label="PM₂.₅", bands=PM25_BANDS, path=AQEWS_PM25_CSV, y_floor=300, very_poor=120,
                  note="bands from CPCB Table 3.11 (24-hour breakpoints)"),
    "PM10": dict(label="PM₁₀", bands=PM10_BANDS, path=AQEWS_PM10_CSV, y_floor=500, very_poor=350,
                 note="bands from CPCB National AQI PM10 24-hour breakpoints"),
}


def get_pm_error_html(col="PM2.5"):
    label = POLLUTANTS[col]["label"]
    return f"""
    <div class="aqi-pm25-error">
       <div class="aqi-forecast-error-title">{label} AQEWS forecast temporarily unavailable</div>
        <ul class="custom-list1">
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>10 day {label} forecast cannot be displayed at this time</li>
        </ul>
    </div>
    """


def get_pm25_error_html():
    return get_pm_error_html("PM2.5")


def load_pm_forecast(col="PM2.5"):
    df = pd.read_csv(POLLUTANTS[col]["path"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def load_pm25_forecast():
    return load_pm_forecast("PM2.5")


def pm_chart(df, daily, col="PM2.5", height=400):
    cfg = POLLUTANTS[col]
    y_max = max(cfg["y_floor"], float(df[col].max()) * 1.12)
    fig = go.Figure()
    add_bands(fig, cfg["bands"], y_max)
    fig.add_scatter(
        x=df["time"], y=df[col], name="2-hourly forecast", mode="lines",
        line=dict(color="rgba(10,61,122,0.55)", width=1.6),
        fill="tozeroy", fillcolor="rgba(10,61,122,0.06)",
        hovertemplate="2-hourly: %{y:.0f} µg/m³<extra></extra>",
    )
    cats = [band_for(v, cfg["bands"]) for v in daily["mean"]]
    fig.add_scatter(
        x=daily["noon"], y=daily["mean"], name="Daily mean (compare with bands)", mode="markers+text",
        marker=dict(size=16, color=[c for _, c in cats], line=dict(width=2, color="#ffffff"), symbol="circle"),
        text=[f"<b>{v:.0f}</b>" for v in daily["mean"]], textposition="top center",
        textfont=dict(size=12, color="#0d2440"), customdata=[n for n, _ in cats],
        hovertemplate="Daily mean: <b>%{y:.0f} µg/m³</b> · %{customdata}<extra></extra>",
    )
    base_layout(fig, height=height, y_title=f"{col} (µg/m³)")
    fig.update_layout(margin=dict(r=86))
    fig.update_yaxes(range=[0, y_max])
    fig.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000)
    return fig


def pm25_chart(df, daily, height=400):
    return pm_chart(df, daily, "PM2.5", height)


def render_pm_fc(col="PM2.5", compact=False):
    cfg = POLLUTANTS[col]
    try:
        df = load_pm_forecast(col)
    except Exception:
        st.markdown(get_pm_error_html(col), unsafe_allow_html=True)
        return
    if col not in df.columns or df[col].fillna(0).sum() == 0:
        st.markdown(get_pm_error_html(col), unsafe_allow_html=True)
        return

    df = df.dropna(subset=[col]).sort_values("time")
    daily = df.groupby(df["time"].dt.normalize())[col].agg(["mean", "count"]).reset_index()
    daily["noon"] = daily["time"] + pd.Timedelta(hours=12)
    peak = daily.loc[daily["mean"].idxmax()]
    peak_cat, peak_colour = band_for(peak["mean"], cfg["bands"])
    over = int((daily["mean"] > cfg["very_poor"]).sum())

    st.markdown(
        f"<div class='fc-summary {'alert' if over else 'ok'}'>"
        f"<div class='fc-summary-main'>{over} of {len(daily)} days with mean {cfg['label']} above "
        f"{cfg['very_poor']} µg/m³</div>"
        f"<div class='fc-summary-peak'>Highest daily mean <b style='color:{peak_colour}'>{peak['mean']:.0f} µg/m³</b> "
        f"({escape(peak_cat)}) on {peak['time']:%a %d %b}</div></div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True, key=f"fc-pm-card-{col.replace('.', '')}"):
        st.markdown(
            f"<div class='chart-title'>{cfg['label']} concentration, {df['time'].min():%d %b} – {df['time'].max():%d %b %Y}</div>"
            f"<div class='chart-sub'>AQEWS 10 km model, 2-hourly. Dots are daily means, coloured by the CPCB 24-hour "
            f"{cfg['label']} band they fall in.</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(pm_chart(df, daily, col, height=320 if compact else 400), key=f"{col}_chart",
                        width="stretch", config=PLOT_CONFIG)
        st.markdown(band_legend_html(cfg["bands"], " µg/m³"), unsafe_allow_html=True)
        source_line("iitm_aqews", "cpcb_aqi", note=cfg["note"])
    partial = daily[daily["count"] < 12]
    if len(partial):
        st.caption("Days with fewer than 12 two-hourly values (usually the first and last day) have a partial-day mean.")


def render_pm25_fc(compact=False):
    render_pm_fc("PM2.5", compact)


def render_pm10_fc(compact=False):
    render_pm_fc("PM10", compact)
