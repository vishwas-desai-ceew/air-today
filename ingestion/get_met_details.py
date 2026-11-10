import sys
import pandas as pd
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.logging_config import get_logger
from config.settings import (
    AQEWS_AQI_CSV as AQI_FC_FILE, AQEWS_CATEGORY_CSV as AQI_FC_CAT,
    CREAMS_HEADLINE_STATES, METEO_HOURLY_CSV as METEO_CSV, VENTILATION_CSV,
)
logger = get_logger(__name__)


def get_tomorrow_avg(c_date, csv_file=METEO_CSV):
    df = pd.read_csv(csv_file)
    df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert("Asia/Kolkata")
    #tomorrow = (datetime.now() + timedelta(days=1)).date()
    c_date = pd.to_datetime(c_date).date()
    
    df_curr = df[df['date'].dt.date == c_date]
    if df_curr.empty:
        return None, None, None 
    min_temp = df_curr['temperature_2m'].min()
    avg_wind = df_curr['wind_speed_10m'].mean()
    avg_rainfall = df_curr['rain'].mean()

    return min_temp, avg_wind, avg_rainfall


def get_latest_fire_count():
    """(date, {state: events}) for Punjab and Haryana from the newest CREAMS
    bulletin, or (None, None) if none is stored."""
    from ingestion.creams import latest_headline
    return latest_headline(CREAMS_HEADLINE_STATES)


def get_fc_aqi(c_date, csv_file=AQI_FC_FILE):
    df_aqi = pd.read_csv(csv_file)
    c_date = pd.to_datetime(c_date).date()
    #tommorrow = (datetime.now() + timedelta(days=1)).date()
    df_aqi = df_aqi[pd.to_datetime(df_aqi['date']).dt.date == c_date]
    if not df_aqi.empty:
        return df_aqi["AQI_overall"].values[0], df_aqi["category"].values[0]
    return None, None


def get_v_index_df(c_date, csv_file=VENTILATION_CSV):
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        return None
    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '')

    if 'ventilation_index' not in df.columns:
        logger.warning(f"CSV missing expected column: {df.columns.tolist()}")
        return None
    c_date = pd.to_datetime(c_date).date()
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

    df = df[df['date'] == c_date]
    if df.empty:
        return None

    return float(df["ventilation_index"].values[0])

def get_aqi_cat(c_date, csv_file=AQI_FC_CAT):
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '')

    if 'category' not in df.columns:
        logger.warning(f"CSV missing expected column: {df.columns.tolist()}")
        return None
    c_date = pd.to_datetime(c_date).date()
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

    df = df[df['date'] == c_date]
    if df.empty:
        return None

    return df["category"].values[0]

