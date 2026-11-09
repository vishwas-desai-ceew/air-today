"""Official bands and thresholds drawn on the forecast and weather charts.

Each entry names its source document so the chart captions can cite it.
Verified against the documents themselves (Nov 2026):

- CPCB (2014), National Air Quality Index, Table 3.2 (AQI ranges),
  Table 3.11 (PM2.5 24-hr breakpoints) and Table 3.12 (health statements).
- IMD, Glossary (imdpune.gov.in/Reports/glossary.pdf): 24-hour rainfall classes.
- IITM AQEWS daily Air Quality and Weather Bulletin for Delhi: "ventilation
  index lower than 6000 m2/s with an average wind speed of less than 10 kmph
  is unfavorable for the dispersion of pollutants".
"""

SOURCES = {
    "cpcb_aqi": ("CPCB, National Air Quality Index (2014)",
                 "https://smartnet.niua.org/sites/default/files/resources/Air%20Quality%20Index.pdf"),
    "imd_glossary": ("IMD, Glossary of meteorological terms",
                     "https://imdpune.gov.in/Reports/glossary.pdf"),
    "iitm_aqews": ("IITM AQEWS, Air Quality and Weather Bulletin for Delhi",
                   "https://ews.tropmet.res.in/"),
    "open_meteo": ("Open-Meteo forecast API", "https://open-meteo.com/en/docs"),
    # Card-level source links (Overview hero, KPI cards, Key insights).
    "cpcb": ("CPCB", "https://cpcb.gov.in/"),
    "aqews": ("IITM AQEWS", "https://ews.tropmet.res.in/"),
    "metar": ("METAR, Indira Gandhi International Airport (VIDP) via NOAA aviationweather.gov",
              "https://aviationweather.gov/data/metar/?ids=VIDP"),
    "open_meteo_model": ("Open-Meteo model", "https://open-meteo.com/"),
    "nasa_fires": ("NASA FIRMS active fires (VIIRS)", "https://firms.modaps.eosdis.nasa.gov/"),
    # GRAP (CAQM). Orders are listed on the GRAP Orders page; the schedule PDF
    # sets the stage AQI ranges (Stage I 201-300 ... Stage IV >450).
    "caqm_grap_orders": ("CAQM, GRAP orders", "https://caqm.nic.in/landingpage/pages/grap/grap-orders"),
    "caqm_grap_schedule": ("CAQM, Revised GRAP for NCR (September 2026)",
                           "https://caqm.nic.in/FileUploadDomain/WebsiteDocument/GRAP/GRAP%20Schedule/"
                           "01fcdebf-83e1-4cfe-bc0c-d0b1470a4d4e.pdf"),
}

# GRAP stages: (stage number, label, CAQM AQI range, colour, text colour on that colour).
# AQI ranges are CAQM's (GRAP schedule; restated in the 2026-27 stage orders).
# The colours are Air Today's own choice - CAQM does not assign colours to
# GRAP stages - and the GRAP page says so wherever they appear.
GRAP_STAGES = [
    (1, "Stage I", "Poor, AQI 201-300", "#F2B705", "#3d2c00"),
    (2, "Stage II", "Very Poor, AQI 301-400", "#E8710A", "#ffffff"),
    (3, "Stage III", "Severe, AQI 401-450", "#C62828", "#ffffff"),
    (4, "Stage IV", "Severe+, AQI above 450", "#6A1B4D", "#ffffff"),
]
GRAP_COLOURS_DISCLAIMER = (
    "Stage colours are Air Today's own, chosen for readability. CAQM does not assign official colours to GRAP stages."
)

# (category, low, high, colour) — CPCB Table 3.2. Colours are the app's AQI palette.
AQI_BANDS = [
    ("Good", 0, 50, "#2d662a"),
    ("Satisfactory", 51, 100, "#03a303"),
    ("Moderate", 101, 200, "#e0b400"),
    ("Poor", 201, 300, "#f78c00"),
    ("Very Poor", 301, 400, "#fc4d02"),
    ("Severe", 401, 500, "#e91902"),
]

# PM2.5 24-hr breakpoints, µg/m³ — CPCB Table 3.11. Severe is 250+ (open-ended).
PM25_BANDS = [
    ("Good", 0, 30, "#2d662a"),
    ("Satisfactory", 31, 60, "#03a303"),
    ("Moderate", 61, 90, "#e0b400"),
    ("Poor", 91, 120, "#f78c00"),
    ("Very Poor", 121, 250, "#fc4d02"),
    ("Severe", 251, None, "#e91902"),
]

# PM10 24-hr breakpoints, µg/m³ — CPCB National AQI (2014). Severe is 431+ (open-ended).
PM10_BANDS = [
    ("Good", 0, 50, "#2d662a"),
    ("Satisfactory", 51, 100, "#03a303"),
    ("Moderate", 101, 250, "#e0b400"),
    ("Poor", 251, 350, "#f78c00"),
    ("Very Poor", 351, 430, "#fc4d02"),
    ("Severe", 431, None, "#e91902"),
]

# National Ambient Air Quality Standards (CPCB notification B-29016/20/90/PCI-L,
# 18 Nov 2009), µg/m³, industrial/residential/rural areas. There is no 1-hour
# standard for PM2.5 or PM10: only 24-hour and annual limits.
NAAQS_24H = {"PM2.5": 60, "PM10": 100}
NAAQS_ANNUAL = {"PM2.5": 40, "PM10": 60}

# CPCB Table 3.12, as worded in the source.
AQI_HEALTH = {
    "Good": "Minimal impact",
    "Satisfactory": "May cause minor breathing discomfort to sensitive people",
    "Moderate": "May cause breathing discomfort to the people with lung disease such as asthma and "
                "discomfort to people with heart disease, children and older adults",
    "Poor": "May cause breathing discomfort to people on prolonged exposure and discomfort to people "
            "with heart disease",
    "Very Poor": "May cause respiratory illness to the people on prolonged exposure. Effect may be more "
                 "pronounced in people with lung and heart diseases",
    "Severe": "May cause respiratory effects even on healthy people and serious health impacts on people "
              "with lung/heart diseases. The health impacts may be experienced even during light physical activity",
}

# IMD 24-hour rainfall classes, mm (Glossary). Upper bound None = open-ended.
RAIN_CLASSES_24H = [
    ("Very light", 0.1, 2.4),
    ("Light", 2.5, 7.5),
    ("Moderate", 7.6, 35.5),
    ("Rather heavy", 35.6, 64.4),
    ("Heavy", 64.5, 124.4),
    ("Very heavy", 124.5, 244.4),
    ("Extremely heavy", 244.5, None),
]

# IITM AQEWS bulletin: below both of these, dispersion is unfavourable.
VENTILATION_INDEX_UNFAVOURABLE = 6000  # m²/s
WIND_UNFAVOURABLE_KMH = 10            # km/h  (≈ 2.8 m/s, the app's wind threshold)


def band_for(value, bands):
    """(category, colour) for a value, or (None, None)."""
    if value is None:
        return None, None
    for name, low, high, colour in bands:
        if high is None or value <= high:
            return name, colour
    return bands[-1][0], bands[-1][3]
