from __future__ import annotations

import json
from pathlib import Path
import runpy

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio", reason="rasterio required for SSURGO study raster tests")
from rasterio.transform import from_origin


pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/ssurgo_empirical_study.py"))


def _write_mukey_raster(path: Path) -> None:
    values = np.array(
        [
            [0, 1001, 1001, 1002],
            [1002, 1002, 1003, 1003],
            [1003, 1003, 1003, 0],
        ],
        dtype=np.uint32,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=values.dtype,
        crs="EPSG:5070",
        transform=from_origin(0, 90, 30, 30),
        nodata=0,
    ) as dataset:
        dataset.write(values, 1)


def _record(mukey: int, outcome: str, reasons: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "mukey_build",
        "cohort_id": "fixture-cohort",
        "raster_source": "fixture-raster",
        "mukey": mukey,
        "outcome": outcome,
        "reason_codes": reasons,
        "build_configuration": {"ksflag": True},
        "failure_evidence": {
            "component_count": 1,
            "eligible_component_count": 1,
            "horizon_count": 1,
            "post_default_valid_horizon_count": 0 if outcome != "valid" else 1,
            "emitted_wepp_layer_count": 0 if outcome != "valid" else 1,
            "restrictive_layer_state": None,
        },
        "raw_data_completeness": {},
        "retained_comparison_features": {},
        "repair_provenance": [],
    }


def test_inventory_streams_mukey_counts_and_marks_smoke_runs_incomplete(tmp_path: Path) -> None:
    module = _module()
    inventory_mukey_raster = module["inventory_mukey_raster"]
    raster_path = tmp_path / "mukey.tif"
    _write_mukey_raster(raster_path)

    inventory = inventory_mukey_raster(raster_path)

    assert inventory["complete"] is True
    assert inventory["inventory_method"] == "raster_blocks"
    assert inventory["pixel_area_m2"] == pytest.approx(900.0)
    assert inventory["valid_pixel_count"] == 10
    assert inventory["mukey_pixel_counts"] == {"1001": 2, "1002": 3, "1003": 5}

    smoke_inventory = inventory_mukey_raster(raster_path, max_windows=1)
    assert smoke_inventory["complete"] is False
    assert smoke_inventory["windows_read"] == 1


def test_diagnostic_and_coverage_summaries_preserve_unobserved_coverage(tmp_path: Path) -> None:
    module = _module()
    inventory_mukey_raster = module["inventory_mukey_raster"]
    summarize_diagnostics = module["summarize_diagnostics"]
    summarize_raster_coverage = module["summarize_raster_coverage"]
    raster_path = tmp_path / "mukey.tif"
    _write_mukey_raster(raster_path)
    records = [
        _record(1001, "valid", []),
        _record(1002, "residual_invalid", ["no_valid_horizons", "missing_sandtotal_r"]),
    ]

    diagnostics = summarize_diagnostics(records)
    coverage = summarize_raster_coverage(inventory_mukey_raster(raster_path), records)

    assert diagnostics["outcome_counts"] == {
        "residual_invalid": 1,
        "valid": 1,
        "worker_failed": 0,
    }
    assert diagnostics["reason_code_counts"] == {
        "missing_sandtotal_r": 1,
        "no_valid_horizons": 1,
    }
    assert coverage["outcome_pixel_counts"] == {
        "residual_invalid": 3,
        "valid": 2,
        "worker_failed": 0,
    }
    assert coverage["unobserved_pixel_count"] == 5
    assert coverage["cohort_id"] == "fixture-cohort"


def test_cli_writes_inventory_and_diagnostic_summaries(tmp_path: Path) -> None:
    module = _module()
    main = module["main"]
    raster_path = tmp_path / "mukey.tif"
    _write_mukey_raster(raster_path)
    inventory_path = tmp_path / "inventory.json"
    diagnostics_path = tmp_path / "diagnostics.jsonl"
    diagnostics_output = tmp_path / "diagnostic-summary.json"
    template_path = tmp_path / "diagnostic-template.json"
    diagnostics_path.write_text(json.dumps(_record(1001, "valid", [])) + "\n", encoding="utf-8")

    assert main(["inventory", "--raster", str(raster_path), "--output", str(inventory_path)]) == 0
    assert main(["diagnostics", "--input", str(diagnostics_path), "--output", str(diagnostics_output)]) == 0
    assert main(["template", "--output", str(template_path)]) == 0

    assert json.loads(inventory_path.read_text(encoding="utf-8"))["distinct_mukey_count"] == 3
    assert json.loads(diagnostics_output.read_text(encoding="utf-8"))["record_count"] == 1
    assert json.loads(template_path.read_text(encoding="utf-8"))["record_type"] == "mukey_build"
