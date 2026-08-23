import contextlib
from types import SimpleNamespace
import pytest
import numpy as np
from sqlalchemy.exc import SQLAlchemyError

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import watershed_routes
from wepppy.runtime_paths.errors import NoDirError
from wepppy.weppcloud.user_preferences import (
    AccountPreferenceSnapshot,
    PreferenceIdentityError,
    StoredPreferenceError,
    UserPreferenceValues,
)
import wepppy.weppcloud.user_preferences as preferences_module


pytestmark = pytest.mark.microservice


class _DummySubmissionLock:
    def acquire(self, **kwargs): return True
    def extend(self, *args, **kwargs): return True
    def release(self): return None


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(watershed_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(watershed_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(
        watershed_routes.Ron,
        "getInstance",
        lambda wd: type("RonStub", (), {"config_stem": "cfg"})(),
    )


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> list[dict]:
    from wepppy.rq import submission_recovery
    captured: list[dict] = []
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            captured.append({"args": kwargs.get("args"), "meta": kwargs.get("meta")})
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: job_id)
    return captured


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def get_rq_job_id(self, key): return None
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(watershed_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _install_wbt_submission_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    claims: dict,
    resolver,
) -> tuple[list[dict], object]:
    captured: list[dict] = []
    monkeypatch.setattr(
        watershed_routes,
        "require_jwt",
        lambda request, required_scopes=None: dict(claims),
    )
    monkeypatch.setattr(
        watershed_routes,
        "authorize_run_access",
        lambda request_claims, runid: None,
    )
    monkeypatch.setattr(
        watershed_routes,
        "resolve_account_preferences",
        resolver,
    )
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        watershed_routes,
        "_preflight_watershed_mutation_root",
        lambda _wd: None,
    )
    _stub_prep(monkeypatch)

    class DummyJob:
        id = "root-policy"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, func, args, **kwargs):
            captured.append(
                {
                    "func": func,
                    "args": args,
                    "meta": kwargs.get("meta"),
                }
            )
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_wbt = True
        wbt_boundary_touch_config_behavior = "warn"
        wbt_boundary_touch_behavior = "warn"

        def __init__(self) -> None:
            self.persist_calls = 0
            self.grouped_update_calls = []

        def persist_wbt_boundary_touch_config_behavior(self) -> None:
            self.persist_calls += 1

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    watershed = DummyWatershed()
    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(
        watershed_routes.redis,
        "Redis",
        lambda **kwargs: DummyRedis(),
    )
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: watershed,
    )
    return captured, watershed


def test_fetch_dem_missing_payload_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Expecting center, zoom, bounds, mcl, and csa"


def test_parse_map_change_derives_center_and_zoom_from_bounds_when_missing() -> None:
    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    error, args = watershed_routes._parse_map_change(payload)

    assert error is None
    assert args is not None
    extent, center, zoom, *_ = args
    assert extent == [-118.0, 46.5, -117.0, 47.0]
    assert center == [-117.5, 46.75]
    assert zoom == pytest.approx(watershed_routes.Map.zoom_for_extent(extent))


def test_parse_map_change_defaults_stream_pruning_method_to_ifolp() -> None:
    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    error, args = watershed_routes._parse_map_change(payload)

    assert error is None
    assert args is not None
    stream_pruning_method = args[5]
    assert stream_pruning_method == "ifolp"


def test_parse_map_change_accepts_legacy_stream_pruning_method() -> None:
    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
        "stream_pruning_method": "remove_short_streams",
    }

    error, args = watershed_routes._parse_map_change(payload)

    assert error is None
    assert args is not None
    stream_pruning_method = args[5]
    assert stream_pruning_method == "remove_short_streams"


def test_parse_map_change_rejects_unknown_stream_pruning_method() -> None:
    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
        "stream_pruning_method": "not_a_method",
    }

    error, args = watershed_routes._parse_map_change(payload)

    assert error is not None
    assert args is None
    body = error.body.decode("utf-8")
    assert "stream_pruning_method must be one of" in body


