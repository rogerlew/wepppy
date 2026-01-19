import json
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import omni_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(omni_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(omni_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_omni(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyOmni:
        def parse_scenarios(self, scenarios) -> None:
            return None

        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())


def test_run_omni_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-11")
    _stub_prep(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-11"
    assert payload["message"] == "Job enqueued."
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-11"


def test_run_omni_requires_scenarios(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Missing scenarios data"


def test_run_omni_contrasts_requires_geojson_in_user_defined_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "GeoJSON upload or path is required for user-defined contrasts."


def test_run_omni_contrasts_requires_pairs_in_user_defined_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_geojson_path": "/tmp/areas.geojson",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "contrast_pairs is required for user-defined contrasts"


def test_run_omni_contrasts_requires_pairs_in_stream_order_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={"omni_contrast_selection_mode": "stream_order"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "contrast_pairs is required for stream-order contrasts"


def test_run_omni_contrasts_stream_order_defaults_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-33")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        delineation_backend_is_wbt = True

    monkeypatch.setattr(omni_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    captured = {}

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            captured["payload"] = payload

        def build_contrasts(self, *args, **kwargs) -> None:
            captured["build"] = kwargs

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "stream_order",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
                "order_reduction_passes": 0,
            },
        )

    assert response.status_code == 202
    assert captured["payload"]["order_reduction_passes"] == 1


def test_run_omni_contrasts_stream_order_requires_wbt(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        delineation_backend_is_wbt = False

    monkeypatch.setattr(omni_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "stream_order",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Stream-order pruning requires the WBT delineation backend."


def test_run_omni_contrasts_passes_geojson_upload_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-22")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    captured = {}

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            captured["payload"] = payload

        def build_contrasts(self, *args, **kwargs) -> None:
            captured["build"] = kwargs

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())
    monkeypatch.setattr(omni_routes, "_save_upload", lambda *args, **kwargs: "/tmp/uploaded.geojson")
    pairs_payload = json.dumps(
        [
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        ]
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": pairs_payload,
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
            files={"omni_contrast_geojson": ("areas.geojson", b"{}", "application/geo+json")},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-22"
    assert payload["message"] == "Job enqueued."
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-22"
    assert captured["payload"]["omni_contrast_geojson_path"] == "/tmp/uploaded.geojson"
    assert captured["payload"]["omni_contrast_pairs"] == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    assert captured["build"]["contrast_pairs"] == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]


def test_run_omni_contrasts_dry_run_cumulative(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts_dry_run_report(self, *args, **kwargs) -> dict:
            return {
                "selection_mode": "cumulative",
                "items": [
                    {"contrast_id": 1, "topaz_id": "10", "run_status": "up_to_date"},
                    {"contrast_id": 2, "topaz_id": "20", "run_status": "needs_run"},
                ],
            }

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            json={
                "omni_contrast_selection_mode": "cumulative",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Dry run complete."
    result = payload["result"]
    assert result["runid"] == "run-1"
    assert result["config"] == "cfg"
    assert result["selection_mode"] == "cumulative"
    assert result["items"][0]["run_status"] == "up_to_date"
    assert result["items"][1]["run_status"] == "needs_run"


def test_run_omni_contrasts_dry_run_user_defined(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts_dry_run_report(self, *args, **kwargs) -> dict:
            return {
                "selection_mode": "user_defined_areas",
                "items": [
                    {
                        "contrast_id": 1,
                        "control_scenario": "uniform_low",
                        "contrast_scenario": "mulch",
                        "area_label": "A1",
                        "n_hillslopes": 0,
                        "skip_status": {"skipped": True, "reason": "no_hillslopes"},
                        "run_status": "skipped",
                    },
                    {
                        "contrast_id": 2,
                        "control_scenario": "uniform_low",
                        "contrast_scenario": "mulch",
                        "area_label": "A2",
                        "n_hillslopes": 3,
                        "skip_status": {"skipped": False, "reason": None},
                        "run_status": "up_to_date",
                    },
                ],
            }

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            json={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
                "omni_contrast_geojson_path": "/tmp/areas.geojson",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    result = payload["result"]
    assert result["selection_mode"] == "user_defined_areas"
    assert result["items"][0]["run_status"] == "skipped"
    assert result["items"][0]["skip_status"]["reason"] == "no_hillslopes"
    assert result["items"][1]["run_status"] == "up_to_date"


def test_run_omni_contrasts_dry_run_stream_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyWatershed:
        delineation_backend_is_wbt = True

    monkeypatch.setattr(omni_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts_dry_run_report(self, *args, **kwargs) -> dict:
            return {
                "selection_mode": "stream_order",
                "items": [
                    {
                        "contrast_id": 1,
                        "control_scenario": "uniform_low",
                        "contrast_scenario": "mulch",
                        "subcatchments_group": 10,
                        "n_hillslopes": 0,
                        "skip_status": {"skipped": True, "reason": "no_hillslopes"},
                        "run_status": "skipped",
                    }
                ],
            }

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            json={
                "omni_contrast_selection_mode": "stream_order",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
                "order_reduction_passes": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    result = payload["result"]
    assert result["selection_mode"] == "stream_order"
    assert result["items"][0]["subcatchments_group"] == 10
    assert result["items"][0]["skip_status"]["reason"] == "no_hillslopes"
    assert result["items"][0]["run_status"] == "skipped"


def test_delete_omni_contrasts(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")
    cleared = {"done": False}

    class DummyOmni:
        def clear_contrasts(self) -> None:
            cleared["done"] = True

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/delete-omni-contrasts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Contrasts deleted."
    assert payload["result"]["deleted"] is True
    assert cleared["done"] is True
