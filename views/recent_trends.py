"""Recent trends: a one-screen winter-season explorer built from the CPCB
daily AQI record - season counts, a daily AQI time series with GRAP orders,
a same-date comparison across winters, and recent Delhi air-quality headlines.
The team's season notes and the GRAP orders open on demand.

AQI is never averaged here: an AQI is a daily index, not a quantity, so the
page reports days, streaks and single-day values instead of mean AQI.

Data: data/delhi_aqi_01Oct24_28Feb25.csv (2024-25) and data/delhi_aqi_cpcb.csv
(Sep 2025 onwards), both CPCB daily bulletin AQI for Delhi.
"""
from datetime import date, datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import AQI_BANDS, band_for
from config.settings import IST
from views.charts import PLOT_CONFIG, add_bands, base_layout, source_line
from views.grap import grap_dialog, orders_by_day
from views import data
from views.render_aqi_fc import band_legend_html
from views.widgets import NEWS_NOTE, news_items_html

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
def _longest_run(s, threshold=300):
    """Longest run of consecutive days with AQI above `threshold`:
    (days, first date, last date), or (0, None, None)."""
    hit = s[s["aqi"] > threshold]["date"].sort_values()
    if hit.empty:
        return 0, None, None
    run_id = (hit.diff() != pd.Timedelta(days=1)).cumsum()
    runs = hit.groupby(run_id)
    best = runs.size().idxmax()
    days = runs.get_group(best)
    return len(days), days.iloc[0], days.iloc[-1]


def _stats_html(s, in_progress):
    worst = s.loc[s["aqi"].idxmax()]
    worst_cat, worst_col = band_for(worst["aqi"], AQI_BANDS)
    vp = int((s["aqi"] > 300).sum())
    sev = int((s["aqi"] > 400).sum())
    good = int((s["aqi"] <= 100).sum())
    run, r0, r1 = _longest_run(s)
    run_note = (f"{r0:%d %b} – {r1:%d %b}" if run > 1 else f"{r0:%d %b}") if run else "none this winter"
    cards = [
        ("Days recorded", f"{len(s)}", "so far" if in_progress else "1 Oct – 28/29 Feb", None),
        ("Worst day", f"{worst['aqi']:.0f}", f"{worst['date']:%d %b %Y} · {worst_cat}", worst_col),
        ("Longest Very Poor+ spell", f"{run} d", run_note, "#fc4d02" if run else None),
        ("Very Poor or worse", f"{vp}", f"days ({vp / len(s):.0%})", "#fc4d02"),
        ("Severe", f"{sev}", "days, AQI above 400", "#e91902"),
        ("Good or Satisfactory", f"{good}", "days, AQI 100 or below", "#03a303"),
    ]
    tiles = "".join(
        f"<div class='lrn-stat'{f' style=\"--c:{c}\"' if c else ''}><span>{escape(k)}</span><b>{escape(v)}</b>"
        f"<small>{escape(n or '')}</small></div>" for k, v, n, c in cards
    )
    return f"<div class='lrn-stats lrn-stats--tight'>{tiles}</div>"


def season_chart(s, orders, height=232):
    """Daily AQI as a time series: a line, with each day's marker in its CPCB
    colour, over the category bands. GRAP orders are dotted lines whose
    markers along the top carry the order on hover."""
    y_max = max(450, float(s["aqi"].max()) + 40)
    # The winter itself (1 Oct to end Feb), or up to the latest day while it runs;
    # GRAP orders outside that window (spring and summer) are left off
    start = pd.Timestamp(year=int(s["date"].min().year if s["date"].min().month >= 10
                                  else s["date"].min().year - 1), month=10, day=1)
    end = min(start + pd.DateOffset(months=5) - pd.Timedelta(days=1), s["date"].max() + pd.Timedelta(days=2))
    orders = {d: o for d, o in orders.items() if start <= pd.Timestamp(d) <= end}
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, y_max)
    fig.add_scatter(x=s["date"], y=s["aqi"], name="Daily AQI", mode="lines+markers",
                    line=dict(color="#0a3d7a", width=1.6),
                    marker=dict(size=6, color=[band_for(v, AQI_BANDS)[1] for v in s["aqi"]],
                                line=dict(width=0.6, color="#ffffff")),
                    customdata=s[["band"]].assign(p=s["pollutant"].fillna("")).values,
                    hovertemplate="%{x|%a %d %b %Y}<br>AQI <b>%{y:.0f}</b> · %{customdata[0]}"
                                  "<br>%{customdata[1]}<extra></extra>")
    tone_colour = {"invoke": "#c22a1e", "revoke": "#1e8e5a", "other": "#46607f"}
    xs, texts, colours = [], [], []
    for day, day_orders in sorted(orders.items()):
        o = next((x for x in day_orders if x["action"] != "other"), day_orders[0])
        colour = tone_colour[o["action"]]
        fig.add_vline(x=pd.Timestamp(day), line=dict(color=colour, width=1.2, dash="dot"))
        xs.append(pd.Timestamp(day))
        texts.append(escape(o["headline"]))
        colours.append(colour)
    if xs:
        fig.add_scatter(x=xs, y=[y_max * 0.97] * len(xs), mode="markers", name="GRAP order",
                        marker=dict(symbol="triangle-down", size=9, color=colours),
                        customdata=texts, hovertemplate="%{x|%d %b}: %{customdata}<extra>GRAP</extra>")
    base_layout(fig, height=height, y_title="AQI", legend=False)
    fig.update_layout(margin=dict(l=48, r=86, t=8, b=28), hovermode="closest")
    fig.update_yaxes(range=[0, y_max])
    rng = [start - pd.Timedelta(hours=12), end + pd.Timedelta(hours=12)]
    if (end - start).days < 75:     # early in a season: weekly dates, not one "Oct" label
        fig.update_xaxes(tickformat="%d %b", dtick=7 * 86400000, tick0=start, range=rng)
    else:
        fig.update_xaxes(tickformat="%b", dtick="M1", ticklabelmode="period", range=rng)
    return fig


