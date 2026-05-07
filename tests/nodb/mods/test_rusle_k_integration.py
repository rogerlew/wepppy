from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import wepppy.nodb.mods.rusle.k_integration as k_integration


pytestmark = pytest.mark.unit


def _write_test_raster(path: Path, data: np.ndarray, *, nodata: float = -9999.0) -> None:
    profile = {
        "driver": "GTiff",
        "height": int(data.shape[0]),
        "width": int(data.shape[1]),
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(0.0, 2.0, 1.0, 1.0),
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data.astype(np.float32), 1)


def _write_polaris_layers(wd: Path) -> None:
    polaris_dir = wd / "polaris"
    polaris_dir.mkdir(parents=True, exist_ok=True)

    layers = {
        "sand_mean_0_5": np.asarray([[45.0, 60.0], [35.0, 70.0]]),
        "sand_mean_5_15": np.asarray([[40.0, 55.0], [30.0, 65.0]]),
        "silt_mean_0_5": np.asarray([[35.0, 25.0], [45.0, 15.0]]),
        "silt_mean_5_15": np.asarray([[40.0, 30.0], [50.0, 20.0]]),
        "clay_mean_0_5": np.asarray([[20.0, 15.0], [20.0, 15.0]]),
        "clay_mean_5_15": np.asarray([[20.0, 15.0], [20.0, 15.0]]),
        "om_mean_0_5": np.log10(np.asarray([[3.5, 2.5], [4.0, 1.5]])),
        "om_mean_5_15": np.log10(np.asarray([[2.8, 2.0], [3.0, 1.2]])),
        "ksat_mean_0_5": np.log10(np.asarray([[4.0, 8.0], [2.0, 30.0]])),
        "ksat_mean_5_15": np.log10(np.asarray([[3.0, 6.0], [1.5, 20.0]])),
    }

    for layer_id, data in layers.items():
        _write_test_raster(polaris_dir / f"{layer_id}.tif", data)


def _write_polaris_layers_with_nodata(
    wd: Path,
    *,
    shape: tuple[int, int],
    nodata_mask: np.ndarray,
) -> None:
    polaris_dir = wd / "polaris"
    polaris_dir.mkdir(parents=True, exist_ok=True)

    rows, cols = shape
    yy, xx = np.indices((rows, cols), dtype=np.float64)
    sand_top = 40.0 + 0.5 * xx + 0.2 * yy
    sand_sub = sand_top - 2.0
    silt_top = 35.0 + 0.3 * yy
    silt_sub = silt_top + 2.0
    clay_top = 18.0 + 0.1 * xx
    clay_sub = clay_top + 0.5
    om_top = np.log10(2.5 + 0.05 * yy)
    om_sub = np.log10(2.0 + 0.04 * yy)
    ksat_top = np.log10(3.0 + 0.1 * xx)
    ksat_sub = np.log10(2.5 + 0.08 * xx)

    layers = {
        "sand_mean_0_5": sand_top,
        "sand_mean_5_15": sand_sub,
        "silt_mean_0_5": silt_top,
        "silt_mean_5_15": silt_sub,
        "clay_mean_0_5": clay_top,
        "clay_mean_5_15": clay_sub,
        "om_mean_0_5": om_top,
        "om_mean_5_15": om_sub,
        "ksat_mean_0_5": ksat_top,
        "ksat_mean_5_15": ksat_sub,
    }

    for layer_id, data in layers.items():
        writable = np.asarray(data, dtype=np.float64).copy()
        writable[nodata_mask] = -9999.0
        _write_test_raster(polaris_dir / f"{layer_id}.tif", writable)


def _write_soils_cfvo_layers(
    wd: Path,
    *,
    top_data: np.ndarray,
    sub_data: np.ndarray,
) -> None:
    soils_dir = wd / "soils"
    soils_dir.mkdir(parents=True, exist_ok=True)
    _write_test_raster(soils_dir / "cfvo_0-5cm_Q0.5.tif", np.asarray(top_data, dtype=np.float64))
    _write_test_raster(soils_dir / "cfvo_5-15cm_Q0.5.tif", np.asarray(sub_data, dtype=np.float64))


