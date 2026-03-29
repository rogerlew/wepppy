from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import export_routes
from wepppy.nodb.mods.features_export.contracts import (
    FeaturesExportValidationError,
    ValidationIssue,
)
from wepppy.nodb.redis_prep import TaskEnum

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(export_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "features-job-1") -> dict[str, object]:
    captured: dict[str, object] = {}

    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, func, args, timeout):
            captured["func"] = func
            captured["args"] = args
            captured["timeout"] = timeout
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(export_routes, "Queue", DummyQueue)
    monkeypatch.setattr(export_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return captured


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    state: dict[str, list[object]] = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            state["jobs"].append((key, job_id))

    monkeypatch.setattr(export_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


def test_features_export_submit_non_json_returns_415(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            data="not-json",
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 415
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_media_type"


def test_features_export_submit_empty_json_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/export/features", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "missing_field"


def test_features_export_profile_resolve_missing_profile_text_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features/profile/resolve",
            json={"format": "geopackage"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["path"] == "profile_text"


def test_features_export_profile_resolve_success_returns_normalized_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        export_routes,
        "parse_profile_text",
        lambda profile_text: {"format": "csv", "units": "si", "layers": ["watershed.subcatchments"]},
    )
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: SimpleNamespace(
            plan=SimpleNamespace(
                request=SimpleNamespace(
                    to_mapping=lambda: {
                        "format": "csv",
                        "units": "si",
                        "layers": ["watershed.subcatchments"],
                    }
                )
            )
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features/profile/resolve",
            json={"profile_text": "request:\n  format: csv\n"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "profile": {
            "format": "csv",
            "units": "si",
            "layers": ["watershed.subcatchments"],
        }
    }


def test_features_export_profile_resolve_invalid_profile_text_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(
        export_routes,
        "parse_profile_text",
        lambda profile_text: (_ for _ in ()).throw(
            export_routes.FeaturesExportProfileError("bad yaml")
        ),
    )
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features/profile/resolve",
            json={"profile_text": "bad"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "invalid_profile_text"


def test_features_export_submit_valid_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="features-job-22")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: SimpleNamespace(cache_key_parts=SimpleNamespace(cache_key="cache-key")),
    )
    monkeypatch.setattr(export_routes, "get_cache_index_entry", lambda wd, cache_key: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={
                "format": "geopackage",
                "units": "si",
                "layers": ["watershed.subcatchments"],
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "features-job-22"
    assert payload["status_url"] == "/rq-engine/api/jobstatus/features-job-22"
    assert payload["download_url"] == "/rq-engine/api/runs/run-1/cfg/export/features/job/features-job-22/download"
    assert captured["func"] is export_routes.run_features_export_rq
    assert prep_state["removed"] == [TaskEnum.run_features_export]
    assert prep_state["jobs"] == [("features_export", "features-job-22")]


def test_features_export_submit_accepts_tabular_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="features-job-tabular")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: SimpleNamespace(cache_key_parts=SimpleNamespace(cache_key="cache-key")),
    )
    monkeypatch.setattr(export_routes, "get_cache_index_entry", lambda wd, cache_key: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={
                "format": "csv",
                "units": "project",
                "layers": ["wepp.summary.hillslopes"],
                "tabular": {"concatenate_tables": True, "temporal_layout": "long"},
            },
        )

    assert response.status_code == 202
    enqueued_payload = captured["args"][2]
    assert enqueued_payload["tabular"] == {"concatenate_tables": True, "temporal_layout": "long"}


def test_features_export_submit_cache_hit_enqueues_finalize_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="features-job-33")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: SimpleNamespace(
            cache_key_parts=SimpleNamespace(cache_key="cache-key"),
            plan=SimpleNamespace(request=SimpleNamespace(format="geopackage")),
        ),
    )
    monkeypatch.setattr(export_routes, "get_cache_index_entry", lambda wd, cache_key: {"artifact_id": "artifact-1"})
    monkeypatch.setattr(export_routes, "cache_entry_supports_cache_hit", lambda wd, **kwargs: True)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={
                "format": "geopackage",
                "units": "si",
                "layers": ["watershed.subcatchments"],
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "features-job-33"
    assert captured["func"] is export_routes.run_features_export_cache_hit_rq


def test_features_export_submit_invalid_cache_entry_falls_back_to_full_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="features-job-44")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: SimpleNamespace(
            cache_key_parts=SimpleNamespace(cache_key="cache-key"),
            plan=SimpleNamespace(request=SimpleNamespace(format="geopackage")),
        ),
    )
    monkeypatch.setattr(export_routes, "get_cache_index_entry", lambda wd, cache_key: {"artifact_id": "artifact-1"})
    monkeypatch.setattr(export_routes, "cache_entry_supports_cache_hit", lambda wd, **kwargs: False)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={
                "format": "geopackage",
                "units": "si",
                "layers": ["watershed.subcatchments"],
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "features-job-44"
    assert captured["func"] is export_routes.run_features_export_rq


def test_features_export_submit_invalid_selector_payload_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: "/tmp/run")

    validation_error = FeaturesExportValidationError(
        [
            ValidationIssue(
                code="unknown_layer_id",
                message="Unknown layer id(s): ['bad.layer'].",
                path="layers",
            )
        ]
    )
    monkeypatch.setattr(
        export_routes,
        "prepare_export_submission",
        lambda wd, payload: (_ for _ in ()).throw(validation_error),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={"format": "geopackage", "units": "si", "layers": ["bad.layer"]},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "unknown_layer_id"


def test_features_export_download_before_finished_returns_409(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "runid": "run-1", "status": "started"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/job/job-9/download")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "conflict"


def test_features_export_download_after_finished_returns_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gpkg"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {
            "job_id": job_id,
            "runid": "run-1",
            "status": "finished",
            "result": {"artifact_relpath": artifact_relpath},
        },
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/job/job-9/download")

    assert response.status_code == 200
    assert "features_export.gpkg" in response.headers.get("content-disposition", "")


def test_features_export_published_download_returns_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gpkg.zip"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, artifact_relpath),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/prep-wepp/download")

    assert response.status_code == 200
    assert "run-1.prep-wepp.geopackage.zip" in response.headers.get("content-disposition", "")


