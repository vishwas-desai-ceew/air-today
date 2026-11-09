import re
import calendar
import pandas as pd
import streamlit as st 
from pathlib import Path
from datetime import date, datetime, timedelta
from config.settings import effective_today
from config.formatting import ordinal
from ingestion.json_store import read_json


from config.settings import ARCHIVE_TEMP, CPCB_AQI_CSV as AQI_CSV_FILE


STYLES = {
            "Good": {"bg": "#2d662a", "color": "white", "shadow": "#9ED990", "impact": "Minimal Impact"}, 
            "Satisfactory": {"bg": "#03A303", "color": "white", "shadow": "#7AB07A", "impact": " Minor breathing discomfort to sensitive people"}, 
            "Moderate": {"bg": "#E0B400", "color": "black", "shadow": "#a18800", "impact": "Breathing discomfort to the people with lungs, asthma and heart diseases"},
            "Poor": {"bg": "#f78c00", "color": "white", "shadow": "#f0c286", "impact": " Breathing discomfort to most people on prolonged exposure"}, 
            "Very Poor": {"bg": "#fc4d02", "color": "white", "shadow": "#f59d77", "impact": "Respiratory illness on prolonged exposure"}, 
            "Severe": {"bg": "#e91902", "color": "white", "shadow": "#c47a7a", "impact": "Affects healthy people and seriously impacts those with existing diseases"}, 
        }
DEF = {"bg": "#820d00", "color": "white", "shadow": "#c47a7a", "category": "No data"}
AQI_CATEGORY_CLASSES = {
    "Good": "aqi-category-chip--good",
    "Satisfactory": "aqi-category-chip--satisfactory",
    "Moderate": "aqi-category-chip--moderate",
    "Poor": "aqi-category-chip--poor",
    "Very Poor": "aqi-category-chip--very-poor",
    "Severe": "aqi-category-chip--severe",
}

def get_last_two_days(csv_path=AQI_CSV_FILE):
    # One implementation, shared with the daily-summary builder.
    from ingestion.get_aqi_summary import get_last_two_days as _shared
    return _shared(csv_path)


def load_summary_json(json_file=ARCHIVE_TEMP):
    data = read_json(json_file)
    return next(iter(data.items()))


def highlight_text(text):
    months = "|".join(calendar.month_name[1:])  
    text = re.sub(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)\s+({months}))\b",
        r"<b>\1</b>",
        text,
    )
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)(?![a-z])\b",
        r"<span style='background:#f0f0f0; padding:0.1rem 0.3rem; border-radius:0.3rem; font-weight:600;'>\1</span>",
        text,
    )

    units = ["m/s", "m²/s", "°C"]
    for unit in units:
        unit_rep = f"<span style='background:#f0f0f0; padding:0.1rem 0.2rem; border-radius:0.3rem; font-weight:600;'>{unit}</span>"
        text = text.replace(unit, unit_rep)
    replacements = {
        "N/A":"<span style='background-color:black;color:white;padding:0.1rem 0.1rem;border-radius:0.3rem;font-weight:100;'>&nbsp;Not&nbsp;Available&nbsp;</span>",
        "Very Poor": "<span style='background-color:#fc4d02;color:white;padding:0.1rem 0.1rem;border-radius:0.3rem;font-weight:600;'>&nbsp;Very&nbsp;Poor&nbsp;</span>",
        "Satisfactory": "<span style='font-weight:600;background-color:#03A303;color:white;padding:0.1rem 0.3rem;border-radius:0.3rem;'>&nbsp;Satisfactory&nbsp;</span>",
        "Moderate": "<span style='font-weight:600;background-color:#E0B400;color:black;padding:0.1rem 0.3rem;border-radius:0.3rem;'>&nbsp;Moderate&nbsp;</span>",
        "Good": "<span style='font-weight:600;background-color:#2d662a;color:white;padding:0.1rem 0.3rem;border-radius:0.3rem;'>&nbsp;Good&nbsp;</span>",
        "Poor": "<span style='font-weight:600;background-color:#f78c00;color:white;padding:0.1rem 0.1rem;border-radius:0.3rem;'>&nbsp;Poor&nbsp;</span>",
        "Severe": "<span style='font-weight:600;background-color:#e91902;color:white;padding:0.1rem 0.3rem;border-radius:0.3rem;'>&nbsp;Severe&nbsp;</span>",
        "AQI": "<span style='font-weight:600;'>AQI</span>",
    }

    keys = sorted(replacements.keys(), key=lambda s: -len(s))
    escaped_keys = [re.escape(k).replace(r'\ ', r'\s+') for k in keys]
    alternation = "|".join(escaped_keys)
    pattern = re.compile(r'(?<!\w)(' + alternation + r')(?!\w)', flags=re.IGNORECASE)
    parts = re.split(r'(<[^>]*>)', text)

    def repl(match):
        matched_text = match.group(0)
        for k in keys:
            key_pattern = re.compile(r'^' + re.escape(k).replace(r'\ ', r'\s+') + r'$', flags=re.IGNORECASE)
            if key_pattern.match(matched_text):
                return replacements[k]
        return matched_text

    for i, seg in enumerate(parts):
        if seg.startswith("<") and seg.endswith(">"):
            continue
        parts[i] = pattern.sub(repl, seg)
    return "".join(parts)


