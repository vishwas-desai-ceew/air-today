import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, timezone
from streamlit_calendar_input import calendar_input
from pathlib import Path
from config.settings import EFFECTIVE_DATE_CUTOFF
from ingestion.json_store import read_json
from views.components import warning_card, danger_card, render_forecast_availability

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


def render_archive_data():
    archived_data = load_json_data()
    archive_dates = []
    for date_str in archived_data:
        try:
            #archive_dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            archive_dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
        except ValueError:
            continue

    if not archive_dates:
        st.info("No archived updates are available yet.")
        return

    year_options = sorted({str(date.year) for date in archive_dates}, reverse=True)
    col1, col2, _ = st.columns([2, 1, 4])
    with col1:
        year_selection = st.segmented_control(
            "**Select year**",
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
    filtered_dates = sorted(date for date in archive_dates if date.year == current_year)
    missing_dates = set(load_missing_days())
    with col2:
        st.space(40)
        view_mode = st.toggle(
            "**Table View**",
            value=False,
            key="archive_table_view",
            help="Select View Mode",
            label_visibility="visible",
            width="content",
        )
    
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
                "forecast_missing": st.column_config.CheckboxColumn(
                    "AQEWS forecast missing"
                ),
            },
        )
        st.download_button(
            "Download as CSV",
            data=table_df.to_csv(index=False).encode("utf-8"),
            file_name=f"aq_archive_{current_year}.csv",
            mime="text/csv",
        )
        st.write("")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        # The calendar component keeps client-side state. Changing the key
        # when the year changes creates a fresh instance with only that
        # year's available dates, avoiding stale selections/view state.
        selected_date = calendar_input(
            available_dates=filtered_dates, key=f"archive_calendar_{current_year}"
        )

    with col2:
        if selected_date and selected_date.year == current_year:
            date_str = selected_date.strftime("%Y-%m-%d")
        else:
            effective_date = get_effective_date_utc()
            # When viewing a prior year, today's effective date is not a
            # useful fallback. Show the most recent archived update instead.
            date_str = (
                effective_date
                if effective_date in archived_data and effective_date.startswith(f"{current_year}-")
                else filtered_dates[-1].strftime("%Y-%m-%d")
            )
        insights_col = st.columns(1)
        if date_str in archived_data:
            desc = archived_data[date_str]
            with insights_col[0].container(border=True):
                st.markdown(
                    f"""
                    <span class="archive_insights">
                        {datetime.strptime(date_str, "%Y-%m-%d").strftime('%A')} |
                        {datetime.strptime(date_str, "%Y-%m-%d").strftime('%d %B %Y')} 
                    </span>
                """,
                    unsafe_allow_html=True,
                )
                st.space(3)
                if date_str in missing_dates:
                    danger_card("AQI forecasts were unavailable as the AQEWS website was temporarily down", "Note:")
                st.space(3)
                if len(desc) >= 1:
                    st.markdown(
                        "<ul style='padding-left:10px;padding-right:50px; "
                        "list-style-type:square; margin-top:5px;'>"
                        + "".join(f"<li>{item}</li>" for item in desc)
                        + "</ul>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("No description available.")

        else:
            st.error("Please select a date in green to view the archive.")

    render_forecast_availability(missing_dates, current_year)
   
