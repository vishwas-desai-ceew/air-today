from google import genai
import streamlit as st
import json
from pathlib import Path


PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
GEMINI_JSON = DATA_DIR / "gemini_summary.json"

def get_gemini_summary():
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    pdf_path = client.files.upload(file="/Users/Vishwas/Desktop/CEEW/work/aq_winter/data/imd_bulletin_today.pdf")
    prompt = """
    You are analyzing the provided PDF document.  
    Your task:
    1. Identify the first 4 points (bullet points, numbered items, or equivalent in the document).  
    2. For each point, write a brief description of its content in your own words.  
    3. Divide the output into sections, with a clear heading for each point.  

    Formatting and rules:
    - There should be a heading under which the descriptions shoudl exist
    - Do not mention the word "Point" as heading or inside the descriptions.   
    - Base your answer strictly on the PDF text; do not add extra information.  
    - If fewer than 4 points exist, output "Not found in document" as a block for missing ones.  
    - Keep each description concise (2-3 sentences maximum).  
    - Do not add any markdown elements or html tags to the response
    """
    response = client.models.generate_content(model = "gemini-2.5-flash", contents=[prompt, pdf_path], config={"temperature": 0,"top_p": 1,"top_k": 1})
    result_text = response.text
    with open(GEMINI_JSON, "w", encoding="utf-8") as f:
        json.dump({"result": result_text}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    get_gemini_summary()
