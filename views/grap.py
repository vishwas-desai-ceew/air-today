"""GRAP orders archive: season pills -> month calendar -> dialog per date.

Each winter is its own JSON file, data/grap_orders_<YYYY>_<YY>.json, written
from that season's Excel sheet by ingestion/convert_grap_orders.py. Seasons
are discovered from the files present, so adding 2026-27 or 2023-24 is just
dropping in another JSON. Sheets differ between years, so the dialog shows
whatever fields a season has: known ones with tidy labels first, the rest
with their column name.
"""
import json
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

from views.calendar_grid import month_calendar, month_picker, months_between

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Known fields, in display order. Anything else is shown after these.
FIELD_LABELS = {
    "aqi_category": "AQI category",
    "aqi_trigger": "AQI / trigger",
    "key_decision": "Key decision",
    "reason": "Reason",
}
HIDDEN_FIELDS = {"sr_no", "date_label", "stage"}  # stage/date_label go in the card header


def load_seasons():
    """{season label: {date: [order, ...]}}, newest season first. Re-reads
    whenever a season file is added or changed."""
    files = tuple((str(p), p.stat().st_mtime) for p in sorted(DATA_DIR.glob("grap_orders_*.json")))
    return _load_seasons(files)


@st.cache_data
def _load_seasons(files):
    seasons = {}
    for path, _mtime in files:
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        label = payload.get("season") or path.stem.removeprefix("grap_orders_").replace("_", "-")
        seasons[label] = {date.fromisoformat(k): v for k, v in payload.get("orders", {}).items()}
    return dict(sorted(seasons.items(), reverse=True))


def _season_months(label, orders):
    """Winter months Oct -> Feb of the season, stretched if any order falls outside."""
    start_year = int(label[:4])
    first, last = date(start_year, 10, 1), date(start_year + 1, 2, 1)
    if orders:
        first, last = min(first, min(orders)), max(last, max(orders))
    return months_between(first, last)


def _tone(stage):
    """Badge colour from the stage text: invocations red, revocations green."""
    s = stage.lower()
    if "revoked" in s:
        return "revoked"
    if "invoked" in s and "no stage invoked" not in s and "no new stage invoked" not in s:
        return "invoked"
    return "other"


def _para(text):
    return "<br>".join(escape(line) for line in str(text).splitlines() if line.strip()) or "—"


def _label(field):
    return FIELD_LABELS.get(field, field.replace("_", " ").capitalize())


def _order_html(o):
    stage = o.get("stage", "")
    head = f"<span class='grap-stage {_tone(stage)}'>{escape(stage)}</span>" if stage else ""
    if o.get("date_label"):
        head += f"<span class='grap-note'>{escape(o['date_label'])}</span>"
    fields = [k for k in FIELD_LABELS if k in o] + [k for k in o if k not in FIELD_LABELS and k not in HIDDEN_FIELDS]
    rows = "".join(f"<dt>{escape(_label(k))}</dt><dd>{_para(o[k])}</dd>" for k in fields if str(o[k]).strip())
    return f"<div class='grap-order'><div class='grap-order-head'>{head}</div><dl>{rows}</dl></div>"


@st.dialog("GRAP orders", width="large")
def grap_dialog(season, day):
    day_orders = load_seasons().get(season, {}).get(day, [])
    n = len(day_orders)
    st.markdown(
        f"<div class='cal-dlg-date'>{day.strftime('%A')} · {day.day} {day.strftime('%B %Y')}</div>"
        f"<div class='cal-dlg-sub'>Winter {escape(season)} · {n} order{'s' if n != 1 else ''} issued</div>",
        unsafe_allow_html=True,
    )
    for o in day_orders:
        st.markdown(_order_html(o), unsafe_allow_html=True)


def render_grap():
    seasons = load_seasons()
    if not seasons:
        st.info("No GRAP orders are available.")
        return

    labels = list(seasons)
    season_col, month_col = st.columns([2, 3], gap="large")
    with season_col:
        season = st.segmented_control(
            "**Winter season**", options=labels, selection_mode="single", default=labels[0], key="grap_season",
        )
    if season not in labels:
        season = labels[0]
    orders = seasons[season]

    months = _season_months(season, orders)
    # Open on the month of the season's first order rather than an empty October.
    first_order = min(orders) if orders else None
    with month_col:
        year, month = month_picker(
            f"grap_month_{season}", months, default=(first_order.year, first_order.month) if first_order else None,
        )

    cal_col, list_col = st.columns([3, 2], gap="large")
    with cal_col:
        month_calendar(
            f"grap_{season}", year, month, set(orders),
            on_select=lambda d: grap_dialog(season, d),
            help_text=lambda d: f"{len(orders[d])} order(s) - click to view",
            caption="Highlighted dates have a GRAP order. Click one to read it.",
        )

    with list_col:
        st.markdown(f"<div class='cal-side-title'>Orders in {date(year, month, 1):%B %Y}</div>", unsafe_allow_html=True)
        month_days = [d for d in orders if (d.year, d.month) == (year, month)]
        if not month_days:
            st.caption("No GRAP orders were issued this month.")
        for day in month_days:
            for i, o in enumerate(orders[day]):
                label = f"{day.day} {day:%b} · {o.get('stage') or 'Order'}"
                if st.button(label, key=f"grap_list_{season}_{day.isoformat()}_{i}", width="stretch"):
                    grap_dialog(season, day)

    st.caption(
        f"Source: CAQM GRAP orders, winter {season}, as compiled in the team's archive. "
        "Check the original CAQM order before citing."
    )
