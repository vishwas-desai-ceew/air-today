import pandas as pd

from views import data, pollutants


def _hours(n, **cols):
    t = pd.date_range("2026-11-01 00:00", periods=n, freq="h")
    return pd.DataFrame({"time": t, **{k: v[:n] for k, v in cols.items()}})


def test_pm_hourly_reads_signalsfunc_shape(tmp_path, monkeypatch):
    p = tmp_path / "pm.csv"
    p.write_text("observation_hour_start,PM25,PM10\n2026-11-01 01:00:00,40,90\n2026-11-01 00:00:00,30,x\n")
    monkeypatch.setattr(data, "SIGNALS_HOURLY_CSV", p)
    data.pm_hourly.clear()
    df = data.pm_hourly()
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
