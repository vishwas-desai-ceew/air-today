"""Farm fires page: paddy residue burning events from the ICAR-IARI CREAMS
daily bulletin (ingestion/creams.py).

Everything is drawn from the bulletin's own tables, not its images:
    data/creams_fires.csv        date, state, events      -> cards, season charts
    data/creams_fire_events.csv  one row per fire          -> district chart, map
    data/creams_bulletin.json    number, dates, highlights -> header and notes
"""
from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import SOURCES
from ingestion.creams import STATES
from views import data
from views.charts import PLOT_CONFIG, base_layout, hex_rgba
from views.components import chart_card, metric_card, warning_card

STATE_COLOURS = {
    "Punjab": "#e0541b", "Haryana": "#0a3d7a", "Uttar Pradesh": "#2f9e8f", "Delhi": "#7b5ea7",
    "Rajasthan": "#c48a00", "Madhya Pradesh": "#8c564b", "Uttarakhand": "#5a6b85",
}
PB_HR = "Punjab + Haryana"
ALL = "All seven"
AREAS = {PB_HR: ["Punjab", "Haryana"], **{s: [s] for s in STATES}, ALL: STATES}
SEASON_START = (9, 15)  # CREAMS counts from 15 September each year


def _d(day) -> str:
    return f"{day.day} {day:%b %Y}"


def _source_line():
    name, url = SOURCES["creams"]
    return (f"<div class='chart-source'>Source: <a href='{url}' target='_blank' rel='noopener'>{escape(name)}</a>, "
            "ICAR-IARI, New Delhi</div>")


def _season(daily: pd.DataFrame, year: int) -> pd.DataFrame:
    start = date(year, *SEASON_START)
    return daily[(daily["date"] >= start) & (daily["date"] <= date(year, 12, 31))]


# ------------------------------------------------------------------ pieces --
def render_header(meta: dict, latest: date):
    bits = [f"Bulletin no. {meta['number']}" if meta.get("number") else None,
            f"fires on {_d(latest)}",
            f"issued {_d(date.fromisoformat(meta['issue_date']))}" if meta.get("issue_date") else None]
    link = (f" · <a href='{escape(meta['url'])}' target='_blank' rel='noopener'>open the bulletin (PDF) ↗</a>"
            if meta.get("url") else "")
    st.markdown(f"<div class='ceew-caption'>{' · '.join(b for b in bits if b)}{link}</div>", unsafe_allow_html=True)


def render_state_cards(daily: pd.DataFrame, latest: date):
    """One card per state: the day's events, change vs the previous day, and
    the season so far against the same dates last year."""
    prev = daily[daily["date"] < latest]["date"].max()
    season, last = _season(daily, latest.year), _season(daily, latest.year - 1)
    cutoff_last = date(latest.year - 1, latest.month, latest.day)
    for row in (STATES[:4], STATES[4:]):
        cols = st.columns(4)
        for col, state in zip(cols, row):
            s = daily[daily["state"] == state]
            today = s.loc[s["date"] == latest, "events"]
            if today.empty:
                continue
            before = s.loc[s["date"] == prev, "events"]
            total = int(season.loc[season["state"] == state, "events"].sum())
            ly = int(last.loc[(last["state"] == state) & (last["date"] <= cutoff_last), "events"].sum())
            change = round(100 * (total - ly) / ly) if ly else None
            vs = ("" if change is None else f" · same as {latest.year - 1}" if change == 0
                  else f" · {change:+d}% vs {latest.year - 1}")
            with col:
                metric_card(state, f"{int(today.iloc[0]):,}",
                            caption=f"Season {total:,}{vs}",
                            delta=None if before.empty else int(today.iloc[0] - before.iloc[0]),
                            delta_good_when="down", color=STATE_COLOURS[state])


def render_highlights(meta: dict):
    """The bulletin's own summary, as published. The first sentence (the
    method) goes into the note at the bottom instead."""
    lines = [s for s in meta.get("highlights", []) if "Standard Protocol" not in s]
    if not lines:
        return
    with chart_card(title="Bulletin highlights", caption="As published by CREAMS (UK = Uttarakhand, MP = Madhya Pradesh)."):
        st.markdown("\n".join(f"- {escape(s)}" for s in lines))


