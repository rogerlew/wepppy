from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Tuple

import importlib.util

import pytest
import wepppy

if "flask" not in sys.modules:
    flask_stub = ModuleType("flask")
    flask_stub.current_app = SimpleNamespace(config={})
    flask_stub.g = SimpleNamespace()

    def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    flask_stub.jsonify = _noop
    flask_stub.make_response = _noop
    flask_stub.render_template = _noop
    flask_stub.url_for = _noop
    sys.modules["flask"] = flask_stub

if "werkzeug" not in sys.modules:
    werkzeug_stub = ModuleType("werkzeug")
    exceptions_stub = ModuleType("werkzeug.exceptions")

    class _HTTPException(Exception):
        pass

    exceptions_stub.HTTPException = _HTTPException
    werkzeug_stub.exceptions = exceptions_stub
    sys.modules["werkzeug"] = werkzeug_stub
    sys.modules["werkzeug.exceptions"] = exceptions_stub

if "redis" not in sys.modules:
    redis_stub = ModuleType("redis")

    class _ConnectionError(Exception):
        pass

    class _ConnectionPool:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class _StrictRedis:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._store: Dict[str, str] = {}

        def ping(self) -> bool:
            return True

        def get(self, key: str) -> str | None:
            return self._store.get(key)

        def set(self, key: str, value: str, ex: int | None = None) -> None:
            self._store[key] = value

    redis_stub.ConnectionPool = _ConnectionPool
    redis_stub.StrictRedis = _StrictRedis
    redis_stub.exceptions = SimpleNamespace(ConnectionError=_ConnectionError)
    sys.modules["redis"] = redis_stub

if "jsonpickle" not in sys.modules:
    jsonpickle_stub = ModuleType("jsonpickle")

    def _passthrough(value: Any, *args: Any, **kwargs: Any) -> Any:
        return value

    jsonpickle_stub.encode = _passthrough
    jsonpickle_stub.decode = _passthrough
    sys.modules["jsonpickle"] = jsonpickle_stub

if "utm" not in sys.modules:
    utm_stub = ModuleType("utm")

    def _utm_from_latlon(*args: Any, **kwargs: Any) -> Tuple[int, int, int, str]:
        return (0, 0, 0, "N")

    def _utm_to_latlon(*args: Any, **kwargs: Any) -> Tuple[float, float]:
        return (0.0, 0.0)

    utm_stub.from_latlon = _utm_from_latlon
    utm_stub.to_latlon = _utm_to_latlon
    sys.modules["utm"] = utm_stub

if "deprecated" not in sys.modules:
    deprecated_stub = ModuleType("deprecated")

    def _deprecated(_reason: Any | None = None, **_kwargs: Any):
        def decorator(func: Any) -> Any:
            return func

        return decorator

    deprecated_stub.deprecated = _deprecated
    sys.modules["deprecated"] = deprecated_stub

if "wepppy.all_your_base.geo" not in sys.modules:
    geo_stub = ModuleType("wepppy.all_your_base.geo")

    class _RasterDatasetInterpolator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class _GeoTransformer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class _RDIOutOfBoundsException(Exception):
        pass

    def _geo_noop(*args: Any, **kwargs: Any) -> Any:
        return None

    geo_stub.RasterDatasetInterpolator = _RasterDatasetInterpolator
    geo_stub.GeoTransformer = _GeoTransformer
    geo_stub.RDIOutOfBoundsException = _RDIOutOfBoundsException
    geo_stub.read_raster = _geo_noop
    geo_stub.raster_stacker = _geo_noop
    geo_stub.validate_srs = _geo_noop
    geo_stub.wgs84_proj4 = "EPSG:4326"
    geo_stub.utm_srid = _geo_noop
    geo_stub.haversine = lambda *args, **kwargs: 0.0
    geo_stub.get_utm_zone = lambda *args, **kwargs: 12
    geo_stub.utm_raster_transform = _geo_noop

    def _geo_getattr(name: str) -> Any:
        return _geo_noop

    geo_stub.__getattr__ = _geo_getattr  # type: ignore[attr-defined]
    sys.modules["wepppy.all_your_base.geo"] = geo_stub

if "wepppy.all_your_base.geo.webclients" not in sys.modules:
    webclients_stub = ModuleType("wepppy.all_your_base.geo.webclients")

    def _webclient_stub(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}

    webclients_stub.wmesque_retrieve = _webclient_stub
    sys.modules["wepppy.all_your_base.geo.webclients"] = webclients_stub


def _ensure_package_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        module.__path__ = []  # type: ignore[attr-defined]
        sys.modules[name] = module
    return module


