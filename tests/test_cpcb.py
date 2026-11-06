from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ingestion import cpcb

FIXTURES = Path(__file__).parent / "fixtures"


def test_ncr_bulletin_finds_delhi_on_page_two():
    # Delhi is listed as District="OuterNorth", City/Town="Delhi" on page 2
    entry = cpcb.parse_bulletin((FIXTURES / "cpcb_ncr_2026_10_26.pdf").read_bytes(), date(2026, 10, 26))
    assert entry == {"date": "2026-10-26", "aqi": 174, "category": "Moderate",
                     "pollutant": "PM2.5, PM10", "stations": ""}


def test_national_bulletin_fallback_reads_split_subscripts_and_stations():
    entry = cpcb.parse_bulletin((FIXTURES / "cpcb_national_2026_10_25.pdf").read_bytes(), date(2026, 10, 25))
    assert entry["aqi"] == 153
    assert entry["pollutant"] == "PM10"   # cell text is "PM\n10"
    assert entry["stations"] == "52/59"


def test_stale_bulletin_is_rejected():
    with pytest.raises(ValueError, match="dated 2026-10-26"):
        cpcb.parse_bulletin((FIXTURES / "cpcb_ncr_2026_10_26.pdf").read_bytes(), date(2026, 10, 25))


@pytest.mark.parametrize("raw, expected", [
    ("PM2.5, PM10", "PM2.5, PM10"),
    ("PM\n2.5, PM\n10", "PM2.5, PM10"),
    ("OZONE,PM10", "PM10, O3"),
    ("O3", "O3"),
    ("PM10", "PM10"),          # the old substring matcher returned "PM2.5, PM10" here
    ("NO2", "NO2"),
    ("", ""),
    (None, ""),
])
def test_normalise_pollutants(raw, expected):
    assert cpcb.normalise_pollutants(raw) == expected


def test_upsert_replaces_a_failed_day(tmp_path):
    csv_path = tmp_path / "aqi.csv"
    pd.DataFrame([{"date": "2026-10-25", "aqi": None, "category": None, "pollutant": None}]).to_csv(csv_path, index=False)
    cpcb.upsert_aqi({"date": "2026-10-25", "aqi": 153, "category": "Moderate", "pollutant": "PM10",
                     "stations": "", "source": "test"}, csv_path)
    cpcb.upsert_aqi({"date": "2026-10-24", "aqi": 191, "category": "Moderate", "pollutant": "PM2.5",
                     "stations": "", "source": "test"}, csv_path)
    df = pd.read_csv(csv_path)
    assert list(df["date"]) == ["2026-10-24", "2026-10-25"]
    assert list(df["aqi"]) == [191, 153]
    assert list(df.columns) == cpcb.CSV_COLUMNS
