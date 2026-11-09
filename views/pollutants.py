"""Pollutants and AQI page: Delhi hourly PM2.5 / PM10 over the CPCB bands, and
the last 7 days of CPCB bulletin AQI.

Replaces the embedded Earthmetry Signals dashboard (an iframe) with charts
drawn from data the app already has:
  - data/signalsfunc_pm25_sample_data.csv - hourly PM2.5 (PM10 when the file
    has it), the shape signalsfunc returns; a sample file for now.
  - data/delhi_aqi_cpcb.csv - the daily CPCB bulletin AQI.

The hourly line is drawn over the shaded CPCB bands. CPCB's bands are defined
for 24-hour averages, so for single hours the shading is a guide, not a CPCB
category.
"""
from datetime import timedelta
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import AQI_BANDS, NAAQS_24H, PM10_BANDS, PM25_BANDS, band_for
from views import data
from views.charts import PLOT_CONFIG, add_bands, base_layout
from views.render_aqi_fc import aqi_chart, band_legend_html
from views.widgets import cpcb_src, icon, side_points, side_source, src

POLLUTANTS = {
    "PM2.5": dict(label="PM₂.₅", bands=PM25_BANDS, colour="#0a3d7a", y_floor=300),
    "PM10": dict(label="PM₁₀", bands=PM10_BANDS, colour="#7a4b0a", y_floor=500),
}
AQI_DAYS = 7


def _period(start, end, fmt="%d %b %Y, %H:%M"):
    return f"{start.strftime(fmt).lstrip('0')} – {end.strftime(fmt).lstrip('0')}"


def pm_chart(df, cols, band_col, height=420, compact=False):
    """One hourly line per pollutant over the shaded CPCB bands of `band_col`."""
    cfg = POLLUTANTS[band_col]
    y_max = max(cfg["y_floor"], float(df[cols].max().max()) * 1.1)
    fig = go.Figure()
    add_bands(fig, cfg["bands"], y_max)
    for c in cols:
        limit = NAAQS_24H.get(c)
        if limit:
            fig.add_hline(y=limit, line=dict(color="#0d2440", width=1.5, dash="dash"))
            fig.add_annotation(x=0.005, xref="x domain", y=limit, yref="y", yanchor="bottom", xanchor="left",
                               showarrow=False, font=dict(size=11, color="#0d2440"),
                               text=f"<b>NAAQS 24-hour {c}: {limit} µg/m³</b>", bgcolor="rgba(255,255,255,0.75)")
        fig.add_scatter(
            x=df["time"], y=df[c], name=f"{c} hourly", mode="lines",
            line=dict(color=POLLUTANTS[c]["colour"], width=2),
            hovertemplate=f"{c}: <b>%{{y:.0f}} µg/m³</b><extra></extra>",
        )
    base_layout(fig, height=height, y_title="µg/m³", legend=len(cols) > 1)
    fig.update_xaxes(hoverformat="%a %d %b, %H:%M IST")
    fig.update_layout(margin=dict(l=40, r=78) if compact else dict(r=86))
    fig.update_yaxes(range=[0, y_max])
    if compact:
        fig.update_xaxes(tickformat="%d<br>%b", dtick=2 * 86400000, tickangle=0)
    else:
        fig.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000)
    return fig


CHART_HEIGHT = 340          # the weather page's strips are 230
CHART_HEIGHT_COMPACT = 300


def _info_html(icon_name, title, period, stat_html, points, source):
    """Left panel of a strip, in the weather page's style: title, period,
    the latest value, two or three short points and a linked source line."""
    return (
        f"<div class='wx-info pol-info'><div class='wx-info-head'>{icon(icon_name, 22)}<span>{escape(title)}</span></div>"
        f"<div class='pol-period'>{escape(period)}</div>"
        f"<div class='pol-info-stat'>{stat_html}</div>{side_points(points)}{source}</div>"
    )


def _cat_chip(cat, colour):
    return f"<em class='pol-chip' style='--c:{colour}'>{escape(cat)}</em>"


