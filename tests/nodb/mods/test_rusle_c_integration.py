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
    with src.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fieldnames = list(rows[0].keys()) if rows else []

    filtered = [row for row in rows if row.get("disturbed_class") != "agriculture_crops"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)


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
    monkeypatch.setattr(c_integration, "request_catalog_refresh", lambda _wd, relpath: catalog_updates.append(relpath))

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
    assert c_manifest["formula"]["fg"] == "100 * (1 - bare_rap_0_1 * (1 - r_bare))"
    assert c_manifest["formula"]["bare_rap_0_1"] == "clamp(bare_ground_pct / 100, 0, 1)"
    assert c_manifest["formula"]["r_bare"] == "clamp(rock_fraction_of_rap_bare, 0, 1)"
    assert c_manifest["neutral_terms"]["canopy"] == pytest.approx(1.0)
    assert c_manifest["rap_band_indices"]["bare_ground"] == 2
    assert c_manifest["rock_fraction_of_rap_bare"]["requested"] == "auto"
    assert c_manifest["rock_fraction_of_rap_bare"]["source"] == "auto:fallback_0"
    assert c_manifest["rock_fraction_of_rap_bare"]["effective"] == pytest.approx(0.0)

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


def test_run_rusle_c_factor_observed_rap_uses_user_rock_fraction_partition(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[50.0, 50.0], [50.0, 50.0]], dtype=np.float32),
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        rap=str(rap_path),
        rock_fraction_of_rap_bare=0.5,
    )

    fg_data, fg_nodata = _read_single_band(result.fg or "")
    valid_fg = np.where(fg_data == fg_nodata, np.nan, fg_data)
    assert np.allclose(valid_fg, 75.0)

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_rap_bare"]
    assert rock_meta["requested"] == pytest.approx(0.5)
    assert rock_meta["effective"] == pytest.approx(0.5)
    assert rock_meta["source"] == "user"


def test_run_rusle_c_factor_observed_rap_auto_prefers_cosurffrags_over_cfvo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[50.0, 50.0], [50.0, 50.0]], dtype=np.float32),
    )

    monkeypatch.setattr(
        c_integration,
        "_load_cosurffrags_surface_proxy_from_soils_parquet",
        lambda wd: (
            0.2,
            {
                "status": "available",
                "source_kind": "soils_parquet_cosurffrags",
                "column": "cosurffrags_cover_pct",
                "cover_pct": 20.0,
            },
        ),
    )

    cfvo_calls = {"count": 0}

    def _unexpected_cfvo(**kwargs):
        cfvo_calls["count"] += 1
        return 0.9, {"status": "available"}

    monkeypatch.setattr(c_integration, "_load_cfvo_surface_proxy_from_raster", _unexpected_cfvo)

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        rap=str(rap_path),
        rock_fraction_of_rap_bare="auto",
    )

    fg_data, fg_nodata = _read_single_band(result.fg or "")
    valid_fg = np.where(fg_data == fg_nodata, np.nan, fg_data)
    assert np.allclose(valid_fg, 70.0)
    assert cfvo_calls["count"] == 0

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_rap_bare"]
    assert rock_meta["source"] == "auto:cosurffrags"
    assert rock_meta["surface_rock_cover_proxy_0_1"] == pytest.approx(0.2)
    assert rock_meta["bare_rap_mean_0_1"] == pytest.approx(0.5)
    assert rock_meta["effective"] == pytest.approx(0.4)


def test_run_rusle_c_factor_observed_rap_rejects_invalid_rock_fraction(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[50.0, 50.0], [50.0, 50.0]], dtype=np.float32),
    )

    with pytest.raises(ValueError, match="rock_fraction_of_rap_bare"):
        c_integration.run_rusle_c_factor(
            wd=str(tmp_path),
            dem=str(dem_path),
            c_mode="observed_rap",
            rap=str(rap_path),
            rock_fraction_of_rap_bare="not-a-number",
        )


