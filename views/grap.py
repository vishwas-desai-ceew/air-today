"""GRAP orders: season timeline -> month calendar -> dialog per date.

Each winter is one JSON in data/grap/ (schema in ingestion/grap_orders.py),
refreshed daily from CAQM's GRAP Orders list. Stages are cumulative: once a
stage is invoked it stays in force, with every stage below it, until CAQM
revokes it. The page works out which stages were in force on each day from
the season's starting stage and its orders, and colours the calendar with
that. The stage colours are our own (config.reference.GRAP_STAGES); the page
says so next to every legend.
"""
from datetime import date, timedelta
from html import escape

import streamlit as st

from config.reference import GRAP_COLOURS_DISCLAIMER, GRAP_STAGES, SOURCES
from config.settings import GRAP_DIR
from ingestion.json_store import read_json
from views.calendar_grid import month_calendar, month_picker, months_between
from views.charts import source_line
from views.widgets import icon

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
STAGE = {n: {"label": label, "range": rng, "colour": c, "text": t} for n, label, rng, c, t in GRAP_STAGES}
NAVY = "#0a3d7a"
DETAIL_LABELS = {
    "aqi_trigger": "AQI / trigger",
    "aqi_category": "AQI category",
    "key_decision": "Key decision",
    "reason": "Reason",
}


# ---------------------------------------------------------------- data --
def load_seasons():
    """{season: {"orders": [...], "by_day": {date: [order]}, "start_level": int,
    "updated_at": str}}, newest first. Re-reads when a season file changes."""
    files = tuple((str(p), p.stat().st_mtime) for p in sorted(GRAP_DIR.glob("grap_*.json")))
    return _load_seasons(files)


@st.cache_data
def _load_seasons(files):
    seasons = {}
    for path, _mtime in files:
        payload = read_json(path)
        if payload.get("schema_version") != 2:
            continue
        by_day = {}
        for o in payload.get("orders", []):
            by_day.setdefault(date.fromisoformat(o["date"]), []).append(o)
        seasons[payload["season"]] = {
            "orders": payload.get("orders", []),
            "by_day": by_day,
            "start_level": int(payload.get("stage_at_start") or 0),
            "updated_at": payload.get("updated_at", ""),
        }
    return dict(sorted(seasons.items(), reverse=True))


def orders_by_day(season):
    """{date: [order]} for one season (used by the Recent trends page)."""
    return load_seasons().get(season, {}).get("by_day", {})


def apply_order(level, order):
    stages = order.get("stages") or []
    if order["action"] == "invoke" and stages:
        return max(level, max(stages))
    if order["action"] == "revoke" and stages:
        return min(level, min(stages) - 1)
    return level


def daily_levels(data, first, last):
    """{date: highest stage in force at the end of that day} from first to last."""
    level, out, day = data["start_level"], {}, first
    by_day = data["by_day"]
    for d in sorted(k for k in by_day if k < first):
        for o in by_day[d]:
            level = apply_order(level, o)
    while day <= last:
        for o in by_day.get(day, []):
            level = apply_order(level, o)
        out[day] = level
        day += timedelta(days=1)
    return out


def _season_months(label, orders):
    """Winter months Oct -> Feb of the season, stretched if any order falls outside."""
    start_year = int(label[:4])
    first, last = date(start_year, 10, 1), date(start_year + 1, 2, 1)
    if orders:
        first, last = min(first, min(orders)), max(last, max(orders))
    return months_between(first, last)


def _season_span(label, by_day):
    months = _season_months(label, by_day)
    (y0, m0), (y1, m1) = months[0], months[-1]
    nxt = date(y1 + (m1 == 12), m1 % 12 + 1, 1)
    return date(y0, m0, 1), nxt - timedelta(days=1)


# ------------------------------------------------------------- styling --
def stages_text(level):
    if level <= 0:
        return "No GRAP stage in force"
    if level == 1:
        return "Stage I in force"
    return f"Stages I–{ROMAN[level]} in force"


def _strip(level):
    """Bottom strip with one segment per stage in force, I..level."""
    w = 100 / level
    stops = ", ".join(f"{STAGE[s]['colour']} {(s - 1) * w:.1f}% {s * w:.1f}%" for s in range(1, level + 1))
    return f"linear-gradient(90deg, {stops}) bottom / 100% 6px no-repeat"


