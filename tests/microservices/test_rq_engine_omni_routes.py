import io
import json
import os
import threading
from pathlib import Path
from typing import Any
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient
FormData = pytest.importorskip("starlette.datastructures").FormData
UploadFile = pytest.importorskip("starlette.datastructures").UploadFile

import wepppy.microservices.rq_engine as rq_engine
import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.microservices.rq_engine import omni_routes
from wepppy.microservices import vector_upload_normalization
from wepppy.runtime_paths.errors import NoDirError
from wepppy.nodb.base import NoDbAlreadyLockedError


pytestmark = pytest.mark.microservice

@pytest.fixture(autouse=True)
def feature_accounts(monkeypatch):
    from tests.factories.feature_access import stub_feature_accounts
    stub_feature_accounts(monkeypatch)



@pytest.fixture(autouse=True)
def legacy_project_policy(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(omni_routes.Ron, "getInstance", lambda wd: SimpleNamespace(
        config_get_str=lambda section, key, default=None: default))


class _VectorReservation:
    reservation_id = "omni-route-test-reservation"

    def commit(self, exact_bytes: int) -> None:
        self.exact_bytes = exact_bytes

    def release_prewrite(self) -> None:
        self.released = True


class _VectorLedger:
    def reserve(self, **kwargs: Any) -> _VectorReservation:
        return _VectorReservation()


class _VectorLease:
    def __init__(self) -> None:
        self.owned = True

    def assert_owned(self) -> None:
        assert self.owned

    def release(self) -> None:
        self.owned = False


@pytest.fixture(autouse=True)
def bounded_vector_normalizer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "omni-route-test")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    real_prepare = vector_upload_normalization.prepare_vector_upload

    def prepare(**kwargs):
        return real_prepare(
            **kwargs,
            ledger=_VectorLedger(),
            scope_lease_factory=lambda _scope: _VectorLease(),
        )

    monkeypatch.setattr(omni_routes, "prepare_vector_upload", prepare)
    monkeypatch.setattr(
        omni_module,
        "RedisScopeLeaseFactory",
        lambda: lambda _scope: _VectorLease(),
    )


def _contrast_polygon_bytes(*, label: str = "Area one") -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": label},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-116.0, 46.0], [-115.9, 46.0], [-115.9, 46.1], [-116.0, 46.0]]
                        ],
                    },
                }
            ],
        },
        separators=(",", ":"),
    ).encode()


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        omni_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "3", "roles": ["Dev"]},
    )
    monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)


_CONTRAST_AUTH_CASES = (
    ("/api/runs/run-1/cfg/run-omni-contrasts", "_run_omni_contrasts"),
    ("/api/runs/run-1/cfg/run-omni-contrasts-dry-run", "_dry_run_omni_contrasts"),
    ("/api/runs/run-1/cfg/delete-omni-contrasts", "_delete_omni_contrasts"),
)


@pytest.mark.parametrize("path,domain_name", _CONTRAST_AUTH_CASES)
@pytest.mark.parametrize(
    "roles,expected_status",
    [
        (["User"], 403),
        (["PowerUser"], 403),
        (["Admin"], 403),
        (["Dev"], 200),
        (["Root"], 200),
    ],
)
def test_contrast_routes_enforce_role_before_domain_behavior(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    domain_name: str,
    roles: list[str],
    expected_status: int,
) -> None:
    entered = {"value": False}

    monkeypatch.setattr(
        omni_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "3", "roles": roles},
    )
    monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)

    async def _domain_stub(*args, **kwargs):
        entered["value"] = True
        return omni_routes.JSONResponse({"ok": True}, status_code=200)

    monkeypatch.setattr(omni_routes, domain_name, _domain_stub)

    with TestClient(rq_engine.app) as client:
        response = client.post(path, json={})

    assert response.status_code == expected_status
    assert entered["value"] is (expected_status == 200)
    if expected_status == 403:
        assert response.json()["error"]["code"] == "feature_membership_required"


