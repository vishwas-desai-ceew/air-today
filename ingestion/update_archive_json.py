import sys
from pathlib import Path

# run cron at 9 pm

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from ingestion.json_store import read_json, write_json_atomic

DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_JSON = DATA_DIR / "archive.json"
ARCHIVE_TEMP = DATA_DIR / "archive_temp.json"


def update_archive_json():
    if not ARCHIVE_TEMP.exists():
        return

    summary_dict = read_json(ARCHIVE_TEMP)
    archive = read_json(ARCHIVE_JSON)
    archive.update(summary_dict)
    write_json_atomic(ARCHIVE_JSON, archive, indent=2, default=str)


if __name__ == "__main__":
    update_archive_json()