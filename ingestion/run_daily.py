"""One entry point for the whole daily update, replacing 8 separately-timed
cron jobs whose ordering mattered but wasn't enforced (the summary could run
before the CPCB bulletin or the forecasts had been fetched).

Each step runs in order, failures are isolated (one dead upstream doesn't stop
the rest), and the outcome of every step is written to
data/pipeline_status.json, which the dashboard's sidebar status panel reads.

Suggested crontab (IST machine clock):
    20 16 * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py
    10 18 * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py
    30 2  * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py --only imd fires
The 16:20 run picks up the CPCB bulletin as soon as it is out; the 18:10 run
is a safety net. Every step is idempotent, so re-running is always safe.

    python ingestion/run_daily.py                 # everything
    python ingestion/run_daily.py --only cpcb summary
"""
import sys
import time
import argparse
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import IST, PIPELINE_STATUS_JSON
from config.logging_config import get_logger
from ingestion.json_store import read_json, write_json_atomic

logger = get_logger(__name__)


def _weather():
    from ingestion import weather
    return weather.run()


def _aqews():
    from ingestion import aqews
    return aqews.run()


def _cpcb():
    from ingestion import cpcb
    return cpcb.run()


def _imd():
    from ingestion import download_imd_bulletin
    download_imd_bulletin.download_pdf()
    return {"file": str(download_imd_bulletin.OUTPUT_FILE)}


def _imd_summary():
    from ingestion import get_gemini_summary
    get_gemini_summary.get_gemini_summary()
    return {"file": str(get_gemini_summary.GEMINI_JSON)}


def _fires():
    # Depends on the private `signalsfunc` package; skipped where it isn't installed.
    from ingestion import get_fire_pbhr
    get_fire_pbhr.main()
    return {}


def _summary():
    from ingestion import get_aqi_summary
    return get_aqi_summary.run()


# Order matters: the summary reads what every earlier step wrote.
STEPS = {
    "weather": ("Open-Meteo forecast", _weather),
    "aqews": ("AQEWS forecast", _aqews),
    "cpcb": ("CPCB AQI bulletin", _cpcb),
    "imd": ("IMD AQ bulletin", _imd),
    "imd_summary": ("IMD bulletin summary (Gemini)", _imd_summary),
    "fires": ("Punjab/Haryana fires", _fires),
    "summary": ("Daily update", _summary),
}


def run(only=None) -> dict:
    status = read_json(PIPELINE_STATUS_JSON)
    for key, (label, fn) in STEPS.items():
        if only and key not in only:
            continue
        started = time.monotonic()
        entry = {"label": label, "ran_at": datetime.now(IST).isoformat(timespec="seconds")}
        try:
            entry["detail"] = fn()
            entry["ok"] = True
            entry["last_success"] = entry["ran_at"]
        except ModuleNotFoundError as e:
            entry.update(ok=None, error=f"skipped: {e}")
            entry["last_success"] = status.get(key, {}).get("last_success")
        except Exception as e:
            entry.update(ok=False, error=f"{type(e).__name__}: {e}")
            entry["last_success"] = status.get(key, {}).get("last_success")
            logger.error("Step %s failed:\n%s", key, traceback.format_exc())
        entry["seconds"] = round(time.monotonic() - started, 1)
        status[key] = entry
        logger.info("%-12s %-5s %ss %s", key, entry["ok"], entry["seconds"], entry.get("error", ""))
        write_json_atomic(PIPELINE_STATUS_JSON, status, indent=2, default=str)
    return status


def main():
    parser = argparse.ArgumentParser(description="Run the Air Today daily update")
    parser.add_argument("--only", nargs="*", choices=list(STEPS), help="run just these steps")
    args = parser.parse_args()
    status = run(only=args.only)
    failed = [k for k, v in status.items() if (not args.only or k in args.only) and v.get("ok") is False]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