def _read_raster_with_nodata(path: Path) -> tuple[np.ndarray, float | None]:
    with rasterio.open(path) as dataset:
        data = dataset.read(1).astype(np.float64)
        nodata = dataset.nodata
    return data, nodata


def test_run_rusle_k_factors_writes_artifacts_manifest_and_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    _write_polaris_layers(wd)

    reference_raster = wd / "gssurgo_kffact.tif"
    _write_test_raster(reference_raster, np.asarray([[0.20, 0.25], [0.30, 0.35]]))

    catalog_updates: list[str] = []
    monkeypatch.setattr(k_integration, "update_catalog_entry", lambda _wd, relpath: catalog_updates.append(relpath))

    result = k_integration.run_rusle_k_factors(
        str(wd),
        reference_paths={"gssurgo_kffact": str(reference_raster)},
        comparison_points=[
            {"point_id": "p00", "x": 0.5, "y": 1.5},
            {"point_id": "p01", "x": 1.5, "y": 1.5},
            {"point_id": "p10", "x": 0.5, "y": 0.5},
            {"point_id": "p11", "x": 1.5, "y": 0.5},
        ],
    )

    assert Path(result.nomograph).exists()
    assert Path(result.epic).exists()
    assert result.k_default is not None and Path(result.k_default).exists()
    assert result.reference_samples is not None and Path(result.reference_samples).exists()
    assert result.comparison_summary is not None and Path(result.comparison_summary).exists()
    assert Path(result.manifest).exists()

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)

    k_manifest = manifest["k"]
    assert k_manifest["default_k_mode"] == "polaris_nomograph"
    assert k_manifest["mode_contract"]["cfvo_scope"] == "optional_implemented"
    assert (
        k_manifest["mode_contract"]["polaris_nomograph"]["cfvo_profile_fragment_adjustment"]["status"]
        == "not_applied"
    )
    assert k_manifest["mode_contract"]["polaris_epic"]["oc_conversion_factor"] == pytest.approx(1.724)

    assert "rusle/k_polaris_nomograph.tif" in catalog_updates
    assert "rusle/k_polaris_epic.tif" in catalog_updates
    assert "rusle/k.tif" in catalog_updates
    assert "rusle/k_reference_samples.json" in catalog_updates
    assert "rusle/k_benchmark_comparison_summary.json" in catalog_updates


def test_run_rusle_k_factors_requires_points_when_reference_requested(tmp_path: Path) -> None:
    _write_polaris_layers(tmp_path)

    with pytest.raises(ValueError, match="comparison_points"):
        k_integration.run_rusle_k_factors(
            str(tmp_path),
            reference_paths={"gssurgo_kffact": str(tmp_path / "missing.tif")},
        )


def test_run_rusle_k_factors_writes_only_selected_mode_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_polaris_layers(tmp_path)

    catalog_updates: list[str] = []
    monkeypatch.setattr(k_integration, "update_catalog_entry", lambda _wd, relpath: catalog_updates.append(relpath))

    result = k_integration.run_rusle_k_factors(
        str(tmp_path),
        selected_modes=["polaris_nomograph"],
        default_k_mode="polaris_nomograph",
        write_default_k=False,
    )

    assert result.nomograph is not None and Path(result.nomograph).exists()
    assert result.epic is None
    assert result.k_default is None

    assert "rusle/k_polaris_nomograph.tif" in catalog_updates
    assert "rusle/k_polaris_epic.tif" not in catalog_updates
    assert "rusle/k.tif" not in catalog_updates

    epic_path = tmp_path / "rusle" / "k_polaris_epic.tif"
    default_path = tmp_path / "rusle" / "k.tif"
    assert not epic_path.exists()
    assert not default_path.exists()


