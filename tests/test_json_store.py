import json

from ingestion.json_store import read_json, write_json_atomic


def test_read_json_missing_file_returns_empty_dict(tmp_path):
    assert read_json(tmp_path / "does_not_exist.json") == {}


def test_read_json_missing_file_returns_custom_default(tmp_path):
    default = {"fallback": True}
    assert read_json(tmp_path / "does_not_exist.json", default=default) == default


def test_write_then_read_round_trips(tmp_path):
    path = tmp_path / "data.json"
    payload = {"2026-01-01": ["a", "b"], "count": 3}

    write_json_atomic(path, payload, indent=2)

    assert path.exists()
    assert read_json(path) == payload


def test_write_json_atomic_leaves_no_leftover_temp_file(tmp_path):
    path = tmp_path / "data.json"
    write_json_atomic(path, {"x": 1})

    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []


def test_write_json_atomic_overwrites_existing_file(tmp_path):
    path = tmp_path / "data.json"
    write_json_atomic(path, {"version": 1})
    write_json_atomic(path, {"version": 2})

    with open(path) as f:
        assert json.load(f) == {"version": 2}
