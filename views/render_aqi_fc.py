"""AQEWS 10-day AQI forecast: severity tiles + bar chart over CPCB AQI bands."""
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import AQI_BANDS, AQI_HEALTH, band_for
from views import data
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

AQEWS_PORTAL = "https://ews.tropmet.res.in/"
SEVERITY_RANK = {name: i for i, (name, *_rest) in enumerate(AQI_BANDS)}


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
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    last_date = df["date"].max().date()
    return last_date < datetime.today().date()


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
    df_aqi = pd.read_csv(DATA_DIR / "AQEWS_AQI_forecast.csv")
    df_aqi['date'] = pd.to_datetime(df_aqi['date'])
    error_flag = False
    if is_data_flat(df_aqi, "AQI_overall") or is_data_old(df_aqi):
        error_flag = True
    return error_flag, df_aqi


def aqi_chart(df, height=400):
    """Daily AQI bars coloured by CPCB category, over the CPCB bands."""
    cats = [band_for(v, AQI_BANDS) for v in df["AQI_overall"]]
    y_max = max(450, float(df["AQI_overall"].max()) + 50)
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, y_max)
    fig.add_bar(
        x=df["date"], y=df["AQI_overall"], name="AQI (overall)",
        marker=dict(color=[c for _, c in cats], line=dict(width=0), cornerradius=6),
        text=[f"<b>{v:.0f}</b>" for v in df["AQI_overall"]], textposition="outside",
        textfont=dict(size=13, color="#0d2440"), cliponaxis=False,
        customdata=list(zip([n for n, _ in cats], df.get("prominent_pollutant", pd.Series([""] * len(df))).fillna(""))),
        hovertemplate="AQI <b>%{y:.0f}</b> · %{customdata[0]}<br>Prominent: %{customdata[1]}<extra></extra>",
    )
    base_layout(fig, height=height, y_title="AQI", legend=False)
    fig.update_layout(margin=dict(r=86))
    fig.update_yaxes(range=[0, y_max])
    fig.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000)
    return fig


def _tiles_html(df, bulletin):
    tiles = []
    for _, r in df.iterrows():
        cat, colour = band_for(r["AQI_overall"], AQI_BANDS)
        b = bulletin.get(r["date"].date())
        cls = "severe" if "Severe" in (cat, b) else "alert" if SEVERITY_RANK.get(cat, 0) >= SEVERITY_RANK["Very Poor"] else ""
        b_html = (f"<div class='fc-tile-bulletin'>Bulletin: {escape(str(b))}</div>"
                  if b and str(b) != cat else "")
        tiles.append(
            f"<div class='fc-tile {cls}' style='--c:{colour}'>"
            f"<div class='fc-tile-day'>{r['date']:%a}</div><div class='fc-tile-date'>{r['date']:%d %b}</div>"
            f"<div class='fc-tile-aqi'>{r['AQI_overall']:.0f}</div><div class='fc-tile-cat'>{escape(cat or '')}</div>"
            f"{b_html}</div>"
        )
    return "<div class='fc-tiles'>" + "".join(tiles) + "</div>"


def _summary_html(df, bulletin=None):
    cats = [band_for(v, AQI_BANDS)[0] for v in df["AQI_overall"]]
    bad = sum(SEVERITY_RANK.get(c, 0) >= SEVERITY_RANK["Very Poor"] for c in cats)
    severe = sum(c == "Severe" for c in cats)
    peak = df.loc[df["AQI_overall"].idxmax()]
    peak_cat, peak_colour = band_for(peak["AQI_overall"], AQI_BANDS)
    n = len(df)
    b_severe = sorted(d for d, c in (bulletin or {}).items()
                      if str(c) == "Severe" and d in set(df["date"].dt.date))
    level = "severe" if severe or b_severe else "alert" if bad else "ok"
    headline = (f"{severe} of {n} days forecast <b>Severe</b>" if severe
                else f"{bad} of {n} days forecast <b>Very Poor or worse</b>" if bad
                else f"No day forecast worse than {escape(max(cats, key=lambda c: SEVERITY_RANK.get(c, 0)))}")
    return (
        f"<div class='fc-summary {level}'>"
        f"<div class='fc-summary-main'>{headline}</div>"
        f"<div class='fc-summary-peak'>Peak <b style='color:{peak_colour}'>{peak['AQI_overall']:.0f}</b> "
        f"({escape(peak_cat)}) on {peak['date']:%a %d %b}</div>"
        + (f"<div class='fc-summary-peak'>AQEWS text bulletin forecasts <b style='color:#e91902'>Severe</b> on "
           f"{', '.join(d.strftime('%a %d %b') for d in b_severe)}</div>" if b_severe else "")
        + f"<div class='fc-summary-health'>CPCB: {escape(AQI_HEALTH.get(peak_cat, ''))}</div></div>"
    )


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
    bf = data.bulletin_forecast()
    bulletin = ({r["date"]: r["category"] for _, r in bf.iterrows() if pd.notna(r.get("category"))}
                if not bf.empty and "category" in bf.columns else {})

    st.markdown(_summary_html(df, bulletin), unsafe_allow_html=True)
    st.markdown(_tiles_html(df, bulletin), unsafe_allow_html=True)
    with st.container(border=True, key="fc-chart-card"):
        st.markdown(
            f"<div class='chart-title'>Daily AQI, {df['date'].min():%d %b} – {df['date'].max():%d %b %Y}</div>"
            "<div class='chart-sub'>Bars are coloured by CPCB AQI category; shading marks the category bands.</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(aqi_chart(df, height=320 if compact else 400), key="aqi_forecast_chart",
                        width="stretch", config=PLOT_CONFIG)
        st.markdown(band_legend_html(AQI_BANDS), unsafe_allow_html=True)
        source_line("iitm_aqews", "cpcb_aqi", note="forecast AQI from AQEWS; bands from CPCB Table 3.2")
    if bulletin:
        st.caption("“Bulletin” on a tile is the category in the AQEWS text bulletin where it differs from the "
                   "numeric model forecast.")
    with st.expander("What the AQI categories mean (CPCB)", icon=":material/health_and_safety:"):
        st.markdown(
            "<table class='band-table'><tr><th>Category</th><th>AQI</th><th>Possible health impact</th></tr>"
            + "".join(f"<tr><td><i style='background:{c}'></i>{escape(n)}</td><td>{lo}–{hi}</td>"
                      f"<td>{escape(AQI_HEALTH[n])}</td></tr>" for n, lo, hi, c in AQI_BANDS)
            + "</table>",
            unsafe_allow_html=True,
        )
        source_line("cpcb_aqi", note="Table 3.12")
