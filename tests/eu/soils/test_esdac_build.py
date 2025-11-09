from __future__ import annotations

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
