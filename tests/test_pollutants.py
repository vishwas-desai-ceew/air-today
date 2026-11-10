import pandas as pd

import os
import time

from ingestion import cpcb_hourly
from views import data, pollutants

RAW = """parameter,observation_hour_start,city_name,avg_of_average_value_in_hour,avg_of_maximum_value_in_hour,state_code,state_name
PM10,2026-11-10 00:00:00,Delhi,341.758915,347.084151,IN-DL,Delhi
PM25,2026-11-10 00:00:00,Delhi,223.485197,227.774364,IN-DL,Delhi
PM10,2026-11-10 01:00:00,Delhi,336.440670,341.739464,IN-DL,Delhi
PM25,2026-11-10 01:00:00,Delhi,226.028491,229.993448,IN-DL,Delhi
PM25,2026-11-10 02:00:00,Delhi,214.267895,218.050000,IN-DL,Delhi
"""


def _hours(n, **cols):
    t = pd.date_range("2026-11-01 00:00", periods=n, freq="h")
    return pd.DataFrame({"time": t, **{k: v[:n] for k, v in cols.items()}})


def test_read_cpcb_long_table_pivots_to_pm25_and_pm10():
    import io
    wide = cpcb_hourly.to_wide(pd.read_csv(io.StringIO(RAW)))
    assert list(wide.columns) == ["time", "PM2.5", "PM10"]
    assert wide["PM2.5"].round(1).tolist() == [223.5, 226.0, 214.3]
    assert pd.isna(wide["PM10"].iloc[2])          # PM10 missing that hour -> gap, not a crash


def test_fresh_cache_is_read_without_calling_read_cpcb(tmp_path, monkeypatch):
    p = tmp_path / "cache.csv"
    p.write_text(RAW)
    monkeypatch.setattr(cpcb_hourly, "fetch", lambda *a: (_ for _ in ()).throw(AssertionError("called")))
    raw, fetched_at, stale = cpcb_hourly.load(p)
    assert len(raw) == 5 and not stale and fetched_at is not None


def test_old_cache_refreshes_and_falls_back_when_fetch_fails(tmp_path, monkeypatch):
    p = tmp_path / "cache.csv"
    p.write_text(RAW)
    old = time.time() - 2 * 3600
    os.utime(p, (old, old))
    calls = []

    def failing_fetch(*a):
        calls.append(1)
        raise ImportError("No module named 'signalsfunc'")
    monkeypatch.setattr(cpcb_hourly, "fetch", failing_fetch)
    raw, _, stale = cpcb_hourly.load(p)
    assert calls and len(raw) == 5 and stale        # tried, then used the old cache

    monkeypatch.setattr(cpcb_hourly, "fetch", lambda *a: pd.read_csv(p).head(2))
    raw, _, stale = cpcb_hourly.load(p)
    assert len(raw) == 2 and not stale              # refreshed and rewritten


def test_pm_hourly_falls_back_to_sample_shape(tmp_path, monkeypatch):
    p = tmp_path / "pm.csv"
    p.write_text("observation_hour_start,PM25,PM10\n2026-11-01 01:00:00,40,90\n2026-11-01 00:00:00,30,x\n")
    monkeypatch.setattr(data, "SIGNALS_HOURLY_CSV", p)
    monkeypatch.setattr(cpcb_hourly, "load", lambda: (pd.DataFrame(), None, True))
    data.pm_hourly.clear()
    df, info = data.pm_hourly()
    assert info["source"] == "sample"
    assert list(df.columns) == ["time", "PM2.5", "PM10"]
    assert df["PM2.5"].tolist() == [30, 40]          # sorted by time
    assert pd.isna(df["PM10"].iloc[0])                 # bad value -> NaN, not a crash


def test_chart_draws_one_line_per_pollutant():
    df = _hours(30, **{"PM2.5": [100] * 30, "PM10": [250] * 30})
    fig = pollutants.pm_chart(df, ["PM2.5", "PM10"], "PM10")
    assert [t.name for t in fig.data] == ["PM2.5 hourly", "PM10 hourly"]
    assert len(fig.layout.shapes) > 0          # CPCB bands are shaded


def test_chart_marks_naaqs_24h_and_shows_hour_on_hover():
    df = _hours(30, **{"PM2.5": [100] * 30})
    fig = pollutants.pm_chart(df, ["PM2.5"], "PM2.5")
    assert any(sh.type == "line" and sh.y0 == 60 for sh in fig.layout.shapes)   # NAAQS 24-h PM2.5
    assert any("NAAQS 24-hour PM2.5: 60" in a.text for a in fig.layout.annotations)
    assert "%H:%M" in fig.layout.xaxis.hoverformat
