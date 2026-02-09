import importlib
from pathlib import Path

import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice


@pytest.fixture
def load_browse(monkeypatch):
    def _allow_auth(*args, **kwargs):
        import wepppy.microservices.browse.auth as auth_mod

        return auth_mod.AuthContext(
            claims={"token_class": "user", "roles": ["User"], "sub": "1"},
            token_class="user",
            roles=frozenset({"user"}),
        )

    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.browse.browse as browse_mod

        browse_mod = importlib.reload(browse_mod)
        monkeypatch.setattr(browse_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(browse_mod, "authorize_group_request", _allow_auth)
        return browse_mod

    return _loader


def _write_file(path: Path, contents: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def test_culvert_browse_root_lists_runs(tmp_path: Path, load_browse):
    culverts_root = tmp_path / "culverts"
    batch_uuid = "culvert-1234"
    _write_file(culverts_root / batch_uuid / "runs" / "1001" / "run_metadata.json", "{}")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        CULVERTS_ROOT=str(culverts_root),
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/culverts/{batch_uuid}/browse/")

    assert response.status_code == 200
    body = response.text
    assert f'href="/weppcloud/culverts/{batch_uuid}/browse/"' in body
    assert f"/weppcloud/culverts/{batch_uuid}/browse/runs/" in body


def test_batch_browse_root_lists_runs(tmp_path: Path, load_browse):
    batch_root = tmp_path / "batch"
    batch_name = "batch-alpha"
    _write_file(batch_root / batch_name / "runs" / "_175" / "run_metadata.json", "{}")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        BATCH_RUNNER_ROOT=str(batch_root),
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/batch/{batch_name}/browse/")

    assert response.status_code == 200
    body = response.text
    assert f'href="/weppcloud/batch/{batch_name}/browse/"' in body
    assert f"/weppcloud/batch/{batch_name}/browse/runs/" in body
