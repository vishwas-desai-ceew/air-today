"""The AQEWS home page redesign (Nov 2026): bulletin day cards and DSS source
apportionment. Fixture trimmed from the live page on 10 Nov 2026."""
from datetime import date
from pathlib import Path

import pytest

from ingestion import aqews

HTML = (Path(__file__).parent / "fixtures" / "aqews_home_cards_2026_11_10.html").read_text()
OLD_HOME = (Path(__file__).parent / "fixtures" / "aqews_home_bulletin_2026_11_06.html").read_text()


def test_cards_give_ventilation_index_mixing_depth_and_category():
    cards = aqews.extract_bulletin_cards(HTML)
    assert cards["issued"] == date(2026, 11, 9)
    parsed = aqews.cards_to_parsed(cards)
    assert parsed["ventilation_index"] == {
        date(2026, 11, 9): 3000, date(2026, 11, 10): 2700, date(2026, 11, 11): 9500, date(2026, 11, 12): 7000,
    }
    assert parsed["mixing_depth"][date(2026, 11, 10)] == 1850
    assert parsed["category"][date(2026, 11, 9)] == "Severe"


def test_card_details():
    first, second = aqews.extract_bulletin_cards(HTML)["days"][:2]
    assert (first["tmax_low"], first["tmax_high"], first["tmin_observed"]) == (28, 30, True)
    assert second["wind_direction"] == "E→NE→E" and second["wind_max_kmh"] == 10
    assert first["dispersion_unfavourable"] is True


def test_year_is_inferred_across_new_year():
    assert aqews._infer_date("Thu, 1 Jan", date(2026, 12, 31)) == date(2027, 1, 1)
    assert aqews._infer_date("Wed, 31 Dec", date(2027, 1, 1)) == date(2026, 12, 31)


def test_source_apportionment():
    sa = aqews.extract_source_apportionment(HTML, ref=date(2026, 11, 10))
    assert sa["date"] == "2026-11-08"
    assert (sa["local_percent"], sa["non_local_percent"]) == (37.0, 63.0)
    assert sa["sources"][0] == {"source": "Others", "percent": 20.6}
    assert round(sum(s["percent"] for s in sa["sources"]), 1) == 100.0


def test_old_page_has_no_cards_so_prose_parser_is_used():
    with pytest.raises(ValueError):
        aqews.extract_bulletin_cards(OLD_HOME)
    assert aqews.parse_bulletin(aqews.bulletin_text(OLD_HOME))["ventilation_index"]


def test_run_fails_loudly_when_no_forecast_is_found(monkeypatch, tmp_path):
    monkeypatch.setattr(aqews, "_fetch", lambda url: "<html><body>redesigned again</body></html>")
    monkeypatch.setattr(aqews, "extract_charts", lambda html: {})
    monkeypatch.setattr(aqews, "save_charts", lambda charts: None)
    with pytest.raises(RuntimeError, match="no forecast found"):
        aqews.run()


def test_delhi_prefixed_sources_add_up_to_the_local_share():
    # views/source_apportionment.py colours a source as local when its name starts
    # with "Delhi"; that only holds if those shares sum to AQEWS's own local share
    from views.source_apportionment import _is_local
    sa = aqews.extract_source_apportionment(HTML, ref=date(2026, 11, 10))
    local = sum(s["percent"] for s in sa["sources"] if _is_local(s["source"]))
    assert abs(local - sa["local_percent"]) < 1
