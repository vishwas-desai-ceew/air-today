import streamlit as st

from views.components import outage_banner, section_header
from views.widgets import render_kpi_grid


def render_home_overview(error_flag, is_mobile=False):
    """Landing page: weather-style KPI cards for air and met conditions. The
    day's written update lives in the hero's Key insights dialog."""
    section_header("Conditions now", caption="Air quality, dispersion and weather for Delhi at a glance")
    render_kpi_grid()
    if error_flag:
        outage_banner(compact=is_mobile)


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
