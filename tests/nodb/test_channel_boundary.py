"""Exercise channel boundary policies against real project settings and assets."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from pathlib import Path

import pytest

from tests.rq.test_rq212_lifecycle import lifecycle  # noqa: F401

from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.core import channel_boundary
from wepppy.nodb.core.channel_boundary import ChannelBoundaryError, validate_channel_extent

pytestmark = pytest.mark.integration

INSIDE = [-116.99, 47.01, -116.98, 47.02]
PARTIAL = [-117.01, 47.01, -116.98, 47.02]
OUTSIDE = [-117.03, 47.01, -117.02, 47.02]


def _polygon(min_x, min_y, max_x, max_y):
    return [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y], [min_x, min_y]]


@pytest.fixture
def boundary_root(tmp_path, monkeypatch):
    root = tmp_path / "static"
    root.mkdir()
    monkeypatch.setattr(channel_boundary, "_STATIC_ROOT", root)
    (root / "area.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [
                    _polygon(-117, 47, -116.9, 47.1),
                    _polygon(-116.96, 47.04, -116.94, 47.06),
                ]},
            },
            {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": [
                    [_polygon(-116.9, 47, -116.8, 47.1)],
                    [_polygon(-116.7, 47, -116.6, 47.1)],
                ]},
            },
        ],
    }))
    return root


@pytest.fixture
def run_config(tmp_path):
    def create(*, boundary='"/static/area.geojson"', setting="", backend="wbt"):
        wd = tmp_path / f"run-{uuid4().hex}"
        wd.mkdir()
        config = "boundary-test.cfg"
        value = f"boundary = {boundary}\n" if boundary is not None else ""
        (wd / config).write_text(
            f"[general]\ncellsize = 30\n[map]\n{value}{setting}\n[watershed]\ndelineation_backend = {backend}\n"
        )
        ron = Ron(str(wd), config, initialize_components=False)
        return ron, config
    return create


@pytest.mark.parametrize(
    ("setting", "extent", "admitted"),
    [
        ("", PARTIAL, True),
        ("boundary_check = ", PARTIAL, True),
        ("boundary_check", PARTIAL, True),
        ("boundary_check = intersects", OUTSIDE, False),
        ("boundary_check = intersects", [-117.01, 46.99, -117, 47], True),
        ("boundary_check = intersects", [-116.959, 47.049, -116.951, 47.051], False),
        ('boundary_check = "CoVeRs"', INSIDE, True),
        ("boundary_check = covers", [-117, 47, -116.98, 47.02], True),
        ("boundary_check = covers", [-116.91, 47.01, -116.89, 47.02], True),
        ("boundary_check = covers", [-116.95, 47.02, -116.89, 47.08], False),
        ("boundary_check = covers", [-116.71, 47.02, -116.61, 47.08], False),
        ("boundary_check = covers", PARTIAL, False),
    ],
)
def test_geometric_policy(boundary_root, run_config, setting, extent, admitted):
    ron, _ = run_config(setting=setting)
    if admitted:
        validate_channel_extent(ron, extent)
    else:
        with pytest.raises(ChannelBoundaryError, match="Choose an extent") as rejected:
            validate_channel_extent(ron, extent)
        assert rejected.value.code == "channel_extent_outside_boundary"


@pytest.mark.parametrize(
    ("reference", "setting"),
    [
        (None, "boundary_check = covers"),
        ('"None"', "boundary_check = covers"),
        ('""', "boundary_check = covers"),
        ("static/missing.geojson", 'boundary_check = "NONE"'),
    ],
)
def test_bypass_uses_config_and_skips_geometry(run_config, reference, setting, monkeypatch):
    ron, _ = run_config(boundary=reference, setting=setting)

    def unexpected(_):
        pytest.fail("Boundary asset was resolved despite bypass")

    monkeypatch.setattr(channel_boundary, "_read_boundary", unexpected)
    # A run overlay carries no policy even if it looks like a static asset.
    ron._boundary = "/static/area.geojson"
    validate_channel_extent(ron, OUTSIDE)


@pytest.mark.parametrize(
    ("reference", "setting"),
    [
        ("static/missing.geojson", ""),
        ("static/escape.geojson", ""),
        ("static/../outside.geojson", ""),
        ("static//etc/passwd", ""),
        ("https://example.org/area.geojson", ""),
        ("static/invalid.geojson", ""),
        ("static/area.geojson", "boundary_check = typo"),
    ],
)
def test_invalid_config_is_safe(tmp_path, boundary_root, run_config, reference, setting):
    outside = tmp_path / "outside.geojson"
    outside.write_bytes((boundary_root / "area.geojson").read_bytes())
    (boundary_root / "escape.geojson").symlink_to(outside)
    (boundary_root / "invalid.geojson").write_text('{"type":"Feature","geometry":null}')
    ron, _ = run_config(boundary=reference, setting=setting)
    with pytest.raises(ChannelBoundaryError) as failure:
        validate_channel_extent(ron, INSIDE)
    assert failure.value.status_code == 500
    assert failure.value.code == "invalid_channel_boundary_config"
    assert reference not in str(failure.value)


@pytest.mark.parametrize("backend", ["wbt", "topaz"])
def test_direct_build_rejects_before_writing_watershed_state(boundary_root, run_config, backend):
    ron, config = run_config(setting="boundary_check = covers", backend=backend)
    ron.set_map(PARTIAL, [-116.995, 47.015], 13)
    watershed = Watershed(ron.wd, config)
    dump = Path(watershed.wd) / "watershed.nodb"
    prior = dump.read_bytes()
    with pytest.raises(ChannelBoundaryError) as rejected:
        watershed.build_channels(csa=17, mcl=25)
    assert rejected.value.code == "channel_extent_outside_boundary"
    assert dump.read_bytes() == prior


@pytest.mark.parametrize("asset, extent", [
    ("lt/lt_basin.json", [-120.14, 39.08, -120.13, 39.09]),
    ("cda/cda_basin.json", [-116.79, 47.51, -116.78, 47.52]),
    ("portland/portland_boundary.json", [-121.989, 45.490, -121.986, 45.492]),
    ("seattle/seattle_boundary.json", [-121.700, 47.359, -121.697, 47.361]),
])
def test_shipped_boundary_loads(run_config, asset, extent):
    ron, _ = run_config(boundary=f"static/mods/{asset}")
    validate_channel_extent(ron, extent)


def _write_dem(path, west, north=47.085, *, epsg=32611):
    import numpy as np
    from osgeo import gdal, osr
    from pyproj import Transformer

    side = 48
    x, y = Transformer.from_crs(4326, epsg, always_xy=True).transform(west, north)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(epsg)
    raster = gdal.GetDriverByName("GTiff").Create(str(path), side, side, 1, gdal.GDT_Float32)
    raster.SetGeoTransform((x, 30, 0, y, 0, -30))
    raster.SetProjection(crs.ExportToWkt())
    rows, cols = np.indices((side, side))
    raster.GetRasterBand(1).WriteArray((500 - rows * 2 + np.abs(cols - side // 2)).astype(np.float32))


def test_uploaded_dem_extent_includes_all_projected_edges(boundary_root, run_config):
    # This boundary includes the opposite-corner bounds but omits the NW edge.
    boundary = _polygon(-121.81, 47.28, -121.77, 47.2999)
    (boundary_root / "area.geojson").write_text(
        json.dumps({"type": "Polygon", "coordinates": [boundary]})
    )
    ron, _ = run_config(setting="boundary_check = covers")
    _write_dem(ron.dem_fn, -121.8, 47.3, epsg=32610)
    with pytest.raises(ChannelBoundaryError, match="fits entirely"):
        validate_channel_extent(ron, use_dem_extent=True)


@pytest.mark.parametrize("extent", [[], [0, 0, float("inf"), 1], [1, 0, 0, 1], [0, 0, "east", 1]])
def test_invalid_extent_returns_safe_error(boundary_root, run_config, extent):
    ron, _ = run_config()
    with pytest.raises(ChannelBoundaryError) as rejected:
        validate_channel_extent(ron, extent)
    assert rejected.value.code == "invalid_channel_extent"


@pytest.mark.parametrize("mode", [0, 1, 2, 3])
def test_route_uses_effective_extent_before_mutation(boundary_root, run_config, mode, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from wepppy.microservices.rq_engine import watershed_routes

    ron, config = run_config(setting="boundary_check = covers")
    Watershed(ron.wd, config)
    ron.set_map(INSIDE, [-116.985, 47.015], 13)
    if mode == 3:
        _write_dem(ron.dem_fn, -117.025)
    dumps = [Path(ron.wd) / name for name in ("ron.nodb", "watershed.nodb")]
    before = [path.read_bytes() for path in dumps]
    mutations = []
    jobs = []
    monkeypatch.setattr(watershed_routes, "get_wd", lambda _: ron.wd)
    monkeypatch.setattr(watershed_routes, "require_jwt", lambda *args, **kwargs: {})
    monkeypatch.setattr(watershed_routes, "authorize_run_access", lambda *args: None)
    monkeypatch.setattr(watershed_routes.RedisPrep, "getInstance", lambda _: SimpleNamespace(
        remove_timestamp=mutations.append,
    ))

    class Redis:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: Redis())
    monkeypatch.setattr(watershed_routes, "Queue", lambda **kwargs: object())

    def enqueue(*args, **kwargs):
        jobs.append(kwargs["args"])
        return SimpleNamespace(id="channel-job")

    monkeypatch.setattr(watershed_routes, "enqueue_tracked_rq_job", enqueue)
    path = f"/runs/run/{ron.config_stem}/fetch-dem-and-build-channels"
    app = FastAPI()
    app.include_router(watershed_routes.router)

    def submit(client, extent):
        payload = {"mcl": 60, "csa": 5, "set_extent_mode": mode, "map_bounds": extent}
        if mode == 2:
            payload["map_bounds"] = INSIDE if extent == PARTIAL else PARTIAL
            payload["map_object"] = {"extent": extent, "center": [-116.99, 47.015], "zoom": 13}
        return client.post(path, json=payload)

    with TestClient(app) as client:
        rejected = submit(client, INSIDE if mode == 3 else PARTIAL)
        assert rejected.status_code == 400
        assert rejected.json()["error"]["code"] == "channel_extent_outside_boundary"
        assert "fits entirely" in rejected.json()["error"]["message"]
        assert not mutations and not jobs
        assert [path.read_bytes() for path in dumps] == before

        if mode == 3:
            _write_dem(ron.dem_fn, -116.99)
            ron.set_map(OUTSIDE, [-117.025, 47.015], 13)
        admitted = submit(client, PARTIAL if mode == 3 else INSIDE)
        assert admitted.status_code == 200
        assert admitted.json() == {"job_id": "channel-job"}
        assert len(jobs) == 1 and len(mutations) == (1 if mode == 3 else 2)
        if mode != 3:
            assert jobs[0][1] == INSIDE


def test_uploaded_dem_builds_channels_and_rejection_preserves_map_artifact(
    boundary_root, run_config, monkeypatch, tmp_path, lifecycle,
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from osgeo import gdal

    import redis
    from rq import Queue, SimpleWorker
    from rq.job import Job

    from wepppy.microservices.rq_engine import watershed_routes
    from wepppy.nodb import redis_prep
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
    from wepppy.rq import exception_logging, project_rq, submission_recovery
    from wepppy.rq.job_info import recursive_get_job_details
    from wepppy.weppcloud.utils import helpers

    ron, config = run_config(setting="boundary_check = covers")
    watershed = Watershed(ron.wd, config)
    connection = lifecycle.connection
    socket = connection.connection_pool.connection_kwargs["path"]
    prep_connection = redis.StrictRedis(unix_socket_path=socket, db=0, decode_responses=True)
    monkeypatch.setattr(redis_prep, "redis_client", lambda *args, **kwargs: prep_connection)
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path / "leases"))
    prep = RedisPrep.getInstance(ron.wd)

    source = tmp_path / "source.tif"
    outside = tmp_path / "outside.tif"
    _write_dem(source, -116.99)
    _write_dem(outside, -117.025)

    monkeypatch.setattr(watershed_routes, "get_wd", lambda _: ron.wd)
    monkeypatch.setattr(watershed_routes, "require_jwt", lambda *args, **kwargs: {})
    monkeypatch.setattr(watershed_routes, "authorize_run_access", lambda *args: None)
    monkeypatch.setattr(project_rq, "get_wd", lambda _: ron.wd)
    monkeypatch.setattr(exception_logging, "get_wd", lambda _: ron.wd)
    monkeypatch.setattr(helpers, "get_wd", lambda _: ron.wd)

    def rq_connection(**kwargs):
        return redis.StrictRedis(unix_socket_path=socket, db=2)

    def native_queue(*, connection):
        return Queue(lifecycle.queue.name, connection=connection)

    for module in (watershed_routes, project_rq):
        monkeypatch.setattr(module, "redis", SimpleNamespace(Redis=rq_connection))
        monkeypatch.setattr(module, "Queue", native_queue)
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *args: None)
    app = FastAPI()
    app.include_router(watershed_routes.router)
    base = f"/runs/{ron.runid}/{ron.config_stem}"

    with TestClient(app) as client:
        uploaded = client.post(
            base + "/tasks/upload-dem/",
            files={"input_upload_dem": ("valley.tif", source.read_bytes(), "image/tiff")},
        )
        assert uploaded.status_code == 200, uploaded.json()
        extent = uploaded.json()["result"]["extent"]
        persisted = Ron.getInstance(ron.wd)
        assert persisted.extent == extent
        validate_channel_extent(persisted, use_dem_extent=True)
        dem = gdal.Open(persisted.dem_fn)
        assert dem.GetFileList()[0].endswith("dem.vrt")
        assert any(path.endswith("valley.tif") for path in dem.GetFileList())
        assert dem.ReadAsArray().shape == (48, 48)
        dem = None

        payload = {"mcl": 30, "csa": 1, "set_extent_mode": 3, "wbt_fill_or_breach": "fill"}
        path = base + "/fetch-dem-and-build-channels"
        accepted = client.post(path, json=payload)
        assert accepted.status_code == 200, accepted.json()
        assert SimpleWorker([lifecycle.queue], connection=connection).work(burst=True)
        root = Job.fetch(accepted.json()["job_id"], connection=connection)
        assert root.is_finished, root.exc_info
        child = Job.fetch(root.meta["jobs:0,func:build_channels_rq"], connection=connection)
        assert child.is_finished, child.exc_info
        assert prep[str(TaskEnum.build_channels)] is not None
        grid = gdal.Open(watershed.netful)
        streams = grid.ReadAsArray()
        assert streams.shape == (48, 48)
        assert (streams > 0).any()
        grid = None
        display_file = Path(watershed.netful_shp)
        display_asset = display_file.read_bytes()
        assert json.loads(display_asset)["features"]

        channel_checkpoint = prep[str(TaskEnum.build_channels)]
        blocked = client.post(path, json={
            "mcl": 30, "csa": 1, "set_extent_mode": 1, "map_bounds": OUTSIDE,
        })
        assert blocked.status_code == 400
        assert blocked.json()["error"]["code"] == "channel_extent_outside_boundary"
        assert prep[str(TaskEnum.build_channels)] == channel_checkpoint
        assert lifecycle.queue.count == 0
        assert Ron.getInstance(ron.wd).extent == extent
        assert display_file.read_bytes() == display_asset

        # Simulate a saved extent change between submission and the locked worker.
        accepted = client.post(path, json=payload)
        assert accepted.status_code == 200
        uploaded = client.post(
            base + "/tasks/upload-dem/",
            files={"input_upload_dem": ("outside.tif", outside.read_bytes(), "image/tiff")},
        )
        assert uploaded.status_code == 200, uploaded.json()
        Ron.getInstance(ron.wd).set_map(INSIDE, [-116.985, 47.015], 13)
        assert SimpleWorker([lifecycle.queue], connection=connection).work(burst=True)
        root = Job.fetch(accepted.json()["job_id"], connection=connection)
        child = Job.fetch(root.meta["jobs:0,func:build_channels_rq"], connection=connection)
        assert child.is_failed
        detail = recursive_get_job_details(child, connection, datetime.now(timezone.utc))
        assert detail["error"] == {
            "code": "channel_extent_outside_boundary",
            "message": "Choose an extent or upload a DEM that fits entirely within the project map boundary.",
            "details": {},
        }
        assert detail["exc_info"] is None and detail["error_id"]
        assert display_file.read_bytes() == display_asset
    prep_connection.close()
