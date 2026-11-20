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


def test_disturbed_esdac_name_selects_its_catalog_without_changing_existing_names():
    plain = load_map("esdac")
    selected = load_map("eu-esdac-disturbed")
    assert selected["22"]["DisturbedClass"] == "forest"
    assert selected["22"]["ManagementFile"] == plain["22"]["ManagementFile"]
    assert "DisturbedClass" not in plain["22"]
    assert load_map("legacy-esdac-mapping") == plain
    assert load_map("eu-disturbed")["25"]["Description"] == "Mixed forest"


def test_explicit_disturbed_esdac_filename_uses_the_given_file(tmp_path):
    explicit = tmp_path / "eu-esdac-disturbed.json"
    explicit.write_text(json.dumps({"1": {"Key": 1, "Description": "Custom"}}), encoding="utf-8")
    assert load_map(str(explicit))["1"]["Description"] == "Custom"


@pytest.mark.parametrize("map_name", ["eu-esdac-disturbed", "eu-disturbed"])
def test_european_grass_fire_classes_match_default_disturbed_templates(map_name):
    from wepppy.nodb.mods.disturbed import build_disturbed_key_lookup

    default = load_map("disturbed")
    selected = load_map(map_name)
    lookup = build_disturbed_key_lookup(selected)
    for key in ("129", "130", "131", "132"):
        row = selected[key]
        assert row["DisturbedClass"] == default[key]["DisturbedClass"]
        assert row["ManagementFile"] == default[key]["ManagementFile"]
        assert row["Description"] == default[key]["Description"]
        assert lookup[row["DisturbedClass"].replace(" ", "_")] == key
