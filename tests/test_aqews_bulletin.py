from datetime import date
from pathlib import Path

from ingestion import aqews

TEXT = (Path(__file__).parent / "fixtures" / "aqews_bulletin_2026_10_25.txt").read_text()


def test_ventilation_index_and_mixing_depth():
    parsed = aqews.parse_bulletin(TEXT)
    assert parsed["ventilation_index"] == {
        date(2026, 10, 25): 4800, date(2026, 10, 26): 11000,
        date(2026, 10, 27): 6000, date(2026, 10, 28): 3800,
    }
    assert parsed["mixing_depth"][date(2026, 10, 25)] == 2150


def test_category_ranges_are_expanded():
    parsed = aqews.parse_bulletin(TEXT)
    assert parsed["category"] == {
        date(2026, 10, 25): "Moderate", date(2026, 10, 26): "Poor",
        date(2026, 10, 27): "Poor", date(2026, 10, 28): "Poor",
    }
    assert parsed["outlook"] == "Poor to Moderate over the following 6 days"


def test_dates_with_stray_spaces():
    # the live page sometimes renders "26.10.202 6"
    parsed = aqews.parse_bulletin(
        "The ventilation index is likely to be 5000 m 2 /s on 26.10.202 6 over Delhi."
    )
    assert parsed["ventilation_index"] == {date(2026, 10, 26): 5000}


def test_missing_sections_return_empty():
    parsed = aqews.parse_bulletin("Nothing useful here.")
    assert parsed == {"mixing_depth": {}, "ventilation_index": {}, "category": {}, "outlook": None}
