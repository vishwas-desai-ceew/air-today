import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from config.settings import EFFECTIVE_DATE_CUTOFF
from ingestion.get_met_details import get_fire_count
from views.delhi_weather import STYLES, get_last_two_days
from views.render_aqi_fc import get_error_message
from views.components import metric_card, section_header


def _effective_today():
    now = datetime.now()
    if now.time() >= EFFECTIVE_DATE_CUTOFF:
        return now.date()
    return (now - timedelta(days=1)).date()


def render_home_overview(error_flag, is_mobile=False):
    """Landing page: the one number that matters (today's AQI), 3 supporting KPIs,
    and the data-freshness strip - see design.md 'Home Dashboard'."""
    today = _effective_today()
    section_header("Overview", caption=f"Delhi NCR &middot; {today.strftime('%d %B %Y')}")

    df = get_last_two_days()
    df1 = df.iloc[0] if not df.empty else None
    df2 = df.iloc[1] if len(df) > 1 else None

    aqi_value, aqi_category, aqi_delta = None, None, None
    if df1 is not None and not pd.isna(df1.get("aqi")):
        aqi_value = int(df1["aqi"])
        aqi_category = df1["category"]
        if df2 is not None and not pd.isna(df2.get("aqi")):
            aqi_delta = aqi_value - int(df2["aqi"])

    fire_total = None
    try:
        fire_counts = get_fire_count(today - timedelta(days=1))
        if fire_counts:
            fire_total = sum(fire_counts.values())
    except Exception:
        fire_total = None

    tomorrow_aqi, tomorrow_category = None, None
    try:
        _, df_aqi = get_error_message()
        tomorrow = today + timedelta(days=1)
        row = df_aqi[df_aqi["date"].dt.date == tomorrow]
        if not row.empty:
            tomorrow_aqi = round(row.iloc[0]["AQI_overall"])
            tomorrow_category = row.iloc[0].get("category")
    except Exception:
        pass

    n_cols = 2 if is_mobile else 4
    cols = st.columns(n_cols)

    with cols[0 % n_cols]:
        metric_card(
            "Latest AQI (Delhi)",
            aqi_value if aqi_value is not None else "—",
            caption=aqi_category or "No bulletin yet",
            delta=aqi_delta,
            delta_good_when="down",
            color=STYLES.get(aqi_category, {}).get("bg") if aqi_category else None,
        )
    with cols[1 % n_cols]:
        metric_card(
            "Fire count (Punjab + Haryana)",
            fire_total if fire_total is not None else "—",
            caption="yesterday, NASA VIIRS",
        )
    with cols[2 % n_cols]:
        metric_card(
            "Tomorrow's AQI forecast",
            tomorrow_aqi if tomorrow_aqi is not None else "—",
            caption=tomorrow_category or "AQEWS forecast",
            color=STYLES.get(tomorrow_category, {}).get("bg") if tomorrow_category else None,
        )
    with cols[3 % n_cols]:
        metric_card(
            "Data status",
            "Outage" if error_flag else "OK",
            caption="AQEWS portal",
            color="#E91902" if error_flag else "#1E8E5A",
        )



def render_glossary():
    glossary_html = """
        <section class="glossary" aria-label="Air quality glossary">
            <div class="glossary-intro">
                <span class="glossary-eyebrow">Reference guide</span>
                <p>Key terms used across Air Today, its data feeds, and daily updates.</p>
            </div>
            <div class="glossary-group">
                <h2>Air quality measures</h2>
                <div class="glossary-grid">
                    <article class="glossary-item"><span class="glossary-term">AQI</span><p><strong>Air Quality Index</strong> — a single number that communicates the health risk from multiple pollutants.</p></article>
                    <article class="glossary-item"><span class="glossary-term">AQ</span><p><strong>Air Quality</strong> — the condition of the air, based on the pollutants it contains.</p></article>
                    <article class="glossary-item"><span class="glossary-term">PM2.5</span><p><strong>Fine particulate matter</strong> — particles with a diameter of 2.5 micrometres or less.</p></article>
                    <article class="glossary-item"><span class="glossary-term">PM10</span><p><strong>Coarse particulate matter</strong> — particles with a diameter of 10 micrometres or less.</p></article>
                    <article class="glossary-item"><span class="glossary-term">NO₂</span><p><strong>Nitrogen dioxide</strong> — a pollutant largely associated with combustion, including road traffic.</p></article>
                    <article class="glossary-item"><span class="glossary-term">O₃</span><p><strong>Ozone</strong> — a ground-level pollutant formed through chemical reactions in sunlight.</p></article>
                    <article class="glossary-item"><span class="glossary-term">CO</span><p><strong>Carbon monoxide</strong> — a colourless gas produced by incomplete combustion.</p></article>
                    <article class="glossary-item"><span class="glossary-term">SO₂</span><p><strong>Sulfur dioxide</strong> — a gas released mainly from burning sulfur-containing fuels.</p></article>
                </div>
            </div>
            <div class="glossary-group">
                <h2>Monitoring &amp; institutions</h2>
                <div class="glossary-grid">
                    <article class="glossary-item"><span class="glossary-term">AQEWS</span><p><strong>Air Quality Early Warning System</strong> — provides air-quality forecasts and early warnings for Delhi.</p></article>
                    <article class="glossary-item"><span class="glossary-term">CAQMS</span><p><strong>Continuous Ambient Air Quality Monitoring System</strong> — automated instruments that measure pollutants continuously.</p></article>
                    <article class="glossary-item"><span class="glossary-term">CPCB</span><p><strong>Central Pollution Control Board</strong> — India’s national pollution-control authority.</p></article>
                    <article class="glossary-item"><span class="glossary-term">SPCB</span><p><strong>State Pollution Control Board</strong> — a state-level authority that regulates and monitors pollution.</p></article>
                    <article class="glossary-item"><span class="glossary-term">IMD</span><p><strong>India Meteorological Department</strong> — India’s national meteorological service.</p></article>
                    <article class="glossary-item"><span class="glossary-term">API</span><p><strong>Application Programming Interface</strong> — a way for systems to exchange data automatically.</p></article>
                </div>
            </div>
            <div class="glossary-group">
                <h2>Data status</h2>
                <div class="glossary-grid glossary-grid--status">
                    <article class="glossary-item"><span class="glossary-term glossary-term--alert">Outage</span><p><strong>Service interruption</strong> — a source or portal is temporarily unavailable or not responding as expected.</p></article>
                    <article class="glossary-item"><span class="glossary-term glossary-term--muted">Insufficient data</span><p><strong>Not enough validated observations</strong> — a value cannot be reliably reported for the relevant period.</p></article>
                </div>
            </div>
        </section>
        """
    st.markdown(
        glossary_html,
        unsafe_allow_html=True,
    )
