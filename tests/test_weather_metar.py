from ingestion.weather import _relative_humidity, describe_metar


def test_relative_humidity_from_dew_point():
    # METAR VIDD 290430Z ... 24/20 -> about 78 %
    assert _relative_humidity(24, 20) == 78
    assert _relative_humidity(20, 20) == 100


def test_present_weather_wins_over_cloud_cover():
    assert describe_metar({"wxString": "BR", "cover": "BKN"}) == "Mist"
    assert describe_metar({"wxString": "-DZ", "cover": "BKN"}) == "Light drizzle"
    assert describe_metar({"wxString": "HZ FU"}) == "Haze and smoke"


def test_cloud_cover_when_no_weather():
    assert describe_metar({"wxString": None, "cover": "SCT"}) == "Partly cloudy"
    assert describe_metar({"cover": "CAVOK"}) == "Clear sky"
