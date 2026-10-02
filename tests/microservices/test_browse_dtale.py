import importlib
import base64
import json
from pathlib import Path

import pandas as pd
import pytest
from werkzeug.exceptions import HTTPException

TestClient = pytest.importorskip("starlette.testclient").TestClient
pytestmark = pytest.mark.microservice

dtale_pkg = pytest.importorskip("wepppy.webservices.dtale")
dtale_submodule = getattr(dtale_pkg, "dtale", None)
if not any(hasattr(obj, "dtale_custom_geojson") for obj in (dtale_pkg, dtale_submodule) if obj is not None):
    pytest.skip("D-Tale optional dependencies not available", allow_module_level=True)

@pytest.fixture
def load_browse(monkeypatch):
    def _allow_auth(*args, **kwargs):
        import wepppy.microservices.browse.auth as auth_mod

        return auth_mod.AuthContext(
            claims={"token_class": "service", "roles": ["Root"], "sub": "1"},
            token_class="service",
            roles=frozenset({"root"}),
        )

    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.browse.auth as auth_mod
        import wepppy.microservices.browse.dtale as dtale_mod
        import wepppy.microservices.browse.browse as browse_mod

        importlib.reload(auth_mod)
        importlib.reload(dtale_mod)
        browse_mod = importlib.reload(browse_mod)
        monkeypatch.setattr(browse_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(browse_mod, "authorize_group_request", _allow_auth)
        monkeypatch.setattr(dtale_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(dtale_mod, "authorize_group_request", _allow_auth)
        return browse_mod

    return _loader


@pytest.fixture
def load_dtale_service(monkeypatch):
    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.webservices.dtale as dtale_module

        return importlib.reload(dtale_module)

    return _loader


@pytest.mark.parametrize(
    ("extension", "resource_public"),
    [(".parquet", False), (".geoparquet", True)],
)
def test_dtale_open_redirect(
    tmp_path: Path,
    monkeypatch,
    load_browse,
    extension: str,
    resource_public: bool,
):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_dir = tmp_path / "wepp" / "output"
    data_dir.mkdir(parents=True)
    data_path = data_dir / f"output{extension}"
    df.to_parquet(data_path)
    if resource_public:
        (tmp_path / "PUBLIC").touch()

    browse = load_browse(
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="secret-token",
        SITE_PREFIX="/weppcloud",
    )

    monkeypatch.setattr(browse, "get_wd", lambda runid: str(tmp_path))

    touched: dict[str, str] = {}
    def _tracking_isfile(path: str) -> bool:
        touched["path"] = path
        return True

    monkeypatch.setattr(browse.os.path, "isfile", _tracking_isfile)

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

    import wepppy.microservices.browse.dtale as dtale_mod

    monkeypatch.setattr(dtale_mod.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient(*args, **kwargs))

    app = browse.create_app()

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(f"/weppcloud/runs/run-1/default/dtale/wepp/output/output{extension}")

    assert response.status_code == 303
    assert response.headers["location"] == "/weppcloud/dtale/main/abc123"
    assert captured["url"] == "http://dtale-service/internal/load"
    expected_payload = {
        "runid": "run-1",
        "config": "default",
        "path": f"wepp/output/output{extension}",
        "resource_public": resource_public,
    }
    if not resource_public:
        expected_payload["access_claims"] = {
            "token_class": "service",
            "roles": ["Root"],
            "sub": "1",
        }
    assert captured["json"] == expected_payload
    assert captured["headers"]["X-DTALE-TOKEN"] == "secret-token"
    assert touched["path"].endswith(f"wepp/output/output{extension}")


def test_dtale_open_rejects_unsupported_extension(tmp_path: Path, monkeypatch, load_browse):
    data_dir = tmp_path / "wepp" / "output"
    data_dir.mkdir(parents=True)
    data_path = data_dir / "notes.txt"
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

    import wepppy.microservices.browse.dtale as dtale_mod

    monkeypatch.setattr(dtale_mod.httpx, "AsyncClient", lambda *args, **kwargs: FailingClient())

    app = browse.create_app()

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/weppcloud/runs/run-1/default/dtale/wepp/output/notes.txt")

    assert response.status_code == 415


def test_dtale_loader_refreshes_missing_state(tmp_path: Path, monkeypatch, load_dtale_service):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
    )

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_dir = tmp_path / "landuse"
    data_dir.mkdir(parents=True)
    data_path = data_dir / "landuse.csv"
    df.to_csv(data_path, index=False)

    target_module = module
    if not hasattr(module, "get_wd") and hasattr(module, "dtale"):
        target_module = module.dtale

    (tmp_path / "PUBLIC").touch()
    monkeypatch.setattr(target_module, "get_wd", lambda runid, **_kwargs: str(tmp_path))
    monkeypatch.setattr(target_module, "_ensure_geojson_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(target_module, "_load_dataframe", lambda path: df.copy())

    state = {"contains": False, "data": None, "dtypes": None}
    cleanup_calls: list[str] = []

    monkeypatch.setattr(target_module.global_state, "contains", lambda data_id: state["contains"])
    monkeypatch.setattr(target_module.global_state, "get_data", lambda data_id: state["data"])
    monkeypatch.setattr(target_module.global_state, "get_dtypes", lambda data_id: state["dtypes"])

    def cleanup_stub(data_id):
        cleanup_calls.append(data_id)
        state["contains"] = False
        state["data"] = None
        state["dtypes"] = None

    monkeypatch.setattr(target_module.global_state, "cleanup", cleanup_stub)
    monkeypatch.setattr(target_module.global_state, "set_data", lambda data_id, data: state.update(data=data))
    monkeypatch.setattr(target_module.global_state, "set_dtypes", lambda data_id, dtypes: state.update(dtypes=dtypes))

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

    monkeypatch.setattr(target_module, "_initialize_dtale_dataset", fake_initialize)

    app = getattr(target_module, "app", getattr(module, "app", None))
    assert app is not None

    with app.test_client() as client:
        first = client.post(
            "/internal/load",
            json={
                "runid": "run-1",
                "config": "default",
                "path": "landuse/landuse.csv",
                "resource_public": True,
            },
        )
        assert first.status_code == 200
        assert init_calls["count"] == 1

        state["dtypes"] = None  # simulate missing dtype metadata

        second = client.post(
            "/internal/load",
            json={
                "runid": "run-1",
                "config": "default",
                "path": "landuse/landuse.csv",
                "resource_public": True,
            },
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

    target_module = module
    if not hasattr(target_module, "dtale_custom_geojson") and hasattr(module, "dtale"):
        target_module = module.dtale

    if target_module is None or target_module.dtale_custom_geojson is None:
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
    target_module.MAP_DEFAULTS.clear()
    target_module.MAP_CHOICES.clear()

    key, featureidkey = target_module._register_geojson_asset(
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
    assert data_id in target_module.MAP_DEFAULTS
    defaults = target_module.MAP_DEFAULTS[data_id]
    assert defaults["geojson"] == key
    assert defaults["loc_mode"] == "geojson-id"
    assert defaults["featureidkey"] in {"wepp_id", "TopazID", "id"}
    assert defaults["loc_candidates"] == ("topaz_id",)
    assert target_module.MAP_CHOICES[data_id][0][0] == "Subcatchments"
    geojson_entry = next(
        entry for entry in target_module.dtale_custom_geojson.CUSTOM_GEOJSON if entry.get("key") == key
    )
    assert "wepp_id" in geojson_entry.get("properties", [])


def test_dtale_open_config_subdir_uses_logical_browse_path(tmp_path: Path, monkeypatch, load_browse):
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

    import wepppy.microservices.browse.dtale as dtale_mod

    monkeypatch.setattr(dtale_mod.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient(*args, **kwargs))

    app = browse.create_app()

    with TestClient(app, follow_redirects=False) as client:
        # NoDir browse paths are run-relative. The internal loader's legacy
        # config fallback is tested separately through its actual Flask route.
        missing = client.get(f"/weppcloud/runs/run-2/{config}/dtale/landuse/landuse.parquet")
        assert missing.status_code == 404
        response = client.get(f"/weppcloud/runs/run-2/{config}/dtale/{config}/landuse/landuse.parquet")

    assert response.status_code == 303
    assert response.headers["location"] == "/weppcloud/dtale/main/xyz789"
    assert captured["json"]["path"] == f"{config}/landuse/landuse.parquet"


def _encode_filter_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def test_dtale_open_forwards_parquet_filter_payload(tmp_path: Path, monkeypatch, load_browse):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_dir = tmp_path / "wepp" / "output"
    data_dir.mkdir(parents=True)
    df.to_parquet(data_dir / "output.parquet")

    browse = load_browse(
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="secret-token",
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    monkeypatch.setattr(browse, "get_wd", lambda runid: str(tmp_path))

    captured = {}

    class DummyResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": "/weppcloud/dtale/main/filter123"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return DummyResponse()

    import wepppy.microservices.browse.dtale as dtale_mod

    monkeypatch.setattr(dtale_mod.httpx, "AsyncClient", lambda *args, **kwargs: DummyClient(*args, **kwargs))

    pqf = _encode_filter_payload(
        {
            "kind": "condition",
            "field": "a",
            "operator": "GreaterThan",
            "value": "1",
        }
    )

    app = browse.create_app()
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(f"/weppcloud/runs/run-3/default/dtale/wepp/output/output.parquet?pqf={pqf}")

    assert response.status_code == 303
    assert captured["url"] == "http://dtale-service/internal/load"
    assert captured["json"]["pqf"] == pqf


def test_dtale_loader_registers_lazy_parquet_and_serves_grid_rows(
    tmp_path: Path,
    monkeypatch,
    load_dtale_service,
):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
    )
    target_module = module if hasattr(module, "get_wd") else module.dtale

    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    data_path = tmp_path / "table.parquet"
    df.to_parquet(data_path, index=False)

    (tmp_path / "PUBLIC").touch()
    monkeypatch.setattr(target_module, "get_wd", lambda runid, **_kwargs: str(tmp_path))
    monkeypatch.setattr(target_module, "_ensure_geojson_assets", lambda *args, **kwargs: None)

    def _fail_eager_load(path):
        raise AssertionError(f"unexpected eager D-Tale load for {path}")

    monkeypatch.setattr(target_module, "_load_dataframe", _fail_eager_load)

    app = getattr(target_module, "app", getattr(module, "app", None))
    assert app is not None
    with app.test_client() as client:
        load_response = client.post(
            "/internal/load",
            json={
                "runid": "run-lazy",
                "config": "default",
                "path": "table.parquet",
                "resource_public": True,
            },
        )
        assert load_response.status_code == 200
        data_id = load_response.get_json()["data_id"]
        assert data_id in target_module.LAZY_PARQUET_DATASETS

        grid_response = client.get(
            f"/dtale/data/{data_id}",
            query_string={"ids": json.dumps(["0-1"])},
        )
        sorted_grid_response = client.get(
            f"/dtale/data/{data_id}",
            query_string={
                "ids": json.dumps(["0-1"]),
                "sort": json.dumps([["a", "DESC"]]),
            },
        )
        export_response = client.get(
            f"/dtale/data/{data_id}",
            query_string={"export": "true", "ids": json.dumps(["0-1"])},
        )

    assert grid_response.status_code == 200
    payload = grid_response.get_json()
    assert payload["total"] == 3
    assert payload["results"]["0"]["a"] == 1
    assert payload["results"]["0"]["b"] == "x"
    assert payload["results"]["1"]["a"] == 2
    assert payload["results"]["1"]["b"] == "y"
    assert sorted_grid_response.status_code == 200
    sorted_payload = sorted_grid_response.get_json()
    assert sorted_payload["total"] == 3
    assert sorted_payload["results"]["0"]["a"] == 3
    assert sorted_payload["results"]["0"]["b"] == "z"
    assert sorted_payload["results"]["1"]["a"] == 2
    assert sorted_payload["results"]["1"]["b"] == "y"
    assert export_response.status_code == 501


def test_private_dtale_requires_launch_capability_while_public_data_remains_anonymous(
    tmp_path: Path,
    monkeypatch,
    load_dtale_service,
):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="private-test-token",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
    )
    target_module = module if hasattr(module, "get_wd") else module.dtale
    monkeypatch.setattr(target_module, "DTALE_INTERNAL_TOKEN", "private-test-token")
    import wepppy.microservices.rq_engine.auth as rq_auth

    revoked_subjects: set[str] = set()

    def require_current_claims(claims):
        if claims["sub"] in revoked_subjects:
            raise rq_auth.AuthError("revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(rq_auth, "require_current_claims", require_current_claims)
    monkeypatch.setattr(rq_auth, "authorize_run_access", lambda *_args, **_kwargs: None)
    member_a_claims = {
        "token_class": "user",
        "sub": "member-a",
        "jti": "member-a-token",
        "exp": 4_102_444_800,
    }
    member_b_claims = {
        "token_class": "user",
        "sub": "member-b",
        "jti": "member-b-token",
        "exp": 4_102_444_800,
    }
    pd.DataFrame({"value": ["private-canary"]}).to_csv(tmp_path / "private.csv", index=False)
    pd.DataFrame({"value": ["public-value"]}).to_csv(tmp_path / "public.csv", index=False)
    (tmp_path / "PUBLIC").touch()
    monkeypatch.setattr(target_module, "get_wd", lambda _runid, **_kwargs: str(tmp_path))
    monkeypatch.setattr(target_module, "_ensure_geojson_assets", lambda *args, **kwargs: None)

    app = target_module.app
    headers = {"X-DTALE-TOKEN": "private-test-token"}
    private_load = app.test_client().post(
        "/internal/load",
        json={
            "runid": "private-run",
            "config": "default",
            "path": "private.csv",
            "resource_public": False,
            "access_claims": member_a_claims,
        },
        headers=headers,
    )
    public_load = app.test_client().post(
        "/internal/load",
        json={
            "runid": "public-run",
            "config": "default",
            "path": "public.csv",
            "resource_public": True,
        },
        headers=headers,
    )
    assert private_load.status_code == 200
    assert public_load.status_code == 200
    private_id = private_load.get_json()["data_id"]
    public_id = public_load.get_json()["data_id"]

    anonymous = app.test_client()
    denied = anonymous.get(
        f"/dtale/data/{private_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    public_grid = anonymous.get(
        f"/dtale/data/{public_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    assert denied.status_code == 403
    assert "private-canary" not in denied.get_data(as_text=True)
    assert public_grid.status_code == 200
    assert "public-value" in public_grid.get_data(as_text=True)
    (tmp_path / "PUBLIC").unlink()
    newly_private_public_grid = app.test_client().get(
        f"/dtale/data/{public_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    assert newly_private_public_grid.status_code == 403
    assert "public-value" not in newly_private_public_grid.get_data(as_text=True)
    (tmp_path / "PUBLIC").touch()
    reopened_public = app.test_client().post(
        "/internal/load",
        json={
            "runid": "public-run",
            "config": "default",
            "path": "public.csv",
            "resource_public": True,
        },
        headers=headers,
    )
    assert reopened_public.status_code == 200
    escaped_id = f"\\u{ord(private_id[0]):04x}{private_id[1:]}"
    encoded_references = [
        json.dumps({"data_id": private_id}),
        f'{{"data_id":"{escaped_id}"}}',
    ]
    for encoded_reference in encoded_references:
        with app.test_request_context(
            "/dtale/merge",
            query_string={"payload": encoded_reference},
        ):
            with pytest.raises(HTTPException) as denied_serialized:
                target_module._request_private_scopes()
            assert getattr(denied_serialized.value, "code", None) == 403
            assert private_id not in target_module._guarded_global_keys()
            assert public_id in target_module._guarded_global_keys()

    target_module.DATASET_ACCESS_SCOPES["1"] = frozenset({private_id})
    with app.test_request_context(
        f"/dtale/data/{public_id}",
        query_string={"ids": json.dumps(["0-1"])},
    ):
        assert target_module._request_private_scopes() == frozenset()
    target_module.global_state.cleanup("1")
    assert "1" not in target_module.DATASET_ACCESS_SCOPES

    launch_path = private_load.get_json()["url"].removeprefix("/weppcloud")
    authorized = app.test_client()
    launch = authorized.get(
        launch_path,
        follow_redirects=False,
    )
    assert launch.status_code == 303
    assert "HttpOnly" in launch.headers["Set-Cookie"]
    private_grid = authorized.get(
        f"/dtale/data/{private_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    assert private_grid.status_code == 200
    assert "private-canary" in private_grid.get_data(as_text=True)

    target_module._initialize_dtale_dataset(
        "1",
        "private numeric source",
        pd.DataFrame({"value": ["private-numeric-canary"]}),
    )
    target_module.DATASET_ACCESS_SCOPES["1"] = frozenset({private_id})
    merge_payload = {
        "action": "stack",
        "config": json.dumps({"ignoreIndex": True}),
        "datasets": json.dumps(
            [{"dataId": 1, "columns": None, "index": []}]
        )
    }
    anonymous_merge = app.test_client().post("/dtale/merge", json=merge_payload)
    assert anonymous_merge.status_code == 403
    authorized_merge = authorized.post("/dtale/merge", json=merge_payload)
    assert authorized_merge.status_code == 200
    derived_id = str(authorized_merge.get_json()["data_id"])
    assert target_module.DATASET_ACCESS_SCOPES[derived_id] == frozenset({private_id})
    anonymous_derived = app.test_client().get(
        f"/dtale/data/{derived_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    assert anonymous_derived.status_code == 403
    assert "private-numeric-canary" not in anonymous_derived.get_data(as_text=True)
    target_module.global_state.cleanup(derived_id)
    target_module.global_state.cleanup("1")

    secure_launch = app.test_client().get(
        launch_path,
        headers={"X-Forwarded-Proto": "https"},
        follow_redirects=False,
    )
    assert "Secure" in secure_launch.headers["Set-Cookie"]

    member_b_load = app.test_client().post(
        "/internal/load",
        json={
            "runid": "private-run",
            "config": "default",
            "path": "private.csv",
            "resource_public": False,
            "access_claims": member_b_claims,
        },
        headers=headers,
    )
    member_b = app.test_client()
    assert member_b.get(
        member_b_load.get_json()["url"].removeprefix("/weppcloud"),
        follow_redirects=False,
    ).status_code == 303
    revoked_subjects.add("member-a")
    assert authorized.get(
        f"/dtale/data/{private_id}",
        query_string={"ids": json.dumps(["0-1"])},
    ).status_code == 403
    assert member_b.get(
        f"/dtale/data/{private_id}",
        query_string={"ids": json.dumps(["0-1"])},
    ).status_code == 200

    pd.DataFrame({"value": ["refreshed-private-canary"]}).to_csv(
        tmp_path / "private.csv",
        index=False,
    )
    refreshed = app.test_client().post(
        "/internal/load",
        json={
            "runid": "private-run",
            "config": "default",
            "path": "private.csv",
            "resource_public": False,
            "access_claims": member_b_claims,
        },
        headers=headers,
    )
    assert refreshed.status_code == 200
    refreshed_denied = app.test_client().get(
        f"/dtale/data/{private_id}",
        query_string={"ids": json.dumps(["0-1"])},
    )
    assert refreshed_denied.status_code == 403
    assert "refreshed-private-canary" not in refreshed_denied.get_data(as_text=True)

    target_module._discard_dataset(private_id)
    target_module._discard_dataset(public_id)


def test_dtale_loader_uses_distinct_dataset_ids_for_distinct_filters(
    tmp_path: Path,
    monkeypatch,
    load_dtale_service,
):
    module = load_dtale_service(
        DTALE_INTERNAL_TOKEN="",
        SITE_PREFIX="/weppcloud",
        HOST="127.0.0.1",
        PORT="9010",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    target_module = module if hasattr(module, "get_wd") else module.dtale

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    data_path = tmp_path / "table.parquet"
    df.to_parquet(data_path, index=False)

    (tmp_path / "PUBLIC").touch()
    monkeypatch.setattr(target_module, "get_wd", lambda runid, **_kwargs: str(tmp_path))
    monkeypatch.setattr(target_module, "BROWSE_PARQUET_FILTERS_ENABLED", True)
    monkeypatch.setattr(target_module, "_ensure_geojson_assets", lambda *args, **kwargs: None)

    payload_a = _encode_filter_payload(
        {"kind": "condition", "field": "a", "operator": "GreaterThan", "value": "1"}
    )
    payload_b = _encode_filter_payload(
        {"kind": "condition", "field": "a", "operator": "GreaterThan", "value": "0"}
    )

    app = getattr(target_module, "app", getattr(module, "app", None))
    assert app is not None
    with app.test_client() as client:
        first = client.post(
            "/internal/load",
            json={
                "runid": "run-1",
                "config": "default",
                "path": "table.parquet",
                "pqf": payload_a,
                "resource_public": True,
            },
        )
        second = client.post(
            "/internal/load",
            json={
                "runid": "run-1",
                "config": "default",
                "path": "table.parquet",
                "pqf": payload_b,
                "resource_public": True,
            },
        )

    assert first.status_code == 200
    assert second.status_code == 200
    first_data_id = first.get_json()["data_id"]
    second_data_id = second.get_json()["data_id"]
    assert first_data_id != second_data_id
    assert target_module.LAZY_PARQUET_DATASETS[first_data_id].rows() == 1
    assert target_module.LAZY_PARQUET_DATASETS[second_data_id].rows() == 2
