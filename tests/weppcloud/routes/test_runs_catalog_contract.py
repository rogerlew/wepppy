from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Blueprint, Flask, jsonify
from flask_wtf.csrf import CSRFError, CSRFProtect
from jinja2 import DictLoader

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_TEMPLATE = (
    REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "user" / "runs2.html"
)


@pytest.fixture()
def runs_renderer() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "runs-render-secret"
    app.jinja_loader = DictLoader(
        {
            "base_pure.htm": (
                "<meta name=\"csrf-token\" content=\"csrf-value\">"
                "{% block body %}{% endblock %}"
                "{% block script_extras %}{% endblock %}"
            ),
            "user/runs2.html": RUNS_TEMPLATE.read_text(encoding="utf-8"),
        }
    )
    user = Blueprint("user", __name__)
    usersum = Blueprint("usersum", __name__)

    @user.get("/runs", endpoint="runs")
    def runs():
        return ""

    @user.get("/profile", endpoint="profile")
    def profile():
        return ""

    @user.get("/runs/catalog", endpoint="runs_catalog")
    def runs_catalog():
        return ""

    @user.get("/runs/map-data", endpoint="runs_map_data")
    def runs_map_data():
        return ""

    @user.get("/runs/users", endpoint="runs_users")
    def runs_users():
        return ""

    @usersum.get("/docs/<doc_id>", endpoint="view_doc")
    def view_doc(doc_id: str):
        return doc_id

    app.register_blueprint(user)
    app.register_blueprint(usersum)
    app.jinja_env.globals["static_url"] = lambda path: f"/static/{path}"
    return app


def _render(app: Flask, *, admin: bool, sort="last_modified", direction="desc", owner=False, per_page=25) -> str:
    with app.test_request_context("/runs"):
        return app.jinja_env.get_template("user/runs2.html").render(
            user=SimpleNamespace(),
            current_user=SimpleNamespace(
                is_authenticated=True, has_role=lambda role: admin and role == "Admin"
            ),
            show_owner=owner,
            sort=sort,
            direction=direction,
            per_page=per_page,
            is_admin_runs_viewer=admin,
            selected_alias="",
            current_user_alias="7",
            site_prefix="/weppcloud",
        )


def test_runs_page_renders_canonical_ordinary_contract(runs_renderer: Flask) -> None:
    rendered = _render(runs_renderer, admin=False)

    assert 'id="runs_search_input"' in rendered
    assert 'id="runs-tab-table"' in rendered
    assert 'id="runs-tab-map"' in rendered
    assert 'id="delete_runs_button"' in rendered
    assert 'id="runs-map-canvas"' in rendered
    assert 'const runsCatalogUrl = "/runs/catalog";' in rendered
    assert 'const runsMapDataUrl = "/runs/map-data";' in rendered
    assert 'const runsUsersUrl = "/runs/users";' in rendered
    assert "const isAdminRunsViewer = false;" in rendered
    assert 'id="runs_admin_user_search"' not in rendered
    assert "Loading runs..." in rendered


def test_runs_page_renders_admin_scope_and_safe_output_primitives(
    runs_renderer: Flask,
) -> None:
    rendered = _render(runs_renderer, admin=True)

    assert 'id="runs_admin_user_search"' in rendered
    assert 'id="runs_admin_user_suggestions"' in rendered
    assert 'id="runs_admin_apply_scope"' in rendered
    assert 'id="runs_admin_reset_scope"' in rendered
    assert "const isAdminRunsViewer = true;" in rendered
    assert "cell.textContent = text;" in rendered
    assert "option.textContent = userLabel(user);" in rendered
    assert "runsMapStatus.textContent = message;" in rendered
    assert "checkbox.disabled = !!run.readonly;" in rendered


