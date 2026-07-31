import streamlit as st
import base64
from datetime import datetime
from pathlib import Path
import os
import pytz

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = DATA_DIR / "imd_bulletin_today.pdf"


@st.cache_data(ttl=3600)
def load_pdf_base64():
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()
    return base64.b64encode(pdf_bytes).decode("utf-8")


def render_aqi_pdf():
    try:
        modification_time = os.path.getmtime(PDF_PATH)
        utc_dt = datetime.fromtimestamp(modification_time, tz=pytz.utc)
        ist_dt = utc_dt.astimezone(pytz.timezone("Asia/Kolkata"))
        formatted_time = ist_dt.strftime("%d %B %Y · %I:%M %p")
        b64_pdf = load_pdf_base64()

        pdf_display = f"""
        <section class="imd-bulletin-viewer">
            <header class="imd-bulletin-header">
                <div class="imd-bulletin-title">
                    <span class="imd-bulletin-icon" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" height="24" width="24" viewBox="0 0 640 640"><path fill="rgb(255, 255, 255)" d="M240 112L128 112C119.2 112 112 119.2 112 128L112 512C112 520.8 119.2 528 128 528L208 528L208 576L128 576C92.7 576 64 547.3 64 512L64 128C64 92.7 92.7 64 128 64L261.5 64C278.5 64 294.8 70.7 306.8 82.7L429.3 205.3C441.3 217.3 448 233.6 448 250.6L448 400.1L400 400.1L400 272.1L312 272.1C272.2 272.1 240 239.9 240 200.1L240 112.1zM380.1 224L288 131.9L288 200C288 213.3 298.7 224 312 224L380.1 224zM272 444L304 444C337.1 444 364 470.9 364 504C364 537.1 337.1 564 304 564L292 564L292 592C292 603 283 612 272 612C261 612 252 603 252 592L252 464C252 453 261 444 272 444zM304 524C315 524 324 515 324 504C324 493 315 484 304 484L292 484L292 524L304 524zM400 444L432 444C460.7 444 484 467.3 484 496L484 560C484 588.7 460.7 612 432 612L400 612C389 612 380 603 380 592L380 464C380 453 389 444 400 444zM432 572C438.6 572 444 566.6 444 560L444 496C444 489.4 438.6 484 432 484L420 484L420 572L432 572zM508 464C508 453 517 444 528 444L576 444C587 444 596 453 596 464C596 475 587 484 576 484L548 484L548 508L576 508C587 508 596 517 596 528C596 539 587 548 576 548L548 548L548 592C548 603 539 612 528 612C517 612 508 603 508 592L508 464z"/></svg></span>
                    <div>
                        <p>India Meteorological Department</p>
                        <h3>Daily Air Quality Bulletin</h3>
                    </div>
                </div>
                <div class="imd-bulletin-actions">
                    <span class="imd-bulletin-updated">Updated {formatted_time} IST</span>
                    <a class="imd-bulletin-download" href="data:application/pdf;base64,{b64_pdf}" download="imd_air_quality_bulletin.pdf"><svg xmlns="http://www.w3.org/2000/svg" height="18" width="18" viewBox="0 0 640 640"><path fill="rgb(255, 255, 255)" d="M352 96C352 78.3 337.7 64 320 64C302.3 64 288 78.3 288 96L288 306.7L246.6 265.3C234.1 252.8 213.8 252.8 201.3 265.3C188.8 277.8 188.8 298.1 201.3 310.6L297.3 406.6C309.8 419.1 330.1 419.1 342.6 406.6L438.6 310.6C451.1 298.1 451.1 277.8 438.6 265.3C426.1 252.8 405.8 252.8 393.3 265.3L352 306.7L352 96zM160 384C124.7 384 96 412.7 96 448L96 480C96 515.3 124.7 544 160 544L480 544C515.3 544 544 515.3 544 480L544 448C544 412.7 515.3 384 480 384L433.1 384L376.5 440.6C345.3 471.8 294.6 471.8 263.4 440.6L206.9 384L160 384zM464 440C477.3 440 488 450.7 488 464C488 477.3 477.3 488 464 488C450.7 488 440 477.3 440 464C440 450.7 450.7 440 464 440z"/></svg>&nbsp;Download PDF</a>
                </div>
            </header>
            <div class="imd-bulletin-frame">
                <iframe
                    title="IMD Daily Air Quality Bulletin"
                    src="data:application/pdf;base64,{b64_pdf}#zoom=page-width"
                    loading="lazy">
                </iframe>
            </div>
        </section>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)

    except FileNotFoundError:
        st.info("The IMD bulletin is not available yet. Please check back later.")

   