nodb_pkg = _ensure_package_module("wepppy.nodb")
setattr(wepppy, "nodb", nodb_pkg)
core_pkg = _ensure_package_module("wepppy.nodb.core")
mods_pkg = _ensure_package_module("wepppy.nodb.mods")
nodb_pkg.core = core_pkg  # type: ignore[attr-defined]
nodb_pkg.mods = mods_pkg  # type: ignore[attr-defined]

if "wepppy.nodb.base" not in sys.modules:
    nodb_base_stub = ModuleType("wepppy.nodb.base")

    def _clear_locks(*args: Any, **kwargs: Any) -> None:
        return []

    nodb_base_stub.clear_locks = _clear_locks
    sys.modules["wepppy.nodb.base"] = nodb_base_stub
    nodb_pkg.base = nodb_base_stub  # type: ignore[attr-defined]

if "wepppy.nodb.core.ron" not in sys.modules:
    ron_stub = ModuleType("wepppy.nodb.core.ron")

    class _Ron:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        @classmethod
        def getInstance(cls, *args: Any, **kwargs: Any) -> "_Ron":
            return cls()

    ron_stub.Ron = _Ron
    sys.modules["wepppy.nodb.core.ron"] = ron_stub
    core_pkg.ron = ron_stub  # type: ignore[attr-defined]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PLAYBACK_PATH = _PROJECT_ROOT / "wepppy" / "profile_recorder" / "playback.py"
_SPEC = importlib.util.spec_from_file_location("tests.profile_recorder.playback_module", _PLAYBACK_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load playback module from {_PLAYBACK_PATH}")
_PLAYBACK_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PLAYBACK_MODULE)
PlaybackSession = getattr(_PLAYBACK_MODULE, "PlaybackSession")
SandboxViolationError = getattr(_PLAYBACK_MODULE, "SandboxViolationError")


class _RecordingSession:
    def __init__(self, call_log: List[Tuple[str, Any, Any]]) -> None:
        self.calls: List[Tuple[str, str, Dict[str, Any]]] = []
        self._call_log = call_log

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        self.calls.append((method, url, kwargs))
        self._call_log.append(("request", method, url))
        payload = {"job_id": f"job-{len(self.calls)}"}
        return _StubResponse(payload)

    def get(self, url: str, **kwargs: Any) -> Any:
        self._call_log.append(("get", url))
        return _StubResponse({}, status_code=200)


