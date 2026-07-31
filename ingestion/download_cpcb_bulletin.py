import os
import re
import certifi
import urllib3
import requests
import pdfplumber
import pandas as pd
import streamlit as st
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from cpcb_common import build_cpcb_urls
from datetime import datetime, timedelta
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# run cron after 6pm IST - 12:30 UTC 


PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(PARENT_DIR))
from config.logging_config import get_logger
logger = get_logger(__name__)

# openssl s_client -showcerts -connect cpcb.nic.in:443 </dev/null 2>/dev/null | openssl x509 -outform PEM > cpcb_cert.pem --> to download SSL certificate

def get_relevant_page(pdf, url_type):
    if url_type == "primary":
        return pdf.pages[0]
    
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "delhi" in text.lower():
            return page
    return pdf.pages[-1]


def extract_pollutants(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text.replace("\n", " ").upper())

    mapping = {
        "PM2.5": ["PM", "2.5"],
        "PM10": ["PM", "10"],
        "SO2": ["SO", "2", "SULPHUR DIOXIDE"],
        "NO2": ["NO", "2", "NITROGEN DIOXIDE"],
        "O3": ["O", "3", "OZONE"],
        "CO": ["CO", "CARBON MONOXIDE"]
    }
    found = []
    for pollutant, patterns in mapping.items():
        if any(p in text for p in patterns):
            found.append(pollutant)
    order = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
    return ", ".join([p for p in order if p in found])

    
def save_aqi_to_csv(url, csv_path, date_str, url_type):
    
    response = requests.get(url, verify=False, timeout=30)
    response.raise_for_status()

    with pdfplumber.open(BytesIO(response.content)) as pdf:
        pdf_page = get_relevant_page(pdf, url_type)
        tables = pdf_page.extract_tables()
        if not tables:
            raise ValueError("No tables found in the PDF")

        table = tables[0]
        df = pd.DataFrame(table[1:], columns=table[0])
        df.columns = [c.strip().replace("\n", " ") for c in df.columns]
        if url_type == "primary":
            x = "District"
        else:
            x = "City"
       
        delhi_row = df[df[x].str.strip().isin(["Delhi", "delhi"])]
        if delhi_row.empty:
            raise ValueError("Delhi row not found in the PDF")

        delhi_row = delhi_row.iloc[0]
        new_entry = pd.DataFrame([{
            "date": date_str,
            "aqi": delhi_row["Index Value"].strip(),
            "category": delhi_row["Air Quality"].strip(),
            "pollutant": extract_pollutants(delhi_row["Prominent Pollutant"])
        }])

        # If file exists, append without duplicates
        if os.path.exists(csv_path):
            existing = pd.read_csv(csv_path)
            if date_str not in existing["date"].values:
                combined = pd.concat([existing, new_entry], ignore_index=True)
                combined = combined.sort_values(by="date")
                combined.to_csv(csv_path, index=False, encoding="utf-8")
            else:
                logger.info(f"Data for {date_str} already exists in {csv_path}. Skipping append.")
        else:
            new_entry.to_csv(csv_path, index=False, encoding="utf-8")

def main():
    today = datetime.today().strftime("%Y_%m_%d")
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y_%m_%d")
    reqd_date = yesterday if datetime.now().hour < 12 else today
    csv_filename = "delhi_aqi_cpcb.csv"
    csv_filepath = os.path.join(DATA_DIR, csv_filename)
    cpcb_url_primary, cpcb_url_fallback = build_cpcb_urls(reqd_date)
    print(cpcb_url_fallback)
    date_str = reqd_date.replace("_", "-")
    pdf_url = None
        

        
    try:
        r = requests.head(cpcb_url_primary, verify=False, timeout=5)
        if r.status_code == 200:
            pdf_url = cpcb_url_primary
            url_type = "primary"
        else:
            raise Exception(f"Primary URL returned {r.status_code}")
    except Exception as e:
        try:
            r = requests.head(cpcb_url_fallback, verify=False, timeout=5)
            if r.status_code == 200:
                pdf_url = cpcb_url_fallback
                url_type = "fallback"
            else:
                raise Exception(f"Fallback URL returned {r.status_code}")
        except Exception as e2:
            raise Exception(f"Fallback URL also failed: {e2}")

    if pdf_url:
        save_aqi_to_csv(pdf_url, csv_filepath, date_str, url_type)
    else:
        logger.warning("No valid CPCB PDF found for today or yesterday.")



if __name__ == "__main__":
    main()