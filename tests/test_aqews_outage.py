"""The AQEWS outage check must never crash a page (it used to read the CSV
directly on every page, so a missing file took the whole app down)."""
from datetime import datetime, timedelta

import pandas as pd

from config.settings import IST
from views import render_aqi_fc


def _forecast(start, days=9, values=None):
    dates = [start + timedelta(days=i) for i in range(days)]
    return pd.DataFrame({"date": dates, "AQI_overall": values or [300 + i for i in range(days)]})


def test_missing_file_is_an_outage_not_a_crash(monkeypatch):
    monkeypatch.setattr(render_aqi_fc.data, "aqews_daily", lambda: pd.DataFrame())
    flag, df = render_aqi_fc.get_error_message()
    assert flag is True and df.empty
    assert render_aqi_fc.aqews_outage() is True


def test_current_forecast_is_fine(monkeypatch):
    today = datetime.now(IST).date()
    monkeypatch.setattr(render_aqi_fc.data, "aqews_daily", lambda: _forecast(today))
    assert render_aqi_fc.aqews_outage() is False


def test_stale_forecast_is_an_outage(monkeypatch):
    old = datetime.now(IST).date() - timedelta(days=20)
    monkeypatch.setattr(render_aqi_fc.data, "aqews_daily", lambda: _forecast(old))
    assert render_aqi_fc.aqews_outage() is True


def test_unexpected_error_is_an_outage(monkeypatch):
    def boom():
        raise OSError("disk gone")
    monkeypatch.setattr(render_aqi_fc.data, "aqews_daily", boom)
    assert render_aqi_fc.aqews_outage() is True
