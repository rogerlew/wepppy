import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient


@pytest.fixture
def load_browse(monkeypatch):
    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.browse as browse_mod

        return importlib.reload(browse_mod)

    return _loader


@pytest.fixture
def load_dtale_service(monkeypatch):
    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.webservices.dtale as dtale_module

        return importlib.reload(dtale_module)

    return _loader


def test_dtale_open_redirect(tmp_path: Path, monkeypatch, load_browse):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_path = tmp_path / "output.parquet"
    df.to_parquet(data_path)

    browse = load_browse(
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="secret-token",
        SITE_PREFIX="/weppcloud",
    )

    monkeypatch.setattr(browse, "get_wd", lambda runid: str(tmp_path))

    captured = {}

    class DummyResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": "/weppcloud/dtale/main/abc123"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(browse.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient(*args, **kwargs))

    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get("/weppcloud/runs/run-1/default/dtale/output.parquet")

    assert response.status_code == 303
    assert response.headers["location"] == "/weppcloud/dtale/main/abc123"
    assert captured["url"] == "http://dtale-service/internal/load"
    assert captured["json"] == {
        "runid": "run-1",
        "config": "default",
        "path": "output.parquet",
    }
    assert captured["headers"]["X-DTALE-TOKEN"] == "secret-token"


def test_dtale_open_rejects_unsupported_extension(tmp_path: Path, monkeypatch, load_browse):
    data_path = tmp_path / "notes.txt"
    data_path.write_text("not tabular")

    browse = load_browse(
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="secret-token",
        SITE_PREFIX="/weppcloud",
    )

    monkeypatch.setattr(browse, "get_wd", lambda runid: str(tmp_path))
    class FailingClient:
        async def __aenter__(self):
            raise RuntimeError("Should not call D-Tale")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(browse.httpx, "AsyncClient", lambda *args, **kwargs: FailingClient())

    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get("/weppcloud/runs/run-1/default/dtale/notes.txt")

    assert response.status_code == 415


def test_dtale_loader_refreshes_missing_state(tmp_path: Path, monkeypatch, load_dtale_service):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
    )

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_path = tmp_path / "landuse.parquet"
    df.to_parquet(data_path)

    monkeypatch.setattr(module, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(module, "_ensure_geojson_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "_load_dataframe", lambda path: df.copy())

    state = {"contains": False, "data": None, "dtypes": None}
    cleanup_calls: list[str] = []

    monkeypatch.setattr(module.global_state, "contains", lambda data_id: state["contains"])
    monkeypatch.setattr(module.global_state, "get_data", lambda data_id: state["data"])
    monkeypatch.setattr(module.global_state, "get_dtypes", lambda data_id: state["dtypes"])

    def cleanup_stub(data_id):
        cleanup_calls.append(data_id)
        state["contains"] = False
        state["data"] = None
        state["dtypes"] = None

    monkeypatch.setattr(module.global_state, "cleanup", cleanup_stub)
    monkeypatch.setattr(module.global_state, "set_data", lambda data_id, data: state.update(data=data))
    monkeypatch.setattr(module.global_state, "set_dtypes", lambda data_id, dtypes: state.update(dtypes=dtypes))

    class DummyInstance:
        def build_main_url(self):
            return "/weppcloud/dtale/main/demo"

    init_calls = {"count": 0}

    def fake_initialize(data_id, display_name, frame):
        init_calls["count"] += 1
        state["contains"] = True
        state["data"] = frame
        state["dtypes"] = ["a", "b"]
        return DummyInstance()

    monkeypatch.setattr(module, "_initialize_dtale_dataset", fake_initialize)

    with module.app.test_client() as client:
        first = client.post(
            "/internal/load",
            json={"runid": "run-1", "config": "default", "path": "landuse/landuse.parquet"},
        )
        assert first.status_code == 200
        assert init_calls["count"] == 1

        state["dtypes"] = None  # simulate missing dtype metadata

        second = client.post(
            "/internal/load",
            json={"runid": "run-1", "config": "default", "path": "landuse/landuse.parquet"},
        )
        assert second.status_code == 200
        assert init_calls["count"] == 2
    assert cleanup_calls, "Expected cleanup to be triggered before reload"


def test_geojson_defaults_applied(tmp_path: Path, load_dtale_service):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
    )

    if module.dtale_custom_geojson is None:
        pytest.skip("dtale custom geojson support not available in this environment")

    geojson_path = tmp_path / "subcatchments.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"wepp_id": 1, "TopazID": 100},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [0.0, 0.0],
                                    [0.0, 1.0],
                                    [1.0, 1.0],
                                    [1.0, 0.0],
                                    [0.0, 0.0],
                                ]
                            ],
                        },
                    }
                ],
            }
        )
    )

    runid = "test-run"
    data_id = "data-1"
    module.MAP_DEFAULTS.clear()
    module.MAP_CHOICES.clear()

    key, featureidkey = module._register_geojson_asset(
        runid,
        "subcatchments",
        geojson_path,
        data_id=data_id,
        label="Subcatchments",
        preferred_keys=("wepp_id", "TopazID"),
        make_default=True,
        loc_candidates=("topaz_id",),
        property_aliases=(("WeppID", "wepp_id"),),
    )

    assert key is not None
    assert data_id in module.MAP_DEFAULTS
    defaults = module.MAP_DEFAULTS[data_id]
    assert defaults["geojson"] == key
    assert defaults["loc_mode"] == "geojson-id"
    assert defaults["featureidkey"] in {"wepp_id", "TopazID", "id"}
    assert defaults["loc_candidates"] == ("topaz_id",)
    assert module.MAP_CHOICES[data_id][0][0] == "Subcatchments"
    geojson_entry = next(entry for entry in module.dtale_custom_geojson.CUSTOM_GEOJSON if entry.get("key") == key)
    assert "wepp_id" in geojson_entry.get("properties", [])


def test_dtale_open_falls_back_to_config_subdir(tmp_path: Path, monkeypatch, load_browse):
    config = "disturbed"
    data_dir = tmp_path / config / "landuse"
    data_dir.mkdir(parents=True)
    df = pd.DataFrame({"a": [5, 6], "b": [7, 8]})
    df.to_parquet(data_dir / "landuse.parquet")

    browse = load_browse(
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="secret-token",
        SITE_PREFIX="/weppcloud",
    )

    monkeypatch.setattr(browse, "get_wd", lambda runid: str(tmp_path))

    captured = {}

    class DummyResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": "/weppcloud/dtale/main/xyz789"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(browse.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient(*args, **kwargs))

    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/run-2/{config}/dtale/landuse/landuse.parquet")

    assert response.status_code == 303
    assert response.headers["location"] == "/weppcloud/dtale/main/xyz789"
    assert captured["json"]["path"] == "landuse/landuse.parquet"
