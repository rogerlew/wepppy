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
    assert k_manifest["mode_contract"]["cfvo_scope"] == "deferred"
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
