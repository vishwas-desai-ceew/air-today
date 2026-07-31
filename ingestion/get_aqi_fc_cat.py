import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re
import io
import pandas as pd
import streamlit as st
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_NAME = "gemini-2.0-flash"
URL = "https://ews.tropmet.res.in/"
OUTPUT_CSV = DATA_DIR / "AQI_forecast_category.csv"


# Initialize Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


def fetch_bulletin_text():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    sections = []
    for id_ in ["bulletin", "message"]:
        el = soup.find("div", id=id_) or soup.find("div", class_=id_)
        if el:
            sections.append(el.get_text(separator=" ", strip=True))
    if not sections:
        text = soup.get_text(separator=" ", strip=True)
        sections.append(text)
    return "\n".join(sections)[:8000]


def extract_table_with_gemini(text):
    prompt = f"""
        You are given an excerpt from an air quality bulletin.

        Extract all the forecasted air quality categories and their date ranges mentioned after phrases like:
        - "The air quality is very likely to be"
        - "Air quality is expected to be"

        For each day in the mentioned date range, output one row in **strict CSV format** with columns:
        date (YYYY-MM-DD), category

        Guidelines:
        - Do NOT include headers or markdown (no ``` or table formatting).
        - Only output raw CSV data.
        - Expand ranges like "from 29.10.2025 to 31.10.2025" into daily entries for 29, 30, and 31.
        - Convert all dates to ISO format (YYYY-MM-DD).
        - Keep only the date and category, comma-separated.
        - Stop after getting 4 rows of data
        - Example output:
        2025-10-29,Poor
        2025-10-30,Poor
        2025-10-31,Poor
        2025-11-01,Very Poor

        Now extract data from the following text:
        {text}
    """
    response = model.generate_content(prompt)
    return response.text.strip()


def save_to_csv(data, filepath):
    cleaned_data = re.sub(r'```.*?```', '', data, flags=re.DOTALL)
    cleaned_data = cleaned_data.replace('```', '').strip()
    cleaned_data = re.sub(r'\s*\n\s*', '\n', cleaned_data).strip()
    df = pd.read_csv(io.StringIO(cleaned_data), names=["date", "category"])
    df.to_csv(filepath, index=False)
   

def main():
    bulletin_text = fetch_bulletin_text()
    gemini_output = extract_table_with_gemini(bulletin_text)
    save_to_csv(gemini_output, OUTPUT_CSV)


if __name__ == "__main__":
    main()