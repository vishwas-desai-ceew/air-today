import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from config.settings import EFFECTIVE_DATE_CUTOFF
from ingestion.json_store import read_json
from views.calendar_grid import month_calendar, month_picker
from views.components import danger_card, render_forecast_availability

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVE_JSON = DATA_DIR / "archive.json"
MISSING_DAYS = DATA_DIR / "missing_forecast_days.txt"


def get_effective_date_utc():
    cutoff = EFFECTIVE_DATE_CUTOFF
    now = datetime.now()
    effective_date = (
        (now - timedelta(days=2)).date()
        if now.time() < cutoff
        else (now - timedelta(days=1)).date()
    )
    return effective_date.strftime("%Y-%m-%d")


def load_json_data():
    return read_json(ARCHIVE_JSON)


def load_missing_days():
    with open(MISSING_DAYS) as f:
        dates = [line.strip() for line in f]
    return dates


def _build_archive_table(archived_data, missing_dates, current_year):
    """Flattens archive.json into a sortable/searchable/downloadable table -
    an alternative to the calendar-card view, not a replacement (design.md: Tables)."""
    rows = []
    for date_str, desc in archived_data.items():
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if dt.year != current_year:
            continue
        rows.append(
            {
                "date": dt.date(),
                "day": dt.strftime("%A"),
                "insights_count": len(desc) if isinstance(desc, list) else 0,
                "forecast_missing": date_str in missing_dates,
            }
        )
    columns = ["date", "day", "insights_count", "forecast_missing"]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)[columns].sort_values("date", ascending=False)


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
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    with col1:
        year_selection = st.segmented_control(
            "**Year**",
            options=year_options,
            selection_mode="single",
            default=year_options[0],
            key="archive_year_selection",
        )
    # A keyed segmented control normally always returns a value, but this
    # fallback also handles a stale session state after the archive changes.
    if year_selection not in year_options:
        year_selection = year_options[0]
    with col2:
        view_mode = st.toggle("**Table view**", value=False, key="archive_table_view")

    current_year = int(year_selection)
    year_dates = sorted(d for d in archive_dates if d.year == current_year)
    missing_dates = set(load_missing_days())

    if view_mode:
        table_df = _build_archive_table(archived_data, missing_dates, current_year)
        st.dataframe(
            table_df,
            width="stretch",
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date"),
                "day": st.column_config.TextColumn("Day"),
                "insights_count": st.column_config.NumberColumn("Insights"),
                "forecast_missing": st.column_config.CheckboxColumn("AQEWS forecast missing"),
            },
        )
        st.download_button(
            "Download as CSV",
            data=table_df.to_csv(index=False).encode("utf-8"),
            file_name=f"aq_archive_{current_year}.csv",
            mime="text/csv",
        )
        return

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
            caption="Highlighted dates have an archived update. Click one to read it.",
        )
    with side_col:
        st.markdown(f"<div class='cal-side-title'>{date(year, month, 1):%B %Y} at a glance</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="cal-stats">
              <div><strong>{len(month_dates)}</strong><span>updates archived</span></div>
              <div><strong>{len(markers)}</strong><span>days without AQEWS forecast</span></div>
            </div>
            <div class="cal-legend">
              <span><i class="cal-key on"></i>Update archived</span>
              <span><i class="cal-key warn"></i>Update archived, AQEWS forecast missing</span>
              <span><i class="cal-key off"></i>No update</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        latest = month_dates[-1]
        if st.button(f"Open latest: {latest.day} {latest:%b}", key=f"archive_latest_{year}_{month}",
                     icon=":material/open_in_new:", width="stretch"):
            archive_dialog(latest.isoformat())

    with st.expander("AQEWS forecast availability through the year", icon=":material/calendar_month:"):
        render_forecast_availability(missing_dates, current_year)
