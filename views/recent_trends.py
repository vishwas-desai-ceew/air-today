"""Recent trends: a winter-season explorer built from the CPCB daily AQI
record, with GRAP orders overlaid where the season's archive exists, a
winter-on-winter comparison, and the team's written notes for the season.

Data: data/delhi_aqi_01Oct24_28Feb25.csv (2024-25) and data/delhi_aqi_cpcb.csv
(Sep 2025 onwards), both CPCB daily bulletin AQI for Delhi.
"""
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import AQI_BANDS, band_for
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line
from views.grap import grap_dialog, orders_by_day
from views.render_aqi_fc import band_legend_html

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AQI_FILES = ["delhi_aqi_01Oct24_28Feb25.csv", "delhi_aqi_cpcb.csv"]
SEASON_COLOURS = ["#0b6bcb", "#e8590c", "#7048e8", "#1e8e5a"]

# Team notes, written for the 2024-25 winter. Text unchanged.
RECENT_TRENDS = {
    "2024-25": [
        (
            "Persistent poor and very poor PM₂.₅ conditions",
            "Since 13 October 2024, Delhi's 24-hour average PM₂.₅ concentration has been in the poor (>90 µg/m³) or very poor (>121 µg/m³) category every day.",
        ),
        (
            "Severe nighttime PM₂.₅ episodes",
            "Between the last week of October and the last week of November, hourly PM₂.₅ concentrations slipped into the severe category (>250 µg/m³) for a few nighttime hours.",
        ),
        (
            "Peak pollution episode in November",
            "PM₂.₅ concentrations breached 500 µg/m³ from 17 to 19 November.",
        ),
        (
            "Daytime improvement, nighttime deterioration",
            "High daytime wind speeds have brought Delhi's average PM₂.₅ below the poor threshold (90 µg/m³) around 3 PM since the first week of December. Concentrations still cross the very poor threshold (120 µg/m³) at night.",
        ),
        (
            "GRAP eased from Stage IV to Stage II",
            "On 5 December, the Supreme Court allowed CAQM to ease restrictions from GRAP Stage IV, which had been in force since 18 November, to Stage II.",
        ),
        (
            "GRAP changes in December",
            "CAQM invoked GRAP III on 16 December as AQI breached 350, then escalated to GRAP IV at 10 PM as AQI crossed 400. GRAP IV was revoked and GRAP III reimposed on 24 December; GRAP III was revoked on 27 December as air quality improved.",
        ),
        (
            "GRAP III invoked in early January",
            "With AQI above 350 and forecasts indicating adverse conditions, CAQM invoked GRAP III on 3 January. It was later revoked on 5 January.",
        ),
        (
            "GRAP III action in mid-January",
            "An increase in observed AQI on 9 January led to the invocation of GRAP III, which was revoked on 12 January.",
        ),
        (
            "Further GRAP III and IV restrictions",
            "CAQM imposed GRAP III and IV on 15 January. GRAP IV and III restrictions were revoked on 16 and 17 January respectively. GRAP III was imposed again on 29 January and revoked on 3 February.",
        ),
        (
            "GRAP I and II revoked",
            "CAQM revoked GRAP II on 24 February and GRAP I on 3 March following an improvement in AQI.",
        ),
    ],
}


# ----------------------------------------------------------------- data --
@st.cache_data(ttl=600)
def load_aqi_history():
    frames = []
    for name in AQI_FILES:
        path = DATA_DIR / name
        if path.exists():
            df = pd.read_csv(path, usecols=lambda c: c in ("date", "aqi", "category", "pollutant"))
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["date", "aqi", "category", "pollutant"])
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    df = df.dropna(subset=["aqi"]).drop_duplicates("date", keep="last").sort_values("date")
    # Winter season = 1 Oct to end of Feb, labelled by its start year ("2025-26").
    df = df[df["date"].dt.month.isin([10, 11, 12, 1, 2])].copy()
    start = df["date"].dt.year.where(df["date"].dt.month >= 10, df["date"].dt.year - 1)
    df["season"] = start.astype(str) + "-" + (start + 1).astype(str).str[-2:]
    df["season_day"] = (df["date"] - pd.to_datetime(start.astype(str) + "-10-01")).dt.days
    df["band"] = [band_for(v, AQI_BANDS)[0] for v in df["aqi"]]
    return df


