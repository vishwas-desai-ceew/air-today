"""Pollutants and AQI page: Delhi hourly PM2.5 / PM10 over the CPCB bands, and
the last 7 days of CPCB bulletin AQI, as one tracker with a PM / AQI switch
(PM by default). The latest PM2.5, PM10 and AQI sit in their own row of tiles
above it, apart from the explanatory text.

Replaces the embedded Earthmetry Signals dashboard (an iframe) with charts
drawn from data the app already has:
  - Earthmetry Signals, signalsfunc.read_cpcb(['PM25', 'PM10'], city = Delhi,
    aggregate_to_city=True): hourly PM2.5 and PM10, the average of all CPCB
    stations in Delhi, cached for an hour (ingestion/cpcb_hourly.py).
    data/signalsfunc_pm25_sample_data.csv is the fallback, labelled as sample.
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
from views.charts import add_bands, base_layout, show_chart
from views.render_aqi_fc import TEXT_ON_WHITE, aqi_chart, band_legend_html
from views.widgets import cpcb_src, icon, side_points, src

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
        if limit and not compact:   # on a phone the two labels overlap; the points below give the limits
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
CHART_HEIGHT_COMPACT = 260
TRACKERS = {"PM": "PM₂.₅ and PM₁₀", "AQI": "AQI"}


def _cat_chip(cat, colour):
    return f"<em class='pol-chip' style='--c:{colour}'>{escape(cat)}</em>"


def _pm_source_line(meta):
    """One line under the tracker: Earthmetry Signals (last refreshed ...) · CPCB AQI bands."""
    if meta["source"] == "live":
        signals = f"Earthmetry Signals (last refreshed: {meta['fetched_at']:%H:%M, %d %b} IST)"
    else:
        signals = "Earthmetry Signals (sample data)"
    return f"<div class='chart-source pol-source'>Source: {signals} · {src('cpcb_aqi', 'CPCB AQI bands')}</div>"


def _aqi_source_line(latest_row, latest):
    return (f"<div class='chart-source pol-source'>Source: {cpcb_src(latest_row)} ({latest.day} {latest:%b}) · "
            f"{src('cpcb_aqi', 'CPCB AQI bands')} · "
            "<a href='/archive' target='_self'>earlier days in the Archive</a></div>")


def _stat_tile(label, stamp, value, unit, cat=None, colour=None):
    chip = _cat_chip(cat, colour) if cat else ""
    ink = TEXT_ON_WHITE.get(cat, colour or "#46607f")
    return (f"<div class='pol-tile' style='--c:{colour or '#46607f'};--t:{ink}'>"
            f"<div class='pol-tile-label'>{label}</div><div class='pol-tile-stamp'>{escape(stamp)}</div>"
            f"<div class='pol-tile-value'><b>{value}</b><span>{unit}</span></div>{chip}</div>")


def _load_pm():
    df, meta = data.pm_hourly()
    cols = [c for c in ("PM2.5", "PM10") if c in df.columns and df[c].notna().any()]
    if cols:
        df = df.dropna(subset=cols, how="all").reset_index(drop=True)
    return df, meta, cols


def _load_aqi_week():
    hist = data.cpcb_history()
    hist = hist[hist["aqi"].notna()] if not hist.empty else hist
    if hist.empty:
        return None
    latest = hist["date"].max()
    start = latest - timedelta(days=AQI_DAYS - 1)
    week = hist[hist["date"] >= start].rename(
        columns={"aqi": "AQI_overall", "pollutant": "prominent_pollutant"}).copy()
    week["date"] = pd.to_datetime(week["date"])
    latest_row = hist[hist["date"] == latest].iloc[0].to_dict()
    return dict(week=week, start=start, latest=latest, latest_row=latest_row)


def stats_html(df, cols, aqi):
    """The headline numbers, on their own row above the tracker: latest hourly
    PM2.5 and PM10 (Earthmetry Signals) and the latest CPCB bulletin AQI."""
    tiles = []
    if cols:
        last = df.iloc[-1]
        for c in ("PM2.5", "PM10"):
            cfg = POLLUTANTS[c]
            if c in cols and pd.notna(last[c]):
                cat, colour = band_for(last[c], cfg["bands"])
                tiles.append(_stat_tile(cfg["label"], f"{last['time']:%H:%M, %d %b} · hourly",
                                        f"{last[c]:.0f}", "µg/m³", cat, colour))
            else:
                tiles.append(_stat_tile(cfg["label"], "not available", "—", "µg/m³"))
    if aqi:
        row, latest = aqi["latest_row"], aqi["latest"]
        cat, colour = band_for(row["aqi"], AQI_BANDS)
        tiles.append(_stat_tile("AQI", f"{latest.day} {latest:%b} · CPCB daily", f"{int(row['aqi'])}", "",
                                cat, colour))
    return f"<div class='pol-tiles'>{''.join(tiles)}</div>" if tiles else ""


def _layout(compact, key, head_html, points_html, draw_chart):
    """Desktop: explainer panel left, chart right. Phone: heading, chart, then the points."""
    with st.container(border=True, key=key):
        if compact:
            st.markdown(f"<div class='wx-info pol-info'>{head_html}</div>", unsafe_allow_html=True)
            draw_chart()
            st.markdown(f"<div class='wx-info pol-info'>{points_html}</div>", unsafe_allow_html=True)
            return
        info, chart = st.columns([1, 3], gap="medium")
        with chart:
            draw_chart()
        with info:
            st.markdown(f"<div class='wx-info pol-info'>{head_html}{points_html}</div>", unsafe_allow_html=True)


def _head(icon_name, title, period):
    return (f"<div class='wx-info-head'>{icon(icon_name, 22)}<span>{escape(title)}</span></div>"
            f"<div class='pol-period'>{escape(period)}</div>")


def render_pm_tracker(compact=False, loaded=None):
    df, meta, cols = loaded or _load_pm()
    if not cols:
        st.info("Hourly PM data is not available yet.")
        return
    names = " and ".join(POLLUTANTS[c]["label"] for c in cols)

    points = []
    for c in cols:
        cfg = POLLUTANTS[c]
        peak = df.loc[df[c].idxmax()]
        points.append(f"<b>{cfg['label']}</b> peak {peak[c]:.0f} at {peak['time']:%H:%M, %d %b}; "
                      f"average {df[c].mean():.0f} µg/m³.")
    limits = ", ".join(f"{POLLUTANTS[c]['label']} {NAAQS_24H[c]}" for c in cols if NAAQS_24H.get(c))
    points.append("Shading shows CPCB bands; the dashed line is the 24-hour NAAQS limit"
                  + (f" ({limits} µg/m³)" if limits else "") + ". Both are set for daily averages, "
                  "so single hours are a guide.")
    if meta["source"] == "live":
        points.append("Each hour is the average across all CPCB monitoring stations in Delhi.")
        if meta["stale"]:
            points.append(f"<i>Couldn't refresh from Earthmetry; showing data fetched "
                          f"{meta['fetched_at']:%H:%M, %d %b}.</i>")
    else:
        points.append("<i>Live data from Earthmetry isn't available, so this is <b>sample data</b>.</i>")
    if "PM10" not in cols:
        points.append("<i>PM₁₀ isn't in the current data yet.</i>")

    def draw():
        band_col = cols[0]
        if len(cols) > 1:
            band_col = st.segmented_control("**Shade CPCB bands for**", options=cols, default=cols[0],
                                            key="pol_band_col") or cols[0]
        show_chart(pm_chart(df, cols, band_col, compact=compact,
                            height=CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT),
                   key="pol_pm_chart", mobile_height=CHART_HEIGHT_COMPACT)
        st.markdown(band_legend_html(POLLUTANTS[band_col]["bands"], " µg/m³"), unsafe_allow_html=True)

    _layout(compact, "pol-strip-pm",
            _head("fog", f"{names}, hourly",
                  f"{_period(df['time'].min(), df['time'].max(), '%d %b, %H:%M')} IST · {len(df)} hours"),
            side_points(points), draw)
    st.markdown(_pm_source_line(meta), unsafe_allow_html=True)


def render_aqi_tracker(compact=False, loaded=None):
    aqi = loaded if loaded is not None else _load_aqi_week()
    if not aqi:
        st.info("No CPCB bulletin AQI is available yet.")
        return
    week, start, latest, latest_row = aqi["week"], aqi["start"], aqi["latest"], aqi["latest_row"]
    missing = AQI_DAYS - len(week)
    lo, hi = week["AQI_overall"].min(), week["AQI_overall"].max()
    points = ([f"7-day range <b>{lo:.0f}–{hi:.0f}</b>.",
               "CPCB's daily bulletin AQI: the 24-hour average up to 4 PM IST."]
              + ([f"<i>{missing} of {AQI_DAYS} days have no bulletin.</i>"] if missing > 0 else []))

    def draw():
        show_chart(aqi_chart(week, compact=compact, height=CHART_HEIGHT_COMPACT if compact else CHART_HEIGHT),
                   key="pol_aqi_chart", mobile_height=CHART_HEIGHT_COMPACT)
        st.markdown(band_legend_html(AQI_BANDS), unsafe_allow_html=True)

    _layout(compact, "pol-strip-aqi",
            _head("aqi", "Delhi AQI, last 7 days", f"{start.day} {start:%b} – {latest.day} {latest:%b %Y}"),
            side_points(points), draw)
    st.markdown(_aqi_source_line(latest_row, latest), unsafe_allow_html=True)


def render_pollutants_page(compact=False):
    pm = _load_pm()
    aqi = _load_aqi_week()
    st.markdown(stats_html(pm[0], pm[2], aqi), unsafe_allow_html=True)
    choice = st.segmented_control("**Tracker**", options=list(TRACKERS), format_func=TRACKERS.get,
                                  default="PM", key="pol_tracker") or "PM"
    if choice == "AQI":
        render_aqi_tracker(compact, aqi)
    else:
        render_pm_tracker(compact, pm)
