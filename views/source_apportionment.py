"""Where Delhi's PM2.5 comes from: the AQEWS Decision Support System's daily
source apportionment, scraped from the AQEWS home page by ingestion/aqews.py.

Replaces the static data/sectors.csv table (views/sectors.py, last updated for
1 January 2025 and no longer shown on any page). Sources whose name starts
with "Delhi" are AQEWS's local sources; their sum matches the page's "Local
(Delhi)" share, so everything else (NCR districts, stubble burning, "Others")
is outside Delhi.
"""
from datetime import date, datetime
from html import escape

import plotly.graph_objects as go
import streamlit as st

from config.settings import IST
from views import data
from views.charts import PLOT_CONFIG, base_layout
from views.widgets import icon, side_points, side_source, src

LOCAL, OUTSIDE = "#0b6bcb", "#e9a23b"
TOP_N = 12          # bars shown; the rest are grouped into one bar
STALE_DAYS = 3


def _is_local(name):
    return name.lower().startswith("delhi")


def sources_chart(sources, height=340):
    shown, rest = sources[:TOP_N], sources[TOP_N:]
    names = [s["source"] for s in shown]
    values = [s["percent"] for s in shown]
    colours = [LOCAL if _is_local(n) else OUTSIDE for n in names]
    if rest:
        names.append(f"{len(rest)} smaller sources")
        values.append(round(sum(s["percent"] for s in rest), 1))
        colours.append("#b8c4d3")
    fig = go.Figure(go.Bar(
        x=values[::-1], y=names[::-1], orientation="h", marker=dict(color=colours[::-1], line=dict(width=0)),
        text=[f"{v:.1f}%" for v in values[::-1]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}% of PM2.5<extra></extra>",
    ))
    base_layout(fig, height=height, legend=False)
    fig.update_layout(margin=dict(l=8, r=40, t=8, b=28), bargap=0.3, hovermode="closest")
    fig.update_xaxes(title=dict(text="Share of Delhi's daily-mean PM2.5 (%)", font=dict(size=12)),
                     range=[0, max(values) * 1.15], showgrid=True, gridcolor="#eef3f9")
    fig.update_yaxes(automargin=True, gridcolor="rgba(0,0,0,0)")
    return fig


def render_source_strip(compact=False):
    sa = data.aqews_sources()
    sources = sa.get("sources") or []
    if not sources:
        st.info("The AQEWS source apportionment has not been downloaded yet.")
        return
    day = date.fromisoformat(sa["date"]) if sa.get("date") else None
    local = sa.get("local_percent")
    outside = sa.get("non_local_percent")
    top = next((s for s in sources if s["source"].lower() != "others"), sources[0])
    stubble = next((s for s in sources if "stubble" in s["source"].lower()), None)

    stat = ""
    if local is not None and outside is not None:
        stat = (f"<div class='sa-split'><div><b style='color:{LOCAL}'>{local:.0f}%</b><span>Delhi sources</span></div>"
                f"<div><b style='color:{OUTSIDE}'>{outside:.0f}%</b><span>Outside Delhi</span></div></div>")
    points = [f"Largest named source: <b>{escape(top['source'])}</b>, {top['percent']:.1f}%."]
    if stubble:
        points.append(f"Stubble burning: <b>{stubble['percent']:.1f}%</b>.")
    points.append("Model estimates from the AQEWS Decision Support System, not measurements.")
    if day and (datetime.now(IST).date() - day).days > STALE_DAYS:
        points.append(f"<i>The latest estimate on AQEWS is for {day:%d %b %Y}.</i>")

    with st.container(border=True, key="pol-strip-sources"):
        info, chart = st.columns([1, 3], gap="medium")
        with chart:
            st.plotly_chart(sources_chart(sources, height=300 if compact else 340), key="pol_sources_chart",
                            width="stretch", config=PLOT_CONFIG)
            st.markdown(
                "<div class='band-legend'>"
                f"<span><i style='background:{LOCAL}'></i>Delhi sources</span>"
                f"<span><i style='background:{OUTSIDE}'></i>Outside Delhi (NCR districts, stubble burning, others)</span>"
                "</div>", unsafe_allow_html=True)
        with info:
            st.markdown(
                f"<div class='wx-info pol-info'><div class='wx-info-head'>{icon('layers', 22)}"
                "<span>Where Delhi's PM2.5 comes from</span></div>"
                f"<div class='pol-period'>{'Daily mean, ' + f'{day:%a %d %b %Y}' if day else 'Daily mean'}</div>"
                f"{stat}{side_points(points)}{side_source(src('aqews_dss'))}</div>",
                unsafe_allow_html=True,
            )
