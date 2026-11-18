"""Live station AQI: the AQEWS home page's "Live station AQI" ticker (hourly
AQI at each CPCB monitoring station in Delhi), shown in a pop-up on the AQEWS
page as a swipeable carousel of station cards.

Data: views.data.aqews_stations() - fetched live from ews.tropmet.res.in and
cached for 30 minutes, with the daily cron snapshot as fallback. Values are
shown as AQEWS publishes them; nothing is averaged or estimated here.
"""
import re
from collections import Counter
from datetime import datetime
from html import escape

import streamlit as st

from config.reference import AQI_BANDS
from views import data
from views.widgets import src

BAND_COLOUR = {n: c for n, _lo, _hi, c in AQI_BANDS}
BAND_ORDER = [n for n, *_ in AQI_BANDS]
# Moderate's yellow is too pale for text on white
TEXT_ON_WHITE = {"Moderate": "#9a7b00"}
AGENCY_RE = re.compile(r"\s*-\s*([A-Z]{2,6})\s*$")


def split_name(name):
    """'Alipur, Delhi - DPCC' -> ('Alipur', 'DPCC'); 'Karala, Delhi-DPCC' -> ('Karala', 'DPCC')."""
    m = AGENCY_RE.search(name)
    agency = m.group(1) if m else ""
    place = name[:m.start()] if m else name
    place = re.sub(r",\s*(?:New\s+)?Delhi\s*$", "", place).strip(" ,-")
    return place or name, agency


def _when(iso):
    if not iso:
        return ""
    t = datetime.fromisoformat(iso)
    return f"{t:%H:%M}, {t.day} {t:%b}"


def cards_html(stations):
    cards = []
    for s in stations:
        place, agency = split_name(s["station"])
        cat = s.get("category") or ""
        colour = BAND_COLOUR.get(cat) or s.get("colour") or "#6b7f99"
        cards.append(
            f"<article class='stn-card' style='--c:{colour};--t:{TEXT_ON_WHITE.get(cat, colour)}'>"
            f"<div class='stn-place' title='{escape(s['station'])}'>{escape(place)}</div>"
            f"<div class='stn-agency'>{escape(agency)}</div>"
            f"<div class='stn-aqi'>{s['aqi']}</div>"
            f"<span class='stn-cat'>{escape(cat)}</span>"
            f"<div class='stn-meta'>{escape(s.get('pollutant') or '—')} · {_when(s.get('observed_at'))}</div>"
            "</article>"
        )
    return f"<div class='stn-track' role='list'>{''.join(cards)}</div>"


def summary_html(stations):
    counts = Counter(s.get("category") for s in stations)
    chips = "".join(
        f"<span class='stn-count' style='--c:{BAND_COLOUR[n]}'><b>{counts[n]}</b>{escape(n)}</span>"
        for n in BAND_ORDER if counts.get(n)
    )
    hi = max(stations, key=lambda s: s["aqi"])
    lo = min(stations, key=lambda s: s["aqi"])
    return (
        f"<div class='stn-summary'>{chips}</div>"
        f"<div class='stn-range'>Highest <b>{hi['aqi']}</b> at {escape(split_name(hi['station'])[0])} · "
        f"lowest <b>{lo['aqi']}</b> at {escape(split_name(lo['station'])[0])}</div>"
    )


@st.dialog("Live station AQI", width="large")
def stations_dialog():
    feed = data.aqews_stations()
    stations = feed.get("stations") or []
    if not stations:
        st.info("Station AQI could not be fetched from AQEWS. Please try again later.")
        return
    st.markdown(
        f"<div class='pol-period'>{len(stations)} CPCB monitoring stations in Delhi · "
        f"hourly AQI at {_when(feed.get('observed_at'))} IST</div>"
        + summary_html(stations),
        unsafe_allow_html=True,
    )
    order = st.segmented_control("Sort stations", ["Highest AQI", "Lowest AQI", "A–Z"], default="Highest AQI",
                                 key="stn_sort", label_visibility="collapsed") or "Highest AQI"
    key = {"Highest AQI": lambda s: -s["aqi"], "Lowest AQI": lambda s: s["aqi"],
           "A–Z": lambda s: split_name(s["station"])[0].lower()}[order]
    st.markdown(cards_html(sorted(stations, key=key)), unsafe_allow_html=True)
    note = "" if feed.get("live") else " · <i>AQEWS could not be reached; showing the last saved readings</i>"
    st.markdown(
        "<div class='chart-source'>Swipe or scroll sideways for more stations. Hourly station AQI is a guide; "
        "CPCB's AQI categories are defined for 24-hour averages.</div>"
        f"<div class='chart-source'>Source: CPCB station data via {src('aqews', 'IITM AQEWS')} "
        f"(Live station AQI){note}</div>",
        unsafe_allow_html=True,
    )


def render_stations_button():
    if st.button("Live station AQI", key="open_station_aqi", icon=":material/sensors:"):
        stations_dialog()