@pytest.mark.parametrize(
    "path",
    (
        "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
        "/api/runs/batch%3B%3Brun-1%3B%3B_base/cfg/fetch-dem-and-build-channels",
    ),
)
def test_fetch_dem_rejects_invalid_conditioning_before_any_mutation_or_queue(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(
        watershed_routes,
        "get_wd",
        lambda runid: pytest.fail("get_wd must not run for an invalid enum"),
    )
    monkeypatch.setattr(
        watershed_routes,
        "Queue",
        lambda *args, **kwargs: pytest.fail("Queue must not be created"),
    )

    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
        "wbt_fill_or_breach": "../../hostile",
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_wbt_fill_or_breach"


@pytest.mark.parametrize(
    ("path", "actual_config"),
    (
        (
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            "other.cfg",
        ),
        (
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            "",
        ),
        (
            "/api/runs/batch%3B%3Brun-1%3B%3Bchild/cfg/fetch-dem-and-build-channels",
            "other.cfg",
        ),
    ),
)
def test_fetch_dem_rejects_config_mismatch_before_watershed_or_queue_mutation(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    actual_config: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")
    calls = {"preflight": 0, "watershed": 0, "queue": 0}
    monkeypatch.setattr(
        watershed_routes.Ron,
        "getInstance",
        lambda wd: type("RonStub", (), {"config_stem": actual_config})(),
    )

    def preflight(wd: str) -> None:
        calls["preflight"] += 1

    monkeypatch.setattr(
        watershed_routes,
        "_preflight_watershed_mutation_root",
        preflight,
    )

    def get_watershed(wd: str):
        calls["watershed"] += 1
        return type("WatershedStub", (), {"run_group": "default"})()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        get_watershed,
    )

    class QueueStub:
        def __init__(self, *args, **kwargs) -> None:
            calls["queue"] += 1

    monkeypatch.setattr(
        watershed_routes,
        "Queue",
        QueueStub,
    )

    payload = {
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
        "wbt_fill_or_breach": "topaz",
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            path,
            json=payload,
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "run_config_mismatch"
    assert calls == {"preflight": 0, "watershed": 0, "queue": 0}


def test_fetch_dem_bounds_only_derives_center_and_zoom(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    enqueue = {"called": False, "func": None, "args": None}

    class DummyJob:
        id = "job-bounds-only"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, func, args, **kwargs):
            enqueue["called"] = True
            enqueue["func"] = func
            enqueue["args"] = args
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_wbt = False

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    bounds = [-118.0, 46.5, -117.0, 47.0]
    payload = {
        "map_bounds": bounds,
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-bounds-only"
    assert enqueue["called"] is True
    assert enqueue["func"] is watershed_routes.fetch_dem_and_build_channels_rq
    call_args = enqueue["args"]
    assert call_args is not None
    assert call_args[0] == "run-1"
    assert call_args[1] == bounds
    assert call_args[2] == [-117.5, 46.75]
    assert call_args[3] == pytest.approx(watershed_routes.Map.zoom_for_extent(bounds))
    assert call_args[6] == "ifolp"


def test_fetch_dem_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-42"


def test_fetch_dem_upload_mode_topaz_rejects_nodata_dem(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used when Topaz upload DEM has NoData values")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_topaz = True

    class DummyRon:
        config_stem = "cfg"
        map = object()
        has_dem = True
        dem_fn = "/tmp/run/dem/dem.vrt"

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes, "_dem_contains_nodata_values", lambda dem_path: True)

    payload = {
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 3,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "TOPAZ_UPLOAD_DEM_NODATA"
    assert body["error"]["message"] == (
        "TOPAZ requires maps without NoData values. Please start a new project with the "
        "WEPPcloud-WBT delineation backend"
    )
    assert queue_called["called"] is False


def test_fetch_dem_upload_mode_topaz_enqueues_when_dem_has_no_nodata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-topaz-ok")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_topaz = True

    class DummyRon:
        config_stem = "cfg"
        map = object()
        has_dem = True
        dem_fn = "/tmp/run/dem/dem.vrt"

    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes, "_dem_contains_nodata_values", lambda dem_path: False)

    payload = {
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 3,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-topaz-ok"


def test_fetch_dem_upload_mode_topaz_rejects_nodata_dem_for_batch_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "batch"
        delineation_backend_is_topaz = True

        @contextlib.contextmanager
        def locked(self):
            yield self

    class DummyRon:
        config_stem = "cfg"
        map = object()
        has_dem = True
        dem_fn = "/tmp/run/dem/dem.vrt"

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes, "_dem_contains_nodata_values", lambda dem_path: True)

    payload = {
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 3,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "TOPAZ_UPLOAD_DEM_NODATA"
    assert body["error"]["message"] == watershed_routes.TOPAZ_UPLOAD_DEM_NODATA_MESSAGE
    assert queue_called["called"] is False


def test_fetch_dem_upload_mode_topaz_returns_400_when_dem_scan_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_topaz = True

    class DummyRon:
        config_stem = "cfg"
        map = object()
        has_dem = True
        dem_fn = "/tmp/run/dem/dem.vrt"

    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())

    def _raise_scan_error(_dem_path):
        raise watershed_routes.UploadError("Unable to read validated DEM.")

    monkeypatch.setattr(watershed_routes, "_dem_contains_nodata_values", _raise_scan_error)

    payload = {
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 3,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["message"] == "Unable to read validated DEM."


def test_dem_contains_nodata_values_true_for_explicit_nodata(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyMaskBand:
        def ReadAsArray(self):
            return np.array([[255, 255], [255, 255]], dtype=np.uint8)

    class DummyBand:
        def GetNoDataValue(self):
            return -9999.0

        def ReadAsArray(self):
            return np.array([[1.0, 2.0], [-9999.0, 4.0]], dtype=np.float32)

        def GetMaskBand(self):
            return DummyMaskBand()

    class DummyDataset:
        def GetRasterBand(self, index):
            assert index == 1
            return DummyBand()

    monkeypatch.setattr(watershed_routes.gdal, "Open", lambda _path: DummyDataset())
    assert watershed_routes._dem_contains_nodata_values("/tmp/dem.vrt") is True


def test_dem_contains_nodata_values_true_for_masked_pixels(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyMaskBand:
        def ReadAsArray(self):
            return np.array([[255, 255], [0, 255]], dtype=np.uint8)

    class DummyBand:
        def GetNoDataValue(self):
            return None

        def ReadAsArray(self):
            return np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)

        def GetMaskBand(self):
            return DummyMaskBand()

    class DummyDataset:
        def GetRasterBand(self, index):
            assert index == 1
            return DummyBand()

    monkeypatch.setattr(watershed_routes.gdal, "Open", lambda _path: DummyDataset())
    assert watershed_routes._dem_contains_nodata_values("/tmp/dem.vrt") is True


def test_dem_contains_nodata_values_false_for_fully_valid_dem(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyMaskBand:
        def ReadAsArray(self):
            return np.array([[255, 255], [255, 255]], dtype=np.uint8)

    class DummyBand:
        def GetNoDataValue(self):
            return None

        def ReadAsArray(self):
            return np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)

        def GetMaskBand(self):
            return DummyMaskBand()

    class DummyDataset:
        def GetRasterBand(self, index):
            assert index == 1
            return DummyBand()

    monkeypatch.setattr(watershed_routes.gdal, "Open", lambda _path: DummyDataset())
    assert watershed_routes._dem_contains_nodata_values("/tmp/dem.vrt") is False


def test_set_outlet_requires_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/set-outlet", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "latitude and longitude must be provided as floats"


def test_set_outlet_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        @staticmethod
        def validate_outlet_location(_lng: float, _lat: float) -> None:
            return None

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda _wd: DummyWatershed(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-outlet",
            json={"latitude": 45.1, "longitude": -120.3},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-99"


def test_set_outlet_rejects_locations_outside_map_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        @staticmethod
        def validate_outlet_location(_lng: float, _lat: float) -> None:
            raise ValueError("Requested Outlet Location must be within map extent")

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda _wd: DummyWatershed(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-outlet",
            json={"latitude": 45.1, "longitude": -120.3},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Requested Outlet Location must be within map extent"


def test_set_outlet_requires_channels_before_setting_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        @staticmethod
        def validate_outlet_location(_lng: float, _lat: float) -> None:
            raise ValueError("Channels must be delineated before setting Outlet Location")

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda _wd: DummyWatershed(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-outlet",
            json={"latitude": 45.1, "longitude": -120.3},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Channels must be delineated before setting Outlet Location"


def test_upload_dem_requires_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: str(tmp_path))

    class DummyRon:
        dem_dir = str(tmp_path)

    class DummyWatershed:
        pass

    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/tasks/upload-dem/")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "input_upload_dem must be provided"
    assert payload["error"]["details"] == "input_upload_dem must be provided"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


def test_upload_dem_success(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: str(tmp_path))

    class DummyRon:
        dem_dir = str(tmp_path)

    class DummyWatershed:
        pass

    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        watershed_routes,
        "_install_uploaded_dem",
        lambda **kwargs: {"dem_filename": "uploaded.tif"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-dem/",
            files={"input_upload_dem": ("sample.tif", b"demo", "image/tiff")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["dem_filename"] == "uploaded.tif"


def test_upload_dem_rejects_oversize_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(watershed_routes, "UPLOAD_DEM_MAX_BYTES", 4)

    class DummyRon:
        dem_dir = str(tmp_path)

    class DummyWatershed:
        pass

    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(watershed_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        watershed_routes,
        "_install_uploaded_dem",
        lambda **kwargs: {"dem_filename": "uploaded.tif"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-dem/",
            files={"input_upload_dem": ("sample.tif", b"abcdef", "image/tiff")},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_validate_dem_dimensions_accepts_limit() -> None:
    class DummyDs:
        RasterXSize = watershed_routes.UPLOAD_DEM_MAX_DIMENSION
        RasterYSize = watershed_routes.UPLOAD_DEM_MAX_DIMENSION

    watershed_routes._validate_dem_dimensions(DummyDs())


def test_validate_dem_dimensions_rejects_larger_rasters() -> None:
    class DummyDs:
        RasterXSize = watershed_routes.UPLOAD_DEM_MAX_DIMENSION + 1
        RasterYSize = watershed_routes.UPLOAD_DEM_MAX_DIMENSION

    with pytest.raises(watershed_routes.UploadError, match="2560x2560"):
        watershed_routes._validate_dem_dimensions(DummyDs())


def test_validate_float_dem_rejects_int(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    class DummyBand:
        DataType = 1

    class DummyDs:
        @staticmethod
        def GetRasterBand(_index: int):
            return DummyBand()

    monkeypatch.setattr(watershed_routes.gdal, "Open", lambda _path: DummyDs())
    monkeypatch.setattr(watershed_routes.gdal, "GetDataTypeName", lambda _dtype: "Int32")

    dem_path = tmp_path / "dem.tif"
    dem_path.write_text("stub")

    with pytest.raises(watershed_routes.UploadError, match="floating point"):
        watershed_routes._validate_float_dem(dem_path)


def test_validate_float_dem_accepts_float64(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    class DummyBand:
        DataType = 1

    class DummyDs:
        @staticmethod
        def GetRasterBand(_index: int):
            return DummyBand()

    monkeypatch.setattr(watershed_routes.gdal, "Open", lambda _path: DummyDs())
    monkeypatch.setattr(watershed_routes.gdal, "GetDataTypeName", lambda _dtype: "Float64")

    dem_path = tmp_path / "dem.tif"
    dem_path.write_text("stub")

    watershed_routes._validate_float_dem(dem_path)


def test_build_subcatchments_enqueues_job_and_caps_mofe_max_ofes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_wbt = False

        def __init__(self) -> None:
            self.grouped_update_calls = []
            self.mofe_max_ofes = None

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)
            if "mofe_max_ofes" in kwargs:
                self.mofe_max_ofes = min(19, max(1, int(kwargs["mofe_max_ofes"])))

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )
    monkeypatch.setattr(
        watershed_routes,
        "resolve_account_preferences",
        lambda _claims: (_ for _ in ()).throw(
            AssertionError("Topaz paths must not resolve WBT preferences")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True, "mofe_max_ofes": "42"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert dummy_watershed.grouped_update_calls == []
    assert captured[0]["args"][1] == {
        "clip_hillslopes": True,
        "mofe_max_ofes": 42,
    }


def test_build_subcatchments_snapshots_initiating_users_boundary_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict] = []
    claims_by_user = {
        23: {"token_class": "user", "sub": "23"},
        24: {"token_class": "user", "sub": "24"},
    }
    claims_iter = iter(claims_by_user.values())
    monkeypatch.setattr(
        watershed_routes,
        "require_jwt",
        lambda request, required_scopes=None: next(claims_iter),
    )
    monkeypatch.setattr(
        watershed_routes,
        "authorize_run_access",
        lambda request_claims, runid: None,
    )
    monkeypatch.setattr(
        watershed_routes,
        "resolve_account_preferences",
        lambda request_claims: AccountPreferenceSnapshot(
            actor_token_class="user",
            user_id=int(request_claims["sub"]),
            preferences=UserPreferenceValues(
                "si",
                "error" if request_claims["sub"] == "23" else "warn",
            ),
        ),
    )
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")
    _stub_prep(monkeypatch)

    class DummyJob:
        id = "root-policy"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, func, args, **kwargs):
            captured.append(
                {
                    "func": func,
                    "args": args,
                    "meta": kwargs.get("meta"),
                }
            )
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_wbt = True
        wbt_boundary_touch_config_behavior = "warn"
        wbt_boundary_touch_behavior = "error"

        def __init__(self) -> None:
            self.persist_calls = 0
            self.grouped_update_calls = []

        def persist_wbt_boundary_touch_config_behavior(self) -> None:
            self.persist_calls += 1

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    watershed = DummyWatershed()
    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(
        watershed_routes.redis,
        "Redis",
        lambda **kwargs: DummyRedis(),
    )
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: watershed,
    )

    with TestClient(rq_engine.app) as client:
        first_response = client.post(
            "/api/runs/shared-run/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )
        second_response = client.post(
            "/api/runs/shared-run/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert captured[0]["args"] == (
        "shared-run",
        {"clip_hillslopes": True},
        {
            "schema_version": 1,
            "effective_policy": "error",
            "source": "user_preference",
        },
    )
    assert captured[0]["meta"] == {
        "runid": "shared-run",
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: {
            "schema_version": 1,
            "runid": "shared-run",
            "actor_token_class": "user",
            "actor_user_id": 23,
            "config_policy": "warn",
            "effective_policy": "error",
            "source": "user_preference",
        }
    }
    assert captured[1]["args"] == (
        "shared-run",
        {"clip_hillslopes": True},
        {
            "schema_version": 1,
            "effective_policy": "warn",
            "source": "user_preference",
        },
    )
    assert captured[1]["meta"] == {
        "runid": "shared-run",
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: {
            "schema_version": 1,
            "runid": "shared-run",
            "actor_token_class": "user",
            "actor_user_id": 24,
            "config_policy": "warn",
            "effective_policy": "warn",
            "source": "user_preference",
        }
    }
    assert captured[0]["args"][2]["effective_policy"] == "error"
    assert watershed.wbt_boundary_touch_behavior == "error"
    assert watershed.wbt_boundary_touch_config_behavior == "warn"
    assert watershed.persist_calls == 0
    assert watershed.grouped_update_calls == []


def test_build_subcatchments_snapshots_account_session_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, watershed = _install_wbt_submission_harness(
        monkeypatch,
        claims={"token_class": "session", "user_id": 31},
        resolver=lambda _claims: AccountPreferenceSnapshot(
            actor_token_class="session",
            user_id=31,
            preferences=UserPreferenceValues("config", "error"),
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/session-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )

    assert response.status_code == 200
    assert captured[0]["args"][2] == {
        "schema_version": 1,
        "effective_policy": "error",
        "source": "user_preference",
    }
    assert captured[0]["meta"][
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY
    ]["actor_token_class"] == "session"
    assert captured[0]["meta"][
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY
    ]["actor_user_id"] == 31
    assert watershed.persist_calls == 0


@pytest.mark.parametrize(
    "claims",
    (
        {"token_class": "service", "sub": "service-1"},
        {"token_class": "mcp", "sub": "mcp-1"},
        {"token_class": "session"},
    ),
)
def test_build_subcatchments_non_account_identity_uses_project_policy(
    monkeypatch: pytest.MonkeyPatch,
    claims: dict,
) -> None:
    captured, watershed = _install_wbt_submission_harness(
        monkeypatch,
        claims=claims,
        resolver=preferences_module.resolve_account_preferences,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/fallback-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )

    assert response.status_code == 200
    assert captured[0]["args"] == ("fallback-run", {}, None)
    assert captured[0]["meta"] == {"runid": "fallback-run"}
    assert watershed.persist_calls == 0


@pytest.mark.parametrize(
    "failure",
    (
        PreferenceIdentityError("inactive or deleted user"),
        PreferenceIdentityError("malformed session user_id"),
        StoredPreferenceError("stored preference token is invalid"),
        SQLAlchemyError("preference database unavailable"),
    ),
)
def test_build_subcatchments_preference_resolution_failure_creates_no_job(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    captured, watershed = _install_wbt_submission_harness(
        monkeypatch,
        claims={"token_class": "user", "sub": "41"},
        resolver=lambda _claims: (_ for _ in ()).throw(failure),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/failure-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "preference_resolution_failed"
    assert payload["error"]["message"] == "Could not resolve user preferences."
    assert payload["error_id"]
    assert captured == []
    assert watershed.persist_calls == 0
    assert watershed.grouped_update_calls == []


def test_build_subcatchments_denied_access_never_reads_user_preferences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        watershed_routes,
        "require_jwt",
        lambda request, required_scopes=None: {
            "token_class": "user",
            "sub": "63",
        },
    )
    monkeypatch.setattr(
        watershed_routes,
        "authorize_run_access",
        lambda _claims, _runid: (_ for _ in ()).throw(
            watershed_routes.AuthError(
                "Run access denied.",
                status_code=403,
                code="forbidden",
            )
        ),
    )
    monkeypatch.setattr(
        watershed_routes,
        "resolve_account_preferences",
        lambda _claims: (_ for _ in ()).throw(
            AssertionError("preferences must be read only after authorization")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/private-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_build_subcatchments_fresh_submission_refreshes_same_users_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferences = iter(
        (
            UserPreferenceValues("config", "error"),
            UserPreferenceValues("config", "warn"),
        )
    )
    captured, watershed = _install_wbt_submission_harness(
        monkeypatch,
        claims={"token_class": "user", "sub": "52"},
        resolver=lambda _claims: AccountPreferenceSnapshot(
            actor_token_class="user",
            user_id=52,
            preferences=next(preferences),
        ),
    )

    with TestClient(rq_engine.app) as client:
        first = client.post(
            "/api/runs/fresh-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )
        second = client.post(
            "/api/runs/fresh-run/cfg/build-subcatchments-and-abstract-watershed",
            json={},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    first_meta = captured[0]["meta"][
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY
    ]
    second_meta = captured[1]["meta"][
        watershed_routes.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY
    ]
    assert first_meta["actor_user_id"] == second_meta["actor_user_id"] == 52
    assert first_meta["effective_policy"] == "error"
    assert second_meta["effective_policy"] == "warn"
    assert captured[0]["args"][2]["effective_policy"] == "error"
    assert captured[1]["args"][2]["effective_policy"] == "warn"
    assert watershed.wbt_boundary_touch_behavior == "warn"
    assert watershed.persist_calls == 0


def test_build_subcatchments_active_conflict_does_not_mutate_run_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, watershed = _install_wbt_submission_harness(
        monkeypatch,
        claims={"token_class": "user", "sub": "52"},
        resolver=lambda _claims: AccountPreferenceSnapshot(
            actor_token_class="user",
            user_id=52,
            preferences=UserPreferenceValues("config", "warn"),
        ),
    )
    removed_timestamps: list[object] = []
    prep = SimpleNamespace(
        remove_timestamp=lambda task: removed_timestamps.append(task),
    )
    monkeypatch.setattr(watershed_routes.RedisPrep, "getInstance", lambda wd: prep)
    enqueue_kwargs: dict[str, object] = {}

    def _reject_active(*args, **kwargs):
        enqueue_kwargs.update(kwargs)
        raise watershed_routes.RqSubmissionConflict("active")

    monkeypatch.setattr(watershed_routes, "enqueue_tracked_rq_job", _reject_active)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/fresh-run/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "job_active"
    assert captured == []
    assert watershed.persist_calls == 0
    assert watershed.grouped_update_calls == []
    assert removed_timestamps == []
    assert enqueue_kwargs["args"][1] == {"clip_hillslopes": True}
    boundary = enqueue_kwargs["excluded_dependency_job_ids"]
    candidate = SimpleNamespace(
        meta={"wbt_subcatchment_admission_previous": "prior-build"}
    )
    assert tuple(boundary(candidate)) == ("prior-build",)


def test_build_subcatchments_forwards_all_grouped_update_fields_with_coercion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-grouped-fields")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.grouped_update_calls = []

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    payload = {
        "clip_hillslopes": "true",
        "walk_flowpaths": 0,
        "clip_hillslope_length": "125.5",
        "mofe_target_length": 80,
        "mofe_buffer": "off",
        "mofe_buffer_length": "35.25",
        "mofe_max_ofes": "9",
        "bieger2015_widths": 1,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-grouped-fields"
    assert dummy_watershed.grouped_update_calls == []
    grouped_updates = captured[0]["args"][1]
    assert grouped_updates["clip_hillslopes"] is True
    assert grouped_updates["walk_flowpaths"] is False
    assert grouped_updates["clip_hillslope_length"] == pytest.approx(125.5)
    assert grouped_updates["mofe_target_length"] == pytest.approx(80.0)
    assert grouped_updates["mofe_buffer"] is False
    assert grouped_updates["mofe_buffer_length"] == pytest.approx(35.25)
    assert grouped_updates["mofe_max_ofes"] == 9
    assert grouped_updates["bieger2015_widths"] is True


def test_build_subcatchments_caps_mofe_max_ofes_floor_to_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-78")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.grouped_update_calls = []
            self.mofe_max_ofes = None

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)
            if "mofe_max_ofes" in kwargs:
                self.mofe_max_ofes = min(19, max(1, int(kwargs["mofe_max_ofes"])))

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True, "mofe_max_ofes": 0},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-78"
    assert dummy_watershed.grouped_update_calls == []
    assert captured[0]["args"][1]["mofe_max_ofes"] == 0


def test_build_subcatchments_ignores_non_finite_mofe_max_ofes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-79")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.grouped_update_calls = []
            self.mofe_max_ofes = 7

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)
            if "mofe_max_ofes" in kwargs:
                self.mofe_max_ofes = min(19, max(1, int(kwargs["mofe_max_ofes"])))

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            content='{"clip_hillslopes": true, "mofe_max_ofes": 1e309}',
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-79"
    assert dummy_watershed.grouped_update_calls == []
    assert "mofe_max_ofes" not in captured[0]["args"][1]
    assert dummy_watershed.mofe_max_ofes == 7


def test_build_subcatchments_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "batch"
        delineation_backend_is_wbt = True

        def __init__(self) -> None:
            self.grouped_update_calls = []

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )
    monkeypatch.setattr(
        watershed_routes,
        "resolve_account_preferences",
        lambda _claims: (_ for _ in ()).throw(
            AssertionError("Batch paths must not resolve WBT preferences")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set subcatchment inputs for batch processing"
    assert queue_called["called"] is False
    assert len(dummy_watershed.grouped_update_calls) == 1
    assert dummy_watershed.grouped_update_calls[0]["clip_hillslopes"] is True


def test_fetch_dem_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "batch"
        delineation_backend_is_wbt = False

        def __init__(self) -> None:
            self._uploaded_dem_filename = "uploaded.tif"

        @contextlib.contextmanager
        def locked(self):
            yield self

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set watershed inputs for batch processing"
    assert queue_called["called"] is False
    assert dummy_watershed._uploaded_dem_filename is None


def test_fetch_dem_batch_upload_mode_preserves_uploaded_dem_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "batch"
        delineation_backend_is_wbt = False

        def __init__(self) -> None:
            self._uploaded_dem_filename = "uploaded.tif"

        @contextlib.contextmanager
        def locked(self):
            yield self

    class DummyRon:
        config_stem = "cfg"
        map = object()
        has_dem = True
        dem_fn = "/tmp/run/dem/dem.vrt"

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )
    monkeypatch.setattr(watershed_routes.Ron, "getInstance", lambda wd: DummyRon())

    payload = {
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 3,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set watershed inputs for batch processing"
    assert queue_called["called"] is False
    assert dummy_watershed._uploaded_dem_filename == "uploaded.tif"


def test_fetch_dem_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for _base runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = ""
        delineation_backend_is_wbt = False

        @contextlib.contextmanager
        def locked(self):
            yield self

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set watershed inputs for batch processing"
    assert queue_called["called"] is False


def test_fetch_dem_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for runid ;;_base runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = ""
        delineation_backend_is_wbt = False

        @contextlib.contextmanager
        def locked(self):
            yield self

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set watershed inputs for batch processing"
    assert queue_called["called"] is False


def test_fetch_dem_returns_400_for_minimum_channel_length_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            raise watershed_routes.MinimumChannelLengthTooShortError()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"
        delineation_backend_is_wbt = False

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "MinimumChannelLengthTooShortError"
    assert "MINIMUM CHANNEL LENGTH" in payload["error"]["details"]


def test_build_subcatchments_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for _base runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = ""

        def __init__(self) -> None:
            self.grouped_update_calls = []

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set subcatchment inputs for batch processing"
    assert queue_called["called"] is False
    assert len(dummy_watershed.grouped_update_calls) == 1
    assert dummy_watershed.grouped_update_calls[0]["clip_hillslopes"] is True


def test_build_subcatchments_returns_400_for_boundary_touches_edge_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            raise watershed_routes.WatershedBoundaryTouchesEdgeError()

    class DummyRedis:
        def lock(self, *args, **kwargs): return _DummySubmissionLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"

        def apply_build_subcatchment_updates(self, **kwargs) -> None:
            return None

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "WatershedBoundaryTouchesEdgeError"
    assert "WATERSHED BOUNDARY TOUCHES THE EDGE OF THE DEM" in payload["error"]["details"]


def test_fetch_dem_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    def _raise_nodir(_wd: str) -> None:
        raise NoDirError(http_status=500, code="NODIR_INVALID_ARCHIVE", message="invalid")

    monkeypatch.setattr(
        watershed_routes,
        "_preflight_watershed_mutation_root",
        _raise_nodir,
    )

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "mcl": 60,
        "csa": 5,
        "set_extent_mode": 0,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json=payload)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "NODIR_INVALID_ARCHIVE"


def test_set_outlet_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str) -> None:
        raise NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")

    monkeypatch.setattr(
        watershed_routes,
        "_preflight_watershed_mutation_root",
        _raise_nodir,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-outlet",
            json={"latitude": 45.1, "longitude": -120.3},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NODIR_LOCKED"


def test_build_subcatchments_propagates_nodir_preflight_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str) -> None:
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(
        watershed_routes,
        "_preflight_watershed_mutation_root",
        _raise_nodir,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"
