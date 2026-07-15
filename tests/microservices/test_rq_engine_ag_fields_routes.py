from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import ag_fields_routes
from wepppy.microservices.rq_engine.auth import AuthError


pytestmark = pytest.mark.microservice


class DummyAgFields:
    def __init__(self, root: Path) -> None:
        self.ag_fields_dir = str(root / "ag_fields")
        self.ag_field_wepp_runs_dir = str(root / "wepp" / "ag_fields" / "runs")
        self.ag_field_wepp_output_dir = str(root / "wepp" / "ag_fields" / "output")
        self.sub_fields_wgs_geojson = str(root / "ag_fields" / "sub_fields" / "sub_fields.WGS.geojson")
        for directory in (
            self.ag_fields_dir,
            self.ag_field_wepp_runs_dir,
            self.ag_field_wepp_output_dir,
            str(Path(self.sub_fields_wgs_geojson).parent),
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)
        self.geojson_is_valid = True
        self.field_boundaries_geojson = "fields.WGS.geojson"
        self.field_boundaries_source_filename = "uploaded-fields.geojson"
        self.geojson_hash = "hash"
        self.geojson_timestamp = 123
        self.field_columns = ["field_id", "Crop2001"]
        self.field_n = 1
        self.field_id_key = "field_id"
        self.rotation_accessor = "Crop{}"
        self.sub_field_n = 2
        self.sub_field_fp_n = 0
        self.wepp_bin = "wepp_dcc52a6"
        self.cleared = False
        self.watershed_cleared = False
        self.watershed_cleared_schemes = []
        self.watershed_job_ids = {}
        self.saved_rows = None

    def validate_field_boundary_geojson(self, path: Path, *, source_filename: str | None = None):
        assert path.name == "field-boundaries-upload.geojson"
        assert source_filename == "fields.geojson"
        self.field_boundaries_source_filename = source_filename
        return {"field_id_duplicates": [7]}

    def confirm_schema(self, field_id_key: str, rotation_accessor: str) -> None:
        if rotation_accessor == "Bad{}":
            raise ValueError("Column key Bad2001 not found")
        self.field_id_key = field_id_key
        self.rotation_accessor = rotation_accessor

    def get_staleness(self):
        return {"subfields": False, "wepp_runs": False}

    def get_readiness(self):
        return {
            "observed_climate": True,
            "observed_start_year": 2001,
            "observed_end_year": 2001,
            "watershed_abstraction": True,
            "parent_wepp": True,
            "missing_parent_wepp_ids": [],
        }

    def get_plant_file_inventory(self):
        return {
            "files": [{"filename": "corn.man", "valid": True}],
            "valid_files": ["corn.man"],
            "invalid_files": [],
        }

    def delete_plant_file(self, filename: str):
        assert filename == "corn.man"
        return {"files": [], "valid_files": [], "invalid_files": []}

    def validate_rotation_lookup(self):
        return [
            {
                "crop_name": "Corn",
                "database": "plant_file_db",
                "rotation_id": "corn.man",
                "status": "ok",
                "valid": True,
                "message": None,
                "used": True,
            }
        ]

    def write_rotation_lookup(self, rows):
        self.saved_rows = rows
        return self.validate_rotation_lookup()

    def get_weppcloud_management_options(self):
        return [{"id": "1", "description": "Corn"}]

    def clear_ag_field_wepp_artifacts(self) -> None:
        self.cleared = True

    def clear_watershed_integration(self, scheme=None) -> None:
        self.watershed_cleared = True
        self.watershed_cleared_schemes.append(scheme.value if hasattr(scheme, "value") else scheme or "concept_2")

    def set_watershed_integration_job_id(self, scheme, job_id) -> None:
        self.watershed_job_ids[scheme.value if hasattr(scheme, "value") else scheme] = job_id

    def set_watershed_integration_job_ids(self, job_ids) -> None:
        self.watershed_job_ids.update(
            {
                scheme.value if hasattr(scheme, "value") else scheme: job_id
                for scheme, job_id in job_ids.items()
            }
        )

    def get_watershed_integration_state(self):
        return {
            "status": "not_run",
            "stale": False,
            "source_signature": None,
            "summary": None,
            "error": None,
            "root_relpath": "wepp/ag_fields/watershed",
            "browse_relpath": "wepp/ag_fields/watershed/",
            "limitation": "Field water and sediment are injected at the parent outlet.",
        }

    def get_watershed_integration_states(self):
        return {
            scheme: {
                **self.get_watershed_integration_state(),
                "scheme": scheme,
                "status": "not_run",
            }
            for scheme in ("concept_1", "concept_2", "hybrid")
        }