def format_date_key(date_key):
    if isinstance(date_key, str):
        date_obj = datetime.strptime(date_key, "%Y-%m-%d").date()
    elif isinstance(date_key, datetime):
        date_obj = date_key.date()
    elif isinstance(date_key, date):
        date_obj = date_key
    else:
        raise ValueError("Invalid date type for date_key")

    return f"{ordinal(date_obj.day)} {date_obj.strftime('%B')}"


def _is_attention_insight(entry):
    """Flag unavailable data and confirmed zero-fire updates for a warning dot."""
    plain_entry = re.sub(r"[*_`]", "", entry)
    is_unavailable = "unavailable" in plain_entry.lower()
    is_zero_fire_count = bool(
        re.search(r"\bfire\s+count\s+on\b.*?\bis\s+0\b", plain_entry, flags=re.IGNORECASE)
    )
    return is_unavailable or is_zero_fire_count


def get_insights():
    date_key, entries = load_summary_json()
    date_str = format_date_key(date_key)
    items_html = "\n".join(
        f'<li class="insight-item--alert">{highlight_text(entry)}</li>'
        if _is_attention_insight(entry)
        else f"<li>{highlight_text(entry)}</li>"
        for entry in entries
    )
    insight = f"""
                <section class="aqi-insights-card">
                    <div class="aqi-panel-title">
                        Key Insights for {date_str}
                    </div>
                    <ul class="custom-list">
                      {items_html}
                    </ul>
                </section>"""
    return insight


def get_aqi_error_html():
    display_date = effective_today()
    today_str = format_date_key(display_date)
    error_message = f"""
    <section class="aqi-error-card">
        <div class="aqi-panel-title">Insufficient AQI Data</div>
        <ul class="custom-list1">
            <li>CPCB bulletin unavailable for <b>{today_str}</b> for the Delhi NCR region</li>
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>Insufficient AQI data to render forecasts or insights for <b>{today_str}</b></li>
        </ul>
    </section>"""
    return error_message
    

def _change_html(row, prev):
    """'▲ 13 vs 5 Nov' coloured by direction, or '' when the previous day is missing."""
    if prev is None:
        return "<div class='aqi-day-change muted'>No bulletin for the day before</div>"
    diff = int(row["aqi"]) - int(prev["aqi"])
    cls = "deteriorated" if diff > 0 else "improved" if diff < 0 else "neutral"
    word = {"deteriorated": "worse", "improved": "better", "neutral": "no change"}[cls]
    symbol = {"deteriorated": "▲", "improved": "▼", "neutral": "•"}[cls]
    return (f"<div class='aqi-day-change {cls}'>{symbol} {abs(diff)} points vs "
            f"{prev['date'].day} {prev['date']:%b} · {word}</div>")


