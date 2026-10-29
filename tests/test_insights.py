from views.widgets import _headline, insight_items

FACTS = {
    "date": "2026-10-28", "forecast_date": "2026-10-29", "fire_date": "2026-10-27",
    "aqi": {"value": 229, "category": "Poor", "pollutant": "PM2.5, PM10", "prev_value": 197, "prev_date": "2026-10-27"},
    "forecast": {"aqi": 312, "category": "Very Poor", "source": "AQEWS model"},
    "wind_ms": 1.25, "min_temp_c": 19.5, "ventilation_index": 2900.0, "rain_mm": 0.0, "fires": None,
}


def _by_icon(facts):
    return {i["icon"]: i for i in insight_items(facts)}


def test_unfavourable_dispersion_is_flagged():
    items = _by_icon(FACTS)
    assert items["wind"]["tone"] == "bad"
    assert items["vent"]["tone"] == "bad"
    assert items["aqi"]["tone"] == "bad"          # worse than yesterday
    assert items["aqi"]["note"].startswith("▲ 32 vs 27 Oct")


def test_missing_fire_feed_is_not_reported_as_zero():
    assert _by_icon(FACTS)["fire"]["value"] == "—"


def test_headline():
    assert _headline(FACTS) == "Poor today → Very Poor tomorrow. Weak wind and low ventilation will hold pollution in."
    good = {**FACTS, "wind_ms": 3.5, "ventilation_index": 9000}
    assert _headline(good) == "Poor today → Very Poor tomorrow. Conditions favour dispersion."


def test_bulletin_not_out_yet():
    facts = {**FACTS, "aqi": {**FACTS["aqi"], "value": None, "category": None, "prev_value": None}}
    assert _by_icon(facts)["aqi"]["value"] == "—"
