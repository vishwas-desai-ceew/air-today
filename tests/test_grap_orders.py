"""GRAP order pipeline: title parsing, classification, cumulative stages."""
from datetime import date

from ingestion.grap_orders import apply_order, build, classify, headline, season_of, title_date


def test_title_dates():
    assert title_date("Order dated 02.11. 2026 - Implementation of actions") == date(2026, 11, 2)
    assert title_date("Order dt. 18.01.2024 - Revocation of Actions") == date(2024, 1, 18)
    assert title_date("Invocation of actions under Stage-III of extant schedule") is None


def test_classify_caqm_titles():
    assert classify("Order dated 21.10.2026 - Implementation of actions under Stage-I (Poor Air Quality, "
                    "AQI: 201-300) of extant schedule of GRAP in Delhi-NCR") == ("invoke", [1])
    assert classify("Order dated 26.11.2025 - Revocation of actions under Stage-III (Severe Air Quality) of GRAP "
                    "and intensifying actions under Stage-II") == ("revoke", [3])
    assert classify("Order dated 05.12.2024 - Revocation of actions under Stage IV (Severe Air Quality) and "
                    "Stage III (Severe Air Quality)") == ("revoke", [3, 4])
    assert classify("Order dated 15.01.2025 - Implementation of Actions under Stage-III (Severe Air Quality and "
                    "Stage - IV (Severe Plus Air Quality)") == ("invoke", [3, 4])
    assert classify("Clarification dated 28.11.2024 - Implementation of Actions under stage-III & IV")[0] == "other"
    corr = "Order dated 04.12.2022 for Implementation of actions under Stage-III of GRAP in Delhi- Corrigendum"
    assert classify(corr) == ("other", [])
    assert headline("other", [], corr) == "Corrigendum to the Stage III order"
    assert classify("Order dated 21.11.2025- Implementation of the Graded Response Action Plan (GRAP)") == ("other", [])


def test_classify_team_sheet_text():
    assert classify("Stage II invoked (in addition to Stage I already in force)") == ("invoke", [2])
    assert classify("Stage III revoked; Stages I and II remain invoked") == ("revoke", [3])
    assert classify("Stage III, Action Point 6 modified (clarification; no new stage invoked)") == ("other", [])


def test_cumulative_stages():
    level = 0
    for action, stages in [("invoke", [1]), ("invoke", [3]), ("invoke", [4]), ("revoke", [4]), ("revoke", [3])]:
        level = apply_order(level, action, stages)
    assert level == 2  # invoking III puts I-III in force; revoking IV then III leaves I-II
    assert apply_order(4, "revoke", [3, 4]) == 2
    assert apply_order(2, "other", []) == 2


def test_build_seasons_and_carry_in():
    listing = [
        {"documentId": 1, "title": "Order dated 19.05.2026 - Implementation of actions under Stage-I (Poor)"},
        {"documentId": 2, "title": "Order dated 21.10.2026 - Implementation of actions under Stage-I (Poor)"},
        {"documentId": 3, "title": "Order dated 02.11.2026 - Implementation of actions under Stage-II (Very Poor)"},
    ]
    out = build(listing, session=None, seasons=["2026-27"])
    p = out["2026-27"]
    assert p["schema_version"] == 2 and p["stage_at_start"] == 1  # Stage I from May never revoked
    assert [o["id"] for o in p["orders"]] == ["caqm-2", "caqm-3"]
    assert p["orders"][1]["headline"] == "Stage II invoked"
    assert season_of(date(2026, 3, 1)) == "2025-26" and season_of(date(2026, 10, 1)) == "2026-27"
    assert headline("other", [], "Order dated 30.10.2026- Implementation of precautionary measures") \
        .startswith("Implementation of precautionary measures")
