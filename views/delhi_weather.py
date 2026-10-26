import re
import calendar
import pandas as pd
import streamlit as st 
from pathlib import Path
from datetime import date, datetime, timedelta
from config.settings import EFFECTIVE_DATE_CUTOFF
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


def render_aqi_card(period, date, new_df, difference=None):
    style = STYLES.get(new_df["category"], DEF)
    if difference is not None:
        status_class = "improved" if difference < 0 else "deteriorated" if difference > 0 else "neutral"
        symbol = "▼" if difference < 0 else "▲" if difference > 0 else "•"
        status = {"improved": "Improved", "deteriorated": "Deteriorated", "neutral": "No change"}[status_class]
        comparison = f"<div class='aqi-comparison {status_class}'>{symbol} {abs(difference)} points · {status} from yesterday</div>"
    else:
        comparison = "<div class='aqi-comparison muted'>Reference bulletin</div>"

    st.markdown(
        f"""
        <article class='aqi-card'>
            <div class='aqi-card-topline'>
                <span class='aqi-period'>{period}</span>
                <span class='aqi-card-date'>{date}</span>
            </div>
            <div class='aqi-value'>{int(new_df["aqi"])}<span class='aqi-label'>AQI</span></div>
            <span class='aqi-category' style='background-color:{style['bg']}; color:{style['color']};'>
                {new_df["category"]}
            </span>
            {comparison}
        </article>
        """,
        unsafe_allow_html=True
    )



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
    cutoff = EFFECTIVE_DATE_CUTOFF
    now = datetime.now()
    if now.time() < cutoff:
        display_date = (now - timedelta(days=1)).date()
    else:
        display_date = now.date()
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
    

def render_aqi_delhi(compact=False):
    df = get_last_two_days()

    def render_fallback_view():
        error_msg = get_aqi_error_html()
        st.markdown(error_msg, unsafe_allow_html=True)
        st.write("")

    if df.empty:
        render_fallback_view()
        return df
        


    # Handle available rows safely
    df1 = df.iloc[0]
    df2 = df.iloc[1] if len(df) > 1 else None

   
    if pd.isna(df1['aqi']):
        st.error(f"No AQI bulletin found for {df1['date'].strftime('%d %B %Y')}. Please check back later.")
        render_fallback_view()
        return df

    # --- Compute AQI difference ---
    diff = 0
    if df2 is not None and not pd.isna(df2['aqi']):
        diff = int(df1['aqi']) - int(df2['aqi'])  # positive = worse
    st.markdown("<div class='aqi-overview-label'>Delhi AQI comparison <span>24-hour average · CPCB</span></div>", unsafe_allow_html=True)
    today_col, yesterday_col = st.columns(2, gap="medium")

    with today_col:
        date1 = df1['date'].strftime("%d %B %Y")
        render_aqi_card(period="Today", date=date1, new_df=df1, difference=diff if df2 is not None and not pd.isna(df2['aqi']) else None)

    with yesterday_col:
        if df2 is not None and not pd.isna(df2['aqi']):
            date2 = df2['date'].strftime("%d %B %Y")
            render_aqi_card(period="Yesterday", date=date2, new_df=df2)
        else:
            st.info("Yesterday's AQI bulletin is not available yet.")

    insights = get_insights()
    st.markdown(insights, unsafe_allow_html=True)
    return df


def render_health_advisory(df=None):
    """Render health guidance using already-loaded AQI rows when available."""
    if df is None:
        df = get_last_two_days()
    # Handle available rows safely
    if df.empty:
        return
    
    df1 = df.iloc[0]
    category = df1["category"]
    category_class = AQI_CATEGORY_CLASSES.get(category, "aqi-category-chip--unknown")
    impact = STYLES.get(category, DEF).get("impact", "No data available")
    st.markdown(
            f"""
            <section class="health-advisory-card">
                <div class="aqi-panel-title">
                    Health Advisory <span>(per CPCB)</span>
                </div>
                <ul>
                <li><span class="aqi-category-chip {category_class}">{category}</span> {impact}</li>
                <li><span class="aqi-category-chip-rec">Recommendation</span> Wear an <b>N95</b> mask outdoors during periods of severe air pollution.</li>
                </ul>
            </section>
            """,
            unsafe_allow_html=True
        )
    
    
        
                    
