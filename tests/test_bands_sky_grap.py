from datetime import date, datetime

import pandas as pd
import pytest

from config.reference import AQI_BANDS, PM25_BANDS, band_for
from views.sky import sky_phase, solar_elevation, wx_icon_name

IST = "Asia/Kolkata"


@pytest.mark.parametrize("value,expected", [
    (0, "Good"), (50, "Good"), (51, "Satisfactory"), (200, "Moderate"), (201, "Poor"),
    (300, "Poor"), (301, "Very Poor"), (400, "Very Poor"), (401, "Severe"), (500, "Severe"),
])
def test_aqi_bands_follow_cpcb_table(value, expected):
    assert band_for(value, AQI_BANDS)[0] == expected


@pytest.mark.parametrize("value,expected", [
    (30, "Good"), (60, "Satisfactory"), (90, "Moderate"), (120, "Poor"), (250, "Very Poor"), (251, "Severe"),
])
def test_pm25_bands_follow_cpcb_table(value, expected):
    assert band_for(value, PM25_BANDS)[0] == expected


def test_band_for_none():
    assert band_for(None, AQI_BANDS) == (None, None)


def test_solar_elevation_delhi_noon_and_midnight():
    noon = solar_elevation(pd.Timestamp("2026-11-05 12:15", tz=IST))
    assert 43 < noon < 47           # 90 - 28.6 lat - ~15.6 declination
    assert solar_elevation(pd.Timestamp("2026-11-05 00:00", tz=IST)) < -30


@pytest.mark.parametrize("hour,expected", [(1, "night"), (6, "dawn"), (12, "day"), (17, "dusk"), (22, "night")])
def test_sky_phase(hour, expected):
    assert sky_phase(datetime(2026, 11, 5, hour, 30, tzinfo=pd.Timestamp.now(tz=IST).tzinfo)) == expected


def test_icon_mapping():
    assert wx_icon_name(0, is_day=1) == "sun"
    assert wx_icon_name(0, is_day=0) == "moon"
    assert wx_icon_name(None, 1, condition="Mist") == "fog"
    assert wx_icon_name(2, is_day=0) == "cloud-moon"
    assert wx_icon_name(0, 1, rain=0.5) == "rain"


def test_grap_date_parsing_and_slugs():
    pytest.importorskip("openpyxl")  # converter is dev-only
    from ingestion.convert_grap_orders import parse_order_date, slug
    assert parse_order_date(datetime(2025, 10, 14)) == (date(2025, 10, 14), "")
    assert parse_order_date("11-Nov-2025 (Clarification order)") == (date(2025, 11, 11), "Clarification order")
    assert parse_order_date("13.12.2025") == (date(2025, 12, 13), "")
    assert slug("GRAP Stage") == "stage"
    assert slug("AQI / Trigger") == "aqi_trigger"
