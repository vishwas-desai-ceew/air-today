"""One-off: convert the winter GRAP orders archive (Excel) into static JSON.

The 2025-26 GRAP orders are a closed archive, so the dashboard reads the JSON
this script writes rather than parsing the workbook on every page load (and
the app venv doesn't need openpyxl).

    python ingestion/convert_grap_orders.py        # needs openpyxl (requirements-dev.txt)

Output (data/grap_orders_2025_26.json):
    {"season": "2025-26", "source": "<xlsx name>",
     "orders": {"YYYY-MM-DD": [{sr_no, date_label, stage, aqi_category,
                                aqi_trigger, key_decision, reason}, ...]}}

Several orders can share a date (e.g. 11-Nov-2025 has a clarification and an
invocation order), so each date maps to a list, kept in the sheet's order.
Cell text is copied verbatim; only surrounding whitespace is stripped.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "AS - Winter GRAP Orders 01Oct2026.xlsx"
OUT = ROOT / "data" / "grap_orders_2025_26.json"

COLUMNS = {
    "Sr no.": "sr_no",
    "Order Date": "date_label",
    "GRAP Stage": "stage",
    "AQI Category": "aqi_category",
    "AQI / Trigger": "aqi_trigger",
    "Key Decision": "key_decision",
    "Reason": "reason",
}


def parse_order_date(value):
    """Returns (date, note). Dates are real Excel dates, or text such as
    '11-Nov-2025 (Clarification order)' where the bracket is a note."""
    if isinstance(value, datetime):
        return value.date(), ""
    text = str(value).strip()
    m = re.match(r"(\d{1,2}-[A-Za-z]{3}-\d{4})\s*(?:\((.*)\))?", text)
    if not m:
        raise ValueError(f"Unrecognised order date: {text!r}")
    return datetime.strptime(m.group(1), "%d-%b-%Y").date(), (m.group(2) or "").strip()


def convert(src=SRC):
    ws = openpyxl.load_workbook(src, read_only=True, data_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else None for c in next(rows)]
    idx = {key: header.index(col) for col, key in COLUMNS.items()}

    orders = {}
    for row in rows:
        if row[idx["date_label"]] is None:
            continue
        day, note = parse_order_date(row[idx["date_label"]])
        rec = {key: ("" if row[i] is None else str(row[i]).strip()) for key, i in idx.items()}
        rec["sr_no"] = int(float(rec["sr_no"])) if rec["sr_no"] else None
        rec["date_label"] = note  # the bracketed note, if any; the date is the key
        orders.setdefault(day.isoformat(), []).append(rec)

    return {"season": "2025-26", "source": Path(src).name, "orders": dict(sorted(orders.items()))}


if __name__ == "__main__":
    payload = convert()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = sum(len(v) for v in payload["orders"].values())
    print(f"Wrote {n} orders on {len(payload['orders'])} dates -> {OUT.relative_to(ROOT)}")