def test_run_rusle_c_factor_scenario_sbs_rejects_invalid_rock_fraction(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[52]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_disturbed_mapping(mapping_path, {52: {"DisturbedClass": "shrub"}})

    with pytest.raises(ValueError, match="rock_fraction_of_sbs_bare"):
        c_integration.run_rusle_c_factor(
            wd=str(tmp_path),
            dem=str(dem_path),
            c_mode="scenario_sbs",
            landuse=str(landuse_path),
            sbs=None,
            disturbed_mapping_path=str(mapping_path),
            rock_fraction_of_sbs_bare="not-a-number",
        )


def test_run_rusle_c_factor_observed_rap_auto_falls_back_to_cfvo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[50.0, 50.0], [50.0, 50.0]], dtype=np.float32),
    )

    monkeypatch.setattr(
        c_integration,
        "_load_cosurffrags_surface_proxy_from_soils_parquet",
        lambda wd: (None, {"status": "unavailable", "reason": "missing_cosurffrags_columns"}),
    )
    monkeypatch.setattr(
        c_integration,
        "_load_cfvo_surface_proxy_from_raster",
        lambda **kwargs: (
            0.25,
            {
                "status": "available",
                "source_kind": "cfvo_top_horizon",
                "cfvo_0_5cm_volpct": 25.0,
            },
        ),
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        rap=str(rap_path),
        rock_fraction_of_rap_bare="auto",
    )

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_rap_bare"]
    assert rock_meta["source"] == "auto:cfvo"
    assert rock_meta["surface_rock_cover_proxy_0_1"] == pytest.approx(0.25)
    assert rock_meta["effective"] == pytest.approx(0.5)


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
    monkeypatch.setattr(c_integration, "request_catalog_refresh", lambda _wd, relpath: catalog_updates.append(relpath))

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
    assert c_manifest["rock_fraction_of_sbs_bare"]["source"] == "auto:fallback_0"
    assert c_manifest["rock_fraction_of_sbs_bare"]["effective"] == pytest.approx(0.0)
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


def test_scenario_sbs_default_lookup_supports_agriculture_unburned(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    sbs_path = tmp_path / "sbs.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[81]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_raster(sbs_path, np.asarray([[0]], dtype=np.uint8), dtype="uint8", nodata=255)
    _write_disturbed_mapping(mapping_path, {81: {"DisturbedClass": "agriculture crops"}})

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
    assert value == pytest.approx(0.02732372244729257)


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


def test_scenario_sbs_without_sbs_uses_unburned_and_does_not_write_sbs_artifact(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[52]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_disturbed_mapping(mapping_path, {52: {"DisturbedClass": "shrub"}})

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=None,
        disturbed_mapping_path=str(mapping_path),
    )

    assert result.sbs_4class is None
    assert not (tmp_path / "rusle" / "sbs_4class.tif").exists()

    c_data, c_nodata = _read_single_band(result.c)
    value = float(c_data[0, 0])
    assert value != c_nodata
    assert value == pytest.approx(0.02732372244729257)

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["c"]["sbs_input_mode"] == "missing_use_unburned"


def test_scenario_sbs_uses_user_rock_fraction_partition(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[52]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_disturbed_mapping(mapping_path, {52: {"DisturbedClass": "shrub"}})

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=None,
        disturbed_mapping_path=str(mapping_path),
        rock_fraction_of_sbs_bare=0.5,
    )

    c_data, c_nodata = _read_single_band(result.c)
    value = float(c_data[0, 0])
    assert value != c_nodata
    assert value == pytest.approx(np.exp(-0.04 * 95.0))

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_sbs_bare"]
    assert rock_meta["requested"] == pytest.approx(0.5)
    assert rock_meta["effective"] == pytest.approx(0.5)
    assert rock_meta["source"] == "user"


def test_scenario_sbs_auto_prefers_cosurffrags_over_cfvo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[52]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_disturbed_mapping(mapping_path, {52: {"DisturbedClass": "shrub"}})

    monkeypatch.setattr(
        c_integration,
        "_load_cosurffrags_surface_proxy_from_soils_parquet",
        lambda wd: (
            0.02,
            {
                "status": "available",
                "source_kind": "soils_parquet_cosurffrags",
                "column": "cosurffrags_cover_pct",
                "cover_pct": 2.0,
            },
        ),
    )

    cfvo_calls = {"count": 0}

    def _unexpected_cfvo(**kwargs):
        cfvo_calls["count"] += 1
        return 0.4, {"status": "available"}

    monkeypatch.setattr(c_integration, "_load_cfvo_surface_proxy_from_raster", _unexpected_cfvo)

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=None,
        disturbed_mapping_path=str(mapping_path),
        rock_fraction_of_sbs_bare="auto",
    )

    assert cfvo_calls["count"] == 0

    c_data, c_nodata = _read_single_band(result.c)
    value = float(c_data[0, 0])
    assert value != c_nodata
    assert value == pytest.approx(np.exp(-0.04 * 92.0))

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_sbs_bare"]
    assert rock_meta["source"] == "auto:cosurffrags"
    assert rock_meta["surface_rock_cover_proxy_0_1"] == pytest.approx(0.02)
    assert rock_meta["bare_lookup_mean_0_1"] == pytest.approx(0.1)
    assert rock_meta["effective"] == pytest.approx(0.2)


