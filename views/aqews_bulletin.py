"""The day's AQEWS "Air Quality and Weather Bulletin for Delhi", shown in full
in a dialog. Saved by ingestion/aqews.py (data/aqews_bulletin.json).

Since AQEWS redesigned its home page (around 7 Nov 2026) the bulletin is a
set of day cards ("days" in the JSON) instead of numbered prose sections
("paragraphs"); both are rendered."""
import re
from datetime import date
from html import escape

import streamlit as st

from config.reference import AQI_BANDS
from config.settings import AQEWS_BULLETIN_JSON
from ingestion.json_store import read_json

URL_RE = re.compile(r"(https?://[^\s)]+?)(?=[.,;]?(?:\s|$))")
SECTION_RE = re.compile(r"^(\d)\.\s*(?:([^:]{3,60}):\s*)?(.*)$")


@st.cache_data(ttl=600)
def load_bulletin() -> dict:
    return read_json(AQEWS_BULLETIN_JSON) or {}


def _linkify(text):
    out, last = [], 0
    for m in URL_RE.finditer(text):
        out.append(escape(text[last:m.start()]))
        url = m.group(1)
        out.append(f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(url)}</a>')
        last = m.end(1)
    out.append(escape(text[last:]))
    return "".join(out)


def _num(v, fmt="{:.0f}"):
    return "—" if v is None else fmt.format(v)


def _span(lo, hi):
    if lo is None:
        return "—"
    return f"{lo:.0f}" if hi is None or lo == hi else f"{lo:.0f}–{hi:.0f}"


def days_html(b: dict) -> str:
    """The bulletin's day cards: one row per day, values as published."""
    colour = {n: c for n, _lo, _hi, c in AQI_BANDS}
    rows = []
    for d in b.get("days", []):
        day = date.fromisoformat(d["date"])
        cat = d.get("category") or "—"
        vi = d.get("ventilation_index")
        verdict = ("<em class='aqb-bad'>Unfavourable for dispersion</em>" if d.get("dispersion_unfavourable")
                   else "")
        rows.append(
            "<div class='aqb-day'>"
            f"<div class='aqb-day-h'><b>{day:%a, %d %b}</b>"
            f"<span class='aqb-cat' style='--c:{colour.get(cat, '#6b7f99')}'>{escape(cat)}</span></div>"
            f"<div class='aqb-sky'>{escape(d.get('sky') or '')}</div>"
            "<dl>"
            f"<div><dt>Max</dt><dd>{_span(d.get('tmax_low'), d.get('tmax_high'))} °C</dd></div>"
            f"<div><dt>Min{' (observed)' if d.get('tmin_observed') else ''}</dt>"
            f"<dd>{_span(d.get('tmin_low'), d.get('tmin_high'))} °C</dd></div>"
            f"<div><dt>Wind</dt><dd>{escape(d.get('wind_direction') or '—')}"
            f"{', up to ' + _num(d.get('wind_max_kmh')) + ' km/h' if d.get('wind_max_kmh') else ''}</dd></div>"
            f"<div><dt>Mixing depth</dt><dd>{_num(d.get('mixing_depth'), '{:,.0f}')} m</dd></div>"
            f"<div><dt>Ventilation index</dt><dd>{_num(vi, '{:,.0f}')} m²/s</dd></div>"
            "</dl>"
            f"{verdict}</div>"
        )
    return f"<div class='aqb-days'>{''.join(rows)}</div>"


def bulletin_html(b: dict) -> str:
    rows = [days_html(b)] if b.get("days") else []
    for para in b.get("paragraphs", []):
        m = SECTION_RE.match(para)
        if m:
            num, head, body = m.groups()
            head_html = f"<b>{escape(head)}</b> " if head else ""
            rows.append(f"<div class='aqb-sec'><span class='aqb-num'>{num}</span>"
                        f"<p>{head_html}{_linkify(body)}</p></div>")
        else:
            rows.append(f"<p class='aqb-foot'>{_linkify(para)}</p>")
    src = b.get("source_url", "https://ews.tropmet.res.in/")
    fetched = b.get("fetched_at", "")
    return (
        f"<div class='aqb'>{''.join(rows)}"
        f"<div class='card-source'>Source: <a href='{escape(src)}' target='_blank' rel='noopener'>IITM AQEWS</a>"
        f"{' · fetched ' + escape(fetched[:16].replace('T', ' ')) + ' IST' if fetched else ''} · "
        + ("values as published on the bulletin cards" if b.get("days") else "shown as published; text is not edited")
        + "</div></div>"
    )


@st.dialog("AQEWS bulletin", width="large")
def bulletin_dialog(b):
    st.markdown(f"<div class='aqb-title'>{escape(b.get('title', ''))}</div>", unsafe_allow_html=True)
    st.markdown(bulletin_html(b), unsafe_allow_html=True)


def render_bulletin_button():
    b = load_bulletin()
    if not (b.get("paragraphs") or b.get("days")):
        return
    day = date.fromisoformat(b["date"]) if b.get("date") else None
    label = f"Read the AQEWS bulletin{f' · {day.day} {day:%b %Y}' if day else ''}"
    with st.container(key="aqews-bulletin-open"):
        if st.button(label, key="open_aqews_bulletin", icon=":material/description:", type="primary"):
            bulletin_dialog(b)
