from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Flask, g

from wepppy.weppcloud.utils import helpers


pytestmark = pytest.mark.unit


def _make_app(*, site_prefix: str = "/weppcloud") -> Flask:
    app = Flask(__name__)
    app.config["SITE_PREFIX"] = site_prefix

    @app.get("/runs/<string:runid>/<config>/", endpoint="run_0.runs0")
    def _runs0(runid: str, config: str) -> str:
        return ""

    return app


def test_url_for_run_rewrites_omni_pup_to_composite_runid() -> None:
    app = _make_app()

    with app.test_request_context("/"):
        g.pup_relpath = "omni/scenarios/treated"
        url = helpers.url_for_run("run_0.runs0", runid="decimal-pleasing", config="cfg")

    assert url == "/weppcloud/runs/decimal-pleasing;;omni;;treated/cfg/"
    assert "pup=" not in url


def test_url_for_run_rewrites_omni_contrast_pup_to_composite_runid() -> None:
    app = _make_app()

    with app.test_request_context("/"):
        g.pup_relpath = "omni/contrasts/3"
        url = helpers.url_for_run("run_0.runs0", runid="decimal-pleasing", config="cfg")

    assert url == "/weppcloud/runs/decimal-pleasing;;omni-contrast;;3/cfg/"
    assert "pup=" not in url


def test_url_for_run_rewrites_omni_pup_for_browse_paths() -> None:
    app = _make_app()

    with app.test_request_context("/"):
        g.pup_relpath = "omni/scenarios/treated"
        url = helpers.url_for_run("browse.browse_tree", runid="decimal-pleasing", config="cfg")

    assert url == "/weppcloud/runs/decimal-pleasing;;omni;;treated/cfg/browse/"


def test_url_for_run_preserves_non_omni_pup_query_param() -> None:
    app = _make_app()

    with app.test_request_context("/"):
        g.pup_relpath = "some/pup"
        url = helpers.url_for_run("run_0.runs0", runid="decimal-pleasing", config="cfg")

    assert url.startswith("/weppcloud/runs/decimal-pleasing/cfg/")
    assert "pup=" in url
