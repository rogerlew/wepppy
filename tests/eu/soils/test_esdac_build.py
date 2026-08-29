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


def test_esdac_batch_rejection_reports_real_categorical_reason(tmp_path) -> None:
    """Replay Forest job 893db465's first rejected raster location."""
    pytest.importorskip("numpy")
    from wepppy.eu.soils.soil_build import (
        ESDACSoilBatchError,
        build_esdac_soils,
    )

    output_dir = tmp_path / "soils"
    with pytest.raises(ESDACSoilBatchError) as error:
        build_esdac_soils(
            [(73, (8.05301393718246, 50.16630252781121))],
            str(output_dir),
        )

    message = str(error.value)
    assert "source.categorical.empty[field=fao90lev1, count=1" in message
    assert 'raw_value=["24","","No information"]' in message
    assert "report: soil_quality.json" in message

    report = json.loads((output_dir / "soil_quality.json").read_text())
    assert report["batch_outcome"] == "rejected"
    assert report["profiles"][0]["diagnostics"] == [
        {
            "code": "source.categorical.empty",
            "exception_type": None,
            "field": "fao90lev1",
            "raw_value": ["24", "", "No information"],
            "severity": "error",
        }
    ]
    assert not list(output_dir.glob("*.sol"))
