from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from wepppy.topo.wbt.terrain_processor import TerrainConfig, TerrainProcessor
from wepppy.topo.wbt.terrain_processor_helpers import derive_flow_stack
from wepppy.topo.wbt.wbt_topaz_emulator import WhiteboxToolsTopazEmulator

pytestmark = pytest.mark.integration

_RUN_FLAG = "TERRAIN_PROCESSOR_WBT_INTEGRATION"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _require_wbt_integration(pytestconfig: pytest.Config) -> None:
    if os.getenv(_RUN_FLAG, "").strip().lower() in _TRUE_VALUES:
        return

    invocation_args = tuple(str(arg) for arg in pytestconfig.invocation_params.args)
    if any(arg.endswith("test_terrain_processor_wbt_integration.py") for arg in invocation_args):
        return

    pytest.skip(
        f"Set {_RUN_FLAG}=1 to include TerrainProcessor WBT integration tests in broader runs."
    )


def _write_dem(path: Path) -> None:
    import rasterio
    from rasterio.transform import from_origin

    # Gentle gradient with a local depression to exercise breach-least-cost.
    dem = np.array(
        [
            [30.0, 29.0, 28.0, 27.0, 26.0, 25.0],
            [29.0, 28.0, 27.0, 26.0, 25.0, 24.0],
            [28.0, 27.0, 20.0, 20.0, 24.0, 23.0],
            [27.0, 26.0, 20.0, 18.0, 23.0, 22.0],
            [26.0, 25.0, 24.0, 23.0, 22.0, 21.0],
            [25.0, 24.0, 23.0, 22.0, 21.0, 20.0],
        ],
        dtype=np.float32,
    )

    profile = {
        "driver": "GTiff",
        "height": dem.shape[0],
        "width": dem.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": from_origin(500000.0, 4100000.0, 1.0, 1.0),
        "nodata": -9999.0,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(dem, 1)



def test_derive_flow_stack_with_real_wbt_supports_blc_controls(
    tmp_path: Path,
    pytestconfig: pytest.Config,
) -> None:
    _require_wbt_integration(pytestconfig)

    dem_path = tmp_path / "dem.tif"
    _write_dem(dem_path)

    emulator = WhiteboxToolsTopazEmulator(
        wbt_wd=str(tmp_path / "wbt"),
        dem_fn=str(dem_path),
    )

    artifacts = derive_flow_stack(
        emulator,
        csa=0.0005,
        mcl=1.0,
        fill_or_breach="breach_least_cost",
        blc_dist=10,
        blc_max_cost=5.0,
        blc_fill=False,
    )

    assert Path(artifacts.relief_path).exists()
    assert Path(artifacts.flow_vector_path).exists()
    assert Path(artifacts.flow_accumulation_path).exists()
    assert Path(artifacts.stream_raster_path).exists()
    assert Path(artifacts.stream_geojson_path).exists()



def test_terrain_processor_phase2_with_real_wbt_generates_flow_stack(
    tmp_path: Path,
    pytestconfig: pytest.Config,
) -> None:
    _require_wbt_integration(pytestconfig)

    dem_path = tmp_path / "dem.tif"
    _write_dem(dem_path)

    processor = TerrainProcessor(
        wbt_wd=str(tmp_path / "terrain_runtime"),
        dem_path=str(dem_path),
        config=TerrainConfig(
            conditioning="breach_least_cost",
            blc_dist_m=10.0,
            blc_max_cost=5.0,
            blc_fill=False,
            csa=0.0005,
            mcl=1.0,
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    phase2 = processor.artifacts_by_phase["phase2_conditioning_flow_stack"]

    assert Path(phase2["relief"]).exists()
    assert Path(phase2["flovec"]).exists()
    assert Path(phase2["floaccum"]).exists()
    assert Path(phase2["netful"]).exists()
    assert Path(phase2["netful_geojson"]).exists()
