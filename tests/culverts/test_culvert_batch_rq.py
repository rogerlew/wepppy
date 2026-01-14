from __future__ import annotations

import json
from pathlib import Path

import pytest

import wepppy.rq.culvert_rq as culvert_rq_module
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