def test_run_rusle_k_factors_fills_small_interior_holes_and_reports_manifest(
    tmp_path: Path,
) -> None:
    nodata_mask = np.zeros((5, 5), dtype=bool)
    nodata_mask[2, 2] = True
    _write_polaris_layers_with_nodata(tmp_path, shape=(5, 5), nodata_mask=nodata_mask)

    result = k_integration.run_rusle_k_factors(str(tmp_path))

    nomograph_data, nomograph_nodata = _read_raster_with_nodata(Path(result.nomograph or ""))
    assert nomograph_nodata is not None
    center = nomograph_data[2, 2]
    assert not np.isclose(center, float(nomograph_nodata))

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    gap_fill = manifest["k"]["gap_fill_summary"]["sand"]["top"]
    assert gap_fill["fill_applied"] is True
    assert int(gap_fill["filled_pixels"]) >= 1
    assert int(gap_fill["nodata_pixels_in"]) == 1
    assert int(gap_fill["nodata_pixels_out"]) == 0


def test_run_rusle_k_factors_skips_fill_when_candidate_fraction_too_high(
    tmp_path: Path,
) -> None:
    nodata_mask = np.zeros((10, 10), dtype=bool)
    nodata_mask[1:9, 1:9] = (np.indices((8, 8)).sum(axis=0) % 2 == 0)
    _write_polaris_layers_with_nodata(tmp_path, shape=(10, 10), nodata_mask=nodata_mask)

    result = k_integration.run_rusle_k_factors(str(tmp_path))

    nomograph_data, nomograph_nodata = _read_raster_with_nodata(Path(result.nomograph or ""))
    assert nomograph_nodata is not None
    valid_nodata = np.isclose(nomograph_data, float(nomograph_nodata))
    # Candidate fraction is intentionally high (>= 10%), so holes should remain.
    assert int(np.count_nonzero(valid_nodata)) >= 30

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    gap_fill = manifest["k"]["gap_fill_summary"]["sand"]["top"]
    assert gap_fill["reason"] == "candidate_fraction_above_threshold"
    assert gap_fill["fill_applied"] is False


