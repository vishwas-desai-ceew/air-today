import sys
import pandas as pd
from datetime import time, datetime, timedelta
from pathlib import Path
from get_met_details import get_tomorrow_avg, get_fire_count, get_fc_aqi, get_v_index_df, get_aqi_cat

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import EFFECTIVE_DATE_CUTOFF
from config.formatting import ordinal
from config.logging_config import get_logger
from ingestion.json_store import write_json_atomic

DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
AQI_CSV_FILE = DATA_DIR / "delhi_aqi_cpcb.csv"
ARCHIVE_JSON = DATA_DIR / "archive.json"
ARCHIVE_TEMP = DATA_DIR / "archive_temp.json"

logger = get_logger(__name__)


def get_last_two_days(csv_path=AQI_CSV_FILE):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    cutoff = EFFECTIVE_DATE_CUTOFF
    # Decide which dates to use
    now = datetime.now()
    if now.time() < cutoff:
        dates_needed = [yesterday, day_before]
    else:
        dates_needed = [today, yesterday]

    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d").dt.date
    filtered = df[df['date'].isin(dates_needed)].sort_values('date', ascending=False)
    return filtered


def save_missing_forecast_days(mf_days):
    try:
        with open(DATA_DIR / "missing_forecast_days.txt") as f:
            existing_dates = {line.strip() for line in f}
    except FileNotFoundError:
        existing_dates = set()

    new_dates = [d for d in mf_days if d not in existing_dates]

    if new_dates:
        with open(DATA_DIR / "missing_forecast_days.txt", "a") as f:
            for date in new_dates:
                f.write(f"{date}\n")
   

def get_aqi_summary(df):
    cutoff = EFFECTIVE_DATE_CUTOFF
    # --- Decide which dates to use ---
    now = datetime.now()
    if now.time() < cutoff:
        today = datetime.today().date() - timedelta(days=1)
    else:
        today = datetime.today().date()
   
    prev_date = today - timedelta(days=1)
    next_date = today + timedelta(days=1)

    def fmt_date(d):
        return f"{ordinal(d.day)} {d.strftime('%B')}"

    # --- initialize all forecast variables ---
    min_temp = avg_wind = avg_rainfall = None
    aqi_forecast = aqi_forecast_cat = v_index_fc = aqi_cat_fallback = None
    fire_counts = {}

    # ---fetch met + forecast data ---
    try:
        min_temp, avg_wind, avg_rainfall = get_tomorrow_avg(next_date)
    except Exception as e:
        logger.warning("get_tomorrow_avg failed: %s", e)

    try:
        aqi_forecast, aqi_forecast_cat = get_fc_aqi(next_date)
    except Exception as e:
        logger.warning("get_fc_aqi failed: %s", e)

    try:
        v_index_fc = get_v_index_df(next_date)
    except Exception as e:
        logger.warning("get_v_index_df failed: %s", e)

    try:
        aqi_cat_fallback = get_aqi_cat(next_date)
    except Exception as e:
        logger.warning("get_aqi_cat failed: %s", e)

    try:
        fire_counts = get_fire_count(prev_date)
    except Exception as e:
        logger.warning("get_fire_count failed: %s", e)
        fire_counts = {}

    # --- observed AQI summary ---
    if df.empty:
        aqi_obs_line = (
            f"Delhi's Air Quality Index (AQI) is N/A for {fmt_date(today)} as the CPCB bulletin is not yet released."
        )
    else:
        df1, df2 = df.iloc[0], df.iloc[1]

        if df1.empty or df2.empty:
            logger.warning("df1 or df2 is empty")

        curr_date = df1["date"]
        curr_date_str = fmt_date(curr_date)
        prev_date_str = fmt_date(df2["date"]) if df2 is not None else fmt_date(prev_date)
        next_date_str = fmt_date(curr_date + timedelta(days=1))

        # Compute AQI difference safely
        try:
            diff = int(df1["aqi"]) - int(df2["aqi"]) if df2 is not None else 0
        except Exception:
            diff = 0

        trend = "deteriorating" if diff > 0 else "improving" if diff < 0 else "unchanged"
        
        aqi_obs_line = (
            f"Delhi's Air Quality Index (AQI) stood at {df1['aqi']} on {curr_date_str}, "
            f"{trend} from {df2['aqi']} on {prev_date_str}."
        )

    # ---- missing forecasts ---- 
    missing_forecast_days = []
    next_date_str = fmt_date(next_date)

    if aqi_forecast is not None and aqi_forecast_cat is not None:
        aqi_fc_line = (
            f"According to the AQEWS, the AQI on {next_date_str} is expected to be around {aqi_forecast} / {aqi_forecast_cat}."
        )
    elif aqi_cat_fallback is not None:
        aqi_fc_line = (
            f"According to the AQEWS, the AQI on {next_date_str} is expected to be in the {aqi_cat_fallback} category."
        )
        missing_forecast_days.append(today)
    else:
        aqi_fc_line = (
            f"AQI forecast for {next_date_str} from AQEWS is currently unavailable."
        )
        missing_forecast_days.append(today)

    if missing_forecast_days:
        save_missing_forecast_days(missing_forecast_days)

    # --- Met details ---
    if avg_rainfall is not None and avg_rainfall >= 0.1:
        rain_fc = f"Expected rainfall for {next_date_str} is {avg_rainfall:.1f} mm."
    else:
        rain_fc = "No rainfall is expected during the forecast period."

    if v_index_fc is not None:
        v_index_line = (
            f"The ventilation index predicted for {next_date_str} is {v_index_fc:.0f} m²/s. (values  greater than 6000 m²/s are favourable for pollutant dispersion.)"
        )
    else:
        v_index_line = (
            f"Ventilation Index forecast unavailable."
        )

    if avg_wind is not None:
        wind_fc = (
            f"The average wind speed predicted for {next_date_str} is {avg_wind:.2f} m/s (values greater than 2.8 m/s is conducive for pollutant dispersion)."
        )
    else:
        wind_fc = "Wind forecast unavailable."

    if min_temp is not None:
        temp_fc = (
            f"The minimum temperature predicted for {next_date_str} is {min_temp:.1f} °C (values less than 10°C may increase biomass burning)."
        )
    else:
        temp_fc = "Temperature forecast unavailable."

    fire_line = (
        f"Fire count on {fmt_date(prev_date)} is {sum(fire_counts.values())} (Punjab: {fire_counts.get('Punjab', 0)}, Haryana: {fire_counts.get('Haryana', 0)})."
    )

    # --- Combine all lines into final summary ---
    aqi_summary = [
        aqi_obs_line,
        fire_line,
        aqi_fc_line,
        wind_fc,
        temp_fc,
        v_index_line,
        rain_fc
    ]

    return today, aqi_summary


def save_file_to_json(date, summary):
    date_str = date.strftime("%Y-%m-%d")
    summary_dict = {date_str: summary}
    write_json_atomic(ARCHIVE_TEMP, summary_dict, indent=2, default=str)


def main():
    df = get_last_two_days()
    print(df)
    date_curr, summary_aqi = get_aqi_summary(df)
    #print(summary_aqi)
    save_file_to_json(date_curr, summary_aqi)


if __name__ == "__main__":
   main()