class _StubResponse:
    def __init__(self, payload: Dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.text = json.dumps(payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


def _install_stub_module(monkeypatch: pytest.MonkeyPatch, name: str, **attrs: Any) -> None:
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _singleton(clazz: type) -> type:
    instance = clazz()
    setattr(clazz, "_instance", instance)
    instance._calls: List[Tuple[Tuple[Any, ...], Dict[str, Any]]] = []

    @classmethod  # type: ignore[misc]
    def get_instance(cls, *args: Any, **kwargs: Any) -> Any:
        instance._calls.append((args, kwargs))
        return instance

    clazz.getInstance = get_instance  # type: ignore[attr-defined]
    return clazz


def _prepare_playback_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    event_specs: List[Dict[str, Any]],
    base_url: str = "http://example.test",
) -> Tuple[PlaybackSession, _RecordingSession, List[Tuple[str, Any, Any]], Dict[str, Any]]:
    playback_root = tmp_path / "playback_runs"
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(playback_root))

    profile_root = tmp_path / "profile"
    capture_dir = profile_root / "capture"
    seed_upload_root = capture_dir / "seed" / "uploads"
    profile_run_root = profile_root / "run"
    for path in (capture_dir, seed_upload_root, profile_run_root):
        path.mkdir(parents=True, exist_ok=True)

    landuse_seed = seed_upload_root / "landuse" / "input_upload_landuse.tif"
    landuse_seed.parent.mkdir(parents=True, exist_ok=True)
    landuse_seed.write_bytes(b"landuse-seed")

    ash_dir = seed_upload_root / "ash"
    ash_dir.mkdir(parents=True, exist_ok=True)
    ash_load = ash_dir / "input_upload_ash_load.tif"
    ash_load.write_bytes(b"ash-load")
    ash_type = ash_dir / "input_upload_ash_type_map.tif"
    ash_type.write_bytes(b"ash-type")

    omni_limbo = seed_upload_root / "omni" / "_limbo"
    omni_limbo.mkdir(parents=True, exist_ok=True)
    omni_seed = omni_limbo / "scenario_seed.tif"
    omni_seed.write_bytes(b"omni-data")

    @_singleton
    class StubLanduse:
        def __init__(self) -> None:
            self.mode = 2
            self.nlcd_db = "nlcd_demo"
            self._single_selection = "demo"
            self.mapping = '{"key":"value"}'
            self.mods = ["disturbed"]

    @_singleton
    class StubSoils:
        def __init__(self) -> None:
            self.initial_sat = 0.42
            self.mods = ["disturbed"]

    @_singleton
    class StubDisturbed:
        def __init__(self) -> None:
            self.burn_shrubs = True
            self.burn_grass = False
            self.sol_ver = 7.5
            self.disturbed_path = str(landuse_seed)

    @_singleton
    class StubAsh:
        def __init__(self) -> None:
            self.ash_depth_mode = 1
            self.fire_date = SimpleNamespace(month=5, day=17)
            self.field_black_ash_bulkdensity = 1.1
            self.field_white_ash_bulkdensity = 2.2
            self.ini_black_ash_depth_mm = 3.3
            self.ini_white_ash_depth_mm = 4.4
            self.run_wind_transport = True
            self.model = "wind"
            self.transport_mode = "mode-x"
            self.ash_load_fn = str(ash_load)
            self.ash_type_map_fn = str(ash_type)

    @_singleton
    class StubOmni:
        def __init__(self) -> None:
            self.scenarios = [
                {
                    "type": "sbs_map",
                    "variant": "demo",
                    "sbs_file_path": str(omni_seed),
                }
            ]

    _install_stub_module(monkeypatch, "wepppy.nodb.core.landuse", Landuse=StubLanduse, LanduseMode=object)
    _install_stub_module(monkeypatch, "wepppy.nodb.core.soils", Soils=StubSoils)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.disturbed", Disturbed=StubDisturbed)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.ash_transport", Ash=StubAsh)
    _install_stub_module(monkeypatch, "wepppy.nodb.mods.omni", Omni=StubOmni)

    run_id = "original-run"
    config_slug = "demo-config"

    events: List[Dict[str, Any]] = []
    for spec in event_specs:
        suffix = spec.get("endpoint_suffix", "")
        suffix = suffix.lstrip("/")
        event = dict(spec)
        event["endpoint"] = f"{base_url}/runs/{run_id}/{config_slug}/{suffix}"
        events.append(event)

    events_path = capture_dir / "events.jsonl"
    with events_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")

    call_log: List[Tuple[str, Any, Any]] = []
    recording_session = _RecordingSession(call_log)

    session = PlaybackSession(
        profile_root=profile_root,
        base_url=base_url,
        execute=True,
        session=recording_session,
        verbose=False,
    )

    info = {
        "base_url": base_url,
        "run_id": run_id,
        "config_slug": config_slug,
        "landuse_seed": landuse_seed,
        "ash_load": ash_load,
        "ash_type": ash_type,
        "omni_seed": omni_seed,
        "stubs": {
            "landuse": StubLanduse,
            "soils": StubSoils,
            "disturbed": StubDisturbed,
            "ash": StubAsh,
            "omni": StubOmni,
        },
    }
    return session, recording_session, call_log, info


@pytest.mark.unit
def test_playback_session_form_payloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        {"stage": "request", "id": "seed", "method": "GET", "endpoint_suffix": "status"},
        {"stage": "response", "id": "seed", "status": 200, "ok": True, "endpoint_suffix": "status"},
    ]
    session, recording_session, call_log, info = _prepare_playback_session(tmp_path, monkeypatch, event_specs=events)

    def execute(endpoint_suffix: str, request_meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
        meta = {"bodyType": "form-data"} if request_meta is None else request_meta
        original_path = f"/runs/{session.original_run_id}/{info['config_slug']}/{endpoint_suffix}"
        effective_path = session._remap_run_path(original_path)
        url = session._build_url(effective_path)
        form_data, files_info = session._build_form_request(effective_path, meta)
        assert form_data or files_info, f"Form data not generated for {endpoint_suffix}"
        session._execute_request(
            "POST",
            url,
            [],
            None,
            200,
            effective_path,
            meta,
        )
        session._pending_jobs.clear()
        call_log.clear()
        return recording_session.calls[-1][2]

    landuse_kwargs = execute("rq/api/build_landuse")
    assert landuse_kwargs["data"]["landuse_mode"] == "2"
    assert landuse_kwargs["data"]["checkbox_burn_shrubs"] == "true"
    assert landuse_kwargs["files"]["input_upload_landuse"][0] == "input_upload_landuse.tif"

    soils_kwargs = execute("rq/api/build_soils", request_meta={})
    assert soils_kwargs["data"]["initial_sat"] == "0.42"
    assert soils_kwargs["data"]["sol_ver"] == "7.5"

    ash_kwargs = execute("rq/api/run_ash")
    assert ash_kwargs["data"]["ash_depth_mode"] == "1"
    assert ash_kwargs["data"]["fire_date"] == "5/17"
    assert ash_kwargs["files"]["input_upload_ash_load"][0] == "input_upload_ash_load.tif"
    assert ash_kwargs["files"]["input_upload_ash_type_map"][0] == "input_upload_ash_type_map.tif"

    omni_kwargs = execute("rq/api/run_omni")
    scenarios = json.loads(omni_kwargs["data"]["scenarios"])
    assert scenarios[0]["sbs_file"] == "scenario_seed.tif"
    assert omni_kwargs["files"]["scenarios[0][sbs_file]"][0] == "scenario_seed.tif"


@pytest.mark.unit
def test_playback_session_remaps_paths_with_prefix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        {"stage": "request", "id": "seed", "method": "GET", "endpoint_suffix": "status"},
        {"stage": "response", "id": "seed", "status": 200, "ok": True, "endpoint_suffix": "status"},
    ]
    session, _, _, info = _prepare_playback_session(tmp_path, monkeypatch, event_specs=events)

    prefixed_path = f"/weppcloud/runs/{session.original_run_id}/{info['config_slug']}/view/demo/"
    remapped = session._remap_run_path(prefixed_path)
    assert remapped.startswith("/weppcloud/runs/")
    parts = [part for part in remapped.split("/") if part]
    assert "runs" in parts
    runs_index = parts.index("runs")
    assert parts[runs_index + 1] == session.playback_run_id


