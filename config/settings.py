from datetime import datetime, time, timedelta
from pathlib import Path

import pytz

# The CPCB/IMD bulletin is published daily around 18:00 IST. Before this
# cutoff, "today" still refers to yesterday's bulletin data. This was
# previously reimplemented independently in 4 places with 3 different
# (partly wrong) values - this is the single source of truth now.
EFFECTIVE_DATE_CUTOFF = time(17, 57)  # 5:57 PM IST

IST = pytz.timezone("Asia/Kolkata")

# ---- Paths: every module used to recompute these on its own ----
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CPCB_AQI_CSV = DATA_DIR / "delhi_aqi_cpcb.csv"
ARCHIVE_JSON = DATA_DIR / "archive.json"
ARCHIVE_TEMP = DATA_DIR / "archive_temp.json"
INSIGHTS_JSON = DATA_DIR / "insights_today.json"
MISSING_FORECAST_DAYS = DATA_DIR / "missing_forecast_days.txt"
METEO_HOURLY_CSV = DATA_DIR / "meteo_api_hourly.csv"
AQEWS_AQI_CSV = DATA_DIR / "AQEWS_AQI_forecast.csv"
AQEWS_PM25_CSV = DATA_DIR / "AQEWS_PM25_forecast.csv"
AQEWS_CATEGORY_CSV = DATA_DIR / "AQI_forecast_category.csv"
VENTILATION_CSV = DATA_DIR / "ventilation_index_forecast.csv"
FIRE_CSV = DATA_DIR / "fire_pbhr.csv"
IMD_BULLETIN_PDF = DATA_DIR / "imd_bulletin_today.pdf"
PIPELINE_STATUS_JSON = DATA_DIR / "pipeline_status.json"

# ---- Location + upstream URLs ----
DELHI_LAT, DELHI_LON = 28.6448, 77.216721

AQEWS_HOME_URL = "https://ews.tropmet.res.in/"
AQEWS_10DAY_URL = "https://ews.tropmet.res.in/10_days_forecast.php"
IMD_BULLETIN_URL = "https://nwp.imd.gov.in/silam/aqbulletin.pdf"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HTTP_HEADERS = {"User-Agent": "CEEW-AirToday/1.0 (+https://www.ceew.in)"}


def effective_today(now=None):
    """The date whose CPCB bulletin is "today's": the calendar date after the
    cutoff, the previous day before it."""
    now = now or datetime.now(IST)
    if now.time() >= EFFECTIVE_DATE_CUTOFF:
        return now.date()
    return (now - timedelta(days=1)).date()
