import json
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import omni_routes
from wepppy.nodir.errors import NoDirError


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


def _stub_omni(monkeypatch: pytest.MonkeyPatch, *, run_group: str = "") -> None:
    class DummyOmni:
        run_group = ""

        def parse_scenarios(self, scenarios) -> None:
            return None

        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            return None

    DummyOmni.run_group = run_group
    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())


def _limit_error_message(
    selection_mode: str,
    pair_count: int,
    group_count: int,
    group_label: str,
    *,
    limit: int = 200,
) -> str:
    labels = {
        "user_defined_areas": "User-defined areas",
        "user_defined_hillslope_groups": "User-defined hillslope groups",
        "stream_order": "Stream-order grouping",
    }
    total = pair_count * group_count
    mode_label = labels.get(selection_mode, selection_mode)
    return (
        f"{mode_label} contrasts are limited to {limit}. "
        f"You requested {total} ({pair_count} contrast pairs x {group_count} {group_label}). "
        f"Reduce the number of contrast pairs or {group_label} to {limit} or fewer."
    )


def _make_pairs(count: int) -> list[dict[str, str]]:
    return [
        {"control_scenario": f"control_{idx}", "contrast_scenario": f"contrast_{idx}"}
        for idx in range(1, count + 1)
    ]


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


def test_run_omni_batch_returns_input_message_without_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="batch")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


def test_run_omni_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


def test_run_omni_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


def test_run_omni_batch_without_scenarios_returns_input_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="batch")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


