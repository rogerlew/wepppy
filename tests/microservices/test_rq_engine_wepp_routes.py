import contextlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import wepp_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(wepp_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(wepp_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(wepp_routes, "release_wepp_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(wepp_routes, "ensure_no_active_wepp_job", lambda _runid, _prep, _redis_conn: None)


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(wepp_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_wepp_stack(
    monkeypatch: pytest.MonkeyPatch,
    *,
    parse_error: bool = False,
    run_group: str = "",
    persist_job_hint_error: bool = False,
    capture: dict[str, object] | None = None,
) -> None:
    class DummyRon:
        mods = []

    class DummySoils:
        clip_soils = False
        clip_soils_depth = None
        clip_soils_minimum = False
        clip_soils_minimum_depth = 0.0
        rosetta_wc_fc_from_disturbed_bd_override = False
        initial_sat = None

    class DummyWatershed:
        clip_hillslopes = False
        clip_hillslope_length = None

    class DummyWepp:
        run_group = ""
        dss_excluded_channel_orders = [1, 2]
        _run_wepp_ui = True
        _run_wepp_watershed = True
        _run_pmet = True
        _run_frost = False
        _run_tcr = False
        _run_snow = True

        def __init__(self) -> None:
            self._job_id = None
            self.job_key = None

        @property
        def job_id(self):
            return self._job_id

        @job_id.setter
        def job_id(self, value):
            if persist_job_hint_error:
                raise RuntimeError("nodb write failed")
            self._job_id = value

        def parse_inputs(self, payload) -> None:
            if parse_error:
                raise ValueError("bad payload")
            self.last_parse_payload = dict(payload)
            if capture is not None:
                capture["parse_payload"] = dict(payload)
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

    dummy_soils = DummySoils()
    dummy_watershed = DummyWatershed()
    dummy_wepp = DummyWepp()
    dummy_wepp.run_group = run_group

    if capture is not None:
        capture["soils"] = dummy_soils
        capture["watershed"] = dummy_watershed
        capture["wepp"] = dummy_wepp

    monkeypatch.setattr(wepp_routes.Soils, "getInstance", lambda wd: dummy_soils)
    monkeypatch.setattr(wepp_routes.Watershed, "getInstance", lambda wd: dummy_watershed)
    monkeypatch.setattr(wepp_routes.Wepp, "getInstance", lambda wd: dummy_wepp)
    monkeypatch.setattr(wepp_routes.Ron, "getInstance", lambda wd: DummyRon())


def test_run_wepp_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"


@pytest.mark.parametrize(
    ("endpoint", "job_id", "job_key"),
    [
        ("/api/runs/run-1/cfg/run-wepp", "job-wepp-201", "run_wepp_rq"),
        ("/api/runs/run-1/cfg/run-wepp-watershed", "job-wepp-202", "run_wepp_watershed_rq"),
        ("/api/runs/run-1/cfg/prep-wepp-watershed", "job-wepp-203", "prep_wepp_watershed_rq"),
    ],
)
def test_wepp_endpoints_persist_job_id_to_wepp_nodb(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    job_id: str,
    job_key: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id=job_id)
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert capture["wepp"].job_id == job_id
    assert capture["wepp"].job_key == job_key


def test_run_wepp_job_hint_persist_failure_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-hint-failed")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, persist_job_hint_error=True)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-hint-failed"}


def test_run_wepp_persists_minimum_clip_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-177")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={
                "clip_soils": True,
                "clip_soils_depth": 300,
                "clip_soils_minimum": True,
                "clip_soils_minimum_depth": 120.5,
                "rosetta_wc_fc_from_disturbed_bd_override": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-177"
    soils = capture["soils"]
    assert soils.clip_soils is True
    assert soils.clip_soils_depth == 300
    assert soils.clip_soils_minimum is True
    assert soils.clip_soils_minimum_depth == 120.5
    assert soils.rosetta_wc_fc_from_disturbed_bd_override is True


def test_run_wepp_propagates_channel_advanced_options_to_wepp_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-channel-propagation")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    payload = {
        "channel_critical_shear": 4.5,
        "channel_erodibility": 0.00001,
        "channel_manning_roughness_coefficient_bare": 0.031,
        "channel_manning_roughness_coefficient_veg": 0.041,
        "minimum_channel_width_m": 0.306,
        "tcr_opts_taumin": 35.0,
        "tcr_opts_taumax": 70.0,
        "tcr_opts_kch": 0.02,
        "tcr_opts_nch": 1.0,
        "baseflow_opts_gwstorage": 200.0,
        "baseflow_opts_bfcoeff": 0.05,
        "baseflow_opts_dscoeff": 0.0,
        "baseflow_opts_bfthreshold": 1.0,
        "snow_opts_rst": 0.0,
        "snow_opts_newsnw": 100.0,
        "snow_opts_ssd": 250.0,
        "frost_opts_wintRed": 1,
        "frost_opts_fineTop": 10,
        "frost_opts_fineBot": 10,
        "frost_opts_ksnowf": 1.0,
        "frost_opts_kresf": 1.0,
        "frost_opts_ksoilf": 1.0,
        "frost_opts_kfactor1": 1e-5,
        "frost_opts_kfactor2": 1e-5,
        "frost_opts_kfactor3": 0.5,
        "pmet_kcb": 0.95,
        "pmet_rawp": 0.8,
        "kslast": "",
        "wepp_bin": "wepp_260324",
        "dtchr_override": 120,
        "ichout_override": 3,
        "chn_topaz_ids_of_interest": "24 34 44",
        "delete_after_interchange": True,
        "surf_runoff": 0.004,
        "lateral_flow": 0.005,
        "baseflow": 0.006,
        "sediment": 800,
        "clip_hillslopes": True,
        "hillslope_clip_length": 123,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp", json=payload)

    assert response.status_code == 200
    parsed_payload = capture["parse_payload"]
    assert parsed_payload["channel_critical_shear"] == 4.5
    assert parsed_payload["channel_erodibility"] == 0.00001
    assert parsed_payload["channel_manning_roughness_coefficient_bare"] == 0.031
    assert parsed_payload["channel_manning_roughness_coefficient_veg"] == 0.041
    assert parsed_payload["minimum_channel_width_m"] == 0.306
    assert parsed_payload["tcr_opts_taumin"] == 35.0
    assert parsed_payload["baseflow_opts_bfcoeff"] == 0.05
    assert parsed_payload["snow_opts_newsnw"] == 100.0
    assert parsed_payload["frost_opts_wintRed"] == 1
    assert parsed_payload["pmet_kcb"] == 0.95
    assert parsed_payload["wepp_bin"] == "wepp_260324"
    assert parsed_payload["dtchr_override"] == 120
    assert parsed_payload["ichout_override"] == 3
    assert parsed_payload["delete_after_interchange"] is True
    assert parsed_payload["surf_runoff"] == 0.004
    assert parsed_payload["lateral_flow"] == 0.005
    assert parsed_payload["baseflow"] == 0.006
    assert parsed_payload["sediment"] == 800
    assert "hillslope_clip_length" not in parsed_payload
    assert "clip_hillslope_length" not in parsed_payload


@pytest.mark.parametrize("clip_length_key", ["hillslope_clip_length", "clip_hillslope_length"])
def test_run_wepp_accepts_hillslope_clip_length_aliases(
    monkeypatch: pytest.MonkeyPatch,
    clip_length_key: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-hillslope-alias")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={
                "clip_hillslopes": True,
                clip_length_key: 222,
            },
        )

    assert response.status_code == 200
    assert capture["watershed"].clip_hillslopes is True
    assert capture["watershed"].clip_hillslope_length == 222


def test_run_wepp_persists_routine_checkbox_overrides_from_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-routine-overrides")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={
                "checkbox_hourly_seepage": False,
                "checkbox_wepp_watershed": False,
                "checkbox_wepp_pmet": False,
                "checkbox_wepp_frost": True,
                "checkbox_wepp_tcr": True,
                "checkbox_wepp_snow": False,
            },
        )

    assert response.status_code == 200
    wepp = capture["wepp"]
    assert wepp._run_wepp_ui is False
    assert wepp._run_wepp_watershed is False
    assert wepp._run_pmet is False
    assert wepp._run_frost is True
    assert wepp._run_tcr is True
    assert wepp._run_snow is False
    parsed_payload = capture["parse_payload"]
    assert "checkbox_hourly_seepage" not in parsed_payload
    assert "checkbox_wepp_watershed" not in parsed_payload
    assert "checkbox_wepp_pmet" not in parsed_payload
    assert "checkbox_wepp_frost" not in parsed_payload
    assert "checkbox_wepp_tcr" not in parsed_payload
    assert "checkbox_wepp_snow" not in parsed_payload