def day_style(level, has_order):
    css = []
    if level > 0:
        top = STAGE[level]["colour"]
        css.append(f"background: {_strip(level)}, color-mix(in srgb, {top} 24%, #ffffff) !important;")
        css.append("color: var(--text-primary) !important; opacity: 1 !important; border-color: transparent !important;")
    if has_order:
        if level == 0:
            css.append("background: #ffffff !important; color: var(--text-primary) !important;")
        css.append(f"box-shadow: inset 0 0 0 2px {NAVY} !important; font-weight: 800 !important;")
    return "".join(css)


def stage_chip(n, outline=False):
    s = STAGE[n]
    if outline:
        return (f"<span class='grap-chip grap-chip--out' style='--c:{s['colour']}'>"
                f"{escape(s['label'])}</span>")
    return (f"<span class='grap-chip' style='background:{s['colour']};color:{s['text']}'>"
            f"{escape(s['label'])}</span>")


def order_badge(o):
    stages = o.get("stages") or []
    if o["action"] == "invoke" and stages:
        s = STAGE[max(stages)]
        return (f"<span class='grap-badge' style='background:{s['colour']};color:{s['text']}'>"
                f"{icon('forecast', 14)}{escape(o['headline'])}</span>")
    if o["action"] == "revoke" and stages:
        return (f"<span class='grap-badge grap-badge--out' style='--c:{STAGE[min(stages)]['colour']}'>"
                f"↓ {escape(o['headline'])}</span>")
    return f"<span class='grap-badge grap-badge--other'>{icon('info', 14)}{escape(o['headline'])}</span>"


def button_css(o):
    stages = o.get("stages") or []
    if o["action"] == "invoke" and stages:
        s = STAGE[max(stages)]
        return (f"background:{s['colour']} !important;border-color:{s['colour']} !important;"
                f"color:{s['text']} !important;")
    if o["action"] == "revoke" and stages:
        c = STAGE[min(stages)]["colour"]
        return (f"background:#ffffff !important;border:2px solid {c} !important;"
                f"color:color-mix(in srgb, {c} 75%, #000000) !important;")
    return f"background:#ffffff !important;border:1px solid {NAVY} !important;color:{NAVY} !important;"


def legend_html():
    rows = "".join(
        f"<div class='grap-leg-row'><i style='background:{STAGE[n]['colour']}'></i>"
        f"<b>{escape(STAGE[n]['label'])}</b><span>{escape(STAGE[n]['range'])}</span></div>"
        for n in STAGE
    )
    return (
        f"<div class='grap-legend'>"
        f"<div class='cal-legend-title'>{icon('info', 15)}How to read the calendar</div>{rows}"
        f"<div class='grap-leg-note'><i class='grap-leg-strip'></i>Coloured day: GRAP in force. "
        f"The strip along the bottom shows every stage in force that day.</div>"
        f"<div class='grap-leg-note'><i class='grap-leg-ring'></i>Outlined day: CAQM issued an order. Click it to read.</div>"
        f"<div class='grap-disclaimer'>{icon('alert', 14)}<span>{escape(GRAP_COLOURS_DISCLAIMER)}</span></div>"
        f"</div>"
    )


# ------------------------------------------------------------ timeline --
def timeline_html(label, data, today):
    first, last = _season_span(label, data["by_day"])
    end = min(last, today)
    levels = daily_levels(data, first, end) if end >= first else {}
    span = (last - first).days + 1
    pct = lambda d: (d - first).days / span * 100

    rows = []
    for n in sorted(STAGE, reverse=True):
        bars, start, days_on = [], None, 0
        for d in sorted(levels):
            on = levels[d] >= n
            days_on += on
            if on and start is None:
                start = d
            if start is not None and (not on or d == end):
                stop = d if on else d - timedelta(days=1)
                bars.append(
                    f"<span class='grap-tl-bar' style='left:{pct(start):.2f}%;width:{(stop - start).days / span * 100 + 100 / span:.2f}%;"
                    f"background:{STAGE[n]['colour']}' title='{escape(STAGE[n]['label'])}: "
                    f"{start:%d %b} – {stop:%d %b %Y}'></span>"
                )
                start = None
        rows.append(
            f"<div class='grap-tl-row'><div class='grap-tl-name'>{escape(STAGE[n]['label'])}</div>"
            f"<div class='grap-tl-track'>{''.join(bars)}</div>"
            f"<div class='grap-tl-days'><b>{days_on}</b> day{'s' if days_on != 1 else ''}</div></div>"
        )

    ticks = "".join(
        f"<span style='left:{pct(date(y, m, 1)):.2f}%'>{date(y, m, 1):%b}</span>"
        for y, m in _season_months(label, data["by_day"])
    )
    marks = "".join(
        f"<span class='grap-tl-mark grap-tl-mark--{o['action']}' style='left:{pct(d) + 50 / span:.2f}%'"
        f" title='{d:%d %b %Y}: {escape(o['headline'])}'></span>"
        for d, day_orders in data["by_day"].items() for o in day_orders[:1] if first <= d <= last
    )
    now = (f"<span class='grap-tl-today' style='--p:{(pct(today) + 50 / span) / 100:.4f}'><em>Today</em></span>"
           if first <= today <= last else "")
    return (f"<div class='grap-tl'>"
            f"<div class='grap-tl-body'>{''.join(rows)}"
            f"<div class='grap-tl-row grap-tl-axis'><div class='grap-tl-name'></div>"
            f"<div class='grap-tl-track grap-tl-ticks'>{ticks}{marks}</div><div class='grap-tl-days'></div></div>{now}"
            f"</div></div>")


