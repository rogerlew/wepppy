import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import watershed_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(watershed_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(watershed_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(watershed_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_fetch_dem_missing_payload_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fetch-dem-and-build-channels", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Expecting center, zoom, bounds, mcl, and csa"


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

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-outlet",
            json={"latitude": 45.1, "longitude": -120.3},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-99"


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


def test_build_subcatchments_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

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

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
