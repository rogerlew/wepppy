from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

flask = pytest.importorskip("flask")
Flask = flask.Flask
Forbidden = pytest.importorskip("werkzeug.exceptions").Forbidden

import wepppy.weppcloud.routes.diff.diff as diff_module
import wepppy.weppcloud.utils.helpers as helpers

pytestmark = pytest.mark.routes


@pytest.fixture()
def diff_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    left_root = tmp_path / "left"
    right_root = tmp_path / "right"
    left_root.mkdir()
    right_root.mkdir()

    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)
    monkeypatch.setattr(
        diff_module,
        "load_run_context",
        lambda runid, config: SimpleNamespace(active_root=left_root),
    )
    monkeypatch.setattr(diff_module, "get_wd", lambda runid: str(right_root))
    monkeypatch.setattr(
        diff_module,
        "url_for_run",
        lambda endpoint, **kwargs: f"/mock/{kwargs['runid']}/{kwargs['subpath']}",
    )
    monkeypatch.setattr(
        diff_module,
        "render_template",
        lambda template_name, **ctx: diff_module.jsonify(ctx),
    )

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.register_blueprint(diff_module.diff_bp)

    with app.test_client() as client:
        yield client, left_root, right_root


def test_diff_comparer_uses_directory_runtime_paths(diff_client) -> None:
    client, left_root, right_root = diff_client
    rel = "watershed/hillslopes/h001.slp"

    left_file = left_root / rel
    right_file = right_root / rel
    left_file.parent.mkdir(parents=True, exist_ok=True)
    right_file.parent.mkdir(parents=True, exist_ok=True)
    left_file.write_text("left", encoding="utf-8")
    right_file.write_text("right", encoding="utf-8")

    response = client.get(f"/runs/run-left/cfg/diff/{rel}?diff=run-right")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["subpath"] == rel
    assert payload["left_download_url"].endswith(f"/run-left/{rel}")
    assert payload["right_download_url"].endswith(f"/run-right/{rel}")


def test_diff_comparer_rejects_archive_boundary_alias_syntax(diff_client) -> None:
    client, _left_root, _right_root = diff_client

    with pytest.raises(Forbidden):
        client.get("/runs/run-left/cfg/diff/watershed.nodir/hillslopes/h001.slp?diff=run-right")


def test_diff_comparer_maps_left_archive_only_root_to_nodir_error(diff_client) -> None:
    client, left_root, right_root = diff_client
    rel = "watershed/hillslopes/h001.slp"

    (left_root / "watershed.nodir").write_bytes(b"archive")
    right_file = right_root / rel
    right_file.parent.mkdir(parents=True, exist_ok=True)
    right_file.write_text("right", encoding="utf-8")

    response = client.get(f"/runs/run-left/cfg/diff/{rel}?diff=run-right")

    assert response.status_code == 409
    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["code"] == "NODIR_ARCHIVE_RETIRED"


def test_diff_comparer_maps_right_archive_only_root_to_nodir_error(diff_client) -> None:
    client, left_root, right_root = diff_client
    rel = "watershed/hillslopes/h001.slp"

    left_file = left_root / rel
    left_file.parent.mkdir(parents=True, exist_ok=True)
    left_file.write_text("left", encoding="utf-8")
    (right_root / "watershed.nodir").write_bytes(b"archive")

    response = client.get(f"/runs/run-left/cfg/diff/{rel}?diff=run-right")

    assert response.status_code == 409
    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["code"] == "NODIR_ARCHIVE_RETIRED"
