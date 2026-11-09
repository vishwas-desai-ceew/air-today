"""Glossary: the AQI and GRAP scale as a picture, then searchable,
filterable term cards on one screen. Each card shows the term and its
expansion; clicking it opens the definition (and source, where a term states
a threshold) in a dialog."""
from html import escape

import streamlit as st

from config.reference import (AQI_BANDS, AQI_HEALTH, GRAP_COLOURS_DISCLAIMER, GRAP_STAGES as GRAP_STAGE_DEFS,
                              SOURCES, VENTILATION_INDEX_UNFAVOURABLE)

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
     "dashboard's live weather uses Indira Gandhi International Airport (VIDP), with Safdarjung (VIDD) as fallback.", "Weather", None),

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
     "expected.", "Data and sources", None),
    ("Insufficient data", "Not enough validated observations", "A value cannot be reliably reported for the "
     "relevant period.", "Data and sources", None),
]
# Terms added on 10 Nov 2026: ones the dashboard has used since the glossary was
# last revised (6 Nov) - fires, pollutants, weather, Recent trends and the
# interventions text.
TERMS += [
    ("NAAQS", "National Ambient Air Quality Standards", "India's legal limits for outdoor air, notified by CPCB "
     "in November 2009. For PM2.5 the limit is 60 µg/m³ over 24 hours and 40 µg/m³ as an annual average; for PM10, "
     "100 µg/m³ and 60 µg/m³. The 24-hour limits must be met 98% of the time in a year.", "Air quality", "cpcb_naaqs"),
    ("Prominent pollutant", "The pollutant that sets the AQI", "The pollutant with the highest sub-index on a "
     "day. CPCB bulletins name it alongside the AQI; in Delhi's winter it is usually PM2.5 or PM10.",
     "Air quality", "cpcb_aqi"),
    ("Very Poor+ spell", "Run of Very Poor or worse days", "Consecutive days with a daily AQI above 300, the "
     "Very Poor and Severe categories. The Recent trends page reports the longest such run in each winter.",
     "Air quality", None),
    ("Stubble burning", "Paddy straw burning", "Setting fire to the straw left in fields after the paddy "
     "harvest to clear them quickly for sowing wheat, mainly in Punjab and Haryana in October and November.",
     "Policy", None),
    ("Active fire", "Satellite fire detection", "A spot where a satellite sensor picks up heat from a fire. "
     "Counts are detections, not individual fires: one large fire can produce several, while small or short fires, "
     "or fires under cloud, can be missed.", "Data and sources", "nasa_fires"),
    ("FIRMS", "Fire Information for Resource Management System", "NASA's service that publishes near real-time "
     "active fire detections from the VIIRS and MODIS sensors. The Fires pages use it.", "Data and sources",
     "nasa_fires"),
    ("VIIRS", "Visible Infrared Imaging Radiometer Suite", "A satellite sensor that detects active fires at "
     "375 m resolution; the dashboard's main source of farm-fire counts.", "Data and sources", "nasa_fires"),
    ("MODIS", "Moderate Resolution Imaging Spectroradiometer", "A sensor on NASA's Terra and Aqua satellites that "
     "detects active fires at 1 km resolution, coarser than VIIRS.", "Data and sources", "nasa_fires"),
    ("Open-Meteo", "Open weather forecast service", "The free weather model service behind the dashboard's "
     "hourly and 3-day forecasts, and the values a METAR report does not include.", "Data and sources",
     "open_meteo"),
    ("NOAA", "National Oceanic and Atmospheric Administration", "The US agency whose aviationweather.gov service "
     "supplies the METAR reports used for live weather.", "Institutions", None),
    ("IST", "Indian Standard Time", "UTC + 5:30. All times on the dashboard are in IST.", "Data and sources", None),
    ("NCR", "National Capital Region", "Delhi together with surrounding districts of Haryana, Uttar Pradesh and "
     "Rajasthan. GRAP applies across the NCR.", "Policy", None),
    ("Feels like", "Apparent temperature", "How warm or cold it feels, combining air temperature with humidity "
     "and wind. The weather card takes it from Open-Meteo.", "Weather", "open_meteo"),
    ("Solar noon", "Midday", "The moment the sun is highest in the sky, halfway between sunrise and sunset. "
     "The weather card's daylight panel marks it.", "Weather", None),
    ("MCD", "Municipal Corporation of Delhi", "The municipal body for most of Delhi.", "Institutions", None),
    ("NDMC", "New Delhi Municipal Council", "The municipal body for central New Delhi.", "Institutions", None),
    ("SAMEER", "CPCB's air quality app", "CPCB's mobile app for AQI updates and pollution complaints.",
     "Institutions", None),
    ("BS-VI", "Bharat Stage VI", "India's current vehicle emission standard.", "Policy", None),
    ("CNG / LNG", "Compressed / liquefied natural gas", "Cleaner-burning gas fuels for vehicles and industry.",
     "Policy", None),
    ("DG set", "Diesel generator set", "A diesel engine that generates electricity, usually as backup power; "
     "restricted under GRAP.", "Policy", None),
    ("MSME", "Micro, small and medium enterprises", "Smaller industrial units, often the focus of clean-fuel "
     "support.", "Policy", None),
    ("IEC", "Information, education and communication", "Public awareness and outreach activities.", "Policy", None),
    ("Hotspot", "Pollution hotspot", "A location with recurring high pollution, usually from local sources such "
     "as traffic, dust or waste burning.", "Policy", None),
]
CATEGORIES = ["All", "Air quality", "Weather", "Policy", "Institutions", "Data and sources"]


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


