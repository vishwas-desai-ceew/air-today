from datetime import date

import pandas as pd
import pytest

from ingestion import get_fire_pbhr as fires
from ingestion import get_met_details


@pytest.fixture
def state_csvs(tmp_path, monkeypatch):
    paths = {"Punjab": tmp_path / "fires_punjab.csv", "Haryana": tmp_path / "fires_haryana.csv"}
    monkeypatch.setattr(fires, "FIRE_STATE_CSVS", paths)
    monkeypatch.setattr(get_met_details, "FIRE_STATE_CSVS", paths)
    return paths


def raw(rows):
    return pd.DataFrame(rows, columns=["state_name", "satellite_instrument", "count_of_incidents"])


def test_to_state_rows_fills_missing_instruments_and_states_with_zero(state_csvs):
    rows = fires.to_state_rows(raw([
        ("Punjab", "NOAA/VIIRS", 200), ("Punjab", "Aqua/MODIS", 400),
        ("Punjab", "Suomi-NPP/VIIRS", 99),  # untracked instrument is ignored
    ]), date(2026, 11, 5))
    assert rows["Punjab"] == {"date": "2026-11-05", "NOAA/VIIRS": 200, "Aqua/MODIS": 400, "Terra/MODIS": 0}
    assert rows["Haryana"] == {"date": "2026-11-05", "NOAA/VIIRS": 0, "Aqua/MODIS": 0, "Terra/MODIS": 0}


def test_to_state_rows_empty_result_writes_nothing():
    assert fires.to_state_rows(raw([]), date(2026, 11, 5)) == {}


def test_upsert_replaces_same_date_and_keeps_others(state_csvs):
    path = state_csvs["Punjab"]
    fires.upsert(path, [{"date": "2026-11-04", "NOAA/VIIRS": 1, "Aqua/MODIS": 2, "Terra/MODIS": 3},
                        {"date": "2026-11-05", "NOAA/VIIRS": 4, "Aqua/MODIS": 5, "Terra/MODIS": 6}])
    fires.upsert(path, [{"date": "2026-11-05", "NOAA/VIIRS": 40, "Aqua/MODIS": 50, "Terra/MODIS": 60}])
    df = fires.read_state_fires("Punjab")
    assert list(df.columns) == ["date", "NOAA/VIIRS", "Aqua/MODIS", "Terra/MODIS"]
    assert df["date"].tolist() == [date(2026, 11, 4), date(2026, 11, 5)]
    assert df["NOAA/VIIRS"].tolist() == [1, 40]
    assert not path.with_suffix(".csv.tmp").exists()


def test_run_writes_one_file_per_state(state_csvs, monkeypatch):
    monkeypatch.setattr(fires, "fetch_day", lambda day: raw([
        ("Punjab", "NOAA/VIIRS", 10), ("Haryana", "NOAA/VIIRS", 2), ("Haryana", "Terra/MODIS", 1),
    ]) if day != date(2026, 11, 3) else raw([]))
    out = fires.run(date(2026, 11, 2), date(2026, 11, 4))
    assert out["days_written"] == 2 and out["no_data"] == ["2026-11-03"]
    hr = fires.read_state_fires("Haryana")
    assert hr["date"].tolist() == [date(2026, 11, 2), date(2026, 11, 4)]
    assert hr["Terra/MODIS"].tolist() == [1, 1]


def test_get_fire_count_uses_headline_instrument(state_csvs):
    fires.upsert(state_csvs["Punjab"], [{"date": "2026-11-05", "NOAA/VIIRS": 245, "Aqua/MODIS": 477, "Terra/MODIS": 12}])
    fires.upsert(state_csvs["Haryana"], [{"date": "2026-11-05", "NOAA/VIIRS": 8, "Aqua/MODIS": 3, "Terra/MODIS": 0}])
    assert get_met_details.get_fire_count("2026-11-05") == {"Punjab": 245, "Haryana": 8}
    assert get_met_details.get_fire_count("2026-11-06") is None
