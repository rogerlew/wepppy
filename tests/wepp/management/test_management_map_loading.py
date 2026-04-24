from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.wepp.management import ManagementMapLoadError, load_map

pytestmark = pytest.mark.unit


def test_load_map_reads_explicit_json_path(tmp_path: Path) -> None:
    map_path = tmp_path / "custom_map.json"
    map_payload = {
        "9": {
            "Key": 9,
            "Description": "Custom class",
            "ManagementFile": "custom.man",
            "ManagementDir": ".",
            "Color": [0, 0, 0, 255],
        }
    }
    map_path.write_text(json.dumps(map_payload), encoding="utf-8")

    mapping = load_map(str(map_path))
    assert "9" in mapping
    assert mapping["9"]["ManagementFile"] == "custom.man"
    assert Path(mapping["9"]["ManagementDir"]).resolve() == map_path.parent.resolve()


def test_load_map_rejects_missing_explicit_json_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing_map.json"

    with pytest.raises(ManagementMapLoadError) as exc_info:
        load_map(str(missing))

    assert exc_info.value.code == "management_map_missing"


def test_load_map_rejects_invalid_explicit_json_path(tmp_path: Path) -> None:
    map_path = tmp_path / "invalid_map.json"
    map_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ManagementMapLoadError) as exc_info:
        load_map(str(map_path))

    assert exc_info.value.code == "management_map_invalid_json"


def test_load_map_rejects_invalid_record_shape(tmp_path: Path) -> None:
    map_path = tmp_path / "invalid_shape.json"
    map_path.write_text(json.dumps({"9": {"Description": "missing key"}}), encoding="utf-8")

    with pytest.raises(ManagementMapLoadError) as exc_info:
        load_map(str(map_path))

    assert exc_info.value.code == "management_map_invalid_shape"


def test_load_map_rejects_management_dir_escape(tmp_path: Path) -> None:
    map_path = tmp_path / "escape_map.json"
    map_payload = {
        "9": {
            "Key": 9,
            "Description": "Custom class",
            "ManagementFile": "custom.man",
            "ManagementDir": "../outside",
            "Color": [0, 0, 0, 255],
        }
    }
    map_path.write_text(json.dumps(map_payload), encoding="utf-8")

    with pytest.raises(ManagementMapLoadError) as exc_info:
        load_map(str(map_path))

    assert exc_info.value.code == "management_map_invalid_shape"