def test_run_omni_batch_multipart_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="batch")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            data={"scenarios": '[{"type":"sbs_map"}]'},
            files={
                "scenarios[0][sbs_file]": (
                    "severity.tif",
                    b"fake-tif-bytes",
                    "image/tiff",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


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


def test_run_omni_invalid_json_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            data="{invalid-json}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    assert "error" in response.json()


def test_run_omni_rejects_non_object_scenarios_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": ["uniform_low"]},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Scenarios data must be valid JSON"


def test_run_omni_rejects_scenarios_without_type(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{}]},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Scenario 0 is missing type"


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


def test_run_omni_contrasts_requires_pairs_in_hillslope_group_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={"omni_contrast_selection_mode": "user_defined_hillslope_groups"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "contrast_pairs is required for user-defined hillslope groups"


def test_run_omni_contrasts_requires_groups_in_hillslope_group_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "user_defined_hillslope_groups",
                "omni_contrast_pairs": [
                    {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
                ],
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert (
        payload["error"]["message"]
        == "omni_contrast_hillslope_groups is required for user-defined hillslope groups"
    )


@pytest.mark.parametrize(
    "selection_mode, group_label, extra_payload, group_count",
    [
        (
            "user_defined_areas",
            "areas",
            {"omni_contrast_geojson_path": "/tmp/areas.geojson"},
            101,
        ),
        (
            "user_defined_hillslope_groups",
            "hillslope groups",
            {"omni_contrast_hillslope_groups": ["11"] * 101},
            101,
        ),
        ("stream_order", "stream-order groups", {}, 101),
    ],
)
def test_run_omni_contrasts_limit_error(
    monkeypatch: pytest.MonkeyPatch,
    selection_mode: str,
    group_label: str,
    extra_payload: dict[str, object],
    group_count: int,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    if selection_mode == "stream_order":
        class DummyWatershed:
            delineation_backend_is_wbt = True

        monkeypatch.setattr(omni_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    pair_count = 2
    expected_message = _limit_error_message(
        selection_mode,
        pair_count,
        group_count,
        group_label,
    )
    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            queue_called["called"] = True
            return None

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            raise ValueError(expected_message)

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    payload = {
        "omni_contrast_selection_mode": selection_mode,
        "omni_contrast_pairs": _make_pairs(pair_count),
        **extra_payload,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-omni-contrasts", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["message"] == expected_message
    assert queue_called["called"] is False


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


def test_run_omni_contrasts_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}
    build_called = {"called": False}

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

    class DummyOmni:
        run_group = "batch"

        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            build_called["called"] = True
            raise AssertionError("build_contrasts should not run for batch input updates")

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "cumulative",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False
    assert build_called["called"] is False


def test_run_omni_contrasts_invalid_json_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            data="{invalid-json}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    assert "error" in response.json()


def test_run_omni_contrasts_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}
    build_called = {"called": False}

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

    class DummyOmni:
        run_group = ""

        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            build_called["called"] = True
            raise AssertionError("build_contrasts should not run for _base input updates")

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "cumulative",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False
    assert build_called["called"] is False


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


def test_run_omni_contrasts_dry_run_invalid_json_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")
    _stub_omni(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            data="{bad-json}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize(
    "selection_mode, group_label, extra_payload, group_count",
    [
        (
            "user_defined_areas",
            "areas",
            {"omni_contrast_geojson_path": "/tmp/areas.geojson"},
            101,
        ),
        (
            "user_defined_hillslope_groups",
            "hillslope groups",
            {"omni_contrast_hillslope_groups": ["11"] * 101},
            101,
        ),
        ("stream_order", "stream-order groups", {}, 101),
    ],
)
def test_run_omni_contrasts_dry_run_limit_error(
    monkeypatch: pytest.MonkeyPatch,
    selection_mode: str,
    group_label: str,
    extra_payload: dict[str, object],
    group_count: int,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    if selection_mode == "stream_order":
        class DummyWatershed:
            delineation_backend_is_wbt = True

        monkeypatch.setattr(omni_routes.Watershed, "getInstance", lambda wd: DummyWatershed())

    pair_count = 2
    expected_message = _limit_error_message(
        selection_mode,
        pair_count,
        group_count,
        group_label,
    )

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts_dry_run_report(self, *args, **kwargs) -> dict:
            raise ValueError(expected_message)

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    payload = {
        "omni_contrast_selection_mode": selection_mode,
        "omni_contrast_pairs": _make_pairs(pair_count),
        **extra_payload,
    }

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            json=payload,
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == expected_message


def test_delete_omni_contrasts(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/delete-omni-contrasts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Delete contrasts job submitted."
    assert payload["result"]["job_id"] == "job-77"
    assert payload["result"]["queued"] is True


@pytest.mark.parametrize(
    ("http_status", "code"),
    [
        (409, "NODIR_MIXED_STATE"),
        (500, "NODIR_INVALID_ARCHIVE"),
        (503, "NODIR_LOCKED"),
    ],
)
def test_run_omni_propagates_nodir_preflight_errors_and_skips_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    code: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _root: str, *, view: str = "effective") -> None:
        raise NoDirError(http_status=http_status, code=code, message="blocked")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used when NoDir preflight fails")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_routes, "nodir_resolve", _raise_nodir)
    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code
    assert queue_called["called"] is False


@pytest.mark.parametrize(
    ("http_status", "code"),
    [
        (409, "NODIR_MIXED_STATE"),
        (500, "NODIR_INVALID_ARCHIVE"),
        (503, "NODIR_LOCKED"),
    ],
)
def test_run_omni_contrasts_propagates_nodir_preflight_errors_and_skips_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    code: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _root: str, *, view: str = "effective") -> None:
        raise NoDirError(http_status=http_status, code=code, message="blocked")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used when NoDir preflight fails")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_routes, "nodir_resolve", _raise_nodir)
    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code
    assert queue_called["called"] is False


@pytest.mark.parametrize(
    ("http_status", "code"),
    [
        (409, "NODIR_MIXED_STATE"),
        (500, "NODIR_INVALID_ARCHIVE"),
        (503, "NODIR_LOCKED"),
    ],
)
def test_run_omni_contrasts_dry_run_propagates_nodir_preflight_errors(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    code: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _root: str, *, view: str = "effective") -> None:
        raise NoDirError(http_status=http_status, code=code, message="blocked")

    monkeypatch.setattr(omni_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts-dry-run",
            json={
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code