def render_pm_tracker(compact=False):
    df = data.pm_hourly()
    cols = [c for c in ("PM2.5", "PM10") if c in df.columns and df[c].notna().any()]
    if not cols:
        st.info("Hourly PM data is not available yet.")
        return
    df = df.dropna(subset=cols, how="all").reset_index(drop=True)
    last = df.iloc[-1]
    names = " and ".join(POLLUTANTS[c]["label"] for c in cols)

    stat, points = "", []
    for c in cols:
        cfg = POLLUTANTS[c]
        if pd.isna(last[c]):
            continue
        _, colour = band_for(last[c], cfg["bands"])
        peak = df.loc[df[c].idxmax()]
        stat += (f"<div class='pol-stat-line'><small>{cfg['label']} · {last['time']:%H:%M, %d %b}</small>"
                 f"<b style='color:{colour}'>{last[c]:.0f}</b><span>µg/m³</span></div>")
        points.append(f"<b>{cfg['label']}</b> peak {peak[c]:.0f} at {peak['time']:%H:%M, %d %b}; "
                      f"average {df[c].mean():.0f} µg/m³.")
    points.append("Shading shows CPCB bands; the dashed line is the 24-hour NAAQS limit. Both are set for "
                  "daily averages, so single hours are a guide.")
    if "PM10" not in cols:
        points.append("<i>PM₁₀ isn't in the current data file yet.</i>")

    with st.container(border=True, key="pol-strip-pm"):
        info, chart = st.columns([1, 3], gap="medium")
        band_col = cols[0]
        with chart:
            if len(cols) > 1:
                band_col = st.segmented_control("**Shade CPCB bands for**", options=cols, default=cols[0],
                                                key="pol_band_col") or cols[0]
            st.plotly_chart(pm_chart(df, cols, band_col, compact=compact,
                                     height=CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT),
                            key="pol_pm_chart", width="stretch", config=PLOT_CONFIG)
            st.markdown(band_legend_html(POLLUTANTS[band_col]["bands"], " µg/m³"), unsafe_allow_html=True)
        with info:
            st.markdown(_info_html(
                "fog", f"{names}, hourly",
                f"{_period(df['time'].min(), df['time'].max(), '%d %b, %H:%M')} IST · {len(df)} hours",
                stat, points,
                side_source("CAAQMS stations via signalsfunc (<b>sample data</b>)",
                            src("cpcb_aqi", "CPCB AQI bands"), src("cpcb_naaqs", "CPCB NAAQS (2009)")),
            ), unsafe_allow_html=True)


def render_aqi_tracker(compact=False):
    hist = data.cpcb_history()
    hist = hist[hist["aqi"].notna()] if not hist.empty else hist
    if hist.empty:
        st.info("No CPCB bulletin AQI is available yet.")
        return
    latest = hist["date"].max()
    start = latest - timedelta(days=AQI_DAYS - 1)
    week = hist[hist["date"] >= start].rename(
        columns={"aqi": "AQI_overall", "pollutant": "prominent_pollutant"}).copy()
    week["date"] = pd.to_datetime(week["date"])
    missing = AQI_DAYS - len(week)
    latest_row = hist[hist["date"] == latest].iloc[0].to_dict()
    cat, colour = band_for(latest_row["aqi"], AQI_BANDS)
    lo, hi = week["AQI_overall"].min(), week["AQI_overall"].max()

    with st.container(border=True, key="pol-strip-aqi"):
        info, chart = st.columns([1, 3], gap="medium")
        with chart:
            st.plotly_chart(aqi_chart(week, compact=compact,
                                      height=CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT),
                            key="pol_aqi_chart", width="stretch", config=PLOT_CONFIG)
            st.markdown(band_legend_html(AQI_BANDS), unsafe_allow_html=True)
        with info:
            st.markdown(_info_html(
                "aqi", "Delhi AQI, last 7 days",
                f"{start.day} {start:%b} – {latest.day} {latest:%b %Y}",
                f"<div class='pol-stat-line'><small>{latest.day} {latest:%b}</small>"
                f"<b style='color:{colour}'>{int(latest_row['aqi'])}</b><span>AQI</span>{_cat_chip(cat, colour)}</div>",
                [f"7-day range <b>{lo:.0f}–{hi:.0f}</b>.",
                 "CPCB's daily bulletin AQI: the 24-hour average up to 4 PM IST."]
                + ([f"<i>{missing} of {AQI_DAYS} days have no bulletin.</i>"] if missing > 0 else []),
                side_source(cpcb_src(latest_row) + f" ({latest.day} {latest:%b})",
                            src("cpcb_aqi", "CPCB AQI bands"),
                            "<a href='/archive' target='_self'>earlier days in the Archive</a>"),
            ), unsafe_allow_html=True)


def render_pollutants_page(compact=False):
    from views.source_apportionment import render_source_strip
    render_pm_tracker(compact)
    render_aqi_tracker(compact)
    render_source_strip(compact)
