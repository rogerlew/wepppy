from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path

import pytest

import wepppy.rq.culvert_rq as culvert_rq_module
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.rq.culvert_rq import run_culvert_batch_rq


pytestmark = [pytest.mark.integration, pytest.mark.nodb]


class _DummyRedis:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_DummyRedis":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def publish(self, *_args, **_kwargs) -> int:
        return 0


class _DummyJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.meta: dict[str, object] = {}

    def save(self) -> None:
        return None


class _DummyQueue:
    def __init__(self, name: str, connection=None, *args, **kwargs) -> None:
        self.name = name
        self.connection = connection

    def enqueue_call(self, *args, **kwargs) -> _DummyJob:
        return _DummyJob("job-123")


def test_culvert_batch_topo_sequence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-123"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    topo_dir.mkdir(parents=True)
    culverts_dir.mkdir(parents=True)

    (topo_dir / "breached_filled_DEM_UTM.tif").write_bytes(b"dem")
    (topo_dir / "streams.tif").write_bytes(b"streams")

    watersheds = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"Point_ID": "1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
            }
        ],
    }
    (culverts_dir / "watersheds.geojson").write_text(
        json.dumps(watersheds), encoding="utf-8"
    )

    metadata = {
        "dem": {"path": "topo/breached_filled_DEM_UTM.tif"},
        "streams": {"path": "topo/streams.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(
            {
                "schema_version": "culvert-model-params-v1",
                "base_project_runid": "batch;;culvert_base;;_base",
            }
        ),
        encoding="utf-8",
    )

    calls: list[str] = []
    monkeypatch.setattr(
        culvert_rq_module,
        "_generate_batch_topo",
        lambda *args, **kwargs: calls.append("generate"),
    )
    monkeypatch.setattr(
        culvert_rq_module,
        "_prune_short_streams",
        lambda *args, **kwargs: calls.append("prune_short"),
    )
    monkeypatch.setattr(
        culvert_rq_module,
        "_prune_stream_order",
        lambda *args, **kwargs: calls.append("prune_order"),
    )
    monkeypatch.setattr(
        culvert_rq_module,
        "_generate_stream_junctions",
        lambda *args, **kwargs: calls.append("chnjnt"),
    )

    class _DummyDataset:
        def GetGeoTransform(self) -> tuple[float, float, float, float, float, float]:
            return (0.0, 10.0, 0.0, 0.0, 0.0, -10.0)

    monkeypatch.setattr(
        culvert_rq_module.gdal,
        "Open",
        lambda *_args, **_kwargs: _DummyDataset(),
    )

    monkeypatch.setattr(culvert_rq_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(culvert_rq_module, "Queue", _DummyQueue)
    monkeypatch.setattr(
        CulvertsRunner,
        "_ensure_base_project",
        lambda self: str(tmp_path / "base"),
    )
    monkeypatch.setattr(CulvertsRunner, "_load_run_ids", lambda self, path: ["1"])
    monkeypatch.setattr(
        culvert_rq_module,
        "_ensure_batch_landuse_soils",
        lambda **_kwargs: (Path("nlcd.tif"), Path("ssurgo.tif")),
    )

    run_culvert_batch_rq(batch_uuid)

    assert calls == ["generate", "prune_short", "prune_order", "chnjnt", "chnjnt"]


def test_culvert_batch_order_reduction_map_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-map"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    topo_dir.mkdir(parents=True)
    culverts_dir.mkdir(parents=True)

    (topo_dir / "breached_filled_DEM_UTM.tif").write_bytes(b"dem")
    (topo_dir / "streams.tif").write_bytes(b"streams")

    watersheds = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"Point_ID": "1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
            }
        ],
    }
    (culverts_dir / "watersheds.geojson").write_text(
        json.dumps(watersheds), encoding="utf-8"
    )

    metadata = {
        "dem": {"path": "topo/breached_filled_DEM_UTM.tif"},
        "streams": {"path": "topo/streams.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(
            {
                "schema_version": "culvert-model-params-v1",
                "base_project_runid": "batch;;culvert_base;;_base",
                "flow_accum_threshold": 900,
            }
        ),
        encoding="utf-8",
    )

    captured: dict[str, int] = {}
    monkeypatch.setattr(
        culvert_rq_module,
        "_generate_batch_topo",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        culvert_rq_module,
        "_prune_short_streams",
        lambda *args, **kwargs: None,
    )

    def _capture_prune_stream_order(_flovec: Path, _netful: Path, passes: int) -> None:
        captured["passes"] = passes

    monkeypatch.setattr(
        culvert_rq_module,
        "_prune_stream_order",
        _capture_prune_stream_order,
    )
    monkeypatch.setattr(
        culvert_rq_module,
        "_generate_stream_junctions",
        lambda *args, **kwargs: None,
    )

    class _DummyDataset:
        def GetGeoTransform(self) -> tuple[float, float, float, float, float, float]:
            return (0.0, 1.0, 0.0, 0.0, 0.0, -1.0)

    monkeypatch.setattr(
        culvert_rq_module.gdal,
        "Open",
        lambda *_args, **_kwargs: _DummyDataset(),
    )

    monkeypatch.setattr(culvert_rq_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(culvert_rq_module, "Queue", _DummyQueue)
    monkeypatch.setattr(
        CulvertsRunner,
        "_ensure_base_project",
        lambda self: str(tmp_path / "base"),
    )
    monkeypatch.setattr(CulvertsRunner, "_load_run_ids", lambda self, path: ["1"])
    monkeypatch.setattr(
        culvert_rq_module,
        "_ensure_batch_landuse_soils",
        lambda **_kwargs: (Path("nlcd.tif"), Path("ssurgo.tif")),
    )

    run_culvert_batch_rq(batch_uuid)

    assert captured["passes"] == 2


def test_culvert_batch_retries_runner_lock_before_state_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-lock-retry"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    topo_dir.mkdir(parents=True)
    culverts_dir.mkdir(parents=True)

    (topo_dir / "breached_filled_DEM_UTM.tif").write_bytes(b"dem")
    (topo_dir / "streams.tif").write_bytes(b"streams")
    (culverts_dir / "watersheds.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []}),
        encoding="utf-8",
    )
    (batch_root / "metadata.json").write_text(
        json.dumps(
            {
                "dem": {"path": "topo/breached_filled_DEM_UTM.tif"},
                "streams": {"path": "topo/streams.tif"},
                "watersheds": {"path": "culverts/watersheds.geojson"},
            }
        ),
        encoding="utf-8",
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(
            {
                "schema_version": "culvert-model-params-v1",
                "base_project_runid": "batch;;culvert_base;;_base",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(culvert_rq_module, "_generate_batch_topo", lambda *a, **k: None)
    monkeypatch.setattr(culvert_rq_module, "_prune_short_streams", lambda *a, **k: None)
    monkeypatch.setattr(culvert_rq_module, "_prune_stream_order", lambda *a, **k: None)
    monkeypatch.setattr(culvert_rq_module, "_generate_stream_junctions", lambda *a, **k: None)
    monkeypatch.setattr(culvert_rq_module.redis, "Redis", _DummyRedis)
    monkeypatch.setattr(culvert_rq_module, "Queue", _DummyQueue)
    monkeypatch.setattr(
        culvert_rq_module,
        "_ensure_batch_landuse_soils",
        lambda **_kwargs: (Path("nlcd.tif"), Path("ssurgo.tif")),
    )

    class _DummyDataset:
        def GetGeoTransform(self) -> tuple[float, float, float, float, float, float]:
            return (0.0, 10.0, 0.0, 0.0, 0.0, -10.0)

    monkeypatch.setattr(culvert_rq_module.gdal, "Open", lambda *a, **k: _DummyDataset())

    runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    monkeypatch.setattr(CulvertsRunner, "getInstance", lambda *a, **k: runner)
    monkeypatch.setattr(
        CulvertsRunner,
        "_ensure_base_project",
        lambda self: str(tmp_path / "base"),
    )
    monkeypatch.setattr(CulvertsRunner, "_load_run_ids", lambda self, path: [])

    original_locked = runner.locked
    lock_attempts = {"count": 0}

    @contextmanager
    def _flaky_locked(*args, **kwargs):
        lock_attempts["count"] += 1
        if lock_attempts["count"] == 1:
            raise NoDbAlreadyLockedError("simulated lock race")
        with original_locked(*args, **kwargs):
            yield

    monkeypatch.setattr(runner, "locked", _flaky_locked)

    sleeps: list[float] = []
    monkeypatch.setattr(culvert_rq_module.time, "sleep", lambda seconds: sleeps.append(float(seconds)))

    run_culvert_batch_rq(batch_uuid)

    assert lock_attempts["count"] >= 2
    assert culvert_rq_module.CULVERT_BATCH_LOCK_RETRY_SECONDS in sleeps


def test_generate_masked_stream_junctions_retries_clip_when_output_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flovec_path = tmp_path / "flovec.tif"
    netful_path = tmp_path / "netful.tif"
    watershed_mask_path = tmp_path / "target_watershed.tif"
    chnjnt_path = tmp_path / "chnjnt.tif"

    flovec_path.write_bytes(b"flovec")
    netful_path.write_bytes(b"netful")
    watershed_mask_path.write_bytes(b"mask")

    clip_outputs: list[Path] = []

    class _DummyWhiteboxTools:
        def __init__(self, verbose: bool = False, raise_on_error: bool = True) -> None:
            self.verbose = verbose
            self.raise_on_error = raise_on_error
            self.working_dir: str | None = None
            self._netful_clip_attempts = 0

        def set_working_dir(self, working_dir: str) -> None:
            self.working_dir = working_dir

        def clip_raster_to_raster(self, i: str, mask: str, output: str) -> int:
            del mask
            output_path = Path(output)
            clip_outputs.append(output_path)
            # Reproduce run 583 behavior: first netful clip returns but no output.
            if Path(i) == netful_path:
                self._netful_clip_attempts += 1
                if self._netful_clip_attempts == 1:
                    return 0
            output_path.write_bytes(b"clipped")
            return 0

        def stream_junction_identifier(
            self, d8_pntr: str, streams: str, output: str
        ) -> int:
            del d8_pntr, streams
            Path(output).write_bytes(b"junctions")
            return 0

    monkeypatch.setattr(culvert_rq_module, "WhiteboxTools", _DummyWhiteboxTools)
    monkeypatch.setattr(culvert_rq_module, "_raster_has_stream_cells", lambda _p: True)

    sleeps: list[float] = []
    monkeypatch.setattr(
        culvert_rq_module.time,
        "sleep",
        lambda seconds: sleeps.append(float(seconds)),
    )

    culvert_rq_module._generate_masked_stream_junctions(
        flovec_path=flovec_path,
        netful_path=netful_path,
        watershed_mask_path=watershed_mask_path,
        chnjnt_path=chnjnt_path,
    )

    netful_masked = chnjnt_path.parent / "netful.masked.tif"
    netful_clip_attempts = clip_outputs.count(netful_masked)
    assert netful_clip_attempts == 2
    assert chnjnt_path.exists()
    assert culvert_rq_module.CULVERT_CLIP_RASTER_RETRY_SECONDS in sleeps
