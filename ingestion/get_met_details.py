import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.logging_config import get_logger
logger = get_logger(__name__)

DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
METEO_CSV = DATA_DIR / "meteo_api_hourly.csv"
AQI_FC_FILE = DATA_DIR / "AQEWS_AQI_forecast.csv"
FIRE_CSV = DATA_DIR / "fire_pbhr.csv"
AQI_FC_CAT = DATA_DIR / "AQI_forecast_category.csv"


def get_tomorrow_avg(c_date, csv_file=METEO_CSV):
    df = pd.read_csv(csv_file)
    df['date'] = pd.to_datetime(df['date'])
    #tomorrow = (datetime.now() + timedelta(days=1)).date()
    c_date = pd.to_datetime(c_date).date()
    
    df_curr = df[df['date'].dt.date == c_date]
    if df_curr.empty:
        return None, None, None 
    min_temp = df_curr['temperature_2m'].min()
    avg_wind = df_curr['wind_speed_10m'].mean()
    avg_rainfall = df_curr['rain'].mean()

    return min_temp, avg_wind, avg_rainfall

def get_fire_count(p_date, csv_file=FIRE_CSV):
    df = pd.read_csv(csv_file)
    p_date = pd.to_datetime(p_date).date()
    fire_df = df[pd.to_datetime(df['date']).dt.date == p_date]
    if fire_df.empty:
        return {}
    fire_counts = fire_df.groupby('state_name')['count_of_incidents'].sum().to_dict()
    return fire_counts


def get_fc_aqi(c_date, csv_file=AQI_FC_FILE):
    df_aqi = pd.read_csv(csv_file)
    c_date = pd.to_datetime(c_date).date()
    #tommorrow = (datetime.now() + timedelta(days=1)).date()
    df_aqi = df_aqi[pd.to_datetime(df_aqi['date']).dt.date == c_date]
    if not df_aqi.empty:
        return df_aqi["AQI_overall"].values[0], df_aqi["category"].values[0]
    return None, None


def get_v_index_df(c_date, csv_file=DATA_DIR / "ventilation_index_forecast.csv"):
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

