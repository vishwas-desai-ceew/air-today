import os
import certifi
import numpy as np
import urllib3
import requests
import pdfplumber
import pandas as pd
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(PARENT_DIR))
from config.logging_config import get_logger
logger = get_logger(__name__)


def extract_delhi_aqi_from_pdf(pdf_content, date_str):
    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
        first_page = pdf.pages[0]
        tables = first_page.extract_tables()
        if not tables:
            raise ValueError("No tables found in the PDF")

        table = tables[0]
        df = pd.DataFrame(table[1:], columns=table[0])
        df.columns = [c.strip().replace("\n", " ") for c in df.columns]
        delhi_row = df[df["District"].str.strip().str.lower() == "delhi"]

        if delhi_row.empty:
            raise ValueError("Delhi row not found in the PDF")

        delhi_row = delhi_row.iloc[0]
        return {
            "date": date_str,
            "aqi": delhi_row["Index Value"].strip(),
            "category": delhi_row["Air Quality"].strip(),
            "pollutant": ",".join([p.strip() for p in delhi_row["Prominent Pollutant"].split(",")])
        }

def download_pdf(url):
    for attempt in range(3):
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            if attempt < 2:
                logger.warning(f"Retry {attempt+1}/3 for {url} due to: {e}")
            else:
                raise e

def save_aqi_range_to_csv(start_date, end_date, csv_path):
    all_data = []
    if os.path.exists(csv_path):
        existing = pd.read_csv(csv_path)
        existing_dates = set(existing["date"].values)
    else:
        existing = pd.DataFrame()
        existing_dates = set()

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        file_date_str = current_date.strftime("%Y_%m_%d")
        url = f"https://cpcb.nic.in//upload/Downloads/Delhi-NCR/NCR_AQI_Bulletin_{file_date_str}.pdf"

        if date_str in existing_dates:
            logger.info(f"Skipping {date_str} (already in file)")
            current_date += timedelta(days=1)
            continue

        try:
            pdf_content = download_pdf(url)
            data = extract_delhi_aqi_from_pdf(pdf_content, date_str)
            all_data.append(data)
            logger.info(f"Fetched {date_str}")
        except Exception as e:
            logger.warning(f"Failed for {date_str}: {e}")
            data = {
            "date": date_str,
            "aqi": np.nan,
            "category": np.nan,
            "pollutant": np.nan
            }
            all_data.append(data)

        current_date += timedelta(days=1)

    if all_data:
        new_df = pd.DataFrame(all_data)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.sort_values(by="date")
        combined.to_csv(csv_path, index=False, encoding="utf-8")
        logger.info(f"Saved data to {csv_path} ({len(new_df)} new entries)")
    else:
        logger.info("No new data fetched.")

def main():
    start_date = datetime(2024, 10, 1)
    end_date = datetime(2025, 2, 28)
    csv_filepath = DATA_DIR / "delhi_aqi_01Oct24_28Feb25.csv"
    save_aqi_range_to_csv(start_date, end_date, csv_filepath)

if __name__ == "__main__":
    main()
