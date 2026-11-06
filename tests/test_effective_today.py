from datetime import date, datetime

from config.settings import IST, effective_today


def _csv(tmp_path, rows):
    p = tmp_path / "cpcb.csv"
    p.write_text("date,aqi,category,pollutant,stations,source\n" + "".join(f"{d},{a},,,,\n" for d, a in rows))
    return p


def test_before_cutoff_without_todays_bulletin_is_yesterday(tmp_path):
    p = _csv(tmp_path, [("2026-11-05", 369)])
    assert effective_today(IST.localize(datetime(2026, 11, 6, 16, 30)), p) == date(2026, 11, 5)


def test_before_cutoff_with_todays_bulletin_is_today(tmp_path):
    p = _csv(tmp_path, [("2026-11-05", 369), ("2026-11-06", 382)])
    assert effective_today(IST.localize(datetime(2026, 11, 6, 16, 30)), p) == date(2026, 11, 6)


def test_blank_aqi_does_not_count_as_published(tmp_path):
    p = _csv(tmp_path, [("2026-11-06", "")])
    assert effective_today(IST.localize(datetime(2026, 11, 6, 16, 30)), p) == date(2026, 11, 5)


def test_after_cutoff_is_today_even_without_bulletin(tmp_path):
    p = _csv(tmp_path, [])
    assert effective_today(IST.localize(datetime(2026, 11, 6, 18, 0)), p) == date(2026, 11, 6)


def test_missing_csv_falls_back_to_cutoff(tmp_path):
    assert effective_today(IST.localize(datetime(2026, 11, 6, 9, 0)), tmp_path / "none.csv") == date(2026, 11, 5)
