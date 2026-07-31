import sys
import requests
from datetime import datetime
from pathlib import Path

# run 1st cronjob at 8 pm
# run 2nd cronjob after midnight (pref 2 AM or 3 AM)

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.logging_config import get_logger
logger = get_logger(__name__)

DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_URL = "https://nwp.imd.gov.in/silam/aqbulletin.pdf"
OUTPUT_FILE =  DATA_DIR / "imd_bulletin_today.pdf"


def download_pdf():
    try:
        r = requests.get(PDF_URL, timeout=60)
        r.raise_for_status()
        with open(OUTPUT_FILE, "wb") as f:
            f.write(r.content)
        logger.info("PDF downloaded successfully")
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")


if __name__ == "__main__":
    download_pdf()