def cumulative_chart(daily: pd.DataFrame, states: list, latest: date, height=400):
    """Season-to-date events for every year, on a common 15 Sep - axis.
    Earlier years run only to the same date, as in the bulletin."""
    fig = go.Figure()
    df = daily[daily["state"].isin(states)]
    years = sorted({d.year for d in df["date"]})
    for year in years:
        s = _season(df, year).groupby("date", as_index=False)["events"].sum().sort_values("date")
        if s.empty:
            continue
        x = [pd.Timestamp(latest.year, d.month, d.day) for d in s["date"]]
        current = year == latest.year
        fig.add_scatter(
            x=x, y=s["events"].cumsum(), name=str(year), mode="lines",
            line=dict(color="#e0541b" if current else hex_rgba("#0a3d7a", 0.25 + 0.6 * (year - years[0]) / max(1, len(years) - 1)),
                      width=3.2 if current else 1.6),
            hovertemplate=f"{year}: <b>%{{y:,}}</b><extra></extra>",
        )
    base_layout(fig, height=height, y_title="Events since 15 Sep (cumulative)")
    fig.update_xaxes(tickformat="%d %b")
    fig.update_yaxes(rangemode="tozero")
    return fig


def daily_chart(daily: pd.DataFrame, states: list, latest: date, height=360):
    """This season's events per day, stacked by state, with last year's daily
    total for the same dates as a line."""
    fig = go.Figure()
    cur = _season(daily, latest.year)
    for state in states:
        s = cur[cur["state"] == state].sort_values("date")
        fig.add_bar(x=pd.to_datetime(s["date"]), y=s["events"], name=state,
                    marker=dict(color=STATE_COLOURS[state]),
                    hovertemplate=f"{state}: <b>%{{y:,}}</b><extra></extra>")
    last = _season(daily, latest.year - 1)
    last = last[last["state"].isin(states)].groupby("date", as_index=False)["events"].sum()
    if not last.empty:
        fig.add_scatter(x=[pd.Timestamp(latest.year, d.month, d.day) for d in last["date"]], y=last["events"],
                        name=f"{latest.year - 1} (all selected)", mode="lines",
                        line=dict(color="#46607f", width=1.6, dash="dot"),
                        hovertemplate=f"{latest.year - 1}: <b>%{{y:,}}</b><extra></extra>")
    base_layout(fig, height=height, y_title="Events per day")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat="%d %b")
    return fig


def district_chart(events: pd.DataFrame, top=15):
    counts = (events.groupby(["state", "district"]).size().reset_index(name="n")
              .sort_values("n", ascending=False).head(top).iloc[::-1])
    fig = go.Figure(go.Bar(
        x=counts["n"], y=[f"{d} ({s})" if len(events["state"].unique()) > 1 else d
                          for d, s in zip(counts["district"], counts["state"])],
        orientation="h", marker=dict(color=[STATE_COLOURS.get(s, "#5a6b85") for s in counts["state"]]),
        hovertemplate="%{y}: <b>%{x}</b><extra></extra>",
    ))
    base_layout(fig, height=max(240, 26 * len(counts) + 60), legend=False)
    fig.update_layout(hovermode="closest", margin=dict(l=8, r=16, t=8, b=32))
    fig.update_yaxes(automargin=True)
    return fig


def fire_map(events: pd.DataFrame, height=520):
    """The day's fires as points, coloured by state, sized by fire radiative power."""
    fig = go.Figure()
    for state, g in events.groupby("state"):
        frp = g["frp_w_m2"].fillna(0).clip(upper=60)
        fig.add_scattermap(
            lat=g["latitude"], lon=g["longitude"], name=f"{state} ({len(g)})", mode="markers",
            marker=dict(size=5 + frp / 6, color=STATE_COLOURS.get(state, "#5a6b85"), opacity=0.75),
            customdata=g[["district", "tehsil", "satellite", "acq_time", "frp_w_m2"]].fillna("").values,
            hovertemplate=("<b>%{customdata[0]}</b>, %{customdata[1]}<br>%{customdata[2]} · %{customdata[3]} IST"
                           "<br>Fire power %{customdata[4]} W/m²<extra></extra>"),
        )
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        map=dict(style="carto-positron", center=dict(lat=events["latitude"].mean(), lon=events["longitude"].mean()),
                 zoom=4.6 if events["state"].nunique() > 2 else 6),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, x=0.01, bgcolor="rgba(255,255,255,0.85)"),
    )
    return fig


