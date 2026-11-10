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
    assert _headline(FACTS) == "Poor on 28 Oct → Very Poor on 29 Oct. Weak wind and low ventilation will hold pollution in."
    good = {**FACTS, "wind_ms": 3.5, "ventilation_index": 9000}
    assert _headline(good) == "Poor on 28 Oct → Very Poor on 29 Oct. Conditions favour dispersion."


def test_bulletin_not_out_yet():
    facts = {**FACTS, "aqi": {**FACTS["aqi"], "value": None, "category": None, "prev_value": None}}
    assert _by_icon(facts)["aqi"]["value"] == "—"


def test_forecast_note_shows_aqews_not_model():
    assert _by_icon(FACTS)["forecast"]["note"] == "AQEWS"


def test_missing_ventilation_is_filled_from_live_aqews():
    from datetime import date
    from views.data import with_live_ventilation
    snap = {**FACTS, "ventilation_index": None}
    seen = []
    lookup = lambda d: (seen.append(d), {"ventilation_index": 9500})[1]
    assert with_live_ventilation(snap, lookup)["ventilation_index"] == 9500.0
    assert seen == [date(2026, 10, 29)]                      # forecast date, not today
    assert with_live_ventilation(FACTS, lookup)["ventilation_index"] == 2900.0   # snapshot value kept
    assert with_live_ventilation(snap, lambda d: {"ventilation_index": None})["ventilation_index"] is None


def test_aqi_tone_follows_category_not_the_daily_change():
    better_but_very_poor = {**FACTS, "aqi": {**FACTS["aqi"], "value": 344, "category": "Very Poor", "prev_value": 376}}
    items = _by_icon(better_but_very_poor)
    assert items["aqi"]["tone"] == "bad"
    assert items["aqi"]["note"].startswith("▼ 32 vs 27 Oct")       # the improvement is still shown
    assert items["forecast"]["tone"] == "bad"                         # Very Poor forecast
    sat = {**FACTS, "aqi": {**FACTS["aqi"], "category": "Satisfactory"}, "forecast": {**FACTS["forecast"], "category": "Moderate"}}
    assert _by_icon(sat)["aqi"]["tone"] == "good" and _by_icon(sat)["forecast"]["tone"] is None