# --------------------------------------------------------------- pieces --
def _stats_html(s, season, in_progress):
    worst = s.loc[s["aqi"].idxmax()]
    worst_cat, worst_col = band_for(worst["aqi"], AQI_BANDS)
    vp = int((s["aqi"] > 300).sum())
    sev = int((s["aqi"] > 400).sum())
    good = int((s["aqi"] <= 100).sum())
    cards = [
        ("Days recorded", f"{len(s)}", "so far" if in_progress else "1 Oct – 28/29 Feb", None),
        ("Mean AQI", f"{s['aqi'].mean():.0f}", band_for(s["aqi"].mean(), AQI_BANDS)[0], band_for(s["aqi"].mean(), AQI_BANDS)[1]),
        ("Worst day", f"{worst['aqi']:.0f}", f"{worst['date']:%d %b %Y} · {worst_cat}", worst_col),
        ("Very Poor or worse", f"{vp}", f"days ({vp / len(s):.0%})", "#fc4d02"),
        ("Severe", f"{sev}", "days with AQI above 400", "#e91902"),
        ("Good or Satisfactory", f"{good}", "days with AQI 100 or below", "#03a303"),
    ]
    return "<div class='lrn-stats'>" + "".join(
        f"<div class='lrn-stat'{f' style=\"--c:{c}\"' if c else ''}><span>{escape(k)}</span><b>{escape(v)}</b>"
        f"<small>{escape(n or '')}</small></div>" for k, v, n, c in cards
    ) + "</div>"


def _category_strip(s):
    counts = s["band"].value_counts()
    total = len(s)
    segs = "".join(
        f"<div style='flex:{counts.get(n, 0)};background:{c}' title='{escape(n)}: {counts.get(n, 0)} days'>"
        f"{counts.get(n, 0) if counts.get(n, 0) / total > 0.06 else ''}</div>"
        for n, _lo, _hi, c in AQI_BANDS if counts.get(n, 0)
    )
    return f"<div class='lrn-strip-label'>Days in each CPCB category</div><div class='lrn-strip'>{segs}</div>"


def season_chart(s, orders):
    y_max = max(450, float(s["aqi"].max()) + 60)
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, y_max)
    fig.add_bar(x=s["date"], y=s["aqi"], name="Daily AQI",
                marker=dict(color=[band_for(v, AQI_BANDS)[1] for v in s["aqi"]], line=dict(width=0)),
                customdata=s[["band"]].assign(p=s["pollutant"].fillna("")).values,
                hovertemplate="%{x|%a %d %b %Y}<br>AQI <b>%{y:.0f}</b> · %{customdata[0]}"
                              "<br>%{customdata[1]}<extra></extra>")
    tone_colour = {"invoke": "#c22a1e", "revoke": "#1e8e5a", "other": "#46607f"}
    for day, day_orders in sorted(orders.items()):
        o = next((x for x in day_orders if x["action"] != "other"), day_orders[0])
        tone = o["action"]
        fig.add_vline(x=pd.Timestamp(day), line=dict(color=tone_colour[tone], width=1.4, dash="dot"))
        short = o["headline"]
        fig.add_annotation(x=pd.Timestamp(day), y=y_max, yanchor="top", text=escape(short[:26]), textangle=-90,
                           showarrow=False, font=dict(size=10, color=tone_colour[tone]), xshift=-7,
                           bgcolor="rgba(255,255,255,0.75)")
    base_layout(fig, height=420, y_title="AQI", legend=False)
    fig.update_layout(margin=dict(r=86), bargap=0.08, hovermode="closest")
    fig.update_yaxes(range=[0, y_max])
    fig.update_xaxes(tickformat="%d %b", dtick="M1", ticklabelmode="period")
    return fig


def compare_chart(df, seasons):
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, 500, alpha=0.08)
    for i, season in enumerate(seasons):
        s = df[df["season"] == season].sort_values("season_day")
        roll = s.set_index("season_day")["aqi"].rolling(7, min_periods=3, center=True).mean()
        fig.add_scatter(x=roll.index, y=roll.values, name=f"Winter {season}", mode="lines",
                        line=dict(color=SEASON_COLOURS[i % len(SEASON_COLOURS)], width=3 if i == 0 else 2),
                        hovertemplate=f"{season}: %{{y:.0f}}<extra></extra>")
    ticks = [0, 31, 61, 92, 123]
    base_layout(fig, height=340, y_title="AQI, 7-day mean")
    fig.update_layout(margin=dict(r=86), hovermode="x unified")
    fig.update_xaxes(tickvals=ticks, ticktext=["1 Oct", "1 Nov", "1 Dec", "1 Jan", "1 Feb"], range=[0, 150])
    fig.update_yaxes(range=[0, 500])
    return fig


