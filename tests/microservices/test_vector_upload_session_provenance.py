"""Signed request identity through real retention accounting at each receiver.

Controller work and queue submission are bounded test doubles here; downstream
artifact correctness belongs to test_vector_upload_exact_downstream. JWT/session
parsing, route actor extraction, retained receipts, and Redis ledger are real.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pickle
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis
from fastapi.testclient import TestClient
from flask import Flask
from flask_login import LoginManager, UserMixin
from itsdangerous import Signer

import wepppy.microservices.rq_engine as rq_engine
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices import vector_upload_normalization as vectors
from wepppy.microservices.rq_engine import ag_fields_routes, auth, omni_routes, session_routes, upload_batch_runner_routes
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.integration


def _source(*, line=False, hostile=False):
    geometry = {"type": "Point", "coordinates": [-116.0, 46.0]} if hostile else (
        {"type": "LineString", "coordinates": [[-116.0, 46.0], [-115.9, 46.1]]} if line else
        {"type": "Polygon", "coordinates": [[[-116.0, 46.0], [-115.9, 46.0], [-115.9, 46.1], [-116.0, 46.0]]]}
    )
    return json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"field_id": 7, "name": "one", "Crop2001": "Corn"}, "geometry": geometry}]}, separators=(",", ":")).encode()


@pytest.fixture
def retained_ledger(tmp_path, monkeypatch):
    filesystem_id = "pytest-provenance-" + uuid.uuid4().hex
    prefix = "vector-upload-retention:" + filesystem_id
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", filesystem_id)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    kwargs = redis_connection_kwargs(RedisDB.LOCK, decode_responses=True)
    password_path = Path(os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password"))
    if password_path.exists():
        kwargs["password"] = password_path.read_text().strip()
    connection = redis.client.Redis(**kwargs)
    connection.ping()
    connection.hset(prefix + ":totals", mapping={"initialized": 1, "committed": 0, "reserved": 0, "inflight": 0})
    ledger = vectors.RedisRetentionLedger(connection)
    lease_factory = vectors.RedisScopeLeaseFactory(connection)

    def prepare(**kwargs):
        return vectors.prepare_vector_upload(**kwargs, ledger=ledger, scope_lease_factory=lease_factory)

    try:
        yield SimpleNamespace(connection=connection, prefix=prefix, prepare=prepare)
    finally:
        keys = list(connection.scan_iter(match=prefix + ":*"))
        if keys:
            connection.delete(*keys)
        connection.close()


def _assert_receipts_and_accounting(root, harness, accepted_source, rejected_source, caplog):
    paths = sorted(root.rglob("normalization.json"))
    assert len(paths) == 2
    receipts = [json.loads(path.read_text()) for path in paths]
    assert {receipt["status"] for receipt in receipts} == {"accepted", "rejected"}
    sources = {"accepted": accepted_source, "rejected": rejected_source}
    retained_bytes = 0
    forbidden_keys = {"session", "session_id", "cookie", "email", "roles", "claims", "client_ip", "authorization", "token"}

    def assert_minimal(value):
        if isinstance(value, dict):
            assert not forbidden_keys.intersection(value)
            for child in value.values():
                assert_minimal(child)
        elif isinstance(value, list):
            for child in value:
                assert_minimal(child)
        elif isinstance(value, str):
            assert not any(secret in value for secret in ("owner-session", "other-session", "owner@example.test", "other@example.test", "203.0.113.9"))

    for path, receipt in zip(paths, receipts):
        assert receipt["actor"] == {"kind": "human", "user_id": 77}
        original = next((path.parent / "original").iterdir())
        assert original.read_bytes() == sources[receipt["status"]]
        assert receipt["source_sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()
        assert receipt["source_size"] == len(original.read_bytes())
        # Sanitized names are required private-receipt metadata, not log fields.
        assert receipt["submitted_name"] in {"fields.geojson", "hostile.geojson"}
        assert_minimal(receipt)
        retained_bytes += sum(item.stat().st_size for item in path.parent.rglob("*") if item.is_file())
    events = [json.loads(record.getMessage().split(" ", 1)[1]) for record in caplog.records if record.getMessage().startswith("vector_upload_security_event_v1 ")]
    assert len(events) == 1
    assert events[0]["actor"] == {"kind": "human", "user_id": 77}
    assert events[0]["source_sha256"] == hashlib.sha256(rejected_source).hexdigest()
    assert_minimal(events[0])
    assert "fields.geojson" not in json.dumps(events)
    assert "hostile.geojson" not in json.dumps(events)
    principal_key = harness.prefix + ":principal:" + hashlib.sha256(b"human:77").hexdigest()
    totals = harness.connection.hgetall(harness.prefix + ":totals")
    principal = harness.connection.hgetall(principal_key)
    assert int(totals["committed"]) == retained_bytes
    assert int(principal["committed"]) == retained_bytes
    assert int(totals["reserved"]) == int(totals["inflight"]) == int(principal["reserved"]) == 0
    assert list(harness.connection.scan_iter(match=harness.prefix + ":principal:*")) == [principal_key]


@pytest.fixture
def signed_sessions(monkeypatch):
    from wepppy.microservices.rq_engine import feature_access
    secret = "vector-provenance-cookie-signing-secret"
    sessions = {
        "owner-session": pickle.dumps({"_user_id": "77", "email": "owner@example.test"}),
        "other-session": pickle.dumps({"_user_id": "88", "email": "other@example.test"}),
    }

    class SessionRedis:
        def get(self, key):
            return sessions.get(key.removeprefix("session:"))

        def exists(self, key):
            return int(key.removeprefix("session:") in sessions)

        def close(self):
            pass

    monkeypatch.setattr(session_routes, "redis", SimpleNamespace(Redis=lambda **kwargs: SessionRedis()))
    monkeypatch.setattr(session_routes, "_secret_key", lambda: secret)
    monkeypatch.setattr(session_routes, "_resolve_roles_for_user_id", lambda user_id: ["User"])
    monkeypatch.setattr(session_routes, "_session_user_authorized_for_run", lambda runid, user_id, roles: (runid, user_id) in {("demo", 77), ("other", 88)})
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: False)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda *args: None)
    monkeypatch.setattr(auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(auth, "_check_session_revocation", lambda sid: None)
    monkeypatch.setattr(auth, "_check_session_marker", lambda sid, runid: None)
    monkeypatch.setattr(auth, "_reject_fork_preparing_run", lambda runid: None)
    monkeypatch.setattr(feature_access, "require_workflow_access", lambda *args, **kwargs: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "vector-provenance-jwt-secret")
    auth_tokens.get_jwt_config.cache_clear()
    try:
        yield Signer(secret, salt="flask-session", key_derivation="hmac")
    finally:
        auth_tokens.get_jwt_config.cache_clear()


@pytest.mark.parametrize("workflow", ["ag_fields", "omni_run", "omni_dry_run", "batch_runner"])
def test_signed_session_receipt_and_real_principal_ledger(
    workflow, tmp_path, monkeypatch, retained_ledger, signed_sessions, caplog,
):
    from tests.microservices.test_rq_engine_ag_fields_routes import DummyAgFields
    from tests.microservices.test_rq_engine_upload_batch_runner_routes import DummyBatchRunner, DummyCollection

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(ag_fields_routes, "get_wd", lambda runid: str(root))
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: str(root))
    for module in (ag_fields_routes, omni_routes, upload_batch_runner_routes):
        monkeypatch.setattr(module, "prepare_vector_upload", retained_ledger.prepare)
        monkeypatch.setattr(module, "require_jwt", auth.require_jwt)

    # Entitlement lookup is a bounded account-store seam; extraction is from the
    # real verified session JWT and a nonmember is rejected before staging.
    def require_membership(claims, *args, **kwargs):
        if claims.get("user_id") != 77:
            raise auth.AuthError("Feature membership required", status_code=403)

    for module in (ag_fields_routes, omni_routes, upload_batch_runner_routes):
        monkeypatch.setattr(module, "require_feature_access", require_membership)
    agfields = DummyAgFields(root)
    monkeypatch.setattr(ag_fields_routes.AgFields, "getInstance", lambda wd: agfields)
    monkeypatch.setattr(ag_fields_routes, "_invalidate_ag_fields_preflight", lambda wd: None)
    batch = DummyBatchRunner(root)
    monkeypatch.setattr(upload_batch_runner_routes.BatchRunner, "getInstanceFromBatchName", lambda name: batch)
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(omni_routes.Ron, "getInstance", lambda wd: SimpleNamespace(config_get_str=lambda section, key, default=None: default))

    class Omni:
        def parse_inputs(self, payload):
            self.accepted_path = payload["omni_contrast_geojson_path"]

        def build_contrasts(self, *args, **kwargs):
            pass

        def build_contrasts_dry_run_report(self, *args, **kwargs):
            return {"contrast_count": 1}

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: Omni())
    monkeypatch.setattr(omni_routes.OmniContrastBuildService, "prevalidate_user_defined_geojson", lambda path: None)
    monkeypatch.setattr(ag_fields_routes, "RedisPrep", SimpleNamespace(tryGetInstance=lambda wd: None))
    monkeypatch.setattr(omni_routes, "RedisPrep", SimpleNamespace(getInstance=lambda wd: SimpleNamespace(remove_timestamp=lambda *args: None)))
    monkeypatch.setattr(omni_routes, "redis", SimpleNamespace(Redis=lambda **kwargs: retained_ledger.connection))
    monkeypatch.setattr(omni_routes, "enqueue_tracked_rq_job", lambda *args, **kwargs: SimpleNamespace(id="provenance-job"))
    monkeypatch.setattr(omni_routes, "Queue", lambda *args, **kwargs: None)
    endpoint, field, status = {
        "ag_fields": ("/api/runs/demo/cfg/agfields/boundaries", "field_boundaries", 200),
        "omni_run": ("/api/runs/demo/cfg/run-omni-contrasts", "omni_contrast_geojson", 202),
        "omni_dry_run": ("/api/runs/demo/cfg/run-omni-contrasts-dry-run", "omni_contrast_geojson", 200),
        "batch_runner": ("/api/batch/_/demo/upload-geojson", "geojson_file", 200),
    }[workflow]
    data = {"omni_contrast_selection_mode": "user_defined_areas", "omni_contrast_pairs": '[{"control_scenario":"uniform_low","contrast_scenario":"mulch"}]'} if workflow.startswith("omni") else {}
    accepted_source, rejected_source = _source(), _source(hostile=True)
    with TestClient(rq_engine.app) as client:
        denied = client.post(endpoint, files={field: ("fields.geojson", accepted_source)}, data=data)
        assert denied.status_code == 401
        for session_id in (None, "other-session"):
            cookies = {} if session_id is None else {"session": signed_sessions.sign(session_id.encode()).decode()}
            denied = client.post("/api/runs/demo/cfg/session-token", cookies=cookies, headers={"Origin": "http://testserver"})
            assert denied.status_code == 401
        other_token_response = client.post(
            "/api/runs/other/cfg/session-token",
            cookies={"session": signed_sessions.sign(b"other-session").decode()},
            headers={"Origin": "http://testserver"},
        )
        assert other_token_response.status_code == 200
        denied = client.post(
            endpoint,
            headers={"Authorization": "Bearer " + other_token_response.json()["token"]},
            files={field: ("fields.geojson", accepted_source)},
            data=data,
        )
        assert denied.status_code == 403
        assert not list(root.rglob("normalization.json"))
        token_response = client.post("/api/runs/demo/cfg/session-token", cookies={"session": signed_sessions.sign(b"owner-session").decode()}, headers={"Origin": "http://testserver"})
        assert token_response.status_code == 200, token_response.text
        headers = {"Authorization": "Bearer " + token_response.json()["token"], "X-Forwarded-For": "203.0.113.9"}
        response = client.post(endpoint, headers=headers, files={field: ("fields.geojson", accepted_source)}, data=data)
        assert response.status_code == status, response.text
        with caplog.at_level("WARNING", logger="wepppy.microservices.vector_upload_normalization"):
            response = client.post(endpoint, headers=headers, files={field: ("hostile.geojson", rejected_source)}, data=data)
        assert response.status_code == 400, response.text
    _assert_receipts_and_accounting(root, retained_ledger, accepted_source, rejected_source, caplog)


def test_roads_signed_flask_session_receipt_and_real_principal_ledger(
    tmp_path, monkeypatch, retained_ledger, caplog,
):
    import wepppy.weppcloud.app as webapp
    import wepppy.weppcloud.routes.nodb_api.roads_bp as roads
    from wepppy.weppcloud.utils import helpers
    from wepppy.weppcloud.routes import _common
    from werkzeug.exceptions import Forbidden
    from wepppy.rq import submission_recovery
    from wepppy.nodb.core import Ron
    from tests.weppcloud.routes.test_roads_bp import RoadsStub

    root = tmp_path / "project"
    root.mkdir()
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="roads-session-signing-secret")
    manager = LoginManager(app)

    class User(UserMixin):
        def __init__(self, user_id):
            self.id = user_id

        def has_role(self, role):
            return False

    owner, other = User(77), User(88)
    users = {"77": owner, "88": other}
    manager.user_loader(users.get)
    app.register_blueprint(roads.roads_bp)
    app.register_error_handler(Forbidden, lambda error: ("forbidden", 403))
    monkeypatch.setattr(_common, "get_wd", lambda runid: str(root))
    monkeypatch.setattr(webapp, "get_run_owners", lambda runid: [owner])
    monkeypatch.setattr(helpers, "get_wd", lambda runid, **kwargs: str(root))
    monkeypatch.setattr(roads, "get_wd", lambda runid, **kwargs: str(root))
    monkeypatch.setattr(roads, "load_run_context", lambda runid, config: SimpleNamespace(active_root=root))
    monkeypatch.setattr(roads, "prepare_vector_upload", retained_ledger.prepare)
    monkeypatch.setattr(roads, "_invalidate_roads_timestamp", lambda wd: None)
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path / "lifecycle"))
    monkeypatch.setattr(helpers, "redis", SimpleNamespace(Redis=lambda **kwargs: retained_ledger.connection))
    controller = RoadsStub(str(root), "cfg")
    controller.set_enabled(True)
    monkeypatch.setattr(roads, "Roads", RoadsStub)
    monkeypatch.setattr(roads, "_sync_roads_enabled_state", lambda wd, cfg: controller)
    monkeypatch.setattr(Ron, "ispublic", lambda wd: False)
    endpoint = "/runs/demo/cfg/tasks/roads/upload_geojson"
    accepted_source, rejected_source = _source(line=True), _source(hostile=True)
    with app.test_client() as client:
        for user_id in (None, "88"):
            with client.session_transaction() as session:
                session.clear()
                if user_id:
                    session["_user_id"] = user_id
                    session["_fresh"] = True
            response = client.post(endpoint, data={"file": (io.BytesIO(accepted_source), "fields.geojson")})
            assert response.status_code == 403
        assert not list(root.rglob("normalization.json"))
        with client.session_transaction() as session:
            session["_user_id"] = "77"
            session["_fresh"] = True
            session["email"] = "owner@example.test"
        response = client.post(endpoint, data={"file": (io.BytesIO(accepted_source), "fields.geojson")})
        assert response.status_code == 200, response.get_json()
        with caplog.at_level("WARNING", logger="wepppy.microservices.vector_upload_normalization"):
            response = client.post(endpoint, data={"file": (io.BytesIO(rejected_source), "hostile.geojson")}, headers={"X-Forwarded-For": "203.0.113.9"})
        assert response.status_code == 400, response.get_json()
    _assert_receipts_and_accounting(root, retained_ledger, accepted_source, rejected_source, caplog)
