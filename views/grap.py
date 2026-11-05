"""GRAP orders archive (winter 2025-26): month calendar -> dialog per date.

Reads data/grap_orders_2025_26.json, written once from the Excel archive by
ingestion/convert_grap_orders.py. Days with an order are clickable; clicking
opens a dialog with every order issued that day.
"""
import calendar
import json
from datetime import date
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

GRAP_JSON = Path(__file__).resolve().parent.parent / "data" / "grap_orders_2025_26.json"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@lru_cache(maxsize=1)
def load_grap_orders():
    with open(GRAP_JSON, encoding="utf-8") as f:
        payload = json.load(f)
    orders = {date.fromisoformat(k): v for k, v in payload["orders"].items()}
    return payload.get("season", ""), orders


def _tone(stage):
    """Badge colour from the stage text: invocations red, revocations green."""
    s = stage.lower()
    if "revoked" in s:
        return "revoked"
    if "invoked" in s and "no stage invoked" not in s and "no new stage invoked" not in s:
        return "invoked"
    return "other"


def _para(text):
    return "<br>".join(escape(line) for line in text.splitlines() if line.strip()) or "—"


def _season_months(order_days):
    first, last = min(order_days), max(order_days)
    months, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


@st.dialog("GRAP orders", width="large")
def grap_dialog(day):
    _, orders = load_grap_orders()
    day_orders = orders.get(day, [])
    st.markdown(
        f"<div class='grap-dlg-date'>{day.strftime('%A')} · {day.day} {day.strftime('%B %Y')}</div>"
        f"<div class='grap-dlg-count'>{len(day_orders)} order{'s' if len(day_orders) != 1 else ''} issued</div>",
        unsafe_allow_html=True,
    )
    for o in day_orders:
        note = f"<span class='grap-note'>{escape(o['date_label'])}</span>" if o["date_label"] else ""
        st.markdown(
            f"""
            <div class="grap-order">
              <div class="grap-order-head">
                <span class="grap-stage {_tone(o['stage'])}">{escape(o['stage'])}</span>{note}
              </div>
              <dl>
                <dt>AQI category</dt><dd>{_para(o['aqi_category'])}</dd>
                <dt>AQI / trigger</dt><dd>{_para(o['aqi_trigger'])}</dd>
                <dt>Key decision</dt><dd>{_para(o['key_decision'])}</dd>
                <dt>Reason</dt><dd>{_para(o['reason'])}</dd>
              </dl>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_grap():
    season, orders = load_grap_orders()
    if not orders:
        st.info("No GRAP orders are available.")
        return

    months = _season_months(orders)
    labels = [date(y, m, 1).strftime("%b %Y") for y, m in months]
    picked = st.segmented_control(
        "**Month**", options=labels, selection_mode="single", default=labels[0], key="grap_month",
    )
    if picked not in labels:  # deselected / stale state
        picked = labels[0]
    year, month = months[labels.index(picked)]

    cal_col, list_col = st.columns([3, 2], gap="large")
    with cal_col:
        with st.container(key="grap-cal", border=True):
            st.markdown(f"<div class='grap-cal-title'>{picked}</div>", unsafe_allow_html=True)
            # One grid row rather than 7 columns: tiny per-column markdown
            # blocks collapse on phones. The grid gap matches the button rows.
            st.markdown(
                "<div class='grap-wd-row'>" + "".join(f"<div class='grap-wd'>{wd}</div>" for wd in WEEKDAYS) + "</div>",
                unsafe_allow_html=True,
            )
            for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
                cols = st.columns(7, gap="small")
                for col, d in zip(cols, week):
                    with col:
                        if d == 0:
                            st.markdown("<div class='grap-blank'></div>", unsafe_allow_html=True)
                            continue
                        day = date(year, month, d)
                        if day in orders:
                            if st.button(str(d), key=f"grap_{day.isoformat()}", type="primary",
                                         width="stretch", help=f"{len(orders[day])} order(s) - click to view"):
                                grap_dialog(day)
                        else:
                            st.button(str(d), key=f"grap_{day.isoformat()}", type="tertiary",
                                      width="stretch", disabled=True)
            st.caption("Highlighted dates have a GRAP order. Click one to read it.")

    with list_col:
        st.markdown(f"<div class='grap-list-title'>Orders in {picked}</div>", unsafe_allow_html=True)
        month_days = [d for d in orders if (d.year, d.month) == (year, month)]
        if not month_days:
            st.caption("No GRAP orders were issued this month.")
        for day in month_days:
            for i, o in enumerate(orders[day]):
                label = f"{day.day} {day.strftime('%b')} · {o['stage']}"
                if st.button(label, key=f"grap_list_{day.isoformat()}_{i}", type="secondary", width="stretch"):
                    grap_dialog(day)

    st.caption(
        f"Source: CAQM GRAP orders, winter {season}, as compiled in the team's archive "
        "(data/AS - Winter GRAP Orders 01Oct2026.xlsx). Check the original CAQM order before citing."
    )
