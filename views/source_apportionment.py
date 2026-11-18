"""Where Delhi's PM2.5 comes from: the AQEWS Decision Support System's daily
source apportionment, scraped from the AQEWS home page by ingestion/aqews.py.
Shown as a donut chart in a pop-up on the AQEWS page (it used to be a bar
chart strip on the Pollutants and AQI page).

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
from views.charts import base_layout, show_chart
from views.widgets import side_points, src

LOCAL, OUTSIDE = "#0b6bcb", "#e9a23b"
# Slice shades: Delhi's own sources in blues, everything outside Delhi in ambers,
# so the local/outside split reads at a glance and slices stay distinguishable.
LOCAL_SHADES = ["#0b4f9c", "#0b6bcb", "#3d8ee0", "#6eaaea", "#9fc6f2", "#c6ddf7"]
OUTSIDE_SHADES = ["#b86e0b", "#d4870f", "#e9a23b", "#f0b866", "#f5cd92", "#f9e0bd"]
GREY = "#b8c4d3"
TOP_N = 9           # slices shown; the rest (and AQEWS's own "Others") become one grey slice
STALE_DAYS = 3


def _is_local(name):
    return name.lower().startswith("delhi")


def pie_slices(sources):
    """[(name, percent, colour, is_local)] for the donut: the TOP_N largest named
    sources, then the remainder grouped, kept on its side of the Delhi/outside
    split ("Other Delhi sources", and "Other sources outside Delhi", which
    includes AQEWS's own "Others")."""
    named = [s for s in sources if s["source"].lower() != "others"]
    shown, rest = named[:TOP_N], named[TOP_N:]
    rest_local = sum(s["percent"] for s in rest if _is_local(s["source"]))
    rest_outside = (sum(s["percent"] for s in rest if not _is_local(s["source"]))
                    + sum(s["percent"] for s in sources if s["source"].lower() == "others"))
    li = oi = 0
    out = []
    for s in shown:
        if _is_local(s["source"]):
            colour, li = LOCAL_SHADES[min(li, len(LOCAL_SHADES) - 1)], li + 1
        else:
            colour, oi = OUTSIDE_SHADES[min(oi, len(OUTSIDE_SHADES) - 1)], oi + 1
        out.append((s["source"], s["percent"], colour, _is_local(s["source"])))
    if rest_local > 0:
        out.append(("Other Delhi sources", round(rest_local, 1), LOCAL_SHADES[-1], True))
    if rest_outside > 0:
        out.append(("Other sources outside Delhi", round(rest_outside, 1), GREY, False))
    return out


def sources_pie(sources, local=None, outside=None, height=340):
    slices = pie_slices(sources)
    fig = go.Figure(go.Pie(
        labels=[n for n, *_ in slices], values=[v for _, v, *_ in slices],
        marker=dict(colors=[c for _, _, c, _ in slices], line=dict(color="#ffffff", width=2)),
        hole=0.58, sort=False, direction="clockwise", rotation=90,
        textinfo="percent", texttemplate=[f"{v:.0f}%" if v >= 4 else "" for _, v, *_ in slices],
        textfont=dict(size=12, color="#0d2440"), insidetextorientation="horizontal",
        hovertemplate="%{label}: <b>%{value:.1f}%</b> of PM2.5<extra></extra>",
    ))
    base_layout(fig, height=height, legend=False)
    fig.update_layout(margin=dict(l=8, r=8, t=8, b=8), hovermode="closest")
    if local is not None:
        centre = (f"<b style='font-size:26px;color:{LOCAL}'>{local:.0f}%</b><br>"
                  "<span style='font-size:12px'>from Delhi</span>")
        if outside is not None:
            centre += (f"<br><b style='font-size:15px;color:{OUTSIDE_SHADES[0]}'>{outside:.0f}%</b>"
                       "<span style='font-size:12px'> outside</span>")
        fig.add_annotation(text=centre, showarrow=False, x=0.5, y=0.5, font=dict(color="#46607f"))
    return fig


def _legend_html(sources):
    slices = pie_slices(sources)
    def col(title, rows):
        return (f"<div><div class='sa-legend-h'>{title}</div>"
                + "".join(f"<div class='sa-legend-row'><i style='background:{c}'></i><span>{escape(n)}</span>"
                          f"<b>{v:.1f}%</b></div>" for n, v, c, _ in rows) + "</div>")
    local = [s for s in slices if s[3]]
    outside = [s for s in slices if not s[3]]
    return f"<div class='sa-legend'>{col('Delhi sources', local)}{col('Outside Delhi', outside)}</div>"


def render_source_apportionment(compact=False):
    """Body of the source apportionment pop-up on the AQEWS page."""
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

    st.markdown(
        f"<div class='pol-period'>{'Daily mean PM2.5, ' + f'{day:%a %d %b %Y}' if day else 'Daily mean PM2.5'}</div>",
        unsafe_allow_html=True)
    show_chart(sources_pie(sources, local, outside, height=300), key="aqews_sources_pie", mobile_height=280)
    st.markdown(_legend_html(sources), unsafe_allow_html=True)
    points = [f"Largest named source: <b>{escape(top['source'])}</b>, {top['percent']:.1f}%."]
    if stubble:
        points.append(f"Stubble burning: <b>{stubble['percent']:.1f}%</b>.")
    points.append("Model estimates from the AQEWS Decision Support System, not measurements. "
                  "Sources named \"Delhi …\" are inside Delhi; NCR districts, stubble burning and "
                  "AQEWS's \"Others\" are outside it.")
    if day and (datetime.now(IST).date() - day).days > STALE_DAYS:
        points.append(f"<i>The latest estimate on AQEWS is for {day:%d %b %Y}.</i>")
    fetched = (sa.get("fetched_at") or "")[:16].replace("T", " ")
    st.markdown(side_points(points)
                + f"<div class='chart-source'>Source: {src('aqews_dss')}"
                + (f" · fetched {escape(fetched)} IST" if fetched else "") + "</div>",
                unsafe_allow_html=True)


@st.dialog("Where Delhi's PM2.5 comes from", width="large")
def source_dialog(compact=False):
    render_source_apportionment(compact)


def render_source_button(compact=False):
    sa = data.aqews_sources()
    if not sa.get("sources"):
        return
    if st.button("Source apportionment", key="open_aqews_sources", icon=":material/donut_large:"):
        source_dialog(compact)
