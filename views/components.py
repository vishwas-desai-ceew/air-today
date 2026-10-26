import pytz
import streamlit as st
import contextlib
import calendar
from pathlib import Path
from datetime import date, datetime, timedelta, time, timezone

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
IST = pytz.timezone("Asia/Kolkata")


def hr(margin_top="1rem", margin_bottom="1rem", margin=None, style="solid"):
    """Shared divider, replacing the 11+ copies of this literal string in dashboard.py."""
    if margin is not None:
        css = f"border:0.3px {style} gray;margin:{margin};"
    else:
        css = f"border: 0.3px {style} gray;margin-top:{margin_top}; margin-bottom:{margin_bottom};"
    st.markdown(f"<hr style='{css}'>", unsafe_allow_html=True)


def outage_banner(compact=False):
    """AQEWS outage notice styled consistently with the dashboard cards."""
    compact_class = "aqews-outage-card--compact" if compact else ""
    st.markdown(
        f"""
        <section class="aqews-outage-card{compact_class}">
            <div class="aqews-outage-heading">
                <span class="aqews-outage-indicator" aria-hidden="true"></span>
                <div>
                    <p class="aqews-outage-eyebrow">AQEWS data status</p>
                    <h3>Forecast service needs attention</h3>
                </div>
            </div>
            <p><strong>The AQEWS portal is currently experiencing an outage or data inconsistency.</strong>
            Interpret AQEWS data with caution.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_status_strip(error_flag):
    """Render a compact data-health panel above the app navigation."""
    sources = [
        ("CPCB AQI", DATA_DIR / "delhi_aqi_cpcb.csv"),
        ("IMD Bulletin", DATA_DIR / "imd_bulletin_today.pdf"),
        ("AQEWS Forecast", DATA_DIR / "AQEWS_AQI_forecast.csv"),
    ]
    now = datetime.now(IST)
    statuses = []

    for label, path in sources:
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime, IST)
            is_fresh = (now - mtime).total_seconds() < 30 * 3600
            state = "fresh" if is_fresh else "attention"
            status = "Up to date" if is_fresh else "Update overdue"
            detail = f"Updated {mtime.strftime('%d %b · %I:%M %p')}"
        else:
            state = "attention"
            status = "No data"
            detail = "Waiting for first update"
        statuses.append((label, detail, status, state))

    portal_state = "attention" if error_flag else "fresh"
    portal_status = "Outage detected" if error_flag else "Operational"
    portal_detail = (
        "Review forecast with caution"
        if error_flag
        else "AQEWS portal responding normally"
    )
    statuses.append(("AQEWS Portal", portal_detail, portal_status, portal_state))

    # Keep every chip in its own Streamlit Markdown element. Concatenating
    # sibling HTML blocks can make Streamlit render subsequent blocks as text.
    with st.container(border=False, key="data-health"):
        for col, (label, detail, status, state) in zip(
            st.columns(len(statuses), gap="small"), statuses
        ):
            with col:
                st.markdown(
                    f"""
                    <div class="data-status-chip {state}">
                        <span class="data-status-indicator" aria-hidden="true"></span>
                        <div class="data-status-content">
                            <div class="data-status-source">{label}</div>
                            <div class="data-status-detail">{detail}</div>
                        </div>
                        <span class="data-status-label">{status}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def section_header(title, caption=None):
    """Page/section title + optional caption, replacing ad hoc `st.markdown('### ...')`
    + manual hr() pairs scattered across dashboard.py."""
    # One element: the old open-div / caption / close-div trio rendered as
    # three siblings, so the wrapper never actually wrapped anything.
    caption_html = f"<div class='ceew-caption'>{caption}</div>" if caption else ""
    st.markdown(
        f"<div class='ceew-section-header'><div class='ceew-h1'>{title}</div>{caption_html}</div>",
        unsafe_allow_html=True,
    )


def metric_card(
    label, value, caption=None, delta=None, delta_good_when="up", color=None
):
    """A single KPI card: label, big number, optional trend delta and accent colour.
    `delta_good_when` is "up" or "down" - whichever direction counts as improving."""
    delta_html = ""
    if delta is not None:
        if delta == 0:
            arrow, delta_class = "—", "ceew-delta-neutral"
        else:
            improving = (delta > 0) if delta_good_when == "up" else (delta < 0)
            arrow = "▲" if delta > 0 else "▼"
            delta_class = "ceew-delta-good" if improving else "ceew-delta-bad"
        delta_html = f" <span class='{delta_class}'>{arrow} {abs(delta)}</span>"

    accent = f"border-top: 3px solid {color};" if color else ""
    st.markdown(
        f"""
        <div class="ceew-metric-card" style="{accent}">
            <div class="ceew-metric-label">{label}</div>
            <div class="ceew-metric-value">{value}{delta_html}</div>
            <div class="ceew-metric-caption">{caption or "&nbsp;"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@contextlib.contextmanager
def chart_card(title=None, caption=None):
    """Bordered container giving every chart in the app a consistent frame.
    Usage: `with chart_card():` then render the chart/table inside as usual.
    Leave `title` unset for functions that already render their own heading,
    to avoid a duplicated title."""
    with st.container(border=True):
        if title:
            st.markdown(
                f"<div class='ceew-card-title'>{title}</div>", unsafe_allow_html=True
            )
        if caption:
            st.markdown(
                f"<div class='ceew-caption'>{caption}</div>", unsafe_allow_html=True
            )
        yield


def warning_card(message, title="Note"):
    """Generic warning banner (amber, not tied to the AQEWS-specific wording
    `outage_banner()` uses)."""
    st.markdown(
        f"""
        <span class="ceew-warning-card">
            <strong>{title}</strong> {message}
        </span>
        """,
        unsafe_allow_html=True,
    )


def danger_card(message, title="Note"):
    st.markdown(
        f"""
        <span class="ceew-danger-card">
            <strong>{title}</strong> {message}
        </span>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label, ok):
    """Inline green/red status dot + label, reusing the same visual language as
    render_status_strip()."""
    dot_class = "ok" if ok else "bad"
    st.markdown(
        f"<span class='ceew-status-dot {dot_class}'></span>{label}",
        unsafe_allow_html=True,
    )


import calendar
from datetime import date, timedelta

import streamlit as st


def render_forecast_availability(missing_dates, year):
    """
    Render a GitHub-style calendar showing missing AQEWS forecasts.

    Parameters
    ----------
    missing_dates : Iterable[str]
        Dates in YYYY-MM-DD format.
    year : int
    """

    missing = {
        d for d in missing_dates
        if d.startswith(f"{year}-")
    }

    if not missing:
        st.error(f"AQEWS forecasts were not tracked in {year}.")
        return
    

    if year == 2025:
        st.info(f"**Note**: Tracking of AQEWS forecasts beganin September {year}")

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    today = date.today()

    # Monday before Jan 1
    calendar_start = start - timedelta(days=start.weekday())

    # Sunday after Dec 31
    calendar_end = end + timedelta(days=(6 - end.weekday()))

    total_weeks = ((calendar_end - calendar_start).days + 1) // 7

    months = []

    for week in range(total_weeks):
        week_start = calendar_start + timedelta(days=week * 7)

        for i in range(7):
            d = week_start + timedelta(days=i)
            if d.year == year and d.day == 1:
                months.append(
                    f'<span style="grid-column:{week+1}">{d.strftime("%b")}</span>'
                )

    cells = []

    current = calendar_start

    while current <= calendar_end:

        in_year = current.year == year

        if not in_year:
            cls = "forecast-cell forecast-cell--empty"

        elif current > today:
            cls = "forecast-cell forecast-cell--future"

        elif current.strftime("%Y-%m-%d") in missing:
            cls = "forecast-cell forecast-cell--missing"

        else:
            cls = "forecast-cell forecast-cell--normal"

        tooltip = current.strftime("%d %b %Y")

        if in_year:
            if current > today:
                tooltip += "&#10;Forecast not yet due"

            elif current.strftime("%Y-%m-%d") in missing:
                tooltip += "&#10;AQEWS forecast unavailable"

            else:
                tooltip += "&#10;AQEWS forecast available"

        display_text = ""

        if in_year and current.day == 1:
            display_text = "1"

        cells.append(
            f"""<span class="{cls}" title="{tooltip}"> {display_text}</span>"""
        )

        current += timedelta(days=1)

    st.markdown(
        f"""
        <div class="forecast-calendar-wrapper">
            <div class="forecast-card">
                <div class="forecast-header">
                    <div>
                        <div class="forecast-eyebrow">
                            AQEWS AVAILABILITY
                        </div>
                        <div class="forecast-title">
                            Forecast gaps in {year}
                        </div>
                        <div class="forecast-subtitle">
                            Hover over a day to view its status.
                        </div>
                    </div>
                </div>
                <div class="forecast-calendar">
                    <div class="forecast-months">
                        {''.join(months)}
                    </div>
                    <div class="forecast-body">
                        <div class="forecast-weekdays">
                            <span>Mon</span>
                            <span>Wed</span>
                            <span>Fri</span>
                        </div>
                        <div class="forecast-grid">
                            {''.join(cells)}
                        </div>
                    </div>
                </div>
                <div class="forecast-legend">
                    <span class="forecast-legend-box forecast-cell--normal"></span>
                    Available
                    <span class="forecast-legend-box forecast-cell--missing"></span>
                    Forecast unavailable
                    <div class="forecast-count">
                            {len(missing)} days unavailable in {year}
                    </div>
                </div>
            </div>
        </div>
        """,
                unsafe_allow_html=True,
            )