def _heatmap_html(s, season):
    start_year = int(season[:4])
    by_date = {d.date(): (a, b) for d, a, b in zip(s["date"], s["aqi"], s["band"])}
    colour = {n: c for n, _lo, _hi, c in AQI_BANDS}
    rows = []
    for y, m in [(start_year, 10), (start_year, 11), (start_year, 12), (start_year + 1, 1), (start_year + 1, 2)]:
        cells = []
        for d in range(1, 32):
            try:
                day = date(y, m, d)
            except ValueError:
                cells.append("<i class='none'></i>")
                continue
            if day in by_date:
                a, b = by_date[day]
                cells.append(f"<i style='background:{colour.get(b, '#ccc')}' title='{day:%d %b %Y}: AQI {a:.0f} ({escape(b)})'></i>")
            else:
                cells.append(f"<i class='empty' title='{day:%d %b %Y}: no data'></i>")
        rows.append(f"<div class='lrn-hm-row'><span>{date(y, m, 1):%b}</span>{''.join(cells)}</div>")
    head = "<div class='lrn-hm-row lrn-hm-head'><span></span>" + "".join(
        f"<em>{d if d in (1, 5, 10, 15, 20, 25, 30) else ''}</em>" for d in range(1, 32)) + "</div>"
    return f"<div class='lrn-hm'>{head}{''.join(rows)}</div>"


def _notes_html(notes):
    return "<ol class='lrn-timeline'>" + "".join(
        f"<li><b>{escape(t)}</b><p>{escape(d)}</p></li>" for t, d in notes) + "</ol>"


# ---------------------------------------------------------------- page --
def render_recent_trends():
    df = load_aqi_history()
    if df.empty:
        st.info("No AQI history is available.")
        return
    seasons = sorted(df["season"].unique(), reverse=True)
    season = st.segmented_control("**Winter season**", options=seasons, selection_mode="single",
                                  default=seasons[0], key="trend_season")
    if season not in seasons:
        season = seasons[0]
    s = df[df["season"] == season]
    in_progress = s["date"].max() >= pd.Timestamp.today().normalize() - pd.Timedelta(days=3)

    st.markdown(_stats_html(s, season, in_progress), unsafe_allow_html=True)
    st.markdown(_category_strip(s), unsafe_allow_html=True)

    grap = orders_by_day(season)
    with st.container(border=True, key="trend-season-card"):
        st.markdown(
            f"<div class='chart-title'>Daily AQI, winter {escape(season)}{' (in progress)' if in_progress else ''}</div>"
            "<div class='chart-sub'>Bars coloured by CPCB category"
            + (". Dotted lines mark GRAP orders: red invoked, green revoked." if grap else ".") + "</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(season_chart(s, grap), key=f"trend_chart_{season}", width="stretch", config=PLOT_CONFIG)
        st.markdown(band_legend_html(AQI_BANDS), unsafe_allow_html=True)
        source_line("cpcb_aqi", note="daily AQI from the CPCB bulletin; GRAP dates from the team's GRAP archive"
                    if grap else "daily AQI from the CPCB bulletin")
        if grap:
            st.markdown("<div class='lrn-mini'>Read a GRAP order:</div>", unsafe_allow_html=True)
            with st.container(horizontal=True, key="trend-grap-chips"):
                for day in sorted(grap):
                    if st.button(f"{day:%d %b}", key=f"trend_grap_{season}_{day}", type="tertiary",
                                 icon=":material/gavel:"):
                        grap_dialog(season, day)

    left, right = st.columns([3, 2], gap="medium")
    with left, st.container(border=True, key="trend-compare-card"):
        st.markdown("<div class='chart-title'>Winter on winter</div>"
                    "<div class='chart-sub'>7-day mean AQI by date in the season, every winter on record</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(compare_chart(df, seasons), key="trend_compare", width="stretch", config=PLOT_CONFIG)
        source_line("cpcb_aqi", note="daily AQI from the CPCB bulletin")
    with right, st.container(border=True, key="trend-heatmap-card"):
        st.markdown(f"<div class='chart-title'>Day by day, {escape(season)}</div>"
                    "<div class='chart-sub'>Each square is one day; hover for the AQI</div>",
                    unsafe_allow_html=True)
        st.markdown(_heatmap_html(s, season), unsafe_allow_html=True)

    notes = RECENT_TRENDS.get(season)
    if notes:
        with st.container(border=True, key="trend-notes-card"):
            st.markdown(f"<div class='chart-title'>Season notes, {escape(season)}</div>"
                        "<div class='chart-sub'>Key observations and GRAP actions recorded by the Clean Air team</div>",
                        unsafe_allow_html=True)
            st.markdown(_notes_html(notes), unsafe_allow_html=True)
    elif RECENT_TRENDS:
        st.caption("Written season notes are available for " + ", ".join(RECENT_TRENDS) + ".")