@pytest.fixture
def route_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    controller = DummyAgFields(tmp_path)
    auth_calls: list[tuple[object, str]] = []
    monkeypatch.setattr(ag_fields_routes, "require_jwt", lambda request, required_scopes=None: {"scopes": required_scopes})
    monkeypatch.setattr(
        ag_fields_routes,
        "authorize_run_access",
        lambda claims, runid: auth_calls.append((claims, runid)),
    )
    monkeypatch.setattr(ag_fields_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(ag_fields_routes.AgFields, "getInstance", lambda wd: controller)
    monkeypatch.setattr(ag_fields_routes.RedisPrep, "tryGetInstance", lambda wd: None)
    return controller, auth_calls


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/runs/demo/cfg/agfields/boundaries"),
        ("post", "/api/runs/demo/cfg/agfields/schema"),
        ("post", "/api/runs/demo/cfg/agfields/build-subfields"),
        ("post", "/api/runs/demo/cfg/agfields/plant-database"),
        ("get", "/api/runs/demo/cfg/agfields/plant-files"),
        ("delete", "/api/runs/demo/cfg/agfields/plant-files/corn.man"),
        ("get", "/api/runs/demo/cfg/agfields/rotation-mapping"),
        ("post", "/api/runs/demo/cfg/agfields/rotation-mapping"),
        ("get", "/api/runs/demo/cfg/agfields/management-options"),
        ("post", "/api/runs/demo/cfg/agfields/run-wepp"),
        ("post", "/api/runs/demo/cfg/agfields/run-watershed"),
        ("post", "/api/runs/demo/cfg/agfields/clear"),
        ("post", "/api/runs/demo/cfg/agfields/clear-watershed"),
        ("get", "/api/runs/demo/cfg/agfields/sub-fields.geojson"),
        ("get", "/api/runs/demo/cfg/agfields/state"),
    ],
)
def test_every_agfields_route_authorizes_run_access(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(ag_fields_routes, "require_jwt", lambda request, required_scopes=None: {})

    def _deny(_claims, runid: str) -> None:
        calls.append(runid)
        raise AuthError("denied", status_code=403, code="forbidden")

    monkeypatch.setattr(ag_fields_routes, "authorize_run_access", _deny)

    with TestClient(rq_engine.app) as client:
        response = client.request(method, path)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert calls == ["demo"]


def test_boundary_upload_returns_controller_summary(route_context) -> None:
    controller, auth_calls = route_context

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/boundaries",
            files={"field_boundaries": ("fields.geojson", b"{}")},
        )

    assert response.status_code == 200
    assert response.json()["result"] == {
        "field_n": 1,
        "field_columns": ["field_id", "Crop2001"],
        "geojson_timestamp": 123,
        "field_id_duplicates": [7],
    }
    assert controller.field_boundaries_source_filename == "fields.geojson"
    assert auth_calls[-1][1] == "demo"


