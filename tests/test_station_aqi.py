from pathlib import Path

import pytest

from ingestion import aqews
from views.source_apportionment import pie_slices
from views.station_aqi import cards_html, split_name, summary_html

TICKER = (Path(__file__).parent / "fixtures" / "aqews_station_ticker_2026_11_18.html").read_text()


def test_extract_station_aqi_reads_every_card():
    feed = aqews.extract_station_aqi(TICKER)
    assert len(feed["stations"]) == 4
    first = feed["stations"][0]
    assert first == {"station": "Alipur, Delhi - DPCC", "aqi": 259, "category": "Poor", "colour": "#e87522",
                     "pollutant": "PM2.5", "observed_at": "2026-11-18T23:00"}
    assert feed["observed_at"] == "2026-11-18T23:00"


def test_extract_station_aqi_fails_loudly_without_the_ticker():
    with pytest.raises(ValueError):
        aqews.extract_station_aqi("<html><body>no ticker</body></html>")


@pytest.mark.parametrize("name, expected", [
    ("Alipur, Delhi - DPCC", ("Alipur", "DPCC")),
    ("Tikri Kalan, Delhi-DPCC", ("Tikri Kalan", "DPCC")),
    ("IGI Airport (T3), Delhi - IITM", ("IGI Airport (T3)", "IITM")),
    ("Mandir Marg, New Delhi - DPCC", ("Mandir Marg", "DPCC")),
    ("North Campus, DU, Delhi - IMD", ("North Campus, DU", "IMD")),
])
def test_split_name(name, expected):
    assert split_name(name) == expected


def test_station_cards_and_summary_render():
    stations = aqews.extract_station_aqi(TICKER)["stations"]
    html = cards_html(stations)
    assert html.count("class='stn-card'") == 4 and "Alipur" in html
    assert "Highest <b>" in summary_html(stations)


def test_pie_keeps_grouped_remainder_on_its_side_of_the_split():
    sources = ([{"source": f"District {i}", "percent": 10.0 - i * 0.5} for i in range(8)]
               + [{"source": "Delhi Transport", "percent": 9.0}, {"source": "Delhi Dust", "percent": 1.0},
                  {"source": "Delhi Waste", "percent": 0.5}, {"source": "Others", "percent": 5.0}])
    sources.sort(key=lambda s: -s["percent"])
    slices = pie_slices(sources)
    by_name = {n: (v, local) for n, v, _c, local in slices}
    assert by_name["Other Delhi sources"] == (1.5, True)
    assert by_name["Other sources outside Delhi"][1] is False
    assert round(sum(v for _n, v, _c, _l in slices), 1) == round(sum(s["percent"] for s in sources), 1)