def test_scenario_sbs_auto_falls_back_to_cfvo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem_path = tmp_path / "dem.tif"
    landuse_path = tmp_path / "landuse.tif"
    mapping_path = tmp_path / "disturbed.json"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_raster(landuse_path, np.asarray([[52]], dtype=np.uint8), dtype="uint8", nodata=0)
    _write_disturbed_mapping(mapping_path, {52: {"DisturbedClass": "shrub"}})

    monkeypatch.setattr(
        c_integration,
        "_load_cosurffrags_surface_proxy_from_soils_parquet",
        lambda wd: (None, {"status": "unavailable", "reason": "missing_cosurffrags_columns"}),
    )
    monkeypatch.setattr(
        c_integration,
        "_load_cfvo_surface_proxy_from_raster",
        lambda **kwargs: (
            0.03,
            {
                "status": "available",
                "source_kind": "cfvo_top_horizon",
                "cfvo_0_5cm_volpct": 3.0,
            },
        ),
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="scenario_sbs",
        landuse=str(landuse_path),
        sbs=None,
        disturbed_mapping_path=str(mapping_path),
        rock_fraction_of_sbs_bare="auto",
    )

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    rock_meta = manifest["c"]["rock_fraction_of_sbs_bare"]
    assert rock_meta["source"] == "auto:cfvo"
    assert rock_meta["surface_rock_cover_proxy_0_1"] == pytest.approx(0.03)
    assert rock_meta["effective"] == pytest.approx(0.3)


def test_observed_rap_supports_mode_specific_output_filename(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    rap_path = tmp_path / "rap.tif"

    _write_raster(dem_path, np.ones((1, 1), dtype=np.float32), dtype="float32", nodata=-9999.0)
    _write_default_rap_dataset(
        rap_path,
        bare_ground=np.asarray([[25.0]], dtype=np.float32),
    )

    result = c_integration.run_rusle_c_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        c_mode="observed_rap",
        c_output_filename="c_observed_rap.tif",
        rap=str(rap_path),
    )

    assert result.c.endswith("rusle/c_observed_rap.tif")
    assert Path(result.c).exists()


