from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import wepppy.nodb.mods.rusle.c_integration as c_integration


pytestmark = pytest.mark.unit


def _write_raster(
    path: Path,
    data: np.ndarray,
    *,
    dtype: str,
    nodata: float | int | None,
    transform=None,
    crs: str = "EPSG:4326",
) -> None:
    if data.ndim == 2:
        count = 1
        height, width = data.shape
        writable = data[np.newaxis, ...]
    else:
        count, height, width = data.shape
        writable = data

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": count,
        "dtype": dtype,
        "crs": crs,
        "transform": transform or from_origin(0.0, float(height), 1.0, 1.0),
        "nodata": nodata,
    }

    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(writable.astype(dtype))


def _read_single_band(path: str) -> tuple[np.ndarray, float | int | None]:
    with rasterio.open(path) as dataset:
        return dataset.read(1), dataset.nodata


def _write_default_rap_dataset(path: Path, *, bare_ground: np.ndarray, invalid_band_mask: np.ndarray | None = None) -> None:
    shape = bare_ground.shape
    cover = np.full(shape, 20.0, dtype=np.float32)
    rap = np.stack(
        [
            cover,  # annual_forb_and_grass
            bare_ground.astype(np.float32),
            cover,  # litter
            cover,  # perennial_forb_and_grass
            cover,  # shrub
            cover,  # tree
        ]
    )

    if invalid_band_mask is not None:
        rap[2][invalid_band_mask] = 65535.0

    _write_raster(path, rap, dtype="float32", nodata=65535.0)


def _write_lookup_without_agriculture(path: Path) -> None:
    src = Path(c_integration.DEFAULT_LOOKUP_PATH)
    path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _write_disturbed_mapping(path: Path, mapping: dict[int, dict[str, object]]) -> None:
    serializable = {str(key): value for key, value in mapping.items()}
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8")


def test_run_rusle_c_factor_observed_rap_writes_artifacts_manifest_and_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[0.0, 25.0], [100.0, 110.0]], dtype=np.float32),
    )

    catalog_updates: list[str] = []
    monkeypatch.setattr(c_integration, "update_catalog_entry", lambda _wd, relpath: catalog_updates.append(relpath))

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        rap=str(rap_path),
    )

    c_data, c_nodata = _read_single_band(result.c)
    fg_data, fg_nodata = _read_single_band(result.fg or "")

    assert c_nodata == -9999.0
    assert fg_nodata == -9999.0

    valid_c = np.where(c_data == c_nodata, np.nan, c_data)
    valid_fg = np.where(fg_data == fg_nodata, np.nan, fg_data)
    expected_fg = np.asarray([[100.0, 75.0], [0.0, 0.0]])
    expected_c = np.exp(-0.04 * expected_fg)

    assert np.allclose(valid_fg, expected_fg)
    assert np.allclose(valid_c, expected_c)

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)

    c_manifest = manifest["c"]
    assert c_manifest["mode"] == "observed_rap"
    assert c_manifest["formula"]["fg"] == "clamp(100 - bare_ground_pct, 0, 100)"
    assert c_manifest["neutral_terms"]["canopy"] == pytest.approx(1.0)
    assert c_manifest["rap_band_indices"]["bare_ground"] == 2

    assert "rusle/c.tif" in catalog_updates
    assert "rusle/c_fg.tif" in catalog_updates
    assert "rusle/manifest.json" in catalog_updates


def test_run_rusle_c_factor_observed_rap_masks_union_nodata_across_cover_bands(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    invalid_mask = np.asarray([[False, True], [False, False]])
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[10.0, 10.0], [10.0, 10.0]], dtype=np.float32),
        invalid_band_mask=invalid_mask,
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        rap=str(rap_path),
    )

    c_data, c_nodata = _read_single_band(result.c)
    fg_data, fg_nodata = _read_single_band(result.fg or "")

    assert c_data[0, 1] == c_nodata
    assert fg_data[0, 1] == fg_nodata
    assert c_data[0, 0] != c_nodata