def compare_chart(df, seasons, height=420):
    """Daily AQI (not averaged) for each winter, aligned by date in the season."""
    fig = go.Figure()
    add_bands(fig, AQI_BANDS, 500, alpha=0.08)
    for i, season in enumerate(seasons):
        s = df[df["season"] == season].sort_values("season_day")
        fig.add_scatter(x=s["season_day"], y=s["aqi"], name=f"Winter {season}", mode="lines",
                        line=dict(color=SEASON_COLOURS[i % len(SEASON_COLOURS)], width=2.4 if i == 0 else 1.6),
                        customdata=s["date"].dt.strftime("%d %b %Y"),
                        hovertemplate="%{customdata}: AQI %{y:.0f}<extra>" + season + "</extra>")
    ticks = [0, 31, 61, 92, 123]
    base_layout(fig, height=height, y_title="Daily AQI")
    fig.update_layout(margin=dict(r=86), hovermode="x unified")
    fig.update_xaxes(tickvals=ticks, ticktext=["1 Oct", "1 Nov", "1 Dec", "1 Jan", "1 Feb"], range=[0, 150])
    fig.update_yaxes(range=[0, 500])
    return fig


def _same_day(df, day):
    """AQI on the same calendar date in each winter on record, newest first."""
    by_date = df.set_index("date")
    rows = []
    for season in sorted(df["season"].unique(), reverse=True):
        start = int(season[:4])
        year = start if day.month >= 10 else start + 1
        try:
            d = pd.Timestamp(date(year, day.month, day.day))
        except ValueError:          # 29 Feb in a non-leap winter
            continue
        a = by_date["aqi"].get(d)
        rows.append((d, None if a is None or pd.isna(a) else float(a)))
    return rows


def _same_day_html(rows, today):
    if not rows:
        return "<div class='lrn-mini'>No winter on record covers this date.</div>"
    ref = rows[0][1]
    out = []
    for i, (d, a) in enumerate(rows):
        if a is None:
            note = "awaiting today's bulletin" if d.date() == today else "no data"
            out.append(f"<div class='lrn-sd-row'><span>{d:%Y}</span><em class='na'>{note}</em></div>")
            continue
        cat, col = band_for(a, AQI_BANDS)
        diff = "<small>today</small>" if d.date() == today else ""
        if i and ref is not None:
            delta = ref - a
            diff = (f"<small>{rows[0][0]:%Y} was {abs(delta):.0f} {'higher' if delta > 0 else 'lower'}</small>"
                    if round(delta) else f"<small>same as {rows[0][0]:%Y}</small>")
        out.append(
            f"<div class='lrn-sd-row'><span>{d:%Y}</span>"
            f"<b style='--c:{col}'>{a:.0f}</b><i style='background:{col}'>{escape(cat)}</i>{diff}</div>"
        )
    return "<div class='lrn-sd'>" + "".join(out) + "</div>"


def _notes_html(notes):
    return "<ol class='lrn-timeline'>" + "".join(
        f"<li><b>{escape(t)}</b><p>{escape(d)}</p></li>" for t, d in notes) + "</ol>"


@st.dialog("Season notes", width="large")
def notes_dialog(season):
    st.markdown(f"<div class='chart-sub'>Winter {escape(season)}: key observations and GRAP actions recorded "
                "by the Clean Air team</div>", unsafe_allow_html=True)
    st.markdown(_notes_html(RECENT_TRENDS[season]), unsafe_allow_html=True)


@st.dialog("Daily AQI", width="large")
def season_dialog(s, season, orders, in_progress):
    st.markdown(
        f"<div class='chart-title'>Winter {escape(season)}{' (in progress)' if in_progress else ''}</div>"
        "<div class='chart-sub'>One point per day, in its CPCB colour"
        + (" · ▼ GRAP order: red invoked, green revoked; hover to read it" if orders else "") + "</div>",
        unsafe_allow_html=True)
    st.plotly_chart(season_chart(s, orders, height=520), key=f"trend_chart_big_{season}", width="stretch",
                    config=PLOT_CONFIG)
    source_line("cpcb_aqi", note="daily bulletin" + ("; GRAP: team archive" if orders else ""))


