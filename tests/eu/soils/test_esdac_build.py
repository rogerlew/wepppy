from __future__ import annotations

import json
from pathlib import Path

import pytest

ESDAC_RASTER_DIR = Path("/geodata/eu/ESDAC_ESDB_rasters")
ESDAC_STU_DIR = Path("/geodata/eu/ESDAC_STU_EU_Layers")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not (ESDAC_RASTER_DIR.is_dir() and ESDAC_STU_DIR.is_dir()),
        reason="ESDAC rasters unavailable",
    ),
]


def test_esdac_build_generates_wepp_soil(tmp_path) -> None:
    pytest.importorskip("numpy")
    from wepppy.eu.soils.esdac import ESDAC

    output_dir = tmp_path / "soils"
    output_dir.mkdir()

    esdac = ESDAC()
    key, _, description = esdac.build_wepp_soil(
        -6.309,
        43.140013,
        str(output_dir),
    )

    sol_path = output_dir / f"{key}.sol"
    assert sol_path.exists(), "WEPP soil file was not created"
    assert description, "Description metadata should be populated"
    content = sol_path.read_text()
    assert "ESDAC ESDB Soil Parameters" in content


def test_esdac_batch_accepts_missing_fao_with_warning(tmp_path) -> None:
    """Replay the real Forest failure with sufficient physical data."""
    pytest.importorskip("numpy")
    from wepppy.eu.soils.soil_build import build_esdac_soils
    from wepppy.wepp.soils.utils import WeppSoilUtil

    output_dir = tmp_path / "soils"
    soils, dominant = build_esdac_soils(
        [(73, (8.05301393718246, 50.16630252781121))], str(output_dir)
    )
    report = json.loads((output_dir / "soil_quality.json").read_text())
    assert report["batch_outcome"] == "accepted"
    assert report["accepted_count"] == 1
    assert report["profiles"][0]["outcome"] == "degraded"
    assert {
        "code": "source.categorical.empty", "exception_type": None,
        "field": "fao90lev1", "raw_value": ["24", "", "No information"],
        "severity": "warning",
    } in report["profiles"][0]["diagnostics"]
    assert soils and dominant
    for path in output_dir.glob("*.sol"):
        parsed = WeppSoilUtil(str(path))
        assert parsed.obj["ofes"][0]["horizons"]


def test_incident_batch_rebuilds_and_retries_with_stable_artifacts(tmp_path) -> None:
    from wepppy.eu.soils.soil_build import build_esdac_soils
    from wepppy.eu.soils.esdac import load_soil_quality_report
    from wepppy.wepp.soils.utils import WeppSoilUtil
    orders = [(42, (6.878030223381789, 47.943332184393924)),
              (22, (6.8763667129917705, 47.943076476022014))]
    soils, dominant = build_esdac_soils(orders, str(tmp_path))
    assert len(dominant) == 2
    before = {p.name: p.read_bytes() for p in tmp_path.glob('*.sol')}
    assert len(before) == len(soils)
    report = load_soil_quality_report(tmp_path / 'soil_quality.json')
    for topaz_id, key in dominant.items():
        assert report[topaz_id].soil_key == key
        assert report[topaz_id].accepted
        assert WeppSoilUtil(str(tmp_path / f'{key}.sol')).obj['ofes'][0]['horizons']
    assert build_esdac_soils(orders, str(tmp_path))[1] == dominant
    assert {p.name:p.read_bytes() for p in tmp_path.glob('*.sol')} == before