@pytest.mark.unit
def test_playback_session_build_url_strips_duplicate_prefix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        {"stage": "request", "id": "seed", "method": "GET", "endpoint_suffix": "status"},
        {"stage": "response", "id": "seed", "status": 200, "ok": True, "endpoint_suffix": "status"},
    ]
    base_url = "http://example.test/weppcloud"
    session, _, _, info = _prepare_playback_session(
        tmp_path,
        monkeypatch,
        event_specs=events,
        base_url=base_url,
    )

    double_prefixed_path = f"/weppcloud/runs/{session.playback_run_id}/{info['config_slug']}/status/"
    resolved = session._build_url(double_prefixed_path)
    assert resolved == f"{base_url}/runs/{session.playback_run_id}/{info['config_slug']}/status/"


@pytest.mark.unit
def test_playback_session_waits_and_skips_polling(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        {"stage": "request", "id": "1", "method": "POST", "endpoint_suffix": "rq/api/build_landuse", "requestMeta": {"bodyType": "form-data"}},
        {"stage": "response", "id": "1", "status": 200, "ok": True, "endpoint_suffix": "rq/api/build_landuse"},
        {"stage": "request", "id": "2", "method": "GET", "endpoint_suffix": "rq/api/jobstatus/demo-job"},
        {"stage": "response", "id": "2", "status": 200, "ok": True, "endpoint_suffix": "rq/api/jobstatus/demo-job"},
        {"stage": "request", "id": "3", "method": "GET", "endpoint_suffix": "elevationquery/sample"},
        {"stage": "response", "id": "3", "status": 200, "ok": True, "endpoint_suffix": "elevationquery/sample"},
        {"stage": "request", "id": "4", "method": "POST", "endpoint_suffix": "rq/api/run_ash", "requestMeta": {"bodyType": "form-data"}},
        {"stage": "response", "id": "4", "status": 200, "ok": True, "endpoint_suffix": "rq/api/run_ash"},
    ]
    session, recording_session, call_log, _ = _prepare_playback_session(tmp_path, monkeypatch, event_specs=events)

    wait_calls: List[str] = []

    def fake_wait(self: PlaybackSession, job_id: str, *, timeout: int = 900, interval: float = 2.0, task: str | None = None) -> None:
        wait_calls.append(job_id)
        call_log.append(("wait", job_id))

    monkeypatch.setattr(PlaybackSession, "_wait_for_job", fake_wait, raising=False)

    session.run()

    post_calls = [call for call in recording_session.calls if call[0] == "POST"]
    assert len(post_calls) == 2

    log_sequence = [entry[0] for entry in call_log]
    assert log_sequence == ["request", "wait", "request", "wait"]

    assert wait_calls == ["job-1", "job-2"]
    assert all("/rq/api/jobstatus/" not in call[1] for call in recording_session.calls)
    assert all("/elevationquery/" not in call[1] for call in recording_session.calls)

    statuses = {status for _, status in session.results}
    assert any("skipped recorded jobstatus poll" in status for status in statuses)
    assert any("skipped recorded elevation query" in status for status in statuses)


@pytest.mark.unit
def test_playback_session_guard_blocks_source_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def passthrough(self: PlaybackSession, path: str) -> str:
        return path

    monkeypatch.setattr(PlaybackSession, "_remap_run_path", passthrough)

    events = [
        {"stage": "request", "id": "seed", "method": "GET", "endpoint_suffix": "status"},
        {"stage": "response", "id": "seed", "status": 200, "ok": True, "endpoint_suffix": "status"},
    ]
    session, _, _, _ = _prepare_playback_session(tmp_path, monkeypatch, event_specs=events)

    with pytest.raises(SandboxViolationError):
        session.run()
