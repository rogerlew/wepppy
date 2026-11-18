"""Run existing browser suites against a disposable, authenticated CI application.

Only the isolated test Compose runtime may invoke this fixture. Credentials stay
in process memory; the app and browser share loopback and never expose a host port.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import secrets
import socket
import time
from contextlib import contextmanager
import subprocess
import threading
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "wepppy/weppcloud/static-src"


def validate_reports(report: Path, axe_report: Path, suite: str) -> None:
    """Reject successful exits that skipped the intended browser coverage."""
    if json.loads(report.read_text())["stats"]["expected"] < 1:
        raise RuntimeError("Browser suite produced no passing checks")
    if suite == "accessibility":
        expected_pages = {
            "ui-components-theme-lab", "ui-components-report-a11y",
            "weppcloud-root", "weppcloud-interfaces", "weppcloud-profile",
            "weppcloud-config-builder", "runs0-dashboard",
        }
        pages = {scan["pageId"] for scan in json.loads(axe_report.read_text())["scans"]}
        if not expected_pages <= pages:
            raise RuntimeError(f"Accessibility checks skipped required pages: {sorted(expected_pages - pages)}")


def prepare_controller_session(base_url: str, scratch: Path) -> Path:
    """Use the real CAPTCHA and password login, retaining cookies only in container temporary storage."""
    import requests

    cap_secret = scratch / "cap-secret"
    cap_secret.write_text(os.environ["CAP_SECRET"])
    cap_secret.chmod(0o600)
    env = dict(os.environ, CAP_SECRET_FILE=str(cap_secret), CAP_PORT=str(urlparse(base_url).port))
    issued = subprocess.run(
        ["node", str(ROOT / "services/cap/canary.js"), "mint"],
        env=env, capture_output=True, text=True, check=False,
    )
    if issued.returncode or not issued.stdout.strip():
        raise RuntimeError("CI CAPTCHA challenge redemption failed")
    with requests.Session() as client:
        response = client.get(base_url + "/login", headers={"Accept": "application/json"}, timeout=30)
        response.raise_for_status()
        csrf = response.json()["response"]["csrf_token"]
        # Chromium permits Secure cookies on loopback; requests needs explicit
        # local transport handling. Server-issued cookie policy is not changed.
        for cookie in client.cookies:
            cookie.secure = False
        response = client.post(base_url + "/login", json={
            "email": os.environ["SMOKE_AGENT_EMAIL"],
            "password": os.environ["SMOKE_AGENT_PASSWORD"],
            "csrf_token": csrf, "cap_token": issued.stdout.strip(), "remember": True,
        }, headers={"Accept": "application/json", "X-CSRFToken": csrf}, timeout=30)
        if response.status_code != 200:
            body = response.json()
            payload = body.get("response") or body.get("error") or {}
            details = payload.get("errors") or payload.get("field_errors") or list(payload)
            raise RuntimeError(f"CI password login failed with HTTP {response.status_code}: {details}")
        primary = client.cookies.get("__Host-weppcloud_session")
        if not primary:
            raise RuntimeError("CI password login did not issue the primary cookie")
        cookies = [{"name": c.name, "value": c.value, "domain": c.domain,
                    "path": c.path, "expires": c.expires or -1,
                    "httpOnly": True, "secure": True, "sameSite": "Lax"}
                   for c in client.cookies if c.name in {"__Host-weppcloud_session", "remember_token"}]
    state = scratch / "storage.json"
    state.write_text(json.dumps({"cookies": cookies, "origins": []}))
    state.chmod(0o600)
    return state


@contextmanager
def rq_api():
    """Serve the existing authenticated RQ API on a private loopback socket."""
    import uvicorn
    from wepppy.microservices.rq_engine import app

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = time.monotonic() + 30
            while not server.started:
                if not worker.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError("Isolated RQ API failed startup")
                time.sleep(0.05)
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            worker.join(timeout=15)
            if worker.is_alive():
                raise RuntimeError("Isolated RQ API failed shutdown")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("controllers", "theme-metrics", "accessibility"))
    args = parser.parse_args()
    if (os.environ.get("WEPPCLOUD_DEPLOYMENT_PROFILE") != "test"
            or os.environ.get("POSTGRES_HOST") != "postgres"
            or not Path("/opt/wepppy-ci/node_modules").is_dir()):
        raise RuntimeError("Browser fixture requires the isolated CI test runtime")

    os.environ["WEPP_AUTH_JWT_SECRETS"] = secrets.token_urlsafe(48)
    os.environ["AGENT_JWT_SECRET"] = secrets.token_urlsafe(48)
    os.environ["SMOKE_AGENT_EMAIL"] = "ci-browser@example.com"
    os.environ["SMOKE_AGENT_PASSWORD"] = secrets.token_urlsafe(32)
    os.environ["SMOKE_AGENT_REQUIRED"] = "true"
    os.environ["SMOKE_SITE_PREFIX"] = "/weppcloud"
    os.environ["SMOKE_RUN_CONFIG"] = "disturbed9002_wbt"
    os.environ["SESSION_COOKIE_NAME"] = "__Host-weppcloud_session"
    os.environ["SESSION_COOKIE_PRIMARY_NAME"] = "__Host-weppcloud_session"
    os.environ["SESSION_COOKIE_LEGACY_NAME"] = "session"
    os.environ["SESSION_COOKIE_MIGRATION_ENABLED"] = "true"
    os.environ["SMOKE_CREATE_RUN"] = "true"
    os.environ["PLAYWRIGHT_HTML_OPEN"] = "never"
    from prepare_ci_runtime import main as prepare_runtime
    prepare_runtime()
    modules = STATIC / "node_modules"

    subprocess.run(["bash", str(STATIC / "build-static-assets.sh"),
                    "--prod", "--skip-controllers"], cwd=ROOT, check=True)

    from bootstrap_ci_database import main as initialize_database
    initialize_database()  # Refuses to touch any database that already has tables.
    from flask_security.utils import hash_password
    from wepppy.weppcloud.app import app, db, Role, user_datastore
    from wepppy.weppcloud.utils.auth_tokens import issue_token
    from werkzeug.serving import make_server
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.exceptions import NotFound
    from werkzeug.middleware.http_proxy import ProxyMiddleware

    with app.app_context():
        user = user_datastore.create_user(
            email=os.environ["SMOKE_AGENT_EMAIL"],
            password=hash_password(os.environ["SMOKE_AGENT_PASSWORD"]),
            active=True, confirmed_at=datetime.now(timezone.utc),
        )
        for name in ("User", "Admin", "Root", "PowerUser"):
            role = Role.query.filter_by(name=name).first()
            if role is None:
                role = Role(name=name, description="Disposable CI browser fixture")
                db.session.add(role)
            user.roles.append(role)
        db.session.commit()
    os.environ["SMOKE_TEST_SUPPORT_TOKEN"] = issue_token(
        "ci-browser", audience="weppcloud-test-support",
        scopes=["test:support"], expires_in=3600,
    )["token"]
    report = STATIC / "test-results/ci-browser-result.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    axe_report = STATIC / "test-results/a11y/axe-violations.json"
    axe_report.unlink(missing_ok=True)
    os.environ["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(report)
    with rq_api() as rq_url:
        server = make_server("127.0.0.1", 0, ProxyMiddleware(
            DispatcherMiddleware(NotFound(), {"/weppcloud": app}),
            {"/cap/": {"target": "http://cap:3000", "remove_prefix": False},
             "/rq-engine/": {"target": rq_url, "remove_prefix": True, "host": None}},
        ), threaded=True)
        os.environ["SMOKE_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/weppcloud"
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        scratch = tempfile.TemporaryDirectory(prefix="ci-browser-")
        try:
            if args.suite == "controllers":
                os.environ["SMOKE_STORAGE_STATE"] = str(prepare_controller_session(
                    os.environ["SMOKE_BASE_URL"], Path(scratch.name)))
            if args.suite == "accessibility":
                subprocess.run([
                    "/opt/venv/bin/python", "-m", "pytest",
                    "tests/weppcloud/routes/test_pure_controls_render.py::test_report_templates_use_semantic_copy_buttons",
                    "tests/weppcloud/routes/test_pure_controls_render.py::test_map_templates_do_not_use_application_role_for_canvas",
                    "tests/weppcloud/routes/test_pure_controls_render.py::test_placeholder_only_controls_have_explicit_accessible_names",
                    "tests/weppcloud/routes/test_pure_controls_render.py::test_standalone_templates_include_lang_and_iframe_titles",
                    "tests/weppcloud/routes/test_user_runs_admin_scope.py::test_runs2_template_requests_catalog_with_ron_meta",
                    "--maxfail=1",
                ], cwd=ROOT, check=True)
                subprocess.run(["node", "--experimental-vm-modules",
                                str(modules / "jest/bin/jest.js"),
                                "--config=jest.config.mjs", "copytext", "map_gl"],
                               cwd=STATIC, check=True)
            pattern = {
                "controllers": "controller regression",
                "theme-metrics": "theme contrast metrics",
                "accessibility": "axe accessibility|theme contrast metrics",
            }[args.suite]
            result = subprocess.run([
                "node", str(modules / "playwright/cli.js"), "test",
                "--config=playwright.config.mjs", "--workers=1", "--grep", pattern,
                "--reporter=list,json,html",
            ], cwd=STATIC, check=False)
            if result.returncode:
                return result.returncode
            validate_reports(report, axe_report, args.suite)
            return 0
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=10)
            scratch.cleanup()



if __name__ == "__main__":
    raise SystemExit(main())