@pytest.mark.parametrize('c_mode', ['observed_rap', 'scenario_sbs'])
@pytest.mark.parametrize('source_path', ['soils/cfvo_0-5cm_Q0.5.tif', 'polaris/cfvo_mean_0_5.tif'])
@pytest.mark.parametrize('stored_cfvo', [0.0, 20.0, 100.0, 101.0, 800.0])
def test_soilgrids_cover_units_reach_rasters_and_manifest(
    tmp_path: Path, c_mode: str, source_path: str, stored_cfvo: float,
) -> None:
    """Exercise real raster alignment, auto resolution, C writer and manifest."""
    dem = tmp_path / 'dem.tif'
    _write_raster(dem, np.ones((1, 2)), dtype='float32', nodata=-9999.0)
    cfvo = tmp_path / source_path
    cfvo.parent.mkdir()
    _write_raster(cfvo, np.array([[stored_cfvo, -9999.0]]), dtype='float32', nodata=-9999.0)
    kwargs = {}
    if c_mode == 'observed_rap':
        rap = tmp_path / 'rap.tif'
        _write_default_rap_dataset(rap, bare_ground=np.array([[50.0, 50.0]]))
        kwargs['rap'] = str(rap)
        bare = 0.5
        key = 'rock_fraction_of_rap_bare'
    else:
        landuse = tmp_path / 'landuse.tif'
        mapping = tmp_path / 'disturbed.json'
        _write_raster(landuse, np.array([[52, 52]]), dtype='uint8', nodata=0)
        _write_disturbed_mapping(mapping, {52: {'DisturbedClass': 'shrub'}})
        kwargs.update(landuse=str(landuse), disturbed_mapping_path=str(mapping))
        bare = 0.1  # Current unburned shrub lookup: ground cover 90%.
        key = 'rock_fraction_of_sbs_bare'
    result = c_integration.run_rusle_c_factor(str(tmp_path), dem=str(dem), c_mode=c_mode, **kwargs)
    manifest = json.loads(Path(result.manifest).read_text())
    rock = manifest['c'][key]
    expected_proxy = stored_cfvo / 1000.0
    assert rock['surface_rock_cover_proxy_0_1'] == pytest.approx(expected_proxy)
    assert rock['sources']['cfvo']['scale_divisor'] == 10.0
    expected_cover = 100 * (1 - bare * (1 - min(expected_proxy / bare, 1)))
    data, nodata = _read_single_band(result.c)
    assert np.all(data != nodata)
    assert np.allclose(data, np.exp(-0.04 * expected_cover))
    # All-nodata optional input must retain the existing fallback, not invent rock.
    _write_raster(cfvo, np.full((1, 2), -9999.0), dtype='float32', nodata=-9999.0)
    empty = c_integration.run_rusle_c_factor(str(tmp_path), dem=str(dem), c_mode=c_mode, **kwargs)
    empty_meta = json.loads(Path(empty.manifest).read_text())['c'][key]
    assert empty_meta['source'] == 'auto:fallback_0'
    assert empty_meta['effective'] == 0.0


def _write_surface_proxy_parquet(path: Path, rows, *, area=True, text=False) -> None:
    """Use the actual parquet reader boundary, including NULL and malformed fields."""
    import duckdb

    path.parent.mkdir(exist_ok=True)
    kind = 'VARCHAR' if text else 'DOUBLE'
    columns = f'cosurffrags_cover_pct {kind}' + (f', area {kind}' if area else '')
    with duckdb.connect() as con:
        con.execute(f'CREATE TABLE proxy ({columns})')
        if rows:
            con.executemany('INSERT INTO proxy VALUES (' + ','.join(['?'] * (2 if area else 1)) + ')', rows)
        destination = str(path).replace("'", "''")
        con.execute(f"COPY proxy TO '{destination}' (FORMAT PARQUET)")


@pytest.mark.parametrize('c_mode', ['observed_rap', 'scenario_sbs'])
def test_surface_proxy_support_reaches_actual_c_artifacts(tmp_path: Path, c_mode: str) -> None:
    rows = [(0, 2), (20, 3), (None, 5), (float('inf'), 7),
            (150, 1), (-10, 1), (50, None), (float('nan'), 9), (10, 0)]
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows)
    dem = tmp_path / 'dem.tif'
    _write_raster(dem, np.ones((1, 2)), dtype='float32', nodata=-9999.0)
    if c_mode == 'observed_rap':
        rap = tmp_path / 'rap.tif'
        _write_default_rap_dataset(rap, bare_ground=np.array([[50., 50.]]))
        kwargs = {'rap': str(rap)}
        key, bare = 'rock_fraction_of_rap_bare', .5
    else:
        landuse, mapping = tmp_path / 'landuse.tif', tmp_path / 'disturbed.json'
        _write_raster(landuse, np.array([[52, 52]]), dtype='uint8', nodata=0)
        _write_disturbed_mapping(mapping, {52: {'DisturbedClass': 'shrub'}})
        kwargs = {'landuse': str(landuse), 'disturbed_mapping_path': str(mapping)}
        key, bare = 'rock_fraction_of_sbs_bare', .1
    result = c_integration.run_rusle_c_factor(str(tmp_path), dem=str(dem), c_mode=c_mode, **kwargs)
    rock = json.loads(Path(result.manifest).read_text())['c'][key]
    source = rock['sources']['cosurffrags']
    assert source['row_count'] == 4
    assert source['support'] == {
        'total_rows': 9, 'missing_cover_rows': 1, 'nonfinite_cover_rows': 2,
        'unparseable_cover_rows': 0, 'out_of_range_cover_rows': 2,
        'zero_cover_rows': 1, 'used_rows': 4,
        'unknown_or_nonpositive_area_rows': 2, 'known_positive_area': 28.,
        'used_positive_area': 7., 'known_area_fraction_used': .25,
    }
    # Independent legacy numeric contract: only finite cover + positive area.
    proxy = (20 * 3 + 150 - 10) / 7 / 100
    assert rock['surface_rock_cover_proxy_0_1'] == pytest.approx(proxy)
    pixels, nodata = _read_single_band(result.c)
    assert np.all(pixels != nodata)
    assert np.allclose(pixels, np.exp(-.04 * 100 * (1 - bare * (1 - min(proxy / bare, 1)))))
    # Explicit same numerical setting must produce exactly the same C raster.
    manual = c_integration.run_rusle_c_factor(
        str(tmp_path), dem=str(dem), c_mode=c_mode, **kwargs, **{key: min(proxy / bare, 1)},
    )
    assert np.array_equal(_read_single_band(manual.c)[0], pixels)