def test_run_rusle_c_factor_scenario_sbs_writes_disturbed_class_alignment_and_lookup_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    sbs_path = tmp_path / "sbs_4class_input.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(
        dem_path,
        np.ones((4, 4), dtype=np.float32),
        dtype="float32",
        nodata=-9999.0,
        transform=from_origin(0.0, 4.0, 1.0, 1.0),
    )
    _write_raster(
        landuse_path,
        np.asarray([[44, 52], [72, 31]], dtype=np.uint8),
        dtype="uint8",
        nodata=0,
        transform=from_origin(0.0, 4.0, 2.0, 2.0),
    )
    _write_raster(
        sbs_path,
        np.asarray([[2, 3], [1, 0]], dtype=np.uint8),
        dtype="uint8",
        nodata=255,
        transform=from_origin(0.0, 4.0, 2.0, 2.0),
    )
    _write_disturbed_mapping(
        mapping_path,
        {
            31: {"DisturbedClass": "bare"},
            44: {"DisturbedClass": "young forest"},
            52: {"DisturbedClass": "shrub"},
            72: {"DisturbedClass": "tall grass"},
        },
    )

    catalog_updates: list[str] = []
    monkeypatch.setattr(c_integration, "update_catalog_entry", lambda _wd, relpath: catalog_updates.append(relpath))

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=str(sbs_path),
        sbs_is_4class=True,
        disturbed_mapping_path=str(mapping_path),
    )

    disturbed_data, disturbed_nodata = _read_single_band(result.disturbed_class or "")
    sbs_data, sbs_nodata = _read_single_band(result.sbs_4class or "")
    c_data, c_nodata = _read_single_band(result.c)

    assert disturbed_nodata == 0
    assert sbs_nodata == 255
    assert disturbed_data.shape == (4, 4)
    assert sbs_data.shape == (4, 4)

    forest_code = 1
    shrub_code = 2
    tall_grass_code = 3
    bare_code = 4

    assert np.all(disturbed_data[:2, :2] == forest_code)
    assert np.all(disturbed_data[:2, 2:] == shrub_code)
    assert np.all(disturbed_data[2:, :2] == tall_grass_code)
    assert np.all(disturbed_data[2:, 2:] == bare_code)

    valid_c = np.where(c_data == c_nodata, np.nan, c_data)
    assert np.allclose(valid_c[:2, :2], 0.09071795328941253)
    assert np.allclose(valid_c[:2, 2:], 0.30119421191220214)
    assert np.allclose(valid_c[2:, :2], 0.09071795328941253)
    assert np.allclose(valid_c[2:, 2:], 1.0)

    with open(result.lookup_copy or "", "r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert any(row["disturbed_class"] == "forest" and row["sbs_class"] == "moderate" for row in rows)

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    c_manifest = manifest["c"]
    assert c_manifest["mode"] == "scenario_sbs"
    assert c_manifest["disturbed_class_codes"]["forest"] == forest_code
    assert any(item["disturbed_class"] == "forest" and item["sbs_class"] == "moderate" for item in c_manifest["lookup_keys_used"])

    assert "rusle/c.tif" in catalog_updates
    assert "rusle/disturbed_class.tif" in catalog_updates
    assert "rusle/sbs_4class.tif" in catalog_updates
    assert "rusle/c_lookup_used.csv" in catalog_updates
    assert "rusle/manifest.json" in catalog_updates


def test_scenario_sbs_masks_non_burnable_nlcd_classes(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    sbs_path = tmp_path / "sbs.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(
        landuse_path,
        np.asarray([[11, 21], [90, 12]], dtype=np.uint8),
        dtype="uint8",
        nodata=0,
    )
    _write_raster(sbs_path, np.asarray([[3, 3], [3, 3]], dtype=np.uint8), dtype="uint8", nodata=255)
    _write_disturbed_mapping(
        mapping_path,
        {
            11: {"DisturbedClass": ""},
            12: {"DisturbedClass": ""},
            21: {"DisturbedClass": "developed low intensity"},
            90: {"DisturbedClass": "short grass"},
        },
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=str(sbs_path),
        sbs_is_4class=True,
        disturbed_mapping_path=str(mapping_path),
    )

    c_data, c_nodata = _read_single_band(result.c)
    assert np.all(c_data == c_nodata)


def test_scenario_sbs_requires_explicit_lookup_row_for_agriculture(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    sbs_path = tmp_path / "sbs.tif"
    mapping_path = tmp_path / "disturbed.json"
    lookup_path = tmp_path / "lookup.csv"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[81]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_raster(sbs_path, np.asarray([[0]], dtype=np.uint8), dtype="uint8", nodata=255)
    _write_disturbed_mapping(mapping_path, {81: {"DisturbedClass": "agriculture crops"}})
    _write_lookup_without_agriculture(lookup_path)

    with pytest.raises(ValueError, match="agriculture_crops"):
        c_integration.run_rusle_c_factor(
            wd=str(tmp_path),
            dem=str(dem_path),
            c_mode="scenario_sbs",
            landuse=str(landuse_path),
            sbs=str(sbs_path),
            sbs_is_4class=True,
            disturbed_mapping_path=str(mapping_path),
            lookup_path=str(lookup_path),
        )


def test_scenario_sbs_uses_unburned_short_grass_row_even_when_sbs_is_burned(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    sbs_path = tmp_path / "sbs.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[73]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_raster(sbs_path, np.asarray([[3]], dtype=np.uint8), dtype="uint8", nodata=255)
    _write_disturbed_mapping(mapping_path, {73: {"DisturbedClass": "short grass"}})

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=str(sbs_path),
        sbs_is_4class=True,
        disturbed_mapping_path=str(mapping_path),
    )

    c_data, c_nodata = _read_single_band(result.c)
    value = float(c_data[0, 0])
    assert value != c_nodata
    assert value == pytest.approx(0.20189651799465538)
