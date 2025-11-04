from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

from wepppy.profile_recorder.playback import PlaybackSession


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

    base_url = "http://example.test"
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