def test_run_wepp_sparse_payload_preserves_existing_boolean_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-sparse-preserve")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    soils = capture["soils"]
    watershed = capture["watershed"]
    wepp = capture["wepp"]
    soils.clip_soils = True
    soils.clip_soils_depth = 300
    soils.clip_soils_minimum = True
    soils.clip_soils_minimum_depth = 100.0
    soils.rosetta_wc_fc_from_disturbed_bd_override = True
    watershed.clip_hillslopes = True
    wepp._prep_details_on_run_completion = True
    wepp._arc_export_on_run_completion = True
    wepp._legacy_arc_export_on_run_completion = True
    wepp._dss_export_on_run_completion = True

    with TestClient(rq_engine.app) as client:
        sparse_response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"initial_sat": 0.42},
        )
        assert sparse_response.status_code == 200
        assert soils.clip_soils is True
        assert soils.clip_soils_minimum is True
        assert soils.rosetta_wc_fc_from_disturbed_bd_override is True
        assert watershed.clip_hillslopes is True
        assert wepp._prep_details_on_run_completion is True
        assert wepp._arc_export_on_run_completion is True
        assert wepp._legacy_arc_export_on_run_completion is True
        assert wepp._dss_export_on_run_completion is True

        clear_response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={
                "clip_soils": False,
                "clip_soils_minimum": False,
                "rosetta_wc_fc_from_disturbed_bd_override": False,
                "clip_hillslopes": False,
                "prep_details_on_run_completion": False,
                "arc_export_on_run_completion": False,
                "legacy_arc_export_on_run_completion": False,
                "dss_export_on_run_completion": False,
            },
        )

    assert clear_response.status_code == 200
    assert soils.clip_soils is False
    assert soils.clip_soils_minimum is False
    assert soils.rosetta_wc_fc_from_disturbed_bd_override is False
    assert watershed.clip_hillslopes is False
    assert wepp._prep_details_on_run_completion is False
    assert wepp._arc_export_on_run_completion is False
    assert wepp._legacy_arc_export_on_run_completion is False
    assert wepp._dss_export_on_run_completion is False


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp",
        "/api/runs/run-1/cfg/run-wepp-watershed",
        "/api/runs/run-1/cfg/prep-wepp-watershed",
    ],
)
def test_wepp_endpoints_persist_rosetta_bd_toggle(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-rosetta")
    _stub_prep(monkeypatch)
    capture: dict[str, object] = {}
    _stub_wepp_stack(monkeypatch, capture=capture)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            endpoint,
            json={"rosetta_wc_fc_from_disturbed_bd_override": True},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-rosetta"
    assert capture["soils"].rosetta_wc_fc_from_disturbed_bd_override is True


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp",
        "/api/runs/run-1/cfg/run-wepp-watershed",
        "/api/runs/run-1/cfg/prep-wepp-watershed",
    ],
)
def test_wepp_endpoints_reject_invalid_minimum_maximum_depth_range(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            endpoint,
            json={
                "clip_soils": True,
                "clip_soils_depth": 100,
                "clip_soils_minimum": True,
                "clip_soils_minimum_depth": 200,
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Invalid soil depth clipping range"
    assert payload["error"]["code"] == "invalid_soil_depth_range"
    assert "clip_soils_minimum_depth" in payload["error"]["details"]


def test_run_wepp_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch, parse_error=True)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "bad payload"


def test_run_wepp_watershed_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-88")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.2},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-88"


def test_prep_wepp_watershed_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/prep-wepp-watershed",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.2},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-99"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp",
        "/api/runs/run-1/cfg/run-wepp-watershed",
        "/api/runs/run-1/cfg/prep-wepp-watershed",
    ],
)
def test_wepp_endpoints_return_409_when_singleflight_conflict(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(wepp_routes, "release_wepp_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(
        wepp_routes,
        "ensure_no_active_wepp_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            wepp_routes.WeppSingleFlightConflict("WEPP job already active for this run.")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 409
    payload = response.json()
    assert "already active" in payload["error"]["message"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp",
        "/api/runs/run-1/cfg/run-wepp-watershed",
        "/api/runs/run-1/cfg/prep-wepp-watershed",
    ],
)
def test_wepp_endpoints_return_409_when_submit_lock_is_busy(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: False)

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 409
    payload = response.json()
    assert "enqueue already in progress" in payload["error"]["message"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp",
        "/api/runs/run-1/cfg/run-wepp-watershed",
        "/api/runs/run-1/cfg/prep-wepp-watershed",
    ],
)
def test_wepp_endpoints_map_auth_runtime_errors_to_canonical_payload(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    monkeypatch.setattr(
        wepp_routes,
        "require_jwt",
        lambda request, required_scopes=None: (_ for _ in ()).throw(RuntimeError("auth backend unavailable")),
    )
    monkeypatch.setattr(wepp_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["message"] == "Failed to authorize request"


def test_run_wepp_release_lock_failure_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-keep")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        wepp_routes,
        "release_wepp_submit_lock",
        lambda _runid, _owner: (_ for _ in ()).throw(RuntimeError("release failed")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-keep"}


def test_run_wepp_batch_returns_input_message_without_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_watershed_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_watershed_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_setup_failure_returns_canonical_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    class ExplodingSoils:
        @property
        def clip_soils(self):
            return False

        @clip_soils.setter
        def clip_soils(self, value):
            raise RuntimeError("soil write failed")

    monkeypatch.setattr(wepp_routes.Soils, "getInstance", lambda wd: ExplodingSoils())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error preparing WEPP run request"
    assert "RuntimeError: soil write failed" in payload["error"]["details"]
