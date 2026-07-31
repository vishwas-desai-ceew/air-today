import json

from ingestion import update_archive_json as uaj


def _point_at_tmp(monkeypatch, tmp_path):
    archive_json = tmp_path / "archive.json"
    archive_temp = tmp_path / "archive_temp.json"
    monkeypatch.setattr(uaj, "ARCHIVE_JSON", archive_json)
    monkeypatch.setattr(uaj, "ARCHIVE_TEMP", archive_temp)
    return archive_json, archive_temp


def test_no_temp_file_is_a_silent_no_op(tmp_path, monkeypatch):
    archive_json, archive_temp = _point_at_tmp(monkeypatch, tmp_path)

    uaj.update_archive_json()

    assert not archive_json.exists()


def test_merges_temp_into_fresh_archive(tmp_path, monkeypatch):
    archive_json, archive_temp = _point_at_tmp(monkeypatch, tmp_path)
    archive_temp.write_text(json.dumps({"2026-01-05": ["today's summary"]}))

    uaj.update_archive_json()

    assert json.loads(archive_json.read_text()) == {"2026-01-05": ["today's summary"]}


def test_merges_temp_into_existing_archive_without_dropping_old_entries(tmp_path, monkeypatch):
    archive_json, archive_temp = _point_at_tmp(monkeypatch, tmp_path)
    archive_json.write_text(json.dumps({"2026-01-01": ["yesterday's summary"]}))
    archive_temp.write_text(json.dumps({"2026-01-02": ["today's summary"]}))

    uaj.update_archive_json()

    merged = json.loads(archive_json.read_text())
    assert merged == {
        "2026-01-01": ["yesterday's summary"],
        "2026-01-02": ["today's summary"],
    }


def test_same_date_in_temp_overwrites_the_archive_entry(tmp_path, monkeypatch):
    archive_json, archive_temp = _point_at_tmp(monkeypatch, tmp_path)
    archive_json.write_text(json.dumps({"2026-01-02": ["stale summary"]}))
    archive_temp.write_text(json.dumps({"2026-01-02": ["corrected summary"]}))

    uaj.update_archive_json()

    merged = json.loads(archive_json.read_text())
    assert merged == {"2026-01-02": ["corrected summary"]}