def render_aqi_days(latest_date, n_days=5):
    """The latest CPCB bulletin as a large blue card (half the width) and the
    previous n_days-1 days as smaller grey archived cards beside it."""
    from html import escape
    from views import data
    from views.widgets import cpcb_src

    hist = data.cpcb_history()
    hist = hist[hist["aqi"].notna() & (hist["date"] <= latest_date)]
    by_date = {r["date"]: r for r in hist.to_dict("records")}
    days = [latest_date - timedelta(days=i) for i in range(n_days)]

    def chip(row):
        style = STYLES.get(row["category"], DEF)
        return (f"<span class='aqi-category' style='background-color:{style['bg']};color:{style['color']}'>"
                f"{escape(str(row['category']))}</span>")

    def prev_of(day):
        return by_date.get(day - timedelta(days=1))

    latest = by_date[latest_date]
    impact = STYLES.get(latest["category"], DEF).get("impact", "").strip()
    pollutant = escape(str(latest.get("pollutant") or "—"))
    latest_html = f"""
        <article class='aqi-day aqi-day--latest'>
            <div class='aqi-day-top'>
                <span class='aqi-day-date'>{latest_date.day} {latest_date:%B %Y}</span>
                <span class='aqi-day-tag'>Latest bulletin</span>
            </div>
            <div class='aqi-day-main'>
                <div class='aqi-value'>{int(latest["aqi"])}<span class='aqi-label'>AQI</span></div>
                {chip(latest)}
            </div>
            <div class='aqi-day-facts'>
                <div><span>Health impact</span><b>{escape(impact) or "—"}</b></div>
                <div><span>Prominent pollutant</span><b>{pollutant}</b></div>
            </div>
            {_change_html(latest, prev_of(latest_date))}
            <div class='card-source'>Source: {cpcb_src(latest)}</div>
        </article>"""

    past_html = ""
    for day in days[1:]:
        row = by_date.get(day)
        if row is None:
            past_html += f"""
                <article class='aqi-day aqi-day--archived aqi-day--missing'>
                    <div class='aqi-day-top'><span class='aqi-day-date'>{day.day} {day:%b %Y}</span></div>
                    <div class='aqi-day-none'>No bulletin</div>
                </article>"""
            continue
        past_html += f"""
            <article class='aqi-day aqi-day--archived'>
                <div class='aqi-day-top'>
                    <span class='aqi-day-date'>{day.day} {day:%b %Y}</span>
                    <span class='aqi-day-tag'>Archived</span>
                </div>
                <div class='aqi-day-main'>
                    <div class='aqi-value'>{int(row["aqi"])}<span class='aqi-label'>AQI</span></div>
                    {chip(row)}
                </div>
                {_change_html(row, prev_of(day))}
                <div class='card-source'>Source: {cpcb_src(row)}</div>
            </article>"""

    st.markdown(
        f"<div class='aqi-overview-label'>Delhi AQI, last {n_days} days <span>24-hour average · CPCB</span></div>"
        f"<div class='aqi-days'>{latest_html}<div class='aqi-days-past'>{past_html}</div></div>"
        .replace("\n", ""),
        unsafe_allow_html=True,
    )


def render_aqi_delhi(compact=False, show_insights=True):
    df = get_last_two_days()

    def render_fallback_view():
        error_msg = get_aqi_error_html()
        st.markdown(error_msg, unsafe_allow_html=True)
        st.write("")

    if df.empty:
        render_fallback_view()
        return df
        


    df1 = df.iloc[0]
    if pd.isna(df1['aqi']):
        st.error(f"No AQI bulletin found for {df1['date'].strftime('%d %B %Y')}. Please check back later.")
        render_fallback_view()
        return df

    render_aqi_days(df1["date"])

    if show_insights:
        st.markdown(get_insights(), unsafe_allow_html=True)
    return df


def render_health_advisory(df=None):
    """Health advisory for the latest CPCB AQI category, from the Ministry of
    Health / NCDC air pollution advisory (config.reference.HEALTH_ADVISORY):
    possible health effects, advice for everyone and for vulnerable groups,
    and, on days above AQI 200, the advisory's practical steps."""
    from html import escape
    from config.reference import HEALTH_ADVISORY, HEALTH_STEPS_ABOVE_200, HEALTH_VULNERABLE, SOURCES
    if df is None:
        df = get_last_two_days()
    if df.empty:
        return
    category = df.iloc[0]["category"]
    if category not in HEALTH_ADVISORY:
        return
    effects, general, vulnerable = HEALTH_ADVISORY[category]
    chip = AQI_CATEGORY_CLASSES.get(category, "aqi-category-chip--unknown")
    name, url = SOURCES["mohfw_air_advisory"]
    steps = ""
    if category in ("Poor", "Very Poor", "Severe"):     # AQI above 200
        steps = ("<div class='ha-steps'><div class='ha-label'>On days above AQI 200</div><ul>"
                 + "".join(f"<li>{escape(step)}</li>" for step in HEALTH_STEPS_ABOVE_200) + "</ul></div>")
    st.markdown(
        "<section class='health-advisory-card'>"
        "<div class='aqi-panel-title'>Health advisory</div>"
        f"<div class='ha-effects'><span class='aqi-category-chip {chip}'>{escape(category)}</span>"
        "<div><div class='ha-label'>Possible health effects</div>"
        + "".join(f"<p>{escape(e)}</p>" for e in effects) + "</div></div>"
        "<div class='ha-advice'>"
        f"<div><div class='ha-label'>Everyone</div><p>{escape(general)}</p></div>"
        f"<div><div class='ha-label'>Vulnerable groups</div><p>{escape(vulnerable)}</p>"
        f"<small>{escape(HEALTH_VULNERABLE)}</small></div>"
        "</div>"
        f"{steps}"
        f"<div class='side-source'><b>Source</b><a href='{escape(url)}' target='_blank' rel='noopener'>"
        f"{escape(name)}</a> · advice for the day's CPCB AQI category</div>"
        "</section>",
        unsafe_allow_html=True,
    )