@pytest.mark.parametrize("path,domain_name", _CONTRAST_AUTH_CASES)
@pytest.mark.parametrize("boundary", ["jwt_scope", "run_access"])
def test_contrast_routes_preserve_jwt_scope_and_run_access_denials(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    domain_name: str,
    boundary: str,
) -> None:
    entered = {"value": False}

    if boundary == "jwt_scope":
        def _deny_scope(request, required_scopes=None):
            raise omni_routes.AuthError(
                "Token missing required scope",
                status_code=403,
                code="forbidden",
            )

        monkeypatch.setattr(omni_routes, "require_jwt", _deny_scope)
        monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)
    else:
        monkeypatch.setattr(
            omni_routes,
            "require_jwt",
            lambda request, required_scopes=None: {"sub": "3", "roles": ["Root"]},
        )

        def _deny_run_access(claims, runid):
            raise omni_routes.AuthError(
                "Run access denied",
                status_code=403,
                code="forbidden",
            )

        monkeypatch.setattr(omni_routes, "authorize_run_access", _deny_run_access)

    async def _domain_stub(*args, **kwargs):
        entered["value"] = True
        return omni_routes.JSONResponse({"ok": True}, status_code=200)

    monkeypatch.setattr(omni_routes, domain_name, _domain_stub)

    with TestClient(rq_engine.app) as client:
        response = client.post(path, json={})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert entered["value"] is False


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
    from wepppy.rq import submission_recovery

    class DummyLock:
        def acquire(self, **kwargs):
            return True
        def extend(self, *args, **kwargs): return True

        def release(self):
            return None

    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs):
            return DummyLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: job_id)


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def get_rq_job_id(self, key):
            return None

        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(omni_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_omni(monkeypatch: pytest.MonkeyPatch, *, run_group: str = "") -> None:
    class DummyOmni:
        run_group = ""
        scenarios = []

        def parse_scenarios(self, scenarios, *, precommit_validator=None) -> None:
            if precommit_validator is not None:
                precommit_validator()
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


def test_prepare_omni_scenarios_normalizes_per_scenario_filter_fields(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    parsed = omni_routes._prepare_omni_scenarios(
        payload={
            "scenarios": [
                {
                    "type": "mulch",
                    "ground_cover_increase": "30",
                    "base_scenario": "uniform_low",
                    "filter_hill_min_slope_pct": "10",
                    "filter_hill_max_slope_pct": "25",
                    "filter_burn_severities": "3, 1, 3",
                }
            ]
        },
        raw_json=None,
        form=FormData({}),
        runid="run-1",
        config="cfg",
        wd=str(wd),
    )

    assert len(parsed) == 1
    _, scenario = parsed[0]
    assert scenario["filter_hill_min_slope_pct"] == 10
    assert scenario["filter_hill_max_slope_pct"] == 25
    assert scenario["filter_burn_severities"] == [1, 3]


def test_prepare_omni_scenarios_rejects_decimal_filter_slope(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="filter_hill_min_slope_pct must be an integer percentage"):
        omni_routes._prepare_omni_scenarios(
            payload={
                "scenarios": [
                    {
                        "type": "thinning",
                        "canopy_cover": "70",
                        "ground_cover": "40",
                        "filter_hill_min_slope_pct": "10.5",
                    }
                ]
            },
            raw_json=None,
            form=FormData({}),
            runid="run-1",
            config="cfg",
            wd=str(wd),
        )


def test_prepare_omni_scenarios_reuses_only_server_authoritative_sbs(tmp_path: Path) -> None:
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    scenario_root = wd / "omni" / "_limbo" / "00"
    scenario_root.mkdir(parents=True)
    source = scenario_root / "severity.tif"
    sbs_raster_bytes(source)

    payload = {
            "scenarios": [
                {"type": "sbs_map", "sbs_file_path": str(source.resolve())}
            ]
        }
    receipts = omni_routes._prevalidate_omni_sbs_inputs(
        payload, None, FormData({}), wd=str(wd), saved_scenarios=payload["scenarios"]
    )
    parsed = omni_routes._prepare_omni_scenarios(
        payload=payload,
        raw_json=None,
        form=FormData({}),
        runid="run-1",
        config="cfg",
        wd=str(wd),
        reuse_receipts=receipts,
    )

    assert parsed[0][1]["sbs_file_path"] == str(source.resolve())


def test_omni_reuse_rejects_unknown_client_path_even_when_row_has_file(tmp_path: Path) -> None:
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    source = wd / "omni/_limbo/00/severity.tif"
    source.parent.mkdir(parents=True)
    sbs_raster_bytes(source)
    saved = [{"type": "sbs_map", "sbs_file_path": str(source)}]
    with pytest.raises(ValueError, match="association is missing or ambiguous"):
        omni_routes._prevalidate_omni_sbs_inputs(
            {"scenarios": [{"type": "sbs_map", "sbs_file_path": "/etc/passwd"}]},
            None, FormData(), wd=str(wd), saved_scenarios=saved,
        )


def test_prevalidate_omni_reuse_rejects_before_any_upload_is_published(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    new_source = tmp_path / "new.tif"
    raw = sbs_raster_bytes(new_source)
    form = FormData(
        {"scenarios[0][sbs_file]": UploadFile(io.BytesIO(raw), filename="new.tif")}
    )
    payload = {
        "scenarios": [
            {"type": "sbs_map"},
            {"type": "sbs_map", "sbs_file_path": "/etc/passwd"},
        ]
    }

    with pytest.raises(ValueError, match="missing or ambiguous"):
        omni_routes._prevalidate_omni_sbs_inputs(
            payload, None, form, wd=str(wd)
        )

    assert not (wd / "omni" / "_limbo" / "00").exists()


def test_prevalidate_omni_missing_later_sbs_before_any_upload_is_published(
    tmp_path: Path,
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    new_source = tmp_path / "new.tif"
    raw = sbs_raster_bytes(new_source)
    form = FormData(
        {"scenarios[0][sbs_file]": UploadFile(io.BytesIO(raw), filename="new.tif")}
    )
    payload = {"scenarios": [{"type": "sbs_map"}, {"type": "sbs_map"}]}

    with pytest.raises(ValueError, match="Missing SBS file for scenario 1"):
        omni_routes._prevalidate_omni_sbs_inputs(
            payload, None, form, wd=str(wd)
        )

    assert not (wd / "omni" / "_limbo" / "00").exists()


def test_prevalidate_omni_rejects_symlinked_server_upload_root(
    tmp_path: Path,
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    (wd / "omni").mkdir(parents=True)
    outside = tmp_path / "outside"
    scenario_root = outside / "00"
    scenario_root.mkdir(parents=True)
    source = scenario_root / "severity.tif"
    sbs_raster_bytes(source)
    (wd / "omni" / "_limbo").symlink_to(outside, target_is_directory=True)
    payload = {
        "scenarios": [{"type": "sbs_map", "sbs_file_path": str(wd / "omni/_limbo/00/severity.tif")}]
    }

    with pytest.raises(omni_routes.UploadError, match="outside the trusted"):
        omni_routes._prevalidate_omni_sbs_inputs(
            payload, None, FormData({}), wd=str(wd), saved_scenarios=payload["scenarios"]
        )


def test_prepare_omni_contrasts_normalizes_integer_slope_percentages(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    parsed = omni_routes._prepare_omni_contrasts(
        payload={
            "omni_contrast_selection_mode": "cumulative",
            "omni_control_scenario": "uniform_low",
            "omni_contrast_scenario": "mulch",
            "omni_contrast_hill_min_slope": "25",
            "omni_contrast_hill_max_slope": "75",
        },
        raw_json=None,
        form=FormData({}),
        runid="run-1",
        config="cfg",
        wd=str(wd),
    )

    assert parsed["omni_contrast_hill_min_slope"] == 25
    assert parsed["omni_contrast_hill_max_slope"] == 75


def test_prepare_omni_contrasts_rejects_decimal_slope_percentages(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="omni_contrast_hill_min_slope must be an integer percentage"):
        omni_routes._prepare_omni_contrasts(
            payload={
                "omni_contrast_selection_mode": "cumulative",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
                "omni_contrast_hill_min_slope": "25.5",
            },
            raw_json=None,
            form=FormData({}),
            runid="run-1",
            config="cfg",
            wd=str(wd),
        )


def test_preflight_omni_roots_rejects_mixed_soils_root(
    tmp_path: Path,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "soils").mkdir()
    (wd / "soils.nodir").write_bytes(b"placeholder archive")

    with pytest.raises(NoDirError) as exc_info:
        omni_routes._preflight_omni_roots(str(wd))

    assert exc_info.value.code == "NODIR_MIXED_STATE"
    assert exc_info.value.http_status == 409
    assert "mixed state" in exc_info.value.message
    assert (wd / "soils.nodir").exists()
    assert (wd / "soils").exists()


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


def test_run_omni_rejects_archive_form_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        omni_routes,
        "nodir_resolve",
        lambda _wd, _root, view="effective": type("Resolved", (), {"form": "archive"})(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_ARCHIVE_ACTIVE"


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
    tmp_path: Path,
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    (tmp_path / "run").mkdir()
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="batch")
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(tmp_path / "run"))

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
                    sbs_raster_bytes(tmp_path / "severity.tif"),
                    "image/tiff",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set omni inputs for batch processing"
    assert queue_called["called"] is False


def test_run_omni_invalid_second_sbs_publishes_no_scenario_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch, run_group="batch")
    run_root = tmp_path / "run"
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(run_root))
    valid = sbs_raster_bytes(tmp_path / "severity.tif")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            data={"scenarios": '[{"type":"sbs_map"},{"type":"sbs_map"}]'},
            files={
                "scenarios[0][sbs_file]": ("first.tif", valid, "image/tiff"),
                "scenarios[1][sbs_file]": (
                    "renamed.img",
                    valid,
                    "application/octet-stream",
                ),
            },
        )

    assert response.status_code == 400
    assert "does not match" in response.json()["error"]["message"]
    assert not (run_root / "omni" / "_limbo").exists()


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


def test_run_omni_rejects_oversize_sbs_upload_with_413(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "SBS_MAX_BYTES", 4)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(tmp_path / "run"))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            data={"scenarios": '[{\"type\":\"sbs_map\"}]'},
            files={
                "scenarios[0][sbs_file]": (
                    "severity.tif",
                    b"abcdef",
                    "image/tiff",
                )
            },
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert "maximum allowed size" in payload["error"]["message"]


def test_run_omni_auth_boundary_error_does_not_include_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_auth_error(request, required_scopes=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(omni_routes, "require_jwt", _raise_auth_error)
    monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["message"] == "Failed to authorize request"
    assert "traceback" not in json.dumps(payload).lower()


def test_run_omni_enqueue_boundary_error_does_not_include_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            raise RuntimeError("queue exploded")

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

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error Handling Request"
    assert "traceback" not in json.dumps(payload).lower()


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


@pytest.mark.parametrize(
    "endpoint,expected_status",
    [
        ("run-omni-contrasts", 202),
        ("run-omni-contrasts-dry-run", 200),
    ],
)
def test_omni_contrast_routes_normalize_before_persisting_geojson_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    endpoint: str,
    expected_status: int,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-22")
    _stub_prep(monkeypatch)
    wd = tmp_path / "run"
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(wd))

    captured = {}
    events: list[str] = []

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            events.append("parse_inputs")
            captured["payload"] = payload

        def build_contrasts(self, *args, **kwargs) -> None:
            captured["build"] = kwargs

        def build_contrasts_dry_run_report(self, *args, **kwargs):
            captured["build"] = kwargs
            return {"contrast_count": 1}

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())

    def prevalidate(path: str) -> None:
        events.append("prevalidate")

    monkeypatch.setattr(
        omni_routes.OmniContrastBuildService,
        "prevalidate_user_defined_geojson",
        prevalidate,
    )
    pairs_payload = json.dumps(
        [
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        ]
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/run-1/cfg/{endpoint}",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": pairs_payload,
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
            files={
                "omni_contrast_geojson": (
                    "areas.geojson",
                    _contrast_polygon_bytes(),
                    "application/geo+json",
                )
            },
        )

    assert response.status_code == expected_status
    payload = response.json()
    if expected_status == 202:
        assert payload["job_id"] == "job-22"
        assert payload["message"] == "Job enqueued."
        assert payload["status_url"] == "/rq-engine/api/jobstatus/job-22"
    else:
        assert payload["message"] == "Dry run complete."
    accepted = Path(captured["payload"]["omni_contrast_geojson_path"])
    assert accepted.parent.parent.name == "_uploads"
    assert accepted.name == "areas.geojson"
    assert accepted.read_bytes() == _contrast_polygon_bytes()
    assert events == ["prevalidate", "prevalidate", "parse_inputs"]
    assert captured["payload"]["omni_contrast_pairs"] == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    assert captured["build"]["contrast_pairs"] == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    attempt = next((wd / "_pups" / "omni" / "contrasts" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    original = next((attempt / "original").iterdir())
    assert original.read_bytes() == _contrast_polygon_bytes()
    assert receipt["status"] == "accepted"
    assert receipt["canonical_path"].startswith("_pups/omni/contrasts/_uploads/")


@pytest.mark.parametrize(
    ("endpoint", "expected_status"),
    [("run-omni-contrasts", 202), ("run-omni-contrasts-dry-run", 200)],
)
def test_exact_converter_formats_cross_omni_http_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    endpoint: str,
    expected_status: int,
) -> None:
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    fixture_root_value = os.getenv("VECTOR_UPLOAD_INTEGRATION_FIXTURES")
    if not converter_url or not fixture_root_value:
        pytest.skip("exact converter integration environment is not configured")
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", converter_url)
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-exact-omni")
    _stub_prep(monkeypatch)
    wd = tmp_path / "run"
    monkeypatch.setattr(omni_routes, "get_wd", lambda _runid: str(wd))
    accepted_paths: list[Path] = []

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            accepted_paths.append(Path(payload["omni_contrast_geojson_path"]))

        def build_contrasts(self, *_args, **_kwargs) -> None:
            return None

        def build_contrasts_dry_run_report(self, *_args, **_kwargs):
            return {"contrast_count": 1}

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda _wd: DummyOmni())
    monkeypatch.setattr(
        omni_routes.OmniContrastBuildService,
        "prevalidate_user_defined_geojson",
        lambda _path: None,
    )
    fixture_root = Path(fixture_root_value)
    semantics: list[dict[str, object]] = []
    with TestClient(rq_engine.app) as client:
        for suffix, fixture_suffix in (("geojson", "geojson"), ("zip", "zip"), ("parquet", "parquet"), ("geoparquet", "parquet")):
            response = client.post(
                f"/api/runs/run-1/cfg/{endpoint}",
                data={
                    "omni_contrast_selection_mode": "user_defined_areas",
                    "omni_contrast_pairs": '[{"control_scenario":"uniform_low","contrast_scenario":"mulch"}]',
                    "omni_control_scenario": "uniform_low",
                    "omni_contrast_scenario": "mulch",
                },
                files={
                    "omni_contrast_geojson": (
                        f"areas.{suffix}",
                        (fixture_root / f"polygon.{fixture_suffix}").read_bytes(),
                    )
                },
            )
            assert response.status_code == expected_status
            payload = json.loads(accepted_paths[-1].read_text())
            semantics.append({"geometry": payload["features"][0]["geometry"], "properties": payload["features"][0]["properties"]})
    from shapely.geometry import shape
    baseline = shape(semantics[0]["geometry"])
    assert all(item["properties"] == semantics[0]["properties"] for item in semantics[1:])
    assert all(baseline.equals(shape(item["geometry"])) for item in semantics[1:])