def test_delete_route_rejects_missing_csrf_before_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_module = __import__(
        "wepppy.weppcloud.routes.nodb_api.project_bp",
        fromlist=["project_bp"],
    )
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="runs-delete-csrf")
    monkeypatch.setattr(
        project_module,
        "current_user",
        SimpleNamespace(is_authenticated=True, get_id=lambda: "7"),
    )
    # This CSRF unit test assumes a valid run; context loading has separate coverage.
    monkeypatch.setattr(project_module, "load_run_context", lambda *_args, **_kwargs: None)
    app.register_blueprint(project_module.project_bp)
    CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify({"error": {"message": error.description}}), 400

    response = app.test_client().post("/runs/run-1/cfg/tasks/delete/")
    assert response.status_code == 400


def test_runs_expiration_sort_and_bulk_protection_controls(runs_renderer):
    rendered = _render(runs_renderer, admin=False)
    assert 'aria-label="Sort Automatic deletion ascending"' in rendered
    assert 'sort=ttl_deletion_at' in rendered
    assert 'id="disable_ttl_runs_button"' in rendered
    assert 'Disable Automated Deletion for Selected' in rendered
    assert rendered.index('id="delete_runs_button"') < rendered.index('id="disable_ttl_runs_button"') < rendered.index('id="runs_table"')


def test_runs_help_is_once_above_table(runs_renderer):
    rendered = _render(runs_renderer, admin=False)
    assert rendered.count("How to keep your project") == 1
    assert rendered.index("How to keep your project") < rendered.index('id="runs_search_input"')
    assert 'ttlHelpLink' not in rendered
    assert '<colgroup>' in rendered


@pytest.mark.parametrize("owner", [False, True])
def test_runs_sort_navigation_and_fixed_layout_in_chromium(runs_renderer, owner):
    import os
    import subprocess
    import threading
    from flask import request, send_file
    from werkzeug.serving import make_server
    from wepppy.weppcloud.routes.user import _normalize_sort_param, _normalize_direction, _sort_metas

    app = runs_renderer
    rows = [
        {"runid": "disabled", "ttl_disabled": True, "ttl_deletion_at": None},
        {"runid": "unknown", "ttl_disabled": None, "ttl_deletion_at": None},
        {"runid": "late", "ttl_disabled": False, "ttl_deletion_at": "2027-01-01T00:00:00Z"},
        {"runid": "early", "ttl_disabled": False, "ttl_deletion_at": "2026-11-01T00:00:00Z"},
    ]
    for index, row in enumerate(rows):
        row.update(name="Project " + row["runid"] + " description " * (index + 1) * 5,
                   scenario="long_" + "x" * (index + 1) * 80, config="cfg", owner="owner@example.test",
                   date_created=f"2025-01-0{index + 1}T00:00:00Z")

    def page():
        return _render(app, admin=False, owner=owner,
                       sort=_normalize_sort_param(request.args.get("sort")),
                       direction=_normalize_direction(request.args.get("direction")),
                       per_page=request.args.get("per_page", 25, type=int))

    def catalog():
        return jsonify(runs=_sort_metas(rows, _normalize_sort_param(request.args.get("sort")),
                                       _normalize_direction(request.args.get("direction")) == "desc"))

    app.view_functions["user.runs"] = page
    app.view_functions["user.runs_catalog"] = catalog
    static_root = REPO_ROOT / "wepppy/weppcloud/static"
    app.add_url_rule("/test-pure.css", endpoint="test_pure_css", view_func=lambda: send_file(static_root / "vendor/purecss/pure-min.css"))
    app.add_url_rule("/test-ui.css", endpoint="test_ui_css", view_func=lambda: send_file(static_root / "css/ui-foundation.css"))
    app.jinja_loader.mapping["base_pure.htm"] += '<link rel="stylesheet" href="/test-pure.css"><link rel="stylesheet" href="/test-ui.css">'
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    static_source = REPO_ROOT / "wepppy/weppcloud/static-src"
    environment = dict(os.environ)
    environment.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(static_source / ".playwright-browsers"))
    try:
        result = subprocess.run(["node", str(Path(__file__).with_name("runs_table_browser.cjs")),
                                 f"http://127.0.0.1:{server.server_port}"], cwd=static_source,
                                env=environment, capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, result.stderr
        assert "Runs table Chromium: PASS" in result.stdout
    finally:
        server.shutdown()
        thread.join(timeout=5)
