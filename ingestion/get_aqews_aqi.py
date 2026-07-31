import requests
from bs4 import BeautifulSoup
import re
from py_mini_racer import py_mini_racer
import json
import pandas as pd
from pathlib import Path

# run very 10 days

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def ds_to_df(data):
    df_pm25 = pd.DataFrame({
    "datetime": pd.to_datetime(data["PM2.5"]["timestamps"]),
    "AQI_PM25": data["PM2.5"]["aqi_values"]
    })
    df_pm10 = pd.DataFrame({
    "datetime": pd.to_datetime(data["PM10"]["timestamps"]),
    "AQI_PM10": data["PM10"]["aqi_values"]
    })

    return df_pm25, df_pm10


def save_aqi_to_csv(df_pm25, df_pm10):
    df_pm25["report_date"] = (df_pm25["datetime"] + pd.Timedelta(hours=8)).dt.date
    df_pm10["report_date"] = (df_pm10["datetime"] + pd.Timedelta(hours=8)).dt.date

    df_pm25_daily = (
        df_pm25.groupby("report_date")["AQI_PM25"]
        .mean()
        .round()
        .astype(int)
        .reset_index()
        .rename(columns={"report_date": "date"})
    )

    df_pm10_daily = (
        df_pm10.groupby("report_date")["AQI_PM10"]
        .mean()
        .round()
        .astype(int)
        .reset_index()
        .rename(columns={"report_date": "date"})
    )

    df_daily = pd.merge(df_pm25_daily, df_pm10_daily, on="date", how="outer")
    df_daily["AQI_overall"] = df_daily[["AQI_PM25", "AQI_PM10"]].max(axis=1)
    df_daily["prominent_pollutant"] = (
        df_daily[["AQI_PM25", "AQI_PM10"]]
        .idxmax(axis=1)
        .str.replace("AQI_", "")
    )
    bins = [0, 50, 100, 200, 300, 400, 500]
    labels = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    df_daily["category"] = pd.cut(
        df_daily["AQI_overall"],
        bins=bins,
        labels=labels,
        right=True,
        include_lowest=True
    )
    df_daily.to_csv(DATA_DIR / "AQEWS_AQI_forecast.csv", index=False)




def fetch_aqi_data():
    url = "https://ews.tropmet.res.in/10_days_forecast.php"
    html = requests.get(url, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    script_text = "\n".join(
        [s.get_text() for s in soup.find_all("script") if "datastack" in s.get_text()]
    )
    js_extract = ""
    for var_name in ["datastack17", "datastack18"]:
        m = re.search(rf"const\s+{var_name}\s*=\s*(\{{.*?\}});", script_text, re.S)
        if m:
            js_extract += f"var {var_name} = {m.group(1)};\n"
    ctx = py_mini_racer.MiniRacer()
    ctx.eval(js_extract)
    pm25_json = ctx.eval("JSON.stringify(datastack17)")
    pm10_json = ctx.eval("JSON.stringify(datastack18)")
    pm25 = json.loads(pm25_json)
    pm10 = json.loads(pm10_json)
    def extract(ds):
        return {
            "label": ds["datasets"][0]["label"],
            "timestamps": ds["labels"],
            "aqi_values": ds["datasets"][0]["data"]
        }
    return {
        "PM2.5": extract(pm25),
        "PM10": extract(pm10)
    }


if __name__ == "__main__":
    data = fetch_aqi_data()
    pm25, pm10 = ds_to_df(data)
    save_aqi_to_csv(pm25, pm10)
