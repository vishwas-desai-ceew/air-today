"""AQEWS 10-day AQI forecast: calendar tiles + time series over the CPCB AQI bands.

Strictly AQEWS: no CPCB bulletin values or AQEWS text-bulletin categories here
(they disagreed with the numeric forecast and read as conflicting).
"""
from datetime import datetime
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import AQI_BANDS, AQI_HEALTH, band_for
from config.settings import IST
from views import data
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line

AQEWS_PORTAL = "https://ews.tropmet.res.in/"
# Category colours as text on a white tile: Moderate's yellow is too pale to read, so darken it
TEXT_ON_WHITE = {"Moderate": "#9a7b00"}


def is_data_flat(df, col, window=6):
    if col not in df.columns or len(df[col].dropna()) < window:
        return False
    recent = df[col].dropna().tail(window)
    if all(recent <= 0):
        return True
    if recent.nunique() == 1:
        return True
    return False


def is_data_old(df):
    """True when the forecast's last day is before today (IST, not the server clock)."""
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return True
    return dates.max().date() < datetime.now(IST).date()


def get_aqi_error_msg():
    return """
    <div class="aqi-forecast-error">
        <div class="aqi-forecast-error-title">AQI forecast temporarily unavailable</div>
        <ul class="custom-list1">
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>10 day AQI forecast data appears unresponsive or stale</li>
            <li>Forecasts and insights cannot be displayed at this time</li>
        </ul>
    </div>
    """


def get_error_message():
    """(outage?, forecast) for the AQEWS AQI forecast.

    Reads through views.data.aqews_daily (cached; an empty frame when the file
    is missing or empty), so a missing or unreadable forecast is reported as an
    outage instead of raising. It used to read the CSV directly from
    dashboard.py on every page, so a missing file crashed the whole app."""
    df = data.aqews_daily().copy()
    if df.empty or not {"date", "AQI_overall"} <= set(df.columns):
        return True, pd.DataFrame(columns=["date", "AQI_overall"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    return bool(df.empty or is_data_flat(df, "AQI_overall") or is_data_old(df)), df


def aqews_outage() -> bool:
    """True when the AQEWS forecast is missing, stale or flat. Never raises."""
    try:
        return get_error_message()[0]
    except Exception:
        return True


def aqi_chart(df, height=400, compact=False):
    """Daily AQEWS AQI as a time series over the CPCB category bands (like the
    PM2.5 chart): one point per day, coloured by its category."""
    cats = [band_for(v, AQI_BANDS) for v in df["AQI_overall"]]
    y_max = max(450, float(df["AQI_overall"].max()) + 50)
    pollutant = df.get("prominent_pollutant", pd.Series([""] * len(df))).fillna("")
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, y_max)
    fig.add_scatter(
        x=df["date"], y=df["AQI_overall"], name="AQEWS AQI forecast", mode="lines+markers+text",
        line=dict(color="rgba(13,36,64,0.55)", width=2.2, shape="spline", smoothing=0.6),
        marker=dict(size=9 if compact else 14, color=[c for _, c in cats], line=dict(width=2, color="#ffffff")),
        text=[f"<b>{v:.0f}</b>" for v in df["AQI_overall"]], textposition="top center",
        textfont=dict(size=9 if compact else 12, color="#0d2440"), cliponaxis=False,
        customdata=list(zip([n for n, _ in cats], pollutant)),
        hovertemplate="AQI <b>%{y:.0f}</b> · %{customdata[0]}<br>Prominent: %{customdata[1]}<extra></extra>",
    )
    base_layout(fig, height=height, y_title="AQI", legend=False)
    fig.update_layout(margin=dict(l=40, r=78) if compact else dict(r=86))
    fig.update_yaxes(range=[0, y_max])
    if compact:
        fig.update_xaxes(tickformat="%d<br>%b", dtick=2 * 86400000, tickangle=0)
    else:
        fig.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000)
    return fig


def _tiles_html(df):
    """Calendar-page tiles: neutral page, with only the AQI value and category
    in the category colour."""
    tiles = []
    for _, r in df.iterrows():
        cat, colour = band_for(r["AQI_overall"], AQI_BANDS)
        ink = TEXT_ON_WHITE.get(cat, colour)
        tiles.append(
            f"<div class='fc-cal' style='--c:{ink}'>"
            f"<div class='fc-cal-head'><span>{r['date']:%a}</span><i> · </i><span>{r['date'].day} {r['date']:%b}</span></div>"
            f"<div class='fc-cal-body'><div class='fc-cal-aqi'>{r['AQI_overall']:.0f}</div>"
            f"<div class='fc-cal-cat'>{escape(cat or '')}</div></div></div>"
        )
    return "<div class='fc-cals'>" + "".join(tiles) + "</div>"


def band_legend_html(bands, unit=""):
    return "<div class='band-legend'>" + "".join(
        f"<span><i style='background:{c}'></i>{escape(n)} <small>{lo}–{hi}{unit}</small></span>" if hi is not None
        else f"<span><i style='background:{c}'></i>{escape(n)} <small>&gt;{lo - 1}{unit}</small></span>"
        for n, lo, hi, c in bands
    ) + "</div>"


def render_aqi_fc(isMobile=False, compact=False):
    flag, df_aqi = get_error_message()
    if flag:
        st.markdown(get_aqi_error_msg(), unsafe_allow_html=True)
        return
    df = df_aqi.dropna(subset=["AQI_overall"]).sort_values("date")

    with st.container(border=True, key="fc-chart-card"):
        # Day cards sit inside the chart card, between the title and the plot
        st.markdown(
            f"<div class='chart-title'>Daily AQI forecast, {df['date'].min():%d %b} – {df['date'].max():%d %b %Y}</div>"
            "<div class='chart-sub'>AQEWS forecast AQI; points are coloured by category and the shading "
            "marks the AQI category bands.</div>" + _tiles_html(df),
            unsafe_allow_html=True,
        )
        st.plotly_chart(aqi_chart(df, height=320 if compact else 400, compact=compact), key="aqi_forecast_chart",
                        width="stretch", config=PLOT_CONFIG)
        st.markdown(band_legend_html(AQI_BANDS), unsafe_allow_html=True)
        source_line("iitm_aqews", "cpcb_aqi", note="forecast AQI from AQEWS; category bands from CPCB Table 3.2")


@st.dialog("What the AQI categories mean (CPCB)", width="large")
def aqi_categories_dialog():
    st.markdown(
        "<table class='band-table'><tr><th>Category</th><th>AQI</th><th>Possible health impact</th></tr>"
        + "".join(f"<tr><td><i style='background:{c}'></i>{escape(n)}</td><td>{lo}–{hi}</td>"
                  f"<td>{escape(AQI_HEALTH[n])}</td></tr>" for n, lo, hi, c in AQI_BANDS)
        + "</table>",
        unsafe_allow_html=True,
    )
    source_line("cpcb_aqi", note="Table 3.12")


def render_aqi_categories_button():
    """Opens the CPCB category table; sits beside the AQEWS bulletin button."""
    if st.button("What the AQI categories mean", key="open_aqi_categories", icon=":material/health_and_safety:"):
        aqi_categories_dialog()