def test_omni_upload_rolls_back_staged_file_when_build_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    wd = tmp_path / "run"
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(wd))

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            self.accepted_path = Path(payload["omni_contrast_geojson_path"])

        def build_contrasts(self, *args, **kwargs) -> None:
            assert self.accepted_path.exists()
            raise ValueError("simulated build failure")

    omni = DummyOmni()
    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: omni)
    monkeypatch.setattr(
        omni_routes.OmniContrastBuildService,
        "prevalidate_user_defined_geojson",
        lambda path: None,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": '[{"control_scenario":"uniform_low","contrast_scenario":"mulch"}]',
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
            files={
                "omni_contrast_geojson": (
                    "areas.geojson",
                    _contrast_polygon_bytes(),
                    "application/geo+json",
                )
            },
        )

    assert response.status_code == 400
    assert not omni.accepted_path.exists()
    attempt = next((wd / "_pups" / "omni" / "contrasts" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert receipt["status"] == "rejected"
    assert receipt["error_code"] == "omni_build_failed"


def test_real_omni_workflow_failure_restores_prior_state_before_concurrent_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow_active = {"value": False}

    class Lease:
        def assert_owned(self) -> None:
            return None

        def release(self) -> None:
            return None

    def lease_factory():
        def acquire(_scope):
            if workflow_active["value"]:
                raise vector_upload_normalization.VectorUploadError(
                    "vector_retention_quota_exceeded", "workflow active", status_code=507
                )
            return Lease()
        return acquire

    monkeypatch.setattr(omni_module, "RedisScopeLeaseFactory", lease_factory)
    controller = omni_routes.Omni(str(tmp_path), "0.cfg")
    prior = tmp_path / "_pups/omni/contrasts/_uploads/prior/areas.geojson"
    prior.parent.mkdir(parents=True)
    prior_bytes = _contrast_polygon_bytes(label="prior")
    prior.write_bytes(prior_bytes)
    with controller.locked():
        controller._contrast_selection_mode = "user_defined_areas"
        controller._contrast_geojson_path = str(prior)
        controller._contrast_geojson_name_key = "name"
        controller._contrast_object_param = "prior-objective"

    candidate = tmp_path / "candidate.geojson"
    candidate.write_bytes(_contrast_polygon_bytes(label="replacement"))
    accepted = tmp_path / "_pups/omni/contrasts/_uploads/current/areas.geojson"

    class Prepared:
        candidate_path = candidate
        receipt = {"status": "prepared"}
        is_terminal = False
        rejected: str | None = None
        lease = type("Lease", (), {"assert_owned": lambda self: None})()

        def reject(self, code: str) -> None:
            self.rejected = code
            self.receipt["status"] = "rejected"
            self.is_terminal = True

    prepared = Prepared()
    prepared_upload = (prepared, accepted)
    transaction = omni_routes._snapshot_omni_nodb(controller, prepared_upload)
    assert transaction is not None
    workflow_active["value"] = True
    omni_routes._parse_inputs_with_prepared_upload(
        omni=controller,
        parsed_inputs={
            "omni_contrast_selection_mode": "user_defined_areas",
            "omni_contrast_geojson_name_key": "name",
        },
        wd=str(tmp_path),
        prepared_upload=prepared_upload,
    )
    # Model a build-owned persistence point before the injected failure.
    with controller.locked():
        controller._contrast_names = ["partial-build"]

    blocked = threading.Event()
    release = threading.Event()

    def concurrent_mutation() -> None:
        try:
            with controller.locked():
                raise AssertionError("concurrent mutation entered the active workflow transaction")
        except NoDbAlreadyLockedError:
            blocked.set()
        release.wait(timeout=2.0)
        with controller.locked():
            controller._contrast_object_param = "concurrent-objective"

    worker = threading.Thread(target=concurrent_mutation)
    worker.start()
    assert blocked.wait(timeout=1.0)
    omni_routes._rollback_prepared_omni_upload(
        prepared_upload,
        omni=controller,
        wd=str(tmp_path),
        nodb_backup=transaction,
        code="omni_build_failed",
    )
    workflow_active["value"] = False
    release.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive()

    reloaded = omni_routes.Omni.load_detached(str(tmp_path))
    assert reloaded._contrast_geojson_path == str(prior)
    assert reloaded._contrast_object_param == "concurrent-objective"
    assert reloaded._contrast_names is None
    assert prior.read_bytes() == prior_bytes
    assert not accepted.exists()
    assert prepared.rejected == "omni_build_failed"


def test_run_omni_contrasts_rejects_oversize_geojson_upload_with_413(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "GEOJSON_MAX_BYTES", 4)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(tmp_path / "run"))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": '[{\"control_scenario\":\"uniform_low\",\"contrast_scenario\":\"mulch\"}]',
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
            files={"omni_contrast_geojson": ("areas.geojson", b"abcdef", "application/geo+json")},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "Uploaded vector exceeds the endpoint size limit."
    assert payload["error"]["code"] == "vector_limit_exceeded"


@pytest.mark.parametrize("endpoint", ["run-omni-contrasts", "run-omni-contrasts-dry-run"])
def test_omni_contrast_routes_reject_unsupported_geometry_before_parse_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    wd = tmp_path / "run"
    prior = wd / "_pups" / "omni" / "contrasts" / "_uploads" / "prior" / "areas.geojson"
    prior.parent.mkdir(parents=True)
    prior_bytes = _contrast_polygon_bytes(label="previous")
    prior.write_bytes(prior_bytes)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(wd))

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            raise AssertionError("parse_inputs must not run for rejected geometry")

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())
    point = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "point"},
                    "geometry": {"type": "Point", "coordinates": [-116.0, 46.0]},
                }
            ],
        }
    ).encode()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/run-1/cfg/{endpoint}",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_contrast_pairs": '[{"control_scenario":"uniform_low","contrast_scenario":"mulch"}]',
            },
            files={"omni_contrast_geojson": ("areas.geojson", point, "application/geo+json")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_vector"
    assert prior.read_bytes() == prior_bytes
    attempt = next((wd / "_pups" / "omni" / "contrasts" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert receipt["status"] == "rejected"


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


def test_saved_sbs_reordered_rows_select_association_not_position(tmp_path):
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    first = wd / "omni/_limbo/00/first.tif"
    second = wd / "omni/_limbo/01/second.tif"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    sbs_raster_bytes(first)
    sbs_raster_bytes(second)
    saved = [{"type": "sbs_map", "sbs_file_path": str(path)} for path in (first, second)]
    receipts = omni_routes._prevalidate_omni_sbs_inputs(
        {"scenarios": [saved[1]]}, None, FormData(), wd=str(wd), saved_scenarios=saved
    )
    parsed = omni_routes._prepare_omni_scenarios(
        {"scenarios": [saved[1]]}, None, FormData(), wd=str(wd),
        runid="run", config="cfg", reuse_receipts=receipts,
    )
    assert parsed[0][1]["sbs_file_path"] == str(second)


def test_saved_sbs_consumed_child_restaged_before_reset_without_receipt(tmp_path):
    from tests.factories.raster import sbs_raster_bytes
    from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition
    from wepppy.nodb.mods.omni.omni_sbs_freshness import SbsExecution
    import shutil

    wd = tmp_path / "run"
    staged = wd / "omni/_limbo/03/severity.tif"
    saved = {"type": "sbs_map", "sbs_file_path": str(staged)}
    child_root = wd / "_pups/omni/scenarios" / _scenario_name_from_scenario_definition(saved)
    child = child_root / "disturbed/severity.tif"
    child.parent.mkdir(parents=True)
    raw = sbs_raster_bytes(child)
    receipts = omni_routes._prevalidate_omni_sbs_inputs(
        {"scenarios": [saved]}, None, FormData(), wd=str(wd), saved_scenarios=[saved]
    )
    assert not staged.exists(), "prevalidation must not publish recovery files"
    parsed = omni_routes._prepare_omni_scenarios(
        {"scenarios": [saved]}, None, FormData(), wd=str(wd),
        runid="run", config="cfg", reuse_receipts=receipts,
    )
    assert parsed[0][1]["sbs_file_path"] == str(staged)
    assert staged.read_bytes() == raw
    execution = SbsExecution.capture(parsed[0][1])
    shutil.rmtree(child_root)
    child.parent.mkdir(parents=True)
    execution.copy_to(child)
    assert child.read_bytes() == raw
    assert not staged.exists()


@pytest.mark.parametrize("old_prefix", [False, True])
def test_saved_sbs_child_collision_rejected_and_fork_rebases_locally(tmp_path, old_prefix):
    from tests.factories.raster import sbs_raster_bytes
    from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition

    wd = tmp_path / "run"
    prefix = "/original/project" if old_prefix else str(wd)
    saved = [{"type": "sbs_map", "sbs_file_path": f"{prefix}/omni/_limbo/{i:02d}/same.tif"}
             for i in range(2)]
    child = wd / "_pups/omni/scenarios" / _scenario_name_from_scenario_definition(saved[0]) / "disturbed/same.tif"
    child.parent.mkdir(parents=True)
    sbs_raster_bytes(child)
    with pytest.raises(ValueError, match="child is ambiguous"):
        omni_routes._prevalidate_omni_sbs_inputs(
            {"scenarios": [saved[0]]}, None, FormData(), wd=str(wd), saved_scenarios=saved,
        )
    receipts = omni_routes._prevalidate_omni_sbs_inputs(
        {"scenarios": [saved[0]]}, None, FormData(), wd=str(wd), saved_scenarios=saved[:1],
    )
    assert receipts[0].source == child
    assert receipts[0].staged == wd / "omni/_limbo/00/same.tif"


@pytest.mark.parametrize("bad_source", ["invalid", "symlink", "traversal"])
def test_saved_sbs_present_invalid_source_never_falls_back(tmp_path, bad_source):
    from tests.factories.raster import sbs_raster_bytes
    from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition

    wd = tmp_path / "run"
    staged = wd / "omni/_limbo/00/map.tif"
    staged.parent.mkdir(parents=True)
    saved = {"type": "sbs_map", "sbs_file_path": str(staged)}
    child = wd / "_pups/omni/scenarios" / _scenario_name_from_scenario_definition(saved) / "disturbed/map.tif"
    child.parent.mkdir(parents=True)
    sbs_raster_bytes(child)
    if bad_source == "invalid":
        staged.write_text("not a raster")
    elif bad_source == "symlink":
        staged.symlink_to(child)
    else:
        saved["sbs_file_path"] = str(wd) + "/omni/_limbo/../map.tif"
    with pytest.raises(omni_routes.UploadError):
        omni_routes._prevalidate_omni_sbs_inputs(
            {"scenarios": [saved]}, None, FormData(), wd=str(wd), saved_scenarios=[saved],
        )


def test_new_sbs_replacement_isolated_from_accepted_same_name(tmp_path):
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "run"
    old = wd / "omni/_limbo/00/severity.tif"
    old.parent.mkdir(parents=True)
    raw = sbs_raster_bytes(old)
    form = FormData({"scenarios[0][sbs_file]": UploadFile(io.BytesIO(raw), filename=old.name)})
    payload = {"scenarios": [{"type": "sbs_map", "sbs_file_path": str(old)}]}
    receipts = omni_routes._prevalidate_omni_sbs_inputs(payload, None, form, wd=str(wd))
    parsed = omni_routes._prepare_omni_scenarios(
        payload, None, form, wd=str(wd), runid="run", config="cfg", reuse_receipts=receipts,
    )
    new = Path(parsed[0][1]["sbs_file_path"])
    assert new != old
    assert new.name == old.name
    assert new.read_bytes() == old.read_bytes() == raw


def test_saved_sbs_restore_checks_copied_bytes_before_publication(tmp_path, monkeypatch):
    from tests.factories.raster import sbs_raster_bytes
    from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition

    wd = tmp_path / "run"
    staged = wd / "omni/_limbo/03/severity.tif"
    saved = {"type": "sbs_map", "sbs_file_path": str(staged)}
    child = wd / "_pups/omni/scenarios" / _scenario_name_from_scenario_definition(saved) / "disturbed/severity.tif"
    child.parent.mkdir(parents=True)
    sbs_raster_bytes(child)
    receipts = omni_routes._prevalidate_omni_sbs_inputs(
        {"scenarios": [saved]}, None, FormData(), wd=str(wd), saved_scenarios=[saved],
    )
    original = omni_routes.save_upload_file

    def mutate_before_copy(upload, **kwargs):
        # A different but valid raster arrives after source validation, before
        # the open stream is copied. Real staged validation must reject it.
        sbs_raster_bytes(child, nodata_only=True)
        return original(upload, **kwargs)

    monkeypatch.setattr(omni_routes, "save_upload_file", mutate_before_copy)
    with pytest.raises(omni_routes.UploadError, match="changed"):
        omni_routes._prepare_omni_scenarios(
            {"scenarios": [saved]}, None, FormData(), wd=str(wd),
            runid="run", config="cfg", reuse_receipts=receipts,
        )
    assert not staged.exists()
    assert child.exists()


@pytest.mark.parametrize("drift", [False, True])
def test_saved_sbs_real_nodb_commit_rechecks_association(tmp_path, monkeypatch, drift):
    from tests.factories.raster import sbs_raster_bytes

    wd = tmp_path / "real-omni-commit"
    wd.mkdir()
    omni = omni_routes.Omni(str(wd), "0.cfg")
    staged = wd / "omni/_limbo/00/severity.tif"
    staged.parent.mkdir(parents=True)
    sbs_raster_bytes(staged)
    saved = {"type": "sbs_map", "sbs_file_path": str(staged)}
    omni.parse_scenarios([(omni_routes.OmniScenario.SBSmap, saved)])
    _stub_auth(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(wd))
    original = omni_routes._prepare_omni_scenarios

    def prepare_with_concurrent_change(*args, **kwargs):
        result = original(*args, **kwargs)
        if drift:
            concurrent = omni_routes.Omni.load_detached(str(wd))
            concurrent._init_logging()
            concurrent.scenarios = [{"type": "uniform_low"}]
        return result

    monkeypatch.setattr(omni_routes, "_prepare_omni_scenarios", prepare_with_concurrent_change)
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/_base/run-omni", json={"scenarios": [saved]})
    assert response.status_code == (400 if drift else 200), response.text
    durable = omni_routes.Omni.load_detached(str(wd))
    assert durable.scenarios == ([{"type": "uniform_low"}] if drift else [saved])
    assert staged.exists()
    if drift:
        assert "changed" in response.json()["error"]["message"]


def test_session_human_is_used_for_omni_retention(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        omni_routes,
        "current_auth_actor",
        lambda: {"token_class": "session", "user_id": 78, "session_id": "not-persisted"},
    )
    assert omni_routes._retention_actor().receipt_value() == {"kind": "human", "user_id": 78}
