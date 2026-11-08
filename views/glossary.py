"""Glossary: the AQI and GRAP scale as a picture, then searchable,
filterable term cards. Terms carry a source where they state a threshold."""
from html import escape

import streamlit as st

from config.reference import (AQI_BANDS, AQI_HEALTH, GRAP_COLOURS_DISCLAIMER, GRAP_STAGES as GRAP_STAGE_DEFS,
                              SOURCES, VENTILATION_INDEX_UNFAVOURABLE)
from views.charts import source_line

# GRAP stages by AQI, from CAQM's GRAP schedule (SOURCES["caqm_grap_schedule"]).
GRAP_STAGES = [("Stage I", 201, 300), ("Stage II", 301, 400), ("Stage III", 401, 450), ("Stage IV", 451, 500)]
_STAGE_COLOUR = {label: colour for _n, label, _r, colour, _t in GRAP_STAGE_DEFS}

# (term, expansion, definition, category, source key or None)
TERMS = [
    ("AQI", "Air Quality Index", "A single number that communicates the health risk from multiple pollutants. CPCB's "
     "index runs from 0 to 500 in six categories; the overall AQI is the highest of the individual pollutant "
     "sub-indices.", "Air quality", "cpcb_aqi"),
    ("AQ", "Air Quality", "The condition of the air, based on the pollutants it contains.", "Air quality", None),
    ("PM2.5", "Fine particulate matter", "Particles with a diameter of 2.5 micrometres or less. CPCB's 24-hour "
     "breakpoints: 30, 60, 90, 120 and 250 µg/m³ mark the upper ends of Good to Very Poor.", "Air quality", "cpcb_aqi"),
    ("PM10", "Coarse particulate matter", "Particles with a diameter of 10 micrometres or less.", "Air quality", None),
    ("NO₂", "Nitrogen dioxide", "A pollutant largely associated with combustion, including road traffic.", "Air quality", None),
    ("O₃", "Ozone", "A ground-level pollutant formed through chemical reactions in sunlight.", "Air quality", None),
    ("CO", "Carbon monoxide", "A colourless gas produced by incomplete combustion.", "Air quality", None),
    ("SO₂", "Sulphur dioxide", "A gas released mainly from burning sulphur-containing fuels.", "Air quality", None),
    ("Sub-index", "Pollutant sub-index", "The AQI value for one pollutant. The overall AQI is the maximum of the "
     "sub-indices, and the pollutant that sets it is the prominent pollutant.", "Air quality", "cpcb_aqi"),

    ("Mixing height", "Boundary layer height", "The depth of the lowest layer of the atmosphere in which pollution "
     "mixes. It is shallow at night and in winter, which keeps pollution close to the ground.", "Weather", None),
    ("Ventilation index", "VI, m²/s", "Mixing height multiplied by the average wind speed in that layer: how well the "
     f"air can carry pollution away. The IITM AQEWS bulletin treats a value below {VENTILATION_INDEX_UNFAVOURABLE:,} "
     "m²/s, with average wind below 10 km/h, as unfavourable for dispersion.", "Weather", "iitm_aqews"),
    ("Inversion", "Temperature inversion", "A layer where temperature rises with height instead of falling. It acts "
     "as a lid on vertical mixing, common on calm winter nights.", "Weather", None),
    ("Rain classes", "IMD 24-hour rainfall", "Very light 0.1–2.4 mm, light 2.5–7.5 mm, moderate 7.6–35.5 mm, rather "
     "heavy 35.6–64.4 mm, heavy 64.5–124.4 mm in a day.", "Weather", "imd_glossary"),
    ("METAR", "Aviation weather report", "A routine observation report from an airport weather station. The "
     "dashboard's live weather uses Safdarjung (VIDD), with IGI Airport (VIDP) as fallback.", "Weather", None),

    ("GRAP", "Graded Response Action Plan", "Emergency measures for Delhi NCR applied in stages as air quality "
     "worsens: Stage I at AQI 201–300, II at 301–400, III at 401–450 and IV above 450. Each stage adds to the ones "
     "before it.", "Policy", None),
    ("CAQM", "Commission for Air Quality Management in NCR and Adjoining Areas", "The statutory body that invokes "
     "and revokes GRAP stages.", "Policy", None),
    ("NCAP", "National Clean Air Programme", "The national programme for improving air quality in Indian cities.",
     "Policy", None),
    ("CRM", "Crop residue management", "Handling paddy straw without burning it, either in the field (in-situ) or "
     "by removing it for other uses (ex-situ).", "Policy", None),
    ("C&D", "Construction and demolition", "Building and demolition activity and its waste, a source of dust.",
     "Policy", None),
    ("PUCC", "Pollution Under Control Certificate", "The certificate a vehicle needs to show its emissions are "
     "within limits.", "Policy", None),
    ("CEMS", "Continuous Emission Monitoring System", "Instruments that measure a plant's stack emissions "
     "continuously.", "Policy", None),

    ("AQEWS", "Air Quality Early Warning System", "Provides air-quality forecasts and early warnings for Delhi; run "
     "by IITM.", "Institutions", "iitm_aqews"),
    ("AQDSS", "Air Quality Decision Support System", "Estimates how much each sector contributes to Delhi's PM2.5; "
     "maintained by the Ministry of Earth Sciences.", "Institutions", None),
    ("CAAQMS", "Continuous Ambient Air Quality Monitoring Station", "Automated instruments that measure pollutants "
     "continuously.", "Institutions", None),
    ("CPCB", "Central Pollution Control Board", "India's national pollution-control authority.", "Institutions", None),
    ("SPCB", "State Pollution Control Board", "A state-level authority that regulates and monitors pollution.",
     "Institutions", None),
    ("DPCC", "Delhi Pollution Control Committee", "Delhi's pollution-control authority.", "Institutions", None),
    ("IMD", "India Meteorological Department", "India's national meteorological service.", "Institutions", None),
    ("IITM", "Indian Institute of Tropical Meteorology", "The Pune institute that runs AQEWS.", "Institutions", None),
    ("GNCTD", "Government of National Capital Territory of Delhi", "The Delhi government.", "Institutions", None),
    ("ULB", "Urban Local Body", "A municipal body such as a municipal corporation.", "Institutions", None),
    ("API", "Application Programming Interface", "A way for systems to exchange data automatically.", "Institutions", None),

    ("Outage", "Service interruption", "A source or portal is temporarily unavailable or not responding as "
     "expected.", "Data status", None),
    ("Insufficient data", "Not enough validated observations", "A value cannot be reliably reported for the "
     "relevant period.", "Data status", None),
]
CATEGORIES = ["All", "Air quality", "Weather", "Policy", "Institutions", "Data status"]


