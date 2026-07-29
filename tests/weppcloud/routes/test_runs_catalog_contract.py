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


def _render(app: Flask, *, admin: bool) -> str:
    with app.test_request_context("/runs"):
        return app.jinja_env.get_template("user/runs2.html").render(
            user=SimpleNamespace(),
            show_owner=False,
            sort="last_modified",
            direction="desc",
            per_page=25,
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
    app.register_blueprint(project_module.project_bp)
    CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify({"error": {"message": error.description}}), 400

    response = app.test_client().post("/runs/run-1/cfg/tasks/delete/")
    assert response.status_code == 400
