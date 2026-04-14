import contextlib
import pytest
import numpy as np

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import watershed_routes
from wepppy.runtime_paths.errors import NoDirError


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


def test_fetch_dem_bounds_only_derives_center_and_zoom(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    enqueue = {"called": False, "func": None, "args": None}

    class DummyJob:
        id = "job-bounds-only"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, func, args, **kwargs):
            enqueue["called"] = True
            enqueue["func"] = func
            enqueue["args"] = args
            return DummyJob()

    class DummyRedis:
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
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.mofe_max_ofes = None

    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: dummy_watershed,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True, "mofe_max_ofes": "42"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert dummy_watershed.mofe_max_ofes == 19


def test_build_subcatchments_caps_mofe_max_ofes_floor_to_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-78")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.mofe_max_ofes = None

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
    assert dummy_watershed.mofe_max_ofes == 1


def test_build_subcatchments_ignores_non_finite_mofe_max_ofes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-79")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        run_group = "default"

        def __init__(self) -> None:
            self.mofe_max_ofes = 7

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

    assert response.status_code == 200
    assert response.json()["message"] == "Set subcatchment inputs for batch processing"
    assert queue_called["called"] is False


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
            "/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set watershed inputs for batch processing"
    assert queue_called["called"] is False


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
            pass

        def enqueue_call(self, *args, **kwargs):
            raise watershed_routes.MinimumChannelLengthTooShortError()

    class DummyRedis:
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

    monkeypatch.setattr(watershed_routes, "Queue", DummyQueue)
    monkeypatch.setattr(watershed_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        watershed_routes.Watershed,
        "getInstance",
        lambda wd: DummyWatershed(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/build-subcatchments-and-abstract-watershed",
            json={"clip_hillslopes": True},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set subcatchment inputs for batch processing"
    assert queue_called["called"] is False


def test_build_subcatchments_returns_400_for_boundary_touches_edge_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(watershed_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            raise watershed_routes.WatershedBoundaryTouchesEdgeError()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyWatershed:
        run_group = "default"

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
