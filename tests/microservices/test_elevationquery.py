import importlib
from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

TestClient = pytest.importorskip("starlette.testclient").TestClient


@pytest.fixture
def load_service(monkeypatch):
    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.elevationquery as module

        return importlib.reload(module)

    return _loader


def _write_dem(path: Path, data: np.ndarray) -> None:
    transform = from_origin(-120.0, 50.0, 0.001, 0.001)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dataset:
        dataset.write(data, 1)


def test_returns_elevation_from_run_dem(tmp_path: Path, monkeypatch, load_service):
    dem_dir = tmp_path / "dem"
    dem_dir.mkdir()
    dem_path = dem_dir / "dem.tif"
    data = np.array(
        [
            [100.0, 101.0],
            [102.0, 103.0],
        ],
        dtype=np.float32,
    )
    _write_dem(dem_path, data)

    module = load_service(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(module, "get_wd", lambda runid, prefer_active=False: str(tmp_path))

    app = module.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/weppcloud/runs/demo/default/elevationquery/",
            json={"lat": 49.9995, "lng": -119.9995},
        )

    payload = response.json()
    assert payload["Elevation"] == pytest.approx(100.0)
    assert payload["Units"] == "m"
    assert payload["Latitude"] == pytest.approx(49.9995)
    assert payload["Longitude"] == pytest.approx(-119.9995)
    assert "Error" not in payload


def test_reports_missing_dem(tmp_path: Path, monkeypatch, load_service):
    module = load_service(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(module, "get_wd", lambda runid, prefer_active=False: str(tmp_path))

    app = module.create_app()

    with TestClient(app) as client:
        response = client.get(
            "/weppcloud/runs/demo/default/elevationquery/?lat=45.0&lng=-116.0",
        )

    payload = response.json()
    assert payload["Elevation"] is None
    assert "dem" in payload["Error"].lower()


def test_returns_error_for_out_of_bounds_query(tmp_path: Path, monkeypatch, load_service):
    dem_dir = tmp_path / "dem"
    dem_dir.mkdir()
    dem_path = dem_dir / "dem.tif"
    data = np.ones((2, 2), dtype=np.float32) * 100.0
    _write_dem(dem_path, data)

    module = load_service(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(module, "get_wd", lambda runid, prefer_active=False: str(tmp_path))

    app = module.create_app()

    with TestClient(app) as client:
        response = client.get(
            "/weppcloud/runs/demo/default/elevationquery/?lat=60.0&lng=-116.0",
        )

    payload = response.json()
    assert payload["Elevation"] is None
    assert "outside" in payload["Error"].lower()


def test_unhandled_exception_returns_transparent_payload(tmp_path: Path, monkeypatch, load_service):
    module = load_service(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(module, "get_wd", lambda runid, prefer_active=False: str(tmp_path))

    def explode(active_root):
        raise RuntimeError("DEM exploded")

    monkeypatch.setattr(module, "_locate_dem", explode)

    app = module.create_app()

    with TestClient(app) as client:
        response = client.get(
            "/weppcloud/runs/demo/default/elevationquery/?lat=45.0&lng=-116.0",
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["Elevation"] is None
    assert "DEM exploded" in payload["Error"]