def _slug(category):
    return category.split()[0].lower()


@st.dialog("Glossary")
def term_dialog(index):
    term, expansion, definition, category, src = TERMS[index]
    src_html = (f"<div class='gl-dlg-src'>Source: <a href='{SOURCES[src][1]}' target='_blank' rel='noopener'>"
                f"{escape(SOURCES[src][0])}</a></div>" if src else "")
    st.markdown(
        f"<div class='gl-dlg gl-{_slug(category)}'>"
        f"<div class='gl-top'><span class='gl-term'>{escape(term)}</span>"
        f"<span class='gl-cat'>{escape(category)}</span></div>"
        f"<div class='gl-exp'>{escape(expansion)}</div><p>{escape(definition)}</p>{src_html}</div>",
        unsafe_allow_html=True,
    )


def render_glossary():
    with st.container(border=True, key="glossary-scale"):
        # Source line in the same block as the scale, so it cannot overlap the stage labels
        links = " · ".join(f"<a href='{SOURCES[k][1]}' target='_blank'>{escape(SOURCES[k][0])}</a>"
                           for k in ("cpcb_aqi", "caqm_grap_schedule"))
        st.markdown(scale_html() + f"<div class='chart-source gl-scale-src'>Source: {links} · "
                    f"{escape(GRAP_COLOURS_DISCLAIMER)}</div>", unsafe_allow_html=True)

    f_col, hint_col = st.columns([3, 2], gap="medium", vertical_alignment="center")
    with f_col:
        cat = st.segmented_control("Category", options=CATEGORIES, default="All", key="gloss_cat",
                                   label_visibility="collapsed") or "All"
    with hint_col, st.container(key="gl-hint"):
        st.markdown(":material/touch_app: **Click a term** to view its definition")
    shown = [i for i, t in enumerate(TERMS) if cat == "All" or t[3] == cat]

    # A to Z, dictionary style: an index of letters to jump to, then one section
    # per letter with its terms as pills that wrap naturally
    groups = {}
    for i in sorted(shown, key=lambda i: TERMS[i][0].casefold()):
        groups.setdefault(TERMS[i][0][0].upper(), []).append(i)
    az = "".join(f"<a href='#gl-{ch}'>{ch}</a>" if ch in groups else f"<span>{ch}</span>"
                 for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    st.markdown(f"<nav class='gl-az' aria-label='Jump to letter'>{az}</nav>", unsafe_allow_html=True)
    with st.container(key="gl-list"):
        for letter, items in groups.items():
            with st.container(horizontal=True, gap="medium", vertical_alignment="top", key=f"gl-sec-{letter}"):
                st.markdown(f"<div class='gl-letter' id='gl-{letter}'>{letter}</div>", unsafe_allow_html=True,
                            width="content")
                with st.container(horizontal=True, gap="small", key=f"gl-terms-{letter}"):
                    for i in items:
                        term, expansion, _d, category, _s = TERMS[i]
                        label = f"**{term}**" + (f" · {expansion}" if expansion != term else "")
                        if st.button(label, key=f"gl-{_slug(category)}-{i}"):
                            term_dialog(i)
