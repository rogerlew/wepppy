from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")

from wepppy.weppcloud._jinja_filters import register_jinja_filters


pytestmark = pytest.mark.unit


def test_usersum_doc_link_helper_renders_prefixed_anchor() -> None:
    app = flask.Flask(__name__)
    app.config["TESTING"] = True

    usersum_bp = flask.Blueprint("usersum", __name__)

    @usersum_bp.route("/usersum/view/<category>/<path:filename>", endpoint="view_markdown")
    def _view_markdown(category: str, filename: str):
        return f"{category}:{filename}"

    app.register_blueprint(usersum_bp)
    register_jinja_filters(app)

    with app.test_request_context("/"):
        rendered = flask.render_template_string(
            "{{ usersum_doc_link('weppcloud', 'disturbed-land-soil-lookup.md', 'WEPPcloud Calibration') }}"
        )

    assert '<a class="wc-link wc-link--file"' in rendered
    assert 'href="/usersum/view/weppcloud/disturbed-land-soil-lookup.md"' in rendered
    assert 'target="_blank"' in rendered
    assert 'rel="noopener"' in rendered
    assert "data-open-tab-pref" in rendered
    assert "📄 WEPPcloud Calibration" in rendered
