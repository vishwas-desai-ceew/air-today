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
    "mohfw_air_advisory": ("MoHFW / NCDC, Health Advisory on Air Pollution (NPCCHH), 1 Nov 2025",
                           "https://ncdc.mohfw.gov.in/uploads/pdf/air2.pdf"),
    "aqews_dss": ("IITM AQEWS, source apportionment (DSS)", "https://ews.tropmet.res.in/"),
    "cpcb_naaqs": ("CPCB, National Ambient Air Quality Standards (Gazette of India, 18 November 2009)",
                   "https://cpcb.gov.in/uploads/National_Ambient_Air_Quality_Standards.pdf"),
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


# ----- Health advisory (Daily update) -------------------------------------
# Source: SOURCES["mohfw_air_advisory"], the Ministry of Health and Family
# Welfare / NCDC "Health Advisory on Air Pollution" under NPCCHH, sent with the
# Health Secretary's D.O. letter of 1 Nov 2025. Wording copied from the scanned
# PDF (read from the page images, 10 Nov 2026); check against the PDF on update.
#
# "Table: AQI levels, Health effects and Certain Protective Health Measures",
# advisory pp. 6-7 (PDF pp. 10-11): category -> (possible health consequences,
# advice for the general population, advice for the vulnerable population).
HEALTH_ADVISORY = {
    "Good": (["Low risk"],
             "No special precautions",
             "No special precautions"),
    "Satisfactory": (["Minor breathing discomfort in vulnerable population"],
                     "No special precautions",
                     "Do less prolonged or strenuous outdoor physical exertion"),
    "Moderate": (["Breathing or other health related discomfort in vulnerable population"],
                 "Do less prolonged or strenuous outdoor physical exertion",
                 "Avoid prolonged or strenuous outdoor physical exertion"),
    "Poor": (["Breathing discomfort in healthy people on prolonged exposure",
              "Breathing or other health related discomfort in vulnerable population on short exposure"],
             "Avoid outdoor physical exertion",
             "Avoid outdoor physical activities"),
    "Very Poor": (["Respiratory illness in healthy people on prolonged exposure",
                   "Pronounced respiratory or other illnesses in vulnerable population on short exposure"],
                  "Avoid outdoor physical activities, especially during morning and late evening hours",
                  "Remain indoors and keep activity levels low"),
    "Severe": (["Respiratory illness in healthy people on prolonged exposure",
                "Serious respiratory or other illnesses in vulnerable population on short exposure"],
               "Avoid outdoor physical activities",
               "Remain indoors and keep activity levels low"),
}
# Who the advisory means by vulnerable (p. 16, Annexure I; Annexure II item 4g adds pregnant women)
HEALTH_VULNERABLE = "Children, elderly people, pregnant women and people with heart or lung conditions"
# Annexure II "Social Media Messages", for days of poor to severe plus air
# pollution (AQI > 200), advisory pp. 19-20. Items 4a-4b, 4c-4d, 14, 11 and 4f,
# lightly shortened; meaning unchanged.
HEALTH_STEPS_ABOVE_200 = [
    "Avoid outdoor morning and late-evening walks, jogging, running and other exertional activity.",
    "Keep external doors and windows shut in the morning and late evening; if needed, ventilate rooms "
    "between 12 PM and 4 PM.",
    "Consider close-fitted N95 or N99 masks to reduce exposure.",
    "People with chronic lung or heart disease should keep their prescribed medicines at hand when going out.",
    "If you have breathlessness, cough, chest discomfort or pain, giddiness, or red or watery eyes, consult "
    "the nearest doctor immediately.",
]

