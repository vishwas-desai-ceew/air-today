from config.reference import AQI_BANDS, HEALTH_ADVISORY, HEALTH_STEPS_ABOVE_200, SOURCES


def test_every_cpcb_category_has_advice():
    names = [n for n, _lo, _hi, _c in AQI_BANDS]
    assert set(HEALTH_ADVISORY) == set(names)
    for effects, general, vulnerable in HEALTH_ADVISORY.values():
        assert effects and general and vulnerable


def test_steps_and_source_present():
    assert len(HEALTH_STEPS_ABOVE_200) >= 3
    assert SOURCES["mohfw_air_advisory"][1].startswith("https://ncdc.mohfw.gov.in/")
