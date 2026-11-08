"""Shared month calendar (GRAP and Archive pages).

A 7-column grid of day buttons: days with content are clickable and call
`on_select(day)` (which opens the page's st.dialog); every other day is
greyed out. Days can carry an extra marker class (e.g. "warn") that is
styled through a small generated <style> block keyed on the button keys.
"""
import calendar
from datetime import date

import streamlit as st

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def months_between(first, last):
    """[(year, month), ...] from first to last inclusive."""
    out, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_picker(key, months, default=None):
    """Segmented control of months -> (year, month). Defaults to `default`
    if given and present, else the first month."""
    labels = [date(y, m, 1).strftime("%b %Y") for y, m in months]
    default_label = labels[months.index(default)] if default in months else labels[0]
    picked = st.segmented_control(
        "**:material/date_range: Month**", options=labels, selection_mode="single", default=default_label, key=key,
    )
    if picked not in labels:  # deselected or stale state from another season/year
        picked = default_label
    return months[labels.index(picked)]


def month_calendar(key, year, month, active_days, on_select, markers=None, help_text=None, caption=None):
    """Render one month. active_days: set of dates that are clickable.
    markers: {date: "warn" | "info"} extra styling. help_text(day) -> tooltip."""
    markers = markers or {}
    btn_key = lambda d: f"{key}_{d.isoformat()}"
    with st.container(key=f"calgrid-{key}", border=True):
        st.markdown(
            f"<div class='cal-title'>{date(year, month, 1).strftime('%B %Y')}</div>"
            "<div class='cal-wd-row'>" + "".join(f"<div class='cal-wd'>{wd}</div>" for wd in WEEKDAYS) + "</div>",
            unsafe_allow_html=True,
        )
        if markers:
            # Per-day marker styles (st.button can't take a class).
            rules = []
            for d, cls in markers.items():
                if (d.year, d.month) == (year, month) and d in active_days:
                    rules.append(f".st-key-{btn_key(d)} button{{{MARKER_CSS.get(cls, '')}}}")
            if rules:
                st.html(f"<style>{''.join(rules)}</style>")
        for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
            for col, d in zip(st.columns(7, gap="small"), week):
                with col:
                    if d == 0:
                        st.markdown("<div class='cal-blank'></div>", unsafe_allow_html=True)
                        continue
                    day = date(year, month, d)
                    if day in active_days:
                        if st.button(str(d), key=btn_key(day), type="primary", width="stretch",
                                     help=help_text(day) if help_text else None):
                            on_select(day)
                    else:
                        st.button(str(d), key=btn_key(day), type="tertiary", width="stretch", disabled=True)
        if caption:
            st.caption(caption)


MARKER_CSS = {
    # amber ring: e.g. archive days whose AQEWS forecast was missing
    "warn": "background:#b7791f !important;border-color:#b7791f !important;",
}