def scale_html():
    """0–500 bar of CPCB categories with the GRAP stages bracketed beneath."""
    pct = lambda v: v / 500 * 100
    bands = "".join(
        f"<div class='gs-band' style='left:{pct(lo if lo == 0 else lo - 1):.2f}%;width:{pct(hi - (lo if lo == 0 else lo - 1)):.2f}%;"
        f"background:{c}' title='{escape(n)}: {escape(AQI_HEALTH[n])}'><b>{escape(n)}</b><small>{lo}–{hi}</small></div>"
        for n, lo, hi, c in AQI_BANDS
    )
    stages = "".join(
        f"<div class='gs-stage' style='left:{pct(lo - 1):.2f}%;width:{pct(hi - lo + 1):.2f}%;--c:{_STAGE_COLOUR[name]}'>"
        f"<span>{escape(name)}</span></div>" for name, lo, hi in GRAP_STAGES
    )
    ticks = "".join(f"<em style='left:{pct(v):.2f}%'>{v}</em>" for v in (0, 100, 200, 300, 400, 450, 500))
    return (f"<div class='gs'><div class='gs-title'>The AQI scale and when GRAP kicks in</div>"
            f"<div class='gs-bar'>{bands}</div><div class='gs-ticks'>{ticks}</div>"
            f"<div class='gs-stages'>{stages}</div></div>")


def render_glossary():
    with st.container(border=True, key="glossary-scale"):
        st.markdown(scale_html(), unsafe_allow_html=True)
        source_line("cpcb_aqi", "caqm_grap_schedule", note="GRAP stage AQI ranges from the CAQM schedule")
        st.caption(f":material/info: {GRAP_COLOURS_DISCLAIMER}")

    q_col, f_col = st.columns([2, 3], gap="medium", vertical_alignment="bottom")
    with q_col:
        query = st.text_input("Search", placeholder="e.g. ventilation, GRAP, PM2.5", key="gloss_q",
                              label_visibility="collapsed", icon=":material/search:")
    with f_col:
        cat = st.segmented_control("Category", options=CATEGORIES, default="All", key="gloss_cat",
                                   label_visibility="collapsed") or "All"
    q = (query or "").strip().lower()
    shown = [t for t in TERMS
             if (cat == "All" or t[3] == cat) and (not q or any(q in x.lower() for x in t[:3]))]
    if not shown:
        st.info("No terms match. Try a shorter word.")
        return
    cards = []
    for term, expansion, definition, category, src in shown:
        src_html = (f"<a class='gl-src' href='{SOURCES[src][1]}' target='_blank'>{escape(SOURCES[src][0])}</a>"
                    if src else "")
        cards.append(
            f"<article class='gl-card gl-{category.split()[0].lower()}'>"
            f"<div class='gl-top'><span class='gl-term'>{escape(term)}</span><span class='gl-cat'>{escape(category)}</span></div>"
            f"<div class='gl-exp'>{escape(expansion)}</div><p>{escape(definition)}</p>{src_html}</article>"
        )
    st.markdown(f"<div class='gl-count'>{len(shown)} term{'s' if len(shown) != 1 else ''}</div>"
                f"<div class='gl-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)