def test_successful_sync_mutations_invalidate_ag_fields_preflight(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[object] = []
    prep = SimpleNamespace(
        remove_timestamp=lambda task: removed.append(task),
        get_rq_job_id=lambda key: None,
    )
    monkeypatch.setattr(ag_fields_routes.RedisPrep, "getInstance", lambda wd: prep)
    monkeypatch.setattr(ag_fields_routes, "_active_job_conflict_response", lambda wd: None)

    with TestClient(rq_engine.app) as client:
        responses = [
            client.post(
                "/api/runs/demo/cfg/agfields/boundaries",
                files={"field_boundaries": ("fields.geojson", b"{}")},
            ),
            client.post(
                "/api/runs/demo/cfg/agfields/schema",
                json={"field_id_key": "field_id", "rotation_accessor": "Crop{}"},
            ),
            client.post(
                "/api/runs/demo/cfg/agfields/rotation-mapping",
                json={"rows": [{"crop_name": "Corn"}]},
            ),
            client.delete("/api/runs/demo/cfg/agfields/plant-files/corn.man"),
            client.post("/api/runs/demo/cfg/agfields/clear"),
        ]

    assert all(response.status_code == 200 for response in responses)
    assert removed == [ag_fields_routes.TaskEnum.run_ag_fields] * len(responses)


def test_boundary_upload_rejects_extension_and_oversize(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(rq_engine.app) as client:
        bad_extension = client.post(
            "/api/runs/demo/cfg/agfields/boundaries",
            files={"field_boundaries": ("fields.txt", b"{}")},
        )
        monkeypatch.setattr(ag_fields_routes, "AGFIELDS_BOUNDARY_MAX_BYTES", 4)
        oversize = client.post(
            "/api/runs/demo/cfg/agfields/boundaries",
            files={"field_boundaries": ("fields.geojson", b"12345")},
        )

    assert bad_extension.status_code == 400
    assert bad_extension.json()["error"]["message"].startswith("Invalid file extension")
    assert oversize.status_code == 413
    assert oversize.json()["error"]["code"] == "payload_too_large"


def test_schema_failure_leaves_field_id_unchanged(route_context) -> None:
    controller, _auth_calls = route_context
    controller.field_id_key = "field_id"

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/schema",
            json={"field_id_key": "Crop2001", "rotation_accessor": "Bad{}"},
        )

    assert response.status_code == 400
    assert controller.field_id_key == "field_id"


def test_build_subfields_enqueues_contractual_job_key(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def _enqueue(wd, job_key, func, args):
        calls.append((wd, job_key, func, args))
        return ag_fields_routes.JSONResponse({"job_id": "build-1"}, status_code=202)

    monkeypatch.setattr(ag_fields_routes, "_enqueue_job", _enqueue)
    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/build-subfields",
            json={"sub_field_min_area_threshold_m2": 20},
        )

    assert response.status_code == 202, response.text
    assert response.json() == {"job_id": "build-1"}
    assert calls[0][1] == "agfields_build_subfields"
    assert calls[0][3] == ("demo", 20.0)


def test_build_subfields_returns_conflict_when_an_agfields_job_is_active(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ag_fields_routes,
        "_enqueue_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ag_fields_routes.AgFieldsJobConflict("AgFields job already active")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/demo/cfg/agfields/build-subfields", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agfields_job_active"


def test_enqueue_job_serializes_submission_and_persists_job_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    class DummyPrep:
        def get_rq_job_id(self, _key: str):
            return None

        def remove_timestamp(self, task) -> None:
            events.append(("preflight-remove", task))

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            events.append(("hint", key, job_id))

    class DummyLockRedis:
        owner = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set(self, key, owner, *, nx, ex):
            events.append(("lock", key, nx, ex))
            self.owner = owner
            return True

        def get(self, _key):
            return self.owner

        def delete(self, key):
            events.append(("unlock", key))

    class DummyRqRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyQueue:
        def __init__(self, connection):
            assert isinstance(connection, DummyRqRedis)

        def enqueue_call(self, func, args, timeout):
            events.append(("enqueue", func, args, timeout))
            return SimpleNamespace(id="job-queued")

    lock_redis = DummyLockRedis()
    rq_redis = DummyRqRedis()
    monkeypatch.setattr(ag_fields_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    monkeypatch.setattr(
        ag_fields_routes,
        "redis_connection_kwargs",
        lambda db, **kwargs: {"db": db},
    )
    monkeypatch.setattr(
        ag_fields_routes.redis,
        "Redis",
        lambda **kwargs: lock_redis if kwargs["db"] == ag_fields_routes.RedisDB.LOCK else rq_redis,
    )
    monkeypatch.setattr(ag_fields_routes, "Queue", DummyQueue)

    response = ag_fields_routes._enqueue_job(
        "/runs/demo",
        "agfields_build_subfields",
        ag_fields_routes.build_ag_fields_subfields_rq,
        ("demo", 0.0),
    )

    assert response.status_code == 202
    assert ("hint", "agfields_build_subfields", "job-queued") in events
    assert ("preflight-remove", ag_fields_routes.TaskEnum.run_ag_fields) in events
    assert events.index(("preflight-remove", ag_fields_routes.TaskEnum.run_ag_fields)) < next(
        index for index, event in enumerate(events) if event[0] == "enqueue"
    )
    assert ("unlock", "agfields:submit_lock:demo") in events
    assert next(event for event in events if event[0] == "lock")[3] == 30


def test_enqueue_watershed_jobs_serializes_run_all_with_allow_failure_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    class DummyPrep:
        def get_rq_job_id(self, _key: str):
            return None

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            events.append(("hint", key, job_id))

    class DummyController:
        def set_watershed_integration_job_ids(self, job_ids) -> None:
            for scheme, job_id in job_ids.items():
                events.append(("state", scheme, job_id))

        def get_watershed_integration_states(self):
            return {
                scheme: {"status": "not_run"}
                for scheme in ("concept_1", "concept_2", "hybrid")
            }

    class DummyRedis:
        owner = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set(self, key, owner, *, nx, ex):
            self.owner = owner
            return True

        def get(self, _key):
            return self.owner

        def delete(self, key):
            events.append(("unlock", key))

    class DummyDependency:
        def __init__(self, *, jobs, allow_failure):
            self.dependencies = jobs
            self.allow_failure = allow_failure
            events.append(("dependency", jobs[0], allow_failure))

    class DummyQueue:
        def __init__(self, connection):
            pass

        def enqueue_call(self, func, args, timeout, depends_on, job_id):
            events.append(("enqueue", args, depends_on, job_id))
            return SimpleNamespace(id=job_id)

    redis_instance = DummyRedis()
    monkeypatch.setattr(ag_fields_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    monkeypatch.setattr(ag_fields_routes.AgFields, "getInstance", lambda wd: DummyController())
    monkeypatch.setattr(ag_fields_routes.redis, "Redis", lambda **kwargs: redis_instance)
    monkeypatch.setattr(ag_fields_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ag_fields_routes, "Dependency", DummyDependency)

    response = ag_fields_routes._enqueue_watershed_jobs(
        "/runs/demo",
        "demo",
        (
            ag_fields_routes.AgFieldsRoutingScheme.CONCEPT_1,
            ag_fields_routes.AgFieldsRoutingScheme.CONCEPT_2,
            ag_fields_routes.AgFieldsRoutingScheme.HYBRID,
        ),
        4,
    )

    assert response.status_code == 202
    payload = json.loads(response.body)
    assert payload["job_id"] == payload["job_ids"]["concept_1"]
    assert set(payload["job_ids"]) == {"concept_1", "concept_2", "hybrid"}
    assert len(set(payload["job_ids"].values())) == 3
    enqueue_events = [event for event in events if event[0] == "enqueue"]
    assert [event[1][2] for event in enqueue_events] == ["concept_1", "concept_2", "hybrid"]
    assert enqueue_events[0][2] is None
    assert [(event[1], event[2]) for event in events if event[0] == "dependency"] == [
        (payload["job_ids"]["concept_1"], True),
        (payload["job_ids"]["concept_2"], True),
    ]
    assert (
        "hint",
        "agfields_run_watershed",
        payload["job_ids"]["concept_2"],
    ) in events
    assert [(event[1], event[2]) for event in events if event[0] == "state"] == [
        ("concept_1", payload["job_ids"]["concept_1"]),
        ("concept_2", payload["job_ids"]["concept_2"]),
        ("hybrid", payload["job_ids"]["hybrid"]),
    ]
    assert max(index for index, event in enumerate(events) if event[0] == "state") < min(
        index for index, event in enumerate(events) if event[0] == "enqueue"
    )


def _plant_zip_bytes() -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("corn.MAN", "management")
    return stream.getvalue()


def test_plant_database_upload_validates_archive_and_enqueues(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def _enqueue(wd, job_key, func, args):
        calls.append((wd, job_key, func, args))
        return ag_fields_routes.JSONResponse({"job_id": "plant-1"}, status_code=202)

    monkeypatch.setattr(ag_fields_routes, "_enqueue_job", _enqueue)
    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/plant-database",
            files={"plant_database": ("plants.zip", _plant_zip_bytes())},
        )

    assert response.status_code == 202, response.text
    assert calls[0][1] == "agfields_plantdb"
    assert calls[0][3][0] == "demo"
    assert calls[0][3][1].startswith("plant-db-")


def test_plant_database_upload_rejects_invalid_and_oversize_archives(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(rq_engine.app) as client:
        invalid = client.post(
            "/api/runs/demo/cfg/agfields/plant-database",
            files={"plant_database": ("plants.zip", b"not-a-zip")},
        )
        monkeypatch.setattr(ag_fields_routes, "AGFIELDS_PLANT_DB_MAX_BYTES", 4)
        oversize = client.post(
            "/api/runs/demo/cfg/agfields/plant-database",
            files={"plant_database": ("plants.zip", _plant_zip_bytes())},
        )

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_archive"
    assert oversize.status_code == 413
    assert oversize.json()["error"]["code"] == "archive_quota_exceeded"


def test_mapping_inventory_delete_management_options_and_clear_routes(route_context) -> None:
    controller, _auth_calls = route_context
    with TestClient(rq_engine.app) as client:
        inventory = client.get("/api/runs/demo/cfg/agfields/plant-files")
        mapping = client.get("/api/runs/demo/cfg/agfields/rotation-mapping")
        saved = client.post(
            "/api/runs/demo/cfg/agfields/rotation-mapping",
            json={"rows": [{"crop_name": "Corn"}]},
        )
        options = client.get("/api/runs/demo/cfg/agfields/management-options")
        deleted = client.delete("/api/runs/demo/cfg/agfields/plant-files/corn.man")
        cleared = client.post("/api/runs/demo/cfg/agfields/clear")

    assert inventory.status_code == 200
    assert mapping.json()["unique_crops"] == ["Corn"]
    assert saved.status_code == 200, saved.text
    assert controller.saved_rows == [{"crop_name": "Corn"}]
    assert options.json()["management_options"][0]["id"] == "1"
    assert deleted.status_code == 200
    assert cleared.status_code == 200
    assert controller.cleared is True


def test_sync_mutation_returns_conflict_while_job_is_active(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    monkeypatch.setattr(
        ag_fields_routes,
        "_active_job_conflict_response",
        lambda wd: ag_fields_routes.error_response(
            "AgFields job active",
            status_code=409,
            code="agfields_job_active",
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/rotation-mapping",
            json={"rows": [{"crop_name": "Corn"}]},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agfields_job_active"
    assert controller.saved_rows is None


def test_sync_mutation_returns_conflict_for_persisted_running_scheme_state(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    original = controller.get_watershed_integration_states

    def _states():
        states = original()
        states["hybrid"]["status"] = "running:parent_execution"
        return states

    monkeypatch.setattr(controller, "get_watershed_integration_states", _states)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/schema",
            json={"field_id_key": "field_id", "rotation_accessor": "Crop{}"},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agfields_job_active"
    assert "hybrid" in response.json()["error"]["details"]


def test_state_and_overlay_return_hydration_contract(route_context) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).write_text(
        json.dumps({"type": "FeatureCollection", "features": []}),
        encoding="utf-8",
    )
    with TestClient(rq_engine.app) as client:
        state = client.get("/api/runs/demo/cfg/agfields/state")
        overlay = client.get("/api/runs/demo/cfg/agfields/sub-fields.geojson")

    assert state.status_code == 200
    payload = state.json()
    assert payload["boundary"]["filename"] == "uploaded-fields.geojson"
    assert payload["schema"]["complete"] is True
    assert payload["subfields"]["complete"] is True
    assert payload["mapping"]["complete"] is True
    assert payload["readiness"]["parent_wepp"] is True
    assert payload["wepp"]["wepp_bin"] == "wepp_dcc52a6"
    assert set(payload["active_job_ids"]) == {
        "agfields_build_subfields",
        "agfields_plantdb",
        "agfields_run_wepp",
        "agfields_run_watershed_concept_1",
        "agfields_run_watershed_concept_2",
        "agfields_run_watershed_hybrid",
        "agfields_run_watershed",
    }
    assert payload["watershed_integration"]["status"] == "not_run"
    assert set(payload["watershed_integrations"]) == {"concept_1", "concept_2", "hybrid"}
    assert overlay.status_code == 200
    assert overlay.headers["content-type"].startswith("application/geo+json")

    controller.field_boundaries_source_filename = None
    with TestClient(rq_engine.app) as client:
        historical_state = client.get("/api/runs/demo/cfg/agfields/state")
    assert historical_state.json()["boundary"]["filename"] == "fields.WGS.geojson"


def test_state_job_ids_only_marks_active_rq_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return {
                "agfields_build_subfields": "build-active",
                "agfields_plantdb": "plant-complete",
                "agfields_run_wepp": None,
                "agfields_run_watershed_concept_1": None,
                "agfields_run_watershed_concept_2": None,
                "agfields_run_watershed_hybrid": None,
                "agfields_run_watershed": None,
            }[key]

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    statuses = {"build-active": "started", "plant-complete": "finished"}
    monkeypatch.setattr(ag_fields_routes.redis, "Redis", lambda **_kwargs: DummyRedis())
    monkeypatch.setattr(
        ag_fields_routes.Job,
        "fetch",
        lambda job_id, connection: SimpleNamespace(
            get_status=lambda refresh=False: statuses[job_id]
        ),
    )

    job_ids, active = ag_fields_routes._job_ids(DummyPrep())
    active_job = ag_fields_routes._find_active_job(DummyPrep(), DummyRedis())

    assert job_ids["agfields_plantdb"] == "plant-complete"
    assert active_job == {
        "key": "agfields_build_subfields",
        "job_id": "build-active",
        "status": "started",
    }
    assert active == {
        "agfields_build_subfields": "build-active",
        "agfields_plantdb": None,
        "agfields_run_wepp": None,
        "agfields_run_watershed_concept_1": None,
        "agfields_run_watershed_concept_2": None,
        "agfields_run_watershed_hybrid": None,
        "agfields_run_watershed": None,
    }


def test_run_and_clear_watershed_routes_use_fixed_additive_surface(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    (Path(controller.ag_field_wepp_runs_dir) / "p1.run").touch()
    calls = []

    def _enqueue(wd, runid, schemes, max_workers):
        calls.append((wd, runid, schemes, max_workers))
        return ag_fields_routes.JSONResponse(
            {"job_id": "watershed-1", "job_ids": {"concept_2": "watershed-1"}},
            status_code=202,
        )

    monkeypatch.setattr(ag_fields_routes, "_enqueue_watershed_jobs", _enqueue)
    monkeypatch.setattr(ag_fields_routes, "_active_job_conflict_response", lambda wd: None)

    with TestClient(rq_engine.app) as client:
        queued = client.post("/api/runs/demo/cfg/agfields/run-watershed", json={})
        cleared = client.post(
            "/api/runs/demo/cfg/agfields/clear-watershed",
            json={"scheme": "concept_1"},
        )

    assert queued.status_code == 202, queued.text
    assert calls[0][1] == "demo"
    assert [scheme.value for scheme in calls[0][2]] == ["concept_2"]
    assert calls[0][3] is None
    assert cleared.status_code == 200
    assert controller.watershed_cleared is True
    assert controller.watershed_cleared_schemes == ["concept_1"]


def test_run_all_expands_in_stable_order_and_clear_all_is_scheme_scoped(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    (Path(controller.ag_field_wepp_runs_dir) / "p1.run").touch()
    calls = []

    def _enqueue(wd, runid, schemes, max_workers):
        calls.append((wd, runid, schemes, max_workers))
        return ag_fields_routes.JSONResponse(
            {
                "job_id": "concept-1-job",
                "job_ids": {
                    "concept_1": "concept-1-job",
                    "concept_2": "concept-2-job",
                    "hybrid": "hybrid-job",
                },
            },
            status_code=202,
        )

    monkeypatch.setattr(ag_fields_routes, "_enqueue_watershed_jobs", _enqueue)
    monkeypatch.setattr(ag_fields_routes, "_active_job_conflict_response", lambda wd: None)

    with TestClient(rq_engine.app) as client:
        queued = client.post(
            "/api/runs/demo/cfg/agfields/run-watershed",
            json={"scheme": "all", "max_workers": 3},
        )
        cleared = client.post(
            "/api/runs/demo/cfg/agfields/clear-watershed",
            json={"scheme": "all"},
        )

    assert queued.status_code == 202, queued.text
    assert queued.json()["job_id"] == "concept-1-job"
    assert list(queued.json()["job_ids"]) == ["concept_1", "concept_2", "hybrid"]
    assert [scheme.value for scheme in calls[0][2]] == ["concept_1", "concept_2", "hybrid"]
    assert calls[0][3] == 3
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["cleared_schemes"] == ["concept_1", "concept_2", "hybrid"]
    assert controller.watershed_cleared_schemes == ["concept_1", "concept_2", "hybrid"]


def test_run_watershed_rejects_worker_count_above_operational_bound(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    (Path(controller.ag_field_wepp_runs_dir) / "p1.run").touch()
    enqueue_calls = []
    monkeypatch.setattr(
        ag_fields_routes,
        "_enqueue_watershed_jobs",
        lambda *args: enqueue_calls.append(args),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/run-watershed",
            json={"scheme": "concept_1", "max_workers": 17},
        )

    assert response.status_code == 400
    assert "between 1 and 16" in response.json()["error"]["message"]
    assert enqueue_calls == []


def test_run_and_clear_watershed_reject_unknown_scheme_before_mutation(
    route_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    (Path(controller.ag_field_wepp_runs_dir) / "p1.run").touch()
    enqueue_calls = []
    monkeypatch.setattr(
        ag_fields_routes,
        "_enqueue_watershed_jobs",
        lambda *args: enqueue_calls.append(args),
    )
    monkeypatch.setattr(ag_fields_routes, "_active_job_conflict_response", lambda wd: None)

    with TestClient(rq_engine.app) as client:
        queued = client.post(
            "/api/runs/demo/cfg/agfields/run-watershed",
            json={"scheme": "concept-1"},
        )
        cleared = client.post(
            "/api/runs/demo/cfg/agfields/clear-watershed",
            json={"scheme": "concept-1"},
        )

    assert queued.status_code == 400
    assert cleared.status_code == 400
    assert enqueue_calls == []
    assert controller.watershed_cleared_schemes == []


def test_run_wepp_enqueues_contractual_job_key(route_context, monkeypatch: pytest.MonkeyPatch) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    calls = []

    def _enqueue(wd, job_key, func, args):
        calls.append((wd, job_key, func, args))
        return ag_fields_routes.JSONResponse({"job_id": "wepp-1"}, status_code=202)

    monkeypatch.setattr(ag_fields_routes, "_enqueue_job", _enqueue)
    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/run-wepp",
            json={"max_workers": 4, "wepp_bin": "wepp_dcc52a6"},
        )

    assert response.status_code == 202
    assert calls[0][1] == "agfields_run_wepp"
    assert calls[0][3] == ("demo", 4, "wepp_dcc52a6")


def test_run_wepp_rejects_unknown_binary(route_context, monkeypatch: pytest.MonkeyPatch) -> None:
    controller, _auth_calls = route_context
    Path(controller.sub_fields_wgs_geojson).touch()
    monkeypatch.setattr(
        ag_fields_routes,
        "get_linux_wepp_bin_opts",
        lambda: ["wepp_dcc52a6"],
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/demo/cfg/agfields/run-wepp",
            json={"wepp_bin": "../../not-a-wepp-binary"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Unknown WEPP executable: ../../not-a-wepp-binary"