def status_html(label, data, today):
    first, last = _season_span(label, data["by_day"])
    current = first <= today <= last
    ref = min(today, last)
    level = daily_levels(data, first, ref).get(ref, data["start_level"]) if ref >= first else data["start_level"]
    peak = max(daily_levels(data, first, ref).values() or [0]) if ref >= first else 0
    if current:
        chips = "".join(stage_chip(n) for n in range(1, level + 1)) or "<span class='grap-none'>None</span>"
        head = f"{icon('alert', 16)}In force today · {today:%d %b %Y}"
    else:
        chips = (stage_chip(peak) if peak else "<span class='grap-none'>None</span>")
        head = f"{icon('forecast', 16)}Highest stage reached in {escape(label)}"
    return (f"<div class='grap-status'><div class='grap-status-head'>{head}</div>"
            f"<div class='grap-status-chips'>{chips}</div></div>")


# -------------------------------------------------------------- dialogs --
def _para(text):
    return "<br>".join(escape(line) for line in str(text).splitlines() if line.strip()) or "—"


def order_html(o):
    details = o.get("details") or {}
    rows = "".join(f"<dt>{escape(DETAIL_LABELS.get(k, k))}</dt><dd>{_para(v)}</dd>"
                   for k, v in details.items() if str(v).strip())
    notes = (f"<div class='grap-notes-title'>{icon('archive', 14)}Team archive notes</div><dl>{rows}</dl>"
             if rows else "")
    if o.get("pdf_url"):
        link = (f"<a class='grap-pdf' href='{escape(o['pdf_url'])}' target='_blank' rel='noopener'>"
                f"{icon('info', 14)}Open the CAQM order (PDF) ↗</a>")
    else:
        link = "<div class='grap-nopdf'>Recorded in the team's archive; no CAQM document is listed for it.</div>"
    title = (f"<div class='grap-title'>{escape(o['title'])}</div>"
             if o.get("title") and o["title"] != o["headline"] else "")
    return f"<div class='grap-order'><div class='grap-order-head'>{order_badge(o)}</div>{title}{notes}{link}</div>"


@st.dialog("GRAP orders", width="large")
def grap_dialog(season, day):
    data = load_seasons().get(season)
    if not data:
        return
    day_orders = data["by_day"].get(day, [])
    first, _ = _season_span(season, data["by_day"])
    level = daily_levels(data, first, day).get(day, 0)
    n = len(day_orders)
    chips = "".join(stage_chip(s) for s in range(1, level + 1)) or "<span class='grap-none'>None</span>"
    st.markdown(
        f"<div class='cal-dlg-date'>{day:%A} · {day.day} {day:%B %Y}</div>"
        f"<div class='cal-dlg-sub'>Winter {escape(season)} · {n} order{'s' if n != 1 else ''} issued</div>"
        f"<div class='grap-after'><span>In force at the end of the day</span>{chips}</div>",
        unsafe_allow_html=True,
    )
    for o in day_orders:
        st.markdown(order_html(o), unsafe_allow_html=True)


@st.dialog("AQI and GRAP stages", width="large")
def scale_dialog():
    from views.glossary import scale_html
    st.markdown(scale_html(), unsafe_allow_html=True)
    source_line("cpcb_aqi", "caqm_grap_schedule", note="GRAP stage AQI ranges from the CAQM schedule")
    st.caption(f":material/info: {GRAP_COLOURS_DISCLAIMER}")


