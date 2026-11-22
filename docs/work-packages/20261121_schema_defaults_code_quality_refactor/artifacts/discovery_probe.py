"""Capture HTTP discovery bodies and their published OpenAPI operations.

Run this probe with pytest from both comparison checkouts. The digest preserves
JSON object and array order as well as statuses, URLs and entity tags.
"""
from dataclasses import replace
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.microservices import test_rq_engine_schema_defaults_routes as fixtures
from wepppy.microservices.rq_engine import app, responses as error_responses, schema_defaults_routes as routes
from wepppy.nodb.redis_prep import RedisPrep


def scenarios():
    binaries = ("wepp_260803", "wepp_dcc52a6")
    graph = fixtures.build_continental_us_capability_graph(
        binaries, fixtures._binary_revisions(binaries),
        wepp_binary_capabilities={"wepp_260803": ("mofe_supported",)},
    )
    europe = fixtures.build_locale_capability_graph(
        "europe", binaries[:1], fixtures._binary_revisions(binaries[:1]),
    )
    yield "legacy", fixtures._sample_runtime(
        active_mods=("wepp",), disturbed_enabled=False, sbs_upload_supported=False,
    )
    yield "stored_conus_disturbed", fixtures._sample_runtime(capability_graph=graph)
    yield "v1_europe_baer", replace(
        fixtures._sample_runtime(active_mods=("baer", "wepp"), capability_graph=europe),
        model_capability_graph=None, projected_domains=frozenset({"climate", "landuse"}),
        v1_capabilities={"soil_builders": ("gridded",), "wepp_binaries": binaries[:1]},
    )


def test_capture_discovery(monkeypatch, tmp_path):
    fixtures._stub_auth(monkeypatch, "rq:read")
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "disposable-test-secret")
    monkeypatch.setattr(routes, "_utc_timestamp", lambda: "2026-11-21T00:00:00Z")
    # Supply an absent run directory and empty job index to the external readers.
    # These two functions own WD lookups in both the baseline and the split.
    monkeypatch.setattr(error_responses, "new_error_id", lambda: "ad" * 16)
    for name, module in sys.modules.copy().items():
        if name.startswith("wepppy.microservices.rq_engine.schema_defaults") and hasattr(module, "get_wd"):
            monkeypatch.setattr(module, "get_wd", lambda runid: str(tmp_path / "absent"))
    prep = SimpleNamespace(get_rq_job_id=lambda key: None, get_rq_job_ids=lambda: {})
    monkeypatch.setattr(RedisPrep, "getInstance", lambda wd: prep)

    report = {}
    with TestClient(app) as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        route_paths = ["/api" + route.path for route in routes.router.routes]
        paths = schema.json()["paths"]
        wire = json.dumps({path: paths[path] for path in route_paths}, separators=(",", ":"))
        report["openapi"] = {"paths": len(route_paths), "sha256": hashlib.sha256(wire.encode()).hexdigest()}
        assert len(route_paths) == 10
        for label, runtime in scenarios():
            base = f"/api/runs/{runtime.runid}/{runtime.config}"
            monkeypatch.setattr(routes, "_load_runtime_state", lambda runid, config: runtime)
            responses = {}

            def get(suffix, expected=200):
                reply = client.get(base + suffix)
                assert reply.status_code == expected, (label, suffix, reply.text)
                payload = reply.json()
                responses[suffix] = [
                    reply.status_code, reply.headers.get("etag"), hashlib.sha256(reply.content).hexdigest()
                ]
                return payload

            get("/geospatial-metadata")
            get("/outputs")
            controllers = get("/controllers")["controllers"]
            for controller in controllers:
                for kind in ("schema", "hints", "templates"):
                    get(f"/controllers/{controller['name']}/{kind}")
            operations = get("/endpoints")["operations"]
            get("/endpoints?include_operation_docs=true")
            for operation in operations:
                for kind in ("schema", "defaults", "errors"):
                    get(f"/endpoints/{operation['operation_id']}/{kind}")
            get("/controllers/unknown/schema", 404)
            get("/endpoints/unknown/defaults", 404)
            operation_ids = {op["operation_id"] for op in operations}
            gated = sorted(operation_ids & {"rq_engine_build_rusle", "rq_engine_upload_sbs"})
            assert bool(gated) == (label != "legacy")
            manifest = Path(f".wctl-test-runs/discovery-parity-{label}.json")
            manifest.write_text(json.dumps(responses, indent=2) + "\n")
            wire = json.dumps(responses, sort_keys=True, separators=(",", ":")).encode()
            report[label] = {
                "operations": len(operations), "controllers": len(controllers),
                "gated_operations": gated, "http_responses": len(responses),
                "sha256": hashlib.sha256(wire).hexdigest(),
            }
    Path(".wctl-test-runs/discovery-parity.json").write_text(json.dumps(report, indent=2) + "\n")
