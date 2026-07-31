import pandas as pd

from ingestion import get_aqews_aqi


def _hourly(date_str, pm25_value, pm10_value):
    """One hourly reading per day at 10:00 -> +8h report-date shift keeps it same-day."""
    ts = pd.to_datetime(f"{date_str}T10:00:00")
    df_pm25 = pd.DataFrame({"datetime": [ts], "AQI_PM25": [pm25_value]})
    df_pm10 = pd.DataFrame({"datetime": [ts], "AQI_PM10": [pm10_value]})
    return df_pm25, df_pm10


def _run(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(get_aqews_aqi, "DATA_DIR", tmp_path)
    pm25_frames, pm10_frames = [], []
    for date_str, pm25_value, pm10_value in rows:
        p25, p10 = _hourly(date_str, pm25_value, pm10_value)
        pm25_frames.append(p25)
        pm10_frames.append(p10)
    df_pm25 = pd.concat(pm25_frames, ignore_index=True)
    df_pm10 = pd.concat(pm10_frames, ignore_index=True)

    get_aqews_aqi.save_aqi_to_csv(df_pm25, df_pm10)

    out = pd.read_csv(tmp_path / "AQEWS_AQI_forecast.csv")
    return dict(zip(out["date"].astype(str), out["category"]))


def test_low_aqi_is_good(tmp_path, monkeypatch):
    categories = _run(tmp_path, monkeypatch, [("2026-01-01", 30, 20)])
    assert categories["2026-01-01"] == "Good"


def test_moderate_aqi_uses_the_higher_of_pm25_pm10(tmp_path, monkeypatch):
    # overall AQI = max(PM2.5, PM10); 150 should land in the "Moderate" bucket (100, 200]
    categories = _run(tmp_path, monkeypatch, [("2026-01-02", 150, 90)])
    assert categories["2026-01-02"] == "Moderate"


def test_severe_aqi_at_top_of_range(tmp_path, monkeypatch):
    categories = _run(tmp_path, monkeypatch, [("2026-01-03", 450, 100)])
    assert categories["2026-01-03"] == "Severe"


def test_bin_boundary_is_inclusive_on_the_upper_edge(tmp_path, monkeypatch):
    # exactly 100 should fall in (50, 100] -> "Satisfactory", not spill into "Moderate"
    categories = _run(tmp_path, monkeypatch, [("2026-01-04", 100, 50)])
    assert categories["2026-01-04"] == "Satisfactory"


def test_multiple_days_are_categorized_independently(tmp_path, monkeypatch):
    categories = _run(
        tmp_path,
        monkeypatch,
        [("2026-01-01", 30, 20), ("2026-01-02", 150, 90), ("2026-01-03", 450, 100)],
    )
    assert categories == {
        "2026-01-01": "Good",
        "2026-01-02": "Moderate",
        "2026-01-03": "Severe",
    }
