import pytest
from flask import Flask


@pytest.mark.unit
def test_logged_blueprint_logs_route_exception(tmp_path, monkeypatch):
    # Ensure get_wd resolves to the per-run temp path
    monkeypatch.setattr(
        "wepppy.weppcloud.routes._common.get_wd",
        lambda runid: str(tmp_path / runid),
    )

    from wepppy.weppcloud.routes import _common

    app = Flask(__name__)
    app.testing = True

    bp = _common.Blueprint("test_bp", __name__)

    @bp.route("/runs/<runid>/explode")
    def explode(runid: str):
        raise RuntimeError(f"explode: {runid}")

    app.register_blueprint(bp)

    with pytest.raises(RuntimeError):
        app.test_client().get("/runs/sample-run/explode")

    log_path = tmp_path / "sample-run" / "exceptions.log"
    assert log_path.exists()
    data = log_path.read_text()
    assert "sample-run" in data
    assert "RuntimeError" in data