@st.dialog("Compare whole winters", width="large")
def compare_dialog(df, seasons):
    picked = st.multiselect("Winters", seasons, default=seasons[:3], key="trend_compare_pick")
    if not picked:
        st.info("Pick at least one winter.")
        return
    st.plotly_chart(compare_chart(df, sorted(picked, reverse=True)), width="stretch", config=PLOT_CONFIG)
    source_line("cpcb_aqi", note="daily AQI from the CPCB bulletin, one value per day, not averaged")


@st.dialog("Delhi air quality in the news", width="large")
def news_dialog(items):
    st.markdown(f"<div class='lrn-news lrn-news--list'>{news_items_html(items)}</div>", unsafe_allow_html=True)
    st.caption(NEWS_NOTE)


# ---------------------------------------------------------------- page --
def render_recent_trends():
    df = load_aqi_history()
    if df.empty:
        st.info("No AQI history is available.")
        return
    seasons = sorted(df["season"].unique(), reverse=True)

    # Row 1: season picker, with notes and GRAP orders on demand
    bar_l, bar_r = st.columns([3, 2], vertical_alignment="center")
    with bar_l:
        season = st.segmented_control("Winter season", options=seasons, selection_mode="single",
                                      default=seasons[0], key="trend_season", label_visibility="collapsed")
    if season not in seasons:
        season = seasons[0]
    s = df[df["season"] == season]
    in_progress = s["date"].max() >= pd.Timestamp.today().normalize() - pd.Timedelta(days=3)
    grap = orders_by_day(season)
    with bar_r, st.container(horizontal=True, horizontal_alignment="right", key="trend-actions"):
        if season in RECENT_TRENDS and st.button("Season notes", icon=":material/notes:", key="trend_notes"):
            notes_dialog(season)
        if grap:
            with st.popover(f"GRAP orders ({len(grap)})", icon=":material/gavel:", type="primary",
                            key="trend_grap_popover"):
                st.caption("Open an order")
                for day in sorted(grap):
                    if st.button(f"{day:%d %b %Y}", key=f"trend_grap_{season}_{day}", type="tertiary"):
                        grap_dialog(season, day)

    # Row 2: season in numbers
    st.markdown(_stats_html(s, in_progress), unsafe_allow_html=True)

    # Row 3: daily AQI time series | same date in other winters | headlines
    left, right, news_col = st.columns([1.9, 1, 1.05], gap="small")
    with left, st.container(border=True, key="trend-season-card"):
        # Pinned to the card's top-right corner by CSS, out of the text flow
        if st.button("", icon=":material/open_in_full:", key="trend_chart_expand", type="tertiary",
                     help="Open a larger chart"):
            season_dialog(s, season, grap, in_progress)
        st.markdown(
            f"<div class='chart-title'>Daily AQI, winter {escape(season)}{' (in progress)' if in_progress else ''}</div>"
            "<div class='chart-sub'>One point per day, in its CPCB colour"
            + (" · ▼ GRAP order: red invoked, green revoked" if grap else "")
            + "</div>", unsafe_allow_html=True)
        st.plotly_chart(season_chart(s, grap), key=f"trend_chart_{season}", width="stretch", config=PLOT_CONFIG)
        source_line("cpcb_aqi", note="daily bulletin" + ("; GRAP: team archive" if grap else ""))
    with right, st.container(border=True, key="trend-compare-card"):
        # Always today (IST): today's AQI against the same date in earlier winters
        today = datetime.now(IST).date()
        st.markdown("<div class='lrn-card-head'><div class='chart-title'>Same date, other winters</div>"
                    f"<span class='lrn-date-badge'>{today:%d %b %Y}</span></div>", unsafe_allow_html=True)
        if today.month in (3, 4, 5, 6, 7, 8, 9):
            st.markdown("<div class='lrn-mini'>Shown during the winter season, 1 Oct to 28/29 Feb.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(_same_day_html(_same_day(df, today), today), unsafe_allow_html=True)
        if st.button("Compare whole winters", icon=":material/stacked_line_chart:", key="trend_compare_open",
                     width="stretch", type="primary"):
            compare_dialog(df, seasons)

    news = data.aqi_news()
    with news_col, st.container(border=True, key="trend-news-card"):
        st.markdown("<div class='chart-title'>In the news</div>", unsafe_allow_html=True)
        if news:
            st.markdown(f"<div class='lrn-news lrn-news--stack'>{news_items_html(news[:3])}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='lrn-mini'>Headlines are unavailable right now.</div>", unsafe_allow_html=True)
        if len(news) > 3 and st.button(f"More headlines ({len(news) - 3})", icon=":material/newspaper:",
                                       key="trend_news_more", width="stretch", type="primary"):
            news_dialog(news)