# ----------------------------------------------------------------- page --
def render_grap():
    seasons = load_seasons()
    if not seasons:
        st.info("No GRAP orders are available yet. They appear after the daily GRAP update has run.")
        return
    today = date.today()

    labels = list(seasons)
    season_col, month_col = st.columns([2, 3], gap="large")
    with season_col:
        season = st.segmented_control(
            "**:material/ac_unit: Winter season**", options=labels, selection_mode="single", default=labels[0],
            key="grap_season",
        )
    if season not in labels:
        season = labels[0]
    data = seasons[season]
    by_day = data["by_day"]

    months = _season_months(season, by_day)
    first, last = _season_span(season, by_day)
    if first <= today <= last:
        default = (today.year, today.month)
    else:
        first_order = min(by_day) if by_day else None
        default = (first_order.year, first_order.month) if first_order else None
    with month_col:
        year, month = month_picker(f"grap_month_{season}", months, default=default)

    with st.container(border=True, key="grap-timeline"):
        head_col, status_col = st.columns([3, 2], vertical_alignment="center")
        head_col.markdown(
            f"<div class='cal-side-title'>{icon('layers', 20)}Winter {escape(season)}: GRAP stages over the season</div>"
            "<div class='grap-tl-sub'>Each bar is a stretch of days a stage was in force. "
            "Stages build on each other: Stage III in force means Stages I and II are too.</div>",
            unsafe_allow_html=True,
        )
        status_col.markdown(status_html(season, data, today), unsafe_allow_html=True)
        st.markdown(timeline_html(season, data, today), unsafe_allow_html=True)

    month_first = date(year, month, 1)
    month_last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    levels = daily_levels(data, first, min(month_last, today)) if min(month_last, today) >= first else {}
    day_css = {d: day_style(levels[d], d in by_day) for d in levels if d >= month_first and (levels[d] or d in by_day)}

    def tip(d):
        heads = "; ".join(o["headline"] for o in by_day[d])
        return f"{heads}. {stages_text(levels.get(d, 0))} at the end of the day. Click to read."

    cal_col, list_col = st.columns([3, 2], gap="large")
    with cal_col:
        month_calendar(
            f"grap_{season}", year, month, set(by_day),
            on_select=lambda d: grap_dialog(season, d),
            help_text=tip,
            caption=":material/info: Coloured days had a GRAP stage in force. Outlined days have a CAQM order: click one to read it.",
            day_css=day_css,
        )
        with st.container(key="grap-caqm-link"):
            st.link_button("CAQM GRAP orders", SOURCES["caqm_grap_orders"][1], icon=":material/open_in_new:",
                           width="stretch")

    with list_col:
        st.markdown(f"<div class='cal-side-title'>{icon('calendar', 20)}Orders in {month_first:%B %Y}</div>",
                    unsafe_allow_html=True)
        month_days = sorted(d for d in by_day if (d.year, d.month) == (year, month))
        if not month_days:
            st.caption(":material/event_busy: No GRAP orders were issued this month.")
        rules = []
        for day in month_days:
            for i, o in enumerate(by_day[day]):
                key = f"grap_list_{season}_{day.isoformat()}_{i}"
                rules.append(f".st-key-{key} button{{{button_css(o)}}}")
                ico = {"invoke": ":material/trending_up:", "revoke": ":material/trending_down:"}.get(
                    o["action"], ":material/description:")
                if st.button(f"{day.day} {day:%b} · {o['headline']}", key=key, icon=ico, width="stretch"):
                    grap_dialog(season, day)
        if rules:
            st.html(f"<style>{''.join(rules)}</style>")
        st.markdown(legend_html(), unsafe_allow_html=True)
        if st.button("AQI and GRAP stages", key="grap_scale", icon=":material/menu_book:", width="stretch"):
            scale_dialog()

    updated = data["updated_at"][:16].replace("T", " ")
    source_line(
        "caqm_grap_orders", "caqm_grap_schedule",
        note=(f"orders as listed by CAQM, last checked {updated} IST" if updated else "orders as listed by CAQM")
        + (". Order notes for 2025-26 are from the team's GRAP archive" if any(o.get("details") for o in data["orders"]) else "")
        + ". Check the original CAQM order before citing",
    )
