"""Farm fires page: daily satellite fire counts for Punjab and Haryana, one
line per instrument, with a state picker.

Reads data/fires_<state>.csv (ingestion/get_fire_pbhr.py). Instruments are
plotted side by side, never summed: each satellite detects the same fires on
its own overpass. Picking "Both" adds the two states per instrument, which is
fine because the states don't overlap.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from config.settings import FIRE_INSTRUMENTS, FIRE_STATE_CSVS
from views import data
from views.charts import PLOT_CONFIG, base_layout
from views.components import chart_card, metric_card, warning_card

INSTRUMENT_COLOURS = {
    "NOAA/VIIRS": "#e0541b",
    "Aqua/MODIS": "#0a3d7a",
    "Terra/MODIS": "#2f9e8f",
}
BOTH = "Both states"
EXTERNAL_DASHBOARD = "https://signals-demo.earthmetry.com/superset/dashboard/fires-pb-hr?standalone=True"


def load(choice) -> pd.DataFrame:
    states = list(FIRE_STATE_CSVS) if choice == BOTH else [choice]
    frames = [data.state_fires(s) for s in states]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames).groupby("date", as_index=False)[FIRE_INSTRUMENTS].sum()
    return df.sort_values("date").reset_index(drop=True)


def fires_chart(df, height=420):
    fig = go.Figure()
    for inst in FIRE_INSTRUMENTS:
        fig.add_scatter(
            x=df["date"], y=df[inst], name=inst, mode="lines+markers",
            line=dict(color=INSTRUMENT_COLOURS[inst], width=2.2),
            marker=dict(size=5, color=INSTRUMENT_COLOURS[inst]),
            hovertemplate=f"{inst}: <b>%{{y:,}}</b><extra></extra>",
        )
    base_layout(fig, height=height, y_title="Fires detected per day")
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(tickformat="%d %b")
    return fig


def render_kpis(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    cols = st.columns(len(FIRE_INSTRUMENTS))
    for col, inst in zip(cols, FIRE_INSTRUMENTS):
        with col:
            delta = None if prev is None else int(latest[inst] - prev[inst])
            metric_card(
                inst, f"{int(latest[inst]):,}",
                caption=f"{latest['date']:%d %b %Y} · change vs previous day",
                delta=delta, delta_good_when="down", color=INSTRUMENT_COLOURS[inst],
            )


def render_fires_page():
    choice = st.segmented_control(
        "**State**", options=[*FIRE_STATE_CSVS, BOTH], selection_mode="single",
        default=BOTH, key="fires_state",
    ) or BOTH
    df = load(choice)

    if df.empty:
        warning_card("No fire counts yet. They appear after the daily fire update has run.",
                     title="Fire data unavailable")
    else:
        render_kpis(df)
        with chart_card(title=f"Daily fire counts · {choice}",
                        caption="One line per satellite instrument. Each satellite passes over at a "
                                "different time and detects fires on its own, so the lines are compared, "
                                "not added together."):
            st.plotly_chart(fires_chart(df), key="fires_chart", width="stretch", config=PLOT_CONFIG)
            st.markdown(
                "<div class='chart-source'>Source: NASA active fire detections (VIIRS and MODIS), "
                "counted per state for Punjab and Haryana</div>",
                unsafe_allow_html=True,
            )

        with st.expander("Daily counts table"):
            table = df.sort_values("date", ascending=False)
            st.dataframe(table, hide_index=True, width="stretch")
            slug = "punjab_haryana" if choice == BOTH else choice.lower()
            st.download_button("Download CSV", table.to_csv(index=False).encode("utf-8"),
                               file_name=f"fires_{slug}.csv", mime="text/csv")

    with st.expander("Detailed dashboard (Earthmetry Signals)"):
        components.iframe(EXTERNAL_DASHBOARD, height=950)