def test_run_rusle_k_factors_applies_cfvo_profile_fragment_adjustment(
    tmp_path: Path,
) -> None:
    base_wd = tmp_path / "base"
    cfvo_wd = tmp_path / "cfvo"
    _write_polaris_layers(base_wd)
    _write_polaris_layers(cfvo_wd)
    _write_soils_cfvo_layers(
        cfvo_wd,
        top_data=np.asarray([[10.0, 350.0], [700.0, 5.0]], dtype=np.float64),
        sub_data=np.asarray([[10.0, 300.0], [650.0, 5.0]], dtype=np.float64),
    )

    base_result = k_integration.run_rusle_k_factors(str(base_wd))
    cfvo_result = k_integration.run_rusle_k_factors(str(cfvo_wd))

    base_nomograph, _ = _read_raster_with_nodata(Path(base_result.nomograph or ""))
    cfvo_nomograph, _ = _read_raster_with_nodata(Path(cfvo_result.nomograph or ""))

    finite = np.isfinite(base_nomograph) & np.isfinite(cfvo_nomograph)
    assert np.any(finite)
    # Cells with strong coarse-fragment signal should shift to less permeable
    # classes and therefore increase nomograph K under this approximation.
    assert float(np.nanmax(cfvo_nomograph - base_nomograph)) > 0.0

    with open(cfvo_result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    cfvo_contract = manifest["k"]["mode_contract"]["polaris_nomograph"]["cfvo_profile_fragment_adjustment"]
    assert cfvo_contract["status"] == "applied"
    assert int(cfvo_contract["changed_cells"]) >= 1
    assert cfvo_contract["source_kind"] == "aligned_from_soils_cfvo_q0_5"
    assert manifest["k"]["cfvo_summary"]["status"] == "available"


def test_run_rusle_k_factors_cfvo_permille_values_below_100_do_not_shift_classes(
    tmp_path: Path,
) -> None:
    base_wd = tmp_path / "base_low"
    cfvo_wd = tmp_path / "cfvo_low"
    _write_polaris_layers(base_wd)
    _write_polaris_layers(cfvo_wd)
    _write_soils_cfvo_layers(
        cfvo_wd,
        top_data=np.asarray([[80.0, 70.0], [60.0, 50.0]], dtype=np.float64),
        sub_data=np.asarray([[70.0, 60.0], [50.0, 40.0]], dtype=np.float64),
    )

    base_result = k_integration.run_rusle_k_factors(str(base_wd))
    cfvo_result = k_integration.run_rusle_k_factors(str(cfvo_wd))

    base_nomograph, _ = _read_raster_with_nodata(Path(base_result.nomograph or ""))
    cfvo_nomograph, _ = _read_raster_with_nodata(Path(cfvo_result.nomograph or ""))
    finite = np.isfinite(base_nomograph) & np.isfinite(cfvo_nomograph)
    assert np.any(finite)
    assert float(np.nanmax(np.abs(cfvo_nomograph - base_nomograph))) < 1e-6

    with open(cfvo_result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    cfvo_contract = manifest["k"]["mode_contract"]["polaris_nomograph"]["cfvo_profile_fragment_adjustment"]
    assert cfvo_contract["status"] == "available_no_change"


def test_run_rusle_k_factors_invalid_mode_does_not_stage_cfvo_side_effects(
    tmp_path: Path,
) -> None:
    _write_polaris_layers(tmp_path)
    _write_soils_cfvo_layers(
        tmp_path,
        top_data=np.asarray([[350.0, 350.0], [350.0, 350.0]], dtype=np.float64),
        sub_data=np.asarray([[300.0, 300.0], [300.0, 300.0]], dtype=np.float64),
    )

    with pytest.raises(ValueError, match="Unsupported K mode"):
        k_integration.run_rusle_k_factors(
            str(tmp_path),
            selected_modes=["unsupported_mode"],
        )

    assert not (tmp_path / "polaris" / "cfvo_mean_0_5.tif").exists()
    assert not (tmp_path / "polaris" / "cfvo_mean_5_15.tif").exists()


def test_run_rusle_k_factors_cfvo_processing_failure_is_optional_skip(
    tmp_path: Path,
) -> None:
    _write_polaris_layers(tmp_path)
    soils_dir = tmp_path / "soils"
    soils_dir.mkdir(parents=True, exist_ok=True)
    (soils_dir / "cfvo_0-5cm_Q0.5.tif").write_text("not-a-raster", encoding="utf-8")
    (soils_dir / "cfvo_5-15cm_Q0.5.tif").write_text("not-a-raster", encoding="utf-8")

    result = k_integration.run_rusle_k_factors(str(tmp_path))

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["k"]["cfvo_summary"]["status"] == "not_applied"
    assert manifest["k"]["cfvo_summary"]["reason"] == "cfvo_layer_processing_failed"


def test_run_rusle_k_factors_reuses_aligned_cfvo_layers_when_present(
    tmp_path: Path,
) -> None:
    _write_polaris_layers(tmp_path)
    polaris_dir = tmp_path / "polaris"
    _write_test_raster(polaris_dir / "cfvo_mean_0_5.tif", np.asarray([[350.0, 350.0], [350.0, 350.0]]))
    _write_test_raster(polaris_dir / "cfvo_mean_5_15.tif", np.asarray([[300.0, 300.0], [300.0, 300.0]]))

    result = k_integration.run_rusle_k_factors(str(tmp_path))
    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    cfvo_contract = manifest["k"]["mode_contract"]["polaris_nomograph"]["cfvo_profile_fragment_adjustment"]
    assert cfvo_contract["source_kind"] == "aligned_polaris_existing"
