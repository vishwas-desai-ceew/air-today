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
    "PM2.5": data["PM2.5"]["data"]
    })

    return df_pm25


def save_to_csv(df_pm25):
    df = df_pm25.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.rename(columns={"datetime": "time"})
    df["PM2.5"] = df["PM2.5"].round(2)
    df.to_csv(DATA_DIR / "AQEWS_PM25_forecast.csv", index=False)


def fetch_aqi_data():
    url = "https://ews.tropmet.res.in/10_days_forecast.php"
    html = requests.get(url, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    script_text = "\n".join(
        [s.get_text() for s in soup.find_all("script") if "datastack" in s.get_text()]
    )
    js_extract = ""
    for var_name in ["datastack9"]:
        m = re.search(rf"const\s+{var_name}\s*=\s*(\{{.*?\}});", script_text, re.S)
        if m:
            js_extract += f"var {var_name} = {m.group(1)};\n"
    ctx = py_mini_racer.MiniRacer()
    ctx.eval(js_extract)
    pm25_json = ctx.eval("JSON.stringify(datastack9)")
    pm25 = json.loads(pm25_json)
    def extract(ds):
        return {
            "label": ds["datasets"][0]["label"],
            "timestamps": ds["labels"],
            "data": ds["datasets"][0]["data"]
        }
    return {
        "PM2.5": extract(pm25)
    }


if __name__ == "__main__":
    data = fetch_aqi_data()
    pm25 = ds_to_df(data)
    save_to_csv(pm25)
