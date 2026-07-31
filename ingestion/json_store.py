import json
from pathlib import Path


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return {} if default is None else default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path, data, **dump_kwargs):
    """Writes via a temp file + rename so a crash mid-write can't corrupt the target file."""
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, **dump_kwargs)
    tmp_path.replace(path)
