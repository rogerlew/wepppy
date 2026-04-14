from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from wepppy.topo.wbt.terrain_processor import TerrainConfig, TerrainProcessor
from wepppy.topo.wbt.terrain_processor_helpers import derive_flow_stack
from wepppy.topo.wbt.wbt_topaz_emulator import (
    DEFAULT_STREAM_PRUNING_MAX_JUNCTIONS,
    WhiteboxToolsTopazEmulator,
)

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



def test_extract_streams_ifolp_path_passes_max_junctions(tmp_path: Path) -> None:
    class DummyWbt:
        def __init__(self) -> None:
            self.ifolp_kwargs: dict[str, object] | None = None
            self.remove_short_streams_called = False

        def extract_streams(self, _floaccum: str, output: str, threshold: float) -> None:
            assert threshold > 0
            Path(output).touch()

        def iterative_first_order_link_prune(self, **kwargs) -> None:
            self.ifolp_kwargs = kwargs
            Path(str(kwargs["output"])).touch()

        def remove_short_streams(self, **kwargs) -> None:
            self.remove_short_streams_called = True
            Path(str(kwargs["output"])).touch()

    emulator = WhiteboxToolsTopazEmulator(wbt_wd=str(tmp_path))
    emulator.cellsize = 1.0
    emulator.csa = 5.0
    emulator.mcl = 60.0
    emulator.stream_pruning_method = "ifolp"
    Path(emulator.floaccum).touch()
    dummy_wbt = DummyWbt()
    emulator._wbt_runner = dummy_wbt

    emulator._extract_streams()

    assert dummy_wbt.ifolp_kwargs is not None
    assert dummy_wbt.ifolp_kwargs["max_junctions"] == DEFAULT_STREAM_PRUNING_MAX_JUNCTIONS
    assert dummy_wbt.ifolp_kwargs["mscl"] == 60.0
    assert dummy_wbt.ifolp_kwargs["csa"] == 5.0
    assert dummy_wbt.remove_short_streams_called is False


def test_extract_streams_legacy_path_uses_remove_short_streams(tmp_path: Path) -> None:
    class DummyWbt:
        def __init__(self) -> None:
            self.remove_short_streams_kwargs: dict[str, object] | None = None
            self.ifolp_called = False

        def extract_streams(self, _floaccum: str, output: str, threshold: float) -> None:
            assert threshold > 0
            Path(output).touch()

        def remove_short_streams(self, **kwargs) -> None:
            self.remove_short_streams_kwargs = kwargs
            Path(str(kwargs["output"])).touch()

        def iterative_first_order_link_prune(self, **kwargs) -> None:
            self.ifolp_called = True
            Path(str(kwargs["output"])).touch()

    emulator = WhiteboxToolsTopazEmulator(wbt_wd=str(tmp_path))
    emulator.cellsize = 1.0
    emulator.csa = 5.0
    emulator.mcl = 60.0
    emulator.stream_pruning_method = "remove_short_streams"
    Path(emulator.floaccum).touch()
    dummy_wbt = DummyWbt()
    emulator._wbt_runner = dummy_wbt

    emulator._extract_streams()

    assert dummy_wbt.remove_short_streams_kwargs is not None
    assert (
        dummy_wbt.remove_short_streams_kwargs["max_junctions"]
        == DEFAULT_STREAM_PRUNING_MAX_JUNCTIONS
    )
    assert dummy_wbt.remove_short_streams_kwargs["min_length"] == 60.0
    assert dummy_wbt.ifolp_called is False


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
    emulator.stream_pruning_method = "remove_short_streams"

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

    emulator = WhiteboxToolsTopazEmulator(
        wbt_wd=str(tmp_path / "terrain_runtime"),
        dem_fn=str(dem_path),
    )
    emulator.stream_pruning_method = "remove_short_streams"

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
        emulator=emulator,
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    phase2 = processor.artifacts_by_phase["phase2_conditioning_flow_stack"]

    assert Path(phase2["relief"]).exists()
    assert Path(phase2["flovec"]).exists()
    assert Path(phase2["floaccum"]).exists()
    assert Path(phase2["netful"]).exists()
    assert Path(phase2["netful_geojson"]).exists()
