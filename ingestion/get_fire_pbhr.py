import pandas as pd
from signalsfunc import read_nasa_active_fires
from datetime import datetime, timedelta
import os
from pathlib import Path

# run cron at midnight


PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FIRE_CSV = DATA_DIR / "fire_pbhr.csv"


def get_start_end_of_yesterday(date_obj):
    start_time = pd.Timestamp(year=date_obj.year, month=date_obj.month, day=date_obj.day, hour=0)
    end_time = pd.Timestamp(year=date_obj.year, month=date_obj.month, day=date_obj.day, hour=23)
    return start_time, end_time


def get_fire_count(start_time, end_time):
    confidence_levels = ['1.Low', '2.Nominal', '3.High']
    df = read_nasa_active_fires(start_time, end_time, confidence_levels_to_filter=confidence_levels, state_codes_to_filter=["IN-PB", "IN-HR"], spatial_aggregation_level='state', temporal_aggregation_level='day', split_by_satellite=True)
    df = df[df['satellite_instrument'] == 'Suomi-NPP/VIIRS']
    return df


def save_to_csv(df, date_str, csv_path):
    new_entry = df[["state_name", "count_of_incidents"]].copy()
    new_entry["date"] = date_str

    if os.path.exists(csv_path):
        existing = pd.read_csv(csv_path)
        existing["key"] = existing["date"].astype(str) + "_" + existing["state_name"].astype(str)
        new_entry["key"] = new_entry["date"].astype(str) + "_" + new_entry["state_name"].astype(str)
        new_entry = new_entry[~new_entry["key"].isin(existing["key"])].drop(columns="key")
        if not new_entry.empty:
            combined = pd.concat([existing.drop(columns="key", errors="ignore"), new_entry], ignore_index=True)
            combined.to_csv(csv_path, index=False, encoding="utf-8")
        else:
            print(f"Data for {date_str} and state(s) already exist. Skipping append.")
    else:
        new_entry.to_csv(csv_path, index=False, encoding="utf-8")


def main():
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    start, end = get_start_end_of_yesterday(yesterday)
    df = get_fire_count(start, end)
    save_to_csv(df, yesterday, FIRE_CSV)


if __name__ == "__main__":
    main()