@pytest.mark.parametrize('rows', [[], [(None, 2.), (None, None)]])
def test_surface_proxy_empty_and_unknown_support(tmp_path: Path, rows) -> None:
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy is None and report['reason'] == 'cosurffrags_no_weighted_rows'
    support = report['support']
    assert support['total_rows'] == support['missing_cover_rows'] == len(rows)
    assert support['used_rows'] == 0
    assert support['known_area_fraction_used'] == (0. if rows else None)


def test_surface_proxy_unweighted_support(tmp_path: Path) -> None:
    rows = [(None,), (float('nan'),), (20.,), (0.,), (150.,), (-10.,)]
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows, area=False)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy == .4 and report['row_count'] == 4
    support = report['support']
    assert support['total_rows'] == 6 and support['used_rows'] == 4
    assert support['out_of_range_cover_rows'] == 2 and support['zero_cover_rows'] == 1
    assert support['missing_cover_rows'] == support['nonfinite_cover_rows'] == 1
    assert all(support[key] is None for key in ('known_positive_area', 'used_positive_area',
               'known_area_fraction_used', 'unknown_or_nonpositive_area_rows'))


def test_surface_proxy_preserves_excluded_malformed_values(tmp_path: Path) -> None:
    rows = [(None, 'bad'), ('bad', None), ('nan', 'bad'), ('20', '2')]
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows, text=True)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy == .2 and report['row_count'] == 1
    support = report['support']
    assert support['unparseable_cover_rows'] == support['missing_cover_rows'] == support['nonfinite_cover_rows'] == 1
    assert support['unknown_or_nonpositive_area_rows'] == 3
    assert support['known_area_fraction_used'] == 1.  # Does not imply a complete footprint.


@pytest.mark.parametrize('rows', [[('bad', '2')], [('20', 'bad')]])
def test_surface_proxy_preserves_consumed_malformed_failure(tmp_path: Path, rows) -> None:
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows, text=True)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy is None and report['reason'] == 'cosurffrags_query_failed'
    assert 'support' not in report


def test_surface_proxy_invalid_area_support(tmp_path: Path) -> None:
    rows = [(10., float('nan')), (20., float('inf')), (30., -1.), (40., 2.)]
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy == .4 and report['row_count'] == 1
    assert report['support']['unknown_or_nonpositive_area_rows'] == 3
    assert report['support']['known_positive_area'] == report['support']['used_positive_area'] == 2.


@pytest.mark.parametrize('rows', [[], [(None,), (float('inf'),)]])
def test_surface_proxy_unweighted_unavailable_support(tmp_path: Path, rows) -> None:
    _write_surface_proxy_parquet(tmp_path / 'soils/soils.parquet', rows, area=False)
    proxy, report = c_integration._load_cosurffrags_surface_proxy_from_soils_parquet(str(tmp_path))
    assert proxy is None and report['reason'] == 'cosurffrags_no_finite_rows'
    assert report['support']['total_rows'] == len(rows)
    assert report['support']['used_rows'] == 0
    assert report['support']['known_area_fraction_used'] is None
