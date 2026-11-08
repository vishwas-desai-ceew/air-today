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


# The dashboard began logging AQEWS forecast availability on this day
# (first entry in data/archive.json with availability tracking).
AQEWS_TRACKING_START = date(2025, 9, 16)

AQEWS_SOURCES = [
    ("AQEWS for Delhi, IITM Pune: About", "https://ews.tropmet.res.in/about.php"),
    ("Decision Support System v1.0 for air quality management in Delhi (Geoscientific Model Development, 2024)",
     "https://gmd.copernicus.org/articles/17/2617/2024/"),
]


def _aqews_day_status(d, tracked, missing, today):
    """One of: available, missing, untracked, future."""
    iso = d.isoformat()
    if d > today:
        return "future"
    if iso in missing:
        return "missing"
    if d < AQEWS_TRACKING_START or iso not in tracked:
        return "untracked"
    return "available"


_AQEWS_STATUS_LABEL = {
    "available": "AQEWS forecast available",
    "missing": "AQEWS forecast unavailable",
    "untracked": "Not tracked (dashboard pipeline did not run)",
    "future": "Not yet due",
}


def render_forecast_availability(missing_dates, year, tracked_dates=(), today=None):
    """
    Month-by-month view of whether the IITM AQEWS forecast could be fetched on
    each day of `year`, shown at all times on the Archive page.

    Parameters
    ----------
    missing_dates : Iterable[str]
        Days (YYYY-MM-DD) on which the AQEWS forecast could not be fetched.
    year : int
    tracked_dates : Iterable[str]
        Days (YYYY-MM-DD) on which the dashboard pipeline ran and so checked
        AQEWS. Days outside this set are shown as "not tracked", not as
        "available".
    today : date, optional
        Defaults to date.today().
    """
    today = today or date.today()
    missing = {d for d in missing_dates if d.startswith(f"{year}-")}
    tracked = {d for d in tracked_dates if d.startswith(f"{year}-")} | missing

    if year < AQEWS_TRACKING_START.year:
        st.info(
            f"AQEWS forecast availability was not tracked in {year}. "
            f"Tracking began on {AQEWS_TRACKING_START:%-d %B %Y}.",
            icon=":material/info:",
        )
        return

    counts = {"available": 0, "missing": 0, "untracked": 0, "future": 0}
    month_cards = []
    for month in range(1, 13):
        n_days = calendar.monthrange(year, month)[1]
        first = date(year, month, 1)
        m_counts = {"available": 0, "missing": 0}
        cells = [
            "<span class='aqews-day aqews-day--pad'></span>"
            for _ in range(first.weekday())
        ]
        for day in range(1, n_days + 1):
            d = date(year, month, day)
            status = _aqews_day_status(d, tracked, missing, today)
            counts[status] += 1
            if status in m_counts:
                m_counts[status] += 1
            cells.append(
                f"<span class='aqews-day aqews-day--{status}'>"
                f"<span class='aqews-tip'><b>{d:%a %-d %b %Y}</b>{_AQEWS_STATUS_LABEL[status]}</span>"
                f"</span>"
            )
        checked = m_counts["available"] + m_counts["missing"]
        if checked:
            pct = round(100 * m_counts["available"] / checked)
            summary = f"{m_counts['available']}/{checked} days"
            badge_cls = "ok" if pct >= 90 else ("mid" if pct >= 50 else "bad")
            badge = f"<span class='aqews-badge aqews-badge--{badge_cls}'>{pct}%</span>"
        else:
            summary = "Not yet due" if first > today else "Not tracked"
            badge = ""
        month_cards.append(
            f"<div class='aqews-month{' aqews-month--quiet' if not checked else ''}'>"
            f"<div class='aqews-month-head'><span class='aqews-month-name'>{first:%b}</span>{badge}</div>"
            f"<div class='aqews-days'>{''.join(cells)}</div>"
            f"<div class='aqews-month-sum'>{summary}</div>"
            f"</div>"
        )

    checked = counts["available"] + counts["missing"]
    pct = f"{round(100 * counts['available'] / checked)}%" if checked else "–"
    legend = "".join(
        f"<span><i class='aqews-day aqews-day--{k}'></i>{label}</span>"
        for k, label in [
            ("available", "Forecast available"),
            ("missing", "Forecast unavailable"),
            ("untracked", "Not tracked"),
            ("future", "Not yet due"),
        ]
    )
    sources = " · ".join(
        f"<a href='{url}' target='_blank' rel='noopener'>{name}</a>"
        for name, url in AQEWS_SOURCES
    )
    tracking_note = (
        f"Tracking began on {AQEWS_TRACKING_START:%-d %B %Y}; earlier days show as not tracked. "
        if year == AQEWS_TRACKING_START.year else ""
    )

    st.markdown(
        f"""
<div class="aqews-card">
  <div class="aqews-head">
    <div>
      <div class="aqews-title">Could the dashboard fetch the AQEWS forecast? {year}</div>
      <div class="aqews-sub">Each square is a day. Hover over one to see its status.</div>
    </div>
    <div class="aqews-stats">
      <div><strong>{pct}</strong><span>of checked days available</span></div>
      <div><strong>{counts['available']}</strong><span>days available</span></div>
      <div><strong>{counts['missing']}</strong><span>days unavailable</span></div>
    </div>
  </div>
  <div class="aqews-months">{''.join(month_cards)}</div>
  <div class="aqews-legend">{legend}</div>
  <div class="aqews-note">
    {tracking_note}<strong>Disclaimer:</strong> The Delhi Decision Support System (DSS) is documented
    as operating in the post-monsoon and winter seasons. Availability may vary with the functioning
    of AQEWS and Air Today.
    <div class="aqews-sources">Sources: {sources}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
