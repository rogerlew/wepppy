from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

flask = pytest.importorskip("flask")
Flask = flask.Flask

import wepppy.weppcloud.routes.diff.diff as diff_module
import wepppy.weppcloud.utils.helpers as helpers

pytestmark = pytest.mark.microservice


def _write_nodir_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


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
    app.register_blueprint(diff_module.diff_bp)

    with app.test_client() as client:
        yield client, left_root, right_root


def test_diff_archive_path_supported_without_filesystem_directory(diff_client) -> None:
    client, left_root, right_root = diff_client

    _write_nodir_zip(left_root / "watershed.nodir", {"hillslopes/h001.slp": "left"})
    _write_nodir_zip(right_root / "watershed.nodir", {"hillslopes/h001.slp": "right"})

    response = client.get(
        "/runs/run-left/cfg/diff/watershed.nodir/hillslopes/h001.slp?diff=run-right"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["subpath"] == "watershed/hillslopes/h001.slp"
    assert payload["left_download_url"].endswith("/run-left/watershed/hillslopes/h001.slp")
    assert payload["right_download_url"].endswith("/run-right/watershed/hillslopes/h001.slp")


@pytest.mark.parametrize(
    ("state", "expected_status", "expected_code"),
    [
        ("mixed", 409, "NODIR_MIXED_STATE"),
        ("invalid", 500, "NODIR_INVALID_ARCHIVE"),
        ("locked", 503, "NODIR_LOCKED"),
    ],
)
def test_diff_nodir_state_errors_propagate_from_left_run(
    diff_client,
    state: str,
    expected_status: int,
    expected_code: str,
) -> None:
    client, left_root, right_root = diff_client

    _write_nodir_zip(right_root / "watershed.nodir", {"hillslopes/h001.slp": "right"})

    if state == "mixed":
        (left_root / "watershed").mkdir()
        _write_nodir_zip(left_root / "watershed.nodir", {"hillslopes/h001.slp": "left"})
    elif state == "invalid":
        (left_root / "watershed.nodir").write_bytes(b"bad-archive")
    else:
        _write_nodir_zip(left_root / "watershed.nodir", {"hillslopes/h001.slp": "left"})
        (left_root / "watershed.thaw.tmp").mkdir()

    response = client.get(
        "/runs/run-left/cfg/diff/watershed.nodir/hillslopes/h001.slp?diff=run-right"
    )

    assert response.status_code == expected_status
    payload = response.get_json()
    assert payload["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("state", "expected_status", "expected_code"),
    [
        ("mixed", 409, "NODIR_MIXED_STATE"),
        ("invalid", 500, "NODIR_INVALID_ARCHIVE"),
        ("locked", 503, "NODIR_LOCKED"),
    ],
)
def test_diff_nodir_state_errors_propagate_from_right_run(
    diff_client,
    state: str,
    expected_status: int,
    expected_code: str,
) -> None:
    client, left_root, right_root = diff_client

    _write_nodir_zip(left_root / "watershed.nodir", {"hillslopes/h001.slp": "left"})

    if state == "mixed":
        (right_root / "watershed").mkdir()
        _write_nodir_zip(right_root / "watershed.nodir", {"hillslopes/h001.slp": "right"})
    elif state == "invalid":
        (right_root / "watershed.nodir").write_bytes(b"bad-archive")
    else:
        _write_nodir_zip(right_root / "watershed.nodir", {"hillslopes/h001.slp": "right"})
        (right_root / "watershed.thaw.tmp").mkdir()

    response = client.get(
        "/runs/run-left/cfg/diff/watershed.nodir/hillslopes/h001.slp?diff=run-right"
    )

    assert response.status_code == expected_status
    payload = response.get_json()
    assert payload["error"]["code"] == expected_code
