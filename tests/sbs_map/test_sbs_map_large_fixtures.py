import json
import os
from pathlib import Path

import pytest
from osgeo import gdal
import numpy as np

from wepppy.all_your_base import isint
from wepppy.all_your_base.geo import validate_srs
from wepppy.nodb.mods.baer import sbs_map as sbs_map_module
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check

pytestmark = [pytest.mark.integration, pytest.mark.slow]

if os.getenv("SBS_MAP_LARGE_FIXTURES") != "1":
    pytest.skip("Set SBS_MAP_LARGE_FIXTURES=1 to run large SBS map fixture tests.", allow_module_level=True)

DATA_DIR = Path(__file__).resolve().parent / "data"
EXPECTATIONS = json.loads((DATA_DIR / "sbs_map_fixtures.json").read_text(encoding="utf-8"))
DETAIL_EXPECTATIONS = json.loads((DATA_DIR / "sbs_map_large_expectations.json").read_text(encoding="utf-8"))
COLOR_MAP_PATH = Path(sbs_map_module.__file__).resolve().parent / "data" / "sbs_color_map.json"

COLOR_TO_SEVERITY = {
    (0, 100, 0): "unburned",
    (0, 0, 0): "unburned",
    (0, 115, 74): "unburned",
    (0, 158, 115): "unburned",
    (0, 175, 166): "unburned",
    (102, 204, 204): "low",
    (102, 205, 205): "low",
    (115, 255, 223): "low",
    (127, 255, 212): "low",
    (0, 255, 255): "low",
    (77, 230, 0): "low",
    (86, 180, 233): "low",
    (255, 255, 0): "mod",
    (255, 232, 32): "mod",
    (240, 228, 66): "mod",
    (255, 0, 0): "high",
    (204, 121, 167): "high",
}


def _summarize_python(path: str) -> dict:
    ds = gdal.Open(path)
    if ds is None:
        raise RuntimeError(f"Failed to open {path}")

    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    unique = np.unique(data)

    classes = []
    has_non_integer = False
    for value in unique:
        if isint(value):
            classes.append(int(value))
        else:
            has_non_integer = True
            classes.append(float(value))

    ct = band.GetRasterColorTable()
    has_ct = ct is not None
    color_table_severities = []
    color_table_valid = False

    if has_ct:
        severity_set = set()
        for idx in range(ct.GetCount()):
            entry = tuple(int(v) for v in ct.GetColorEntry(idx)[:3])
            severity = COLOR_TO_SEVERITY.get(entry)
            if severity:
                severity_set.add(severity)
        color_table_severities = sorted(severity_set)
        color_table_valid = any(sev in ("low", "mod", "high") for sev in severity_set)

    srs_valid = validate_srs(path)

    if not srs_valid:
        sanity_status = 1
        sanity_message = "Map contains an invalid projection. Try reprojecting to UTM."
    elif len(unique) > 256:
        sanity_status = 1
        sanity_message = "Map has more than 256 classes"
    elif has_non_integer:
        sanity_status = 1
        sanity_message = "Map has non-integer classes"
    elif has_ct:
        if color_table_valid:
            sanity_status = 0
            sanity_message = "Map has valid color table"
        else:
            sanity_status = 1
            sanity_message = "Map has no valid color table"
    else:
        sanity_status = 0
        sanity_message = "Map has valid classes"

    ds = None

    return {
        "filename": os.path.basename(path),
        "size_bytes": os.path.getsize(path),
        "srs_valid": bool(srs_valid),
        "class_count": int(len(unique)),
        "unique_classes": classes,
        "has_non_integer": bool(has_non_integer),
        "has_color_table": bool(has_ct),
        "color_table_severities": color_table_severities,
        "color_table_valid": bool(color_table_valid),
        "sanity_status": int(sanity_status),
        "sanity_message": sanity_message,
    }


def _summarize(path: str) -> dict:
    try:
        from wepppyo3 import sbs_map as rust_sbs_map

        summarize = getattr(rust_sbs_map, "summarize_sbs_raster", None)
        if callable(summarize):
            return summarize(path)
    except Exception:
        pass

    return _summarize_python(path)


def _get_rust_module():
    try:
        from wepppyo3 import sbs_map as rust_sbs_map
    except Exception:
        return None
    return rust_sbs_map


@pytest.fixture(scope="session")
def sbs_maps() -> dict[str, SoilBurnSeverityMap]:
    maps = {}
    for filename in EXPECTATIONS:
        fixture_path = DATA_DIR / filename
        maps[filename] = SoilBurnSeverityMap(str(fixture_path))
    return maps