def test_features_export_published_download_alias_uses_canonical_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gpkg.zip"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, artifact_relpath),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/post_wepp/download")

    assert response.status_code == 200
    assert "run-1.prep-wepp.geopackage.zip" in response.headers.get("content-disposition", "")


def test_features_export_published_download_prep_details_filename_includes_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.csv.zip"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, artifact_relpath),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/prep-details/download")

    assert response.status_code == 200
    assert "run-1.prep-details.csv.zip" in response.headers.get("content-disposition", "")


def test_features_export_published_download_stale_returns_409(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (_ for _ in ()).throw(
            export_routes.FeaturesExportServiceError(
                "Published features export artifact is stale.",
                status_code=409,
                code="stale_publication",
                details="profile=prep-wepp: stale",
            )
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/prep-wepp/download")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "stale_publication"


def test_features_export_submit_auth_401_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        export_routes,
        "require_jwt",
        lambda request, required_scopes=None: (_ for _ in ()).throw(
            export_routes.AuthError("Missing Authorization header", status_code=401, code="unauthorized")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/export/features",
            json={"format": "geopackage", "units": "si", "layers": ["watershed.subcatchments"]},
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"


def test_features_export_download_auth_403_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(
        export_routes,
        "authorize_run_access",
        lambda claims, runid: (_ for _ in ()).throw(
            export_routes.AuthError("Token not authorized for run", status_code=403, code="forbidden")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/job/job-9/download")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_features_export_download_public_run_allows_missing_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gpkg"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "_is_public_run_for_download", lambda runid: True)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {
            "job_id": job_id,
            "runid": "run-1",
            "status": "finished",
            "result": {"artifact_relpath": artifact_relpath},
        },
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/job/job-9/download")

    assert response.status_code == 200
    assert "features_export.gpkg" in response.headers.get("content-disposition", "")


def test_features_export_published_download_public_run_allows_missing_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gpkg.zip"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    monkeypatch.setattr(export_routes, "_is_public_run_for_download", lambda runid: True)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(tmp_path))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, artifact_relpath),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/prep-wepp/download")

    assert response.status_code == 200
    assert "run-1.prep-wepp.geopackage.zip" in response.headers.get("content-disposition", "")


def test_features_export_published_download_private_run_requires_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(export_routes, "_is_public_run_for_download", lambda runid: False)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/export/features/published/prep-wepp/download")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
