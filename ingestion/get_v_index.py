"""Kept so existing cron entries keep working - the logic now lives in
ingestion/aqews.py (AQEWS forecasts). New cron entries should call
ingestion/run_daily.py instead, which runs every step in order."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingestion import aqews

if __name__ == "__main__":
    aqews.run()
