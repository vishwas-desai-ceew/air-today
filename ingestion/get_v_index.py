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
MODEL_NAME = "gemini-3.0-flash"
URL = "https://ews.tropmet.res.in/"
OUTPUT_CSV = DATA_DIR / "ventilation_index_forecast.csv"


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
    The text below is from the Indian Institute of Tropical Meteorology EWS bulletin.
    Locate 'Point 3' or any section about 'Ventilation Index Forecast'.
    Do not add any additonal characters like quotes or words like "text" or "table".
    Return a clean table with coulmn names in plain text (no markdown formatting, no SI units)
    with columns:
    date (YYYY-MM-DD), mixing_depth, ventilation_index
    {text}

    """
    response = model.generate_content(prompt)
    return response.text.strip()


def save_to_csv(data, filepath):
    cleaned_data = re.sub(r'```.*?```', '', data, flags=re.DOTALL)
    cleaned_data = cleaned_data.replace('```', '').replace('text', '').strip()
    cleaned_data = cleaned_data.replace('"', '').replace("'", '')
    df = pd.read_csv(io.StringIO(cleaned_data))
    df.to_csv(filepath, index=False)

def main():
    bulletin_text = fetch_bulletin_text()
    gemini_output = extract_table_with_gemini(bulletin_text)
    save_to_csv(gemini_output, OUTPUT_CSV)


if __name__ == "__main__":
    main()