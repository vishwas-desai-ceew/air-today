import streamlit as st
from datetime import date, datetime, timedelta
from pathlib import Path
from config.settings import effective_today
from ingestion.json_store import read_json
from views.calendar_grid import month_calendar, month_picker
from views.components import danger_card, render_forecast_availability
from views.widgets import icon

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVE_JSON = DATA_DIR / "archive.json"
MISSING_DAYS = DATA_DIR / "missing_forecast_days.txt"


def get_effective_date_utc():
    """The latest archived day: the day before the effective "today"."""
    effective_date = effective_today() - timedelta(days=1)
    return effective_date.strftime("%Y-%m-%d")


def load_json_data():
    return read_json(ARCHIVE_JSON)


def load_missing_days():
    with open(MISSING_DAYS) as f:
        dates = [line.strip() for line in f]
    return dates


@st.dialog("Archived update", width="large")
def archive_dialog(date_str):
    archived_data = load_json_data()
    day = datetime.strptime(date_str, "%Y-%m-%d")
    desc = archived_data.get(date_str) or []
    st.markdown(
        f"<div class='cal-dlg-date'>{day:%A} · {day.day} {day:%B %Y}</div>"
        f"<div class='cal-dlg-sub'>{len(desc)} insight{'s' if len(desc) != 1 else ''} archived</div>",
        unsafe_allow_html=True,
    )
    if date_str in set(load_missing_days()):
        danger_card("AQI forecasts were unavailable as the AQEWS website was temporarily down", "Note:")
    if desc:
        st.markdown(
            "<ul class='archive-dlg-list'>" + "".join(f"<li>{item}</li>" for item in desc) + "</ul>",
            unsafe_allow_html=True,
        )
    else:
        st.write("No description available.")


@st.dialog("AQEWS Forecast Availability", width="large")
def availability_dialog(year):
    render_forecast_availability(
        set(load_missing_days()), year, tracked_dates=load_json_data().keys()
    )


def render_archive_data():
    archived_data = load_json_data()
    archive_dates = []
    for date_str in archived_data:
        try:
            archive_dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
        except ValueError:
            continue

    if not archive_dates:
        st.info("No archived updates are available yet.")
        return

    year_options = sorted({str(d.year) for d in archive_dates}, reverse=True)
    year_selection = st.segmented_control(
        "**:material/calendar_today: Year**",
        options=year_options,
        selection_mode="single",
        default=year_options[0],
        key="archive_year_selection",
    )
    # A keyed segmented control normally always returns a value, but this
    # fallback also handles a stale session state after the archive changes.
    if year_selection not in year_options:
        year_selection = year_options[0]

    current_year = int(year_selection)
    year_dates = sorted(d for d in archive_dates if d.year == current_year)
    missing_dates = set(load_missing_days())

    # Only months that actually have updates; open on the latest one.
    months = sorted({(d.year, d.month) for d in year_dates})
    year, month = month_picker(f"archive_month_{current_year}", months, default=months[-1])
    month_dates = [d for d in year_dates if (d.year, d.month) == (year, month)]
    markers = {d: "warn" for d in month_dates if d.isoformat() in missing_dates}

    cal_col, side_col = st.columns([3, 2], gap="large")
    with cal_col:
        month_calendar(
            f"archive_{current_year}", year, month, set(month_dates),
            on_select=lambda d: archive_dialog(d.isoformat()),
            markers=markers,
            caption=":material/info: Highlighted dates have an archived update. Click one to read it.",
        )
    with side_col:
        st.markdown(
            f"<div class='cal-side-title'>{icon('calendar', 20)}{date(year, month, 1):%B %Y} at a glance</div>"
            f"<div class='arch-kpis'>"
            f"<div class='arch-kpi' style='--accent: var(--brand)'>"
            f"<div class='arch-kpi-head'>{icon('archive', 16)}Updates archived</div>"
            f"<div class='arch-kpi-value'>{len(month_dates)}</div></div>"
            f"<div class='arch-kpi' style='--accent: #b7791f'>"
            f"<div class='arch-kpi-head'>{icon('alert', 16)}Days without AQEWS forecast</div>"
            f"<div class='arch-kpi-value'>{len(markers)}</div></div>"
            f"</div>"
            f"<div class='cal-legend cal-legend--card'>"
            f"<div class='cal-legend-title'>{icon('info', 15)}Legend</div>"
            f"<span><i class='cal-key on'></i>Update archived</span>"
            f"<span><i class='cal-key warn'></i>Update archived, AQEWS forecast missing</span>"
            f"<span><i class='cal-key off'></i>No update</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        latest = month_dates[-1]
        if st.button(f"Open latest: {latest.day} {latest:%b}", key=f"archive_latest_{year}_{month}",
                     icon=":material/open_in_new:", width="stretch"):
            archive_dialog(latest.isoformat())
        if st.button("AQEWS Forecast Availability", key=f"archive_aqews_{current_year}",
                     icon=":material/calendar_month:", width="stretch"):
            availability_dialog(current_year)