# -------------------------------------------------------------------- page --
def render_fires_page():
    daily, events, meta = data.creams_daily(), data.creams_events(), data.creams_bulletin()
    if daily.empty:
        warning_card("No CREAMS fire counts yet. They appear after the daily fire update has run.",
                     title="Fire data unavailable")
        return
    latest = (date.fromisoformat(meta["events_date"]) if meta.get("events_date")
              else daily["date"].max())
    render_header(meta, latest)
    render_state_cards(daily, latest)
    render_highlights(meta)

    area = st.segmented_control("**Area**", options=list(AREAS), selection_mode="single",
                                default=PB_HR, key="fires_area") or PB_HR
    states = AREAS[area]

    with chart_card(title=f"Season so far against earlier years · {area}",
                    caption=f"Cumulative paddy residue burning events from 15 September. Earlier years are shown "
                            f"to the same date ({latest:%d %b}), as in the bulletin."):
        st.plotly_chart(cumulative_chart(daily, states, latest), key="fires_cumulative", width="stretch",
                        config=PLOT_CONFIG)
        st.markdown(_source_line(), unsafe_allow_html=True)

    with chart_card(title=f"Events per day, {latest.year} season · {area}",
                    caption=f"Bars: {latest.year}, by state. Dotted line: {latest.year - 1} on the same dates."):
        st.plotly_chart(daily_chart(daily, states, latest), key="fires_daily", width="stretch", config=PLOT_CONFIG)
        st.markdown(_source_line(), unsafe_allow_html=True)

    day_events = events[(events["date"] == latest) & (events["state"].isin(states))]
    if day_events.empty:
        st.caption(f"No individual fires listed for {area} on {_d(latest)}.")
    else:
        left, right = st.columns([3, 2])
        with left, chart_card(title=f"Where the fires were · {_d(latest)}",
                              caption="One point per fire; larger points had higher fire radiative power."):
            st.plotly_chart(fire_map(day_events), key="fires_map", width="stretch",
                            config={**PLOT_CONFIG, "scrollZoom": True})
            st.markdown(_source_line(), unsafe_allow_html=True)
        with right, chart_card(title=f"Top districts · {_d(latest)}", caption=f"{len(day_events):,} fires in {area}."):
            st.plotly_chart(district_chart(day_events), key="fires_districts", width="stretch", config=PLOT_CONFIG)

    with st.expander("Data tables and downloads"):
        season = _season(daily, latest.year)
        table = (season[season["state"].isin(states)].pivot(index="date", columns="state", values="events")
                 .reindex(columns=states).sort_index(ascending=False).reset_index())
        st.markdown(f"**Events per day, {latest.year} season · {area}**")
        st.dataframe(table, hide_index=True, width="stretch")
        st.download_button("Download all CREAMS daily counts (2020 onwards, CSV)",
                           daily.to_csv(index=False).encode("utf-8"), file_name="creams_fires.csv",
                           mime="text/csv", key="dl_creams_daily")
        if not day_events.empty:
            st.markdown(f"**Fires listed on {_d(latest)} · {area}**")
            st.dataframe(day_events.drop(columns=["date"]), hide_index=True, width="stretch")
            st.download_button(f"Download the fire list for {_d(latest)} (CSV)",
                               events[events["date"] == latest].to_csv(index=False).encode("utf-8"),
                               file_name=f"creams_fire_events_{latest}.csv", mime="text/csv", key="dl_creams_events")

    st.caption(
        "Counts are paddy residue burning events identified by the CREAMS Lab, ICAR-IARI, under the "
        "\"Standard Protocol for Estimation of Crop Residue Burning Fire Events using Satellite Data\", from VIIRS "
        "(Suomi NPP, NOAA-20) and MODIS (Terra, Aqua) detections received at the NRSC ground station and NASA FIRMS. "
        "Satellites see a fire only if it is burning at overpass time and not under cloud, so a day's count is a "
        "lower bound; check the highlights for cloud cover."
    )
