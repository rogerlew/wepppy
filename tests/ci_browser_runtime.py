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
import subprocess
import threading

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
    os.environ["SMOKE_AGENT_EMAIL"] = "ci-browser@example.invalid"
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
    modules = STATIC / "node_modules"
    if not modules.exists():
        modules.symlink_to("/opt/wepppy-ci/node_modules", target_is_directory=True)

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
    server = make_server("127.0.0.1", 0, DispatcherMiddleware(NotFound(), {"/weppcloud": app}), threaded=True)
    os.environ["SMOKE_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/weppcloud"
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
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


if __name__ == "__main__":
    raise SystemExit(main())
