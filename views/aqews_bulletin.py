"""The day's AQEWS "Air Quality and Weather Bulletin for Delhi", shown in full
in a dialog. Text is saved by ingestion/aqews.py (data/aqews_bulletin.json)."""
import re
from datetime import date
from html import escape

import streamlit as st

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


def bulletin_html(b: dict) -> str:
    rows = []
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
        "shown as published; text is not edited</div></div>"
    )


@st.dialog("AQEWS bulletin", width="large")
def bulletin_dialog(b):
    st.markdown(f"<div class='aqb-title'>{escape(b.get('title', ''))}</div>", unsafe_allow_html=True)
    st.markdown(bulletin_html(b), unsafe_allow_html=True)


def render_bulletin_button():
    b = load_bulletin()
    if not b.get("paragraphs"):
        return
    day = date.fromisoformat(b["date"]) if b.get("date") else None
    label = f"Read the AQEWS bulletin{f' · {day.day} {day:%b %Y}' if day else ''}"
    with st.container(key="aqews-bulletin-open"):
        if st.button(label, key="open_aqews_bulletin", icon=":material/description:", type="primary"):
            bulletin_dialog(b)