@pytest.mark.parametrize("filename", sorted(EXPECTATIONS))
def test_large_fixture_summary_matches_expectations(filename: str) -> None:
    expected = EXPECTATIONS[filename]
    fixture_path = DATA_DIR / filename
    assert fixture_path.exists(), f"Missing fixture {fixture_path}"

    actual = _summarize(str(fixture_path))

    for key in (
        "sanity_status",
        "sanity_message",
        "has_color_table",
        "color_table_valid",
        "class_count",
        "has_non_integer",
        "srs_valid",
    ):
        assert actual[key] == expected[key]

    assert set(actual["unique_classes"]) == set(expected["unique_classes"])
    assert sorted(actual["color_table_severities"]) == expected["color_table_severities"]
    assert actual["size_bytes"] == expected["size_bytes"]


@pytest.mark.parametrize("filename", sorted(EXPECTATIONS))
def test_large_fixture_sanity_check_matches_expectations(filename: str) -> None:
    fixture_path = DATA_DIR / filename
    status, message = sbs_map_sanity_check(str(fixture_path))

    expected = EXPECTATIONS[filename]
    assert status == expected["sanity_status"]
    assert message == expected["sanity_message"]


@pytest.mark.parametrize("filename", sorted(DETAIL_EXPECTATIONS))
def test_large_fixture_sbs_map_metadata(filename: str, sbs_maps: dict[str, SoilBurnSeverityMap]) -> None:
    expected = DETAIL_EXPECTATIONS[filename]
    sbs = sbs_maps[filename]

    assert (sbs.ct is not None) == expected["ct_present"]
    assert sbs.breaks == expected["breaks"]
    assert bool(sbs.is256) == expected["is256"]
    assert sbs.classes == expected["classes"]
    assert sbs.nodata_vals == expected["nodata_vals"]

    color_map = sbs.color_map or {}
    actual_severities = sorted({sev for sev in color_map.values() if sev})
    assert actual_severities == expected["color_map_severities"]


@pytest.mark.parametrize("filename", sorted(DETAIL_EXPECTATIONS))
def test_large_fixture_class_map(filename: str, sbs_maps: dict[str, SoilBurnSeverityMap]) -> None:
    expected = DETAIL_EXPECTATIONS[filename]["class_map"]
    sbs = sbs_maps[filename]

    actual = [
        {"value": int(val), "severity": severity, "count": int(count)}
        for val, severity, count in sbs.class_map
    ]
    assert actual == expected


@pytest.mark.parametrize("filename", sorted(DETAIL_EXPECTATIONS))
def test_large_fixture_class_pixel_map(filename: str, sbs_maps: dict[str, SoilBurnSeverityMap]) -> None:
    expected = DETAIL_EXPECTATIONS[filename]["class_pixel_map"]
    sbs = sbs_maps[filename]

    assert sbs.class_pixel_map == expected


@pytest.mark.parametrize("filename", sorted(EXPECTATIONS))
def test_rust_read_color_table_matches_expectations(filename: str) -> None:
    rust = _get_rust_module()
    if rust is None or not callable(getattr(rust, "read_color_table", None)):
        pytest.skip("Rust read_color_table helper not available.")

    fixture_path = DATA_DIR / filename
    info = rust.read_color_table(str(fixture_path), color_map_path=str(COLOR_MAP_PATH))
    expected = EXPECTATIONS[filename]

    assert info["has_color_table"] == expected["has_color_table"]
    assert sorted(info["color_table_severities"]) == expected["color_table_severities"]

    if expected["has_color_table"]:
        assert info["class_index_map"] is not None
        for severity in ("unburned", "low", "mod", "high"):
            assert severity in info["class_index_map"]
    else:
        assert info["class_index_map"] is None


@pytest.mark.parametrize("filename", sorted(EXPECTATIONS))
def test_rust_summarize_color_table_matches_expectations(filename: str) -> None:
    rust = _get_rust_module()
    if rust is None or not callable(getattr(rust, "summarize_color_table", None)):
        pytest.skip("Rust summarize_color_table helper not available.")

    fixture_path = DATA_DIR / filename
    info = rust.summarize_color_table(str(fixture_path), color_map_path=str(COLOR_MAP_PATH))
    expected = EXPECTATIONS[filename]

    assert info["has_color_table"] == expected["has_color_table"]
    assert info["color_table_valid"] == expected["color_table_valid"]
    assert sorted(info["color_table_severities"]) == expected["color_table_severities"]

    if expected["has_color_table"]:
        severity_counts = info["severity_counts"]
        for severity in ("unburned", "low", "mod", "high"):
            assert severity in severity_counts
