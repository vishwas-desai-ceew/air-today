import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import (
    ARCHIVE_JSON, ARCHIVE_TEMP, CPCB_AQI_CSV as AQI_CSV_FILE, DATA_DIR,
    MISSING_FORECAST_DAYS, effective_today,
)
from config.formatting import ordinal
from config.logging_config import get_logger
from ingestion.json_store import read_json, write_json_atomic
from ingestion.get_met_details import get_tomorrow_avg, get_fire_count, get_fc_aqi, get_v_index_df, get_aqi_cat

logger = get_logger(__name__)


def get_last_two_days(csv_path=AQI_CSV_FILE, today=None):
    """CPCB rows for the effective "today" and the day before, newest first.
    Single implementation shared by the summary builder and the dashboard."""
    today = today or effective_today()
    dates_needed = [today, today - timedelta(days=1)]
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d").dt.date
    df['aqi'] = pd.to_numeric(df['aqi'], errors='coerce')
    filtered = df[df['date'].isin(dates_needed)].sort_values('date', ascending=False)
    return filtered


def save_missing_forecast_days(mf_days):
    try:
        with open(MISSING_FORECAST_DAYS) as f:
            existing_dates = {line.strip() for line in f}
    except FileNotFoundError:
        existing_dates = set()

    new_dates = [d for d in mf_days if d not in existing_dates]

    if new_dates:
        with open(MISSING_FORECAST_DAYS, "a") as f:
            for date in new_dates:
                f.write(f"{date}\n")
   

def get_aqi_summary(df):
    today = effective_today()
    prev_date = today - timedelta(days=1)
    next_date = today + timedelta(days=1)

    def fmt_date(d):
        return f"{ordinal(d.day)} {d.strftime('%B')}"

    # --- initialize all forecast variables ---
    min_temp = avg_wind = avg_rainfall = None
    aqi_forecast = aqi_forecast_cat = v_index_fc = aqi_cat_fallback = None
    fire_counts = None

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

    # --- observed AQI summary ---
    rows = df.dropna(subset=["aqi"]) if not df.empty else df
    if rows.empty or rows.iloc[0]["date"] != today:
        aqi_obs_line = (
            f"Delhi's Air Quality Index (AQI) is N/A for {fmt_date(today)} as the CPCB bulletin is not yet released."
        )
    else:
        df1 = rows.iloc[0]
        aqi_now = int(df1["aqi"])
        aqi_obs_line = f"Delhi's Air Quality Index (AQI) stood at {aqi_now} on {fmt_date(df1['date'])}"
        if len(rows) > 1:
            df2 = rows.iloc[1]
            diff = aqi_now - int(df2["aqi"])
            trend = "deteriorating" if diff > 0 else "improving" if diff < 0 else "unchanged"
            aqi_obs_line += f", {trend} from {int(df2['aqi'])} on {fmt_date(df2['date'])}."
        else:
            aqi_obs_line += "."

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

    if fire_counts is None:
        fire_line = f"Fire count for {fmt_date(prev_date)} is currently unavailable."
    else:
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
    """Writes today's summary for the dashboard and merges it straight into the
    archive (previously a separate 9 PM cron, update_archive_json.py, did the
    merge - if it didn't run, the day was lost from the archive)."""
    date_str = date.strftime("%Y-%m-%d")
    summary_dict = {date_str: summary}
    write_json_atomic(ARCHIVE_TEMP, summary_dict, indent=2, default=str)
    archive = read_json(ARCHIVE_JSON)
    archive.update(summary_dict)
    write_json_atomic(ARCHIVE_JSON, archive, indent=2, default=str)


def run():
    df = get_last_two_days()
    date_curr, summary_aqi = get_aqi_summary(df)
    save_file_to_json(date_curr, summary_aqi)
    return {"date": str(date_curr), "lines": len(summary_aqi), "aqi_line": summary_aqi[0]}


if __name__ == "__main__":
    print(run())
