from __future__ import annotations

import io
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _load_module() -> Any:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = (
        repo_root
        / "docs"
        / "culvert-at-risk-integration"
        / "dev-package"
        / "scripts"
        / "download_skeletons.py"
    )
    spec = spec_from_file_location("devpkg_download_skeletons", script_path)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("runs_manifest.md", "# runs\n")
        zf.writestr("runs/123/run_metadata.json", '{"status":"finished"}\n')
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self._body = body
        try:
            self.text = body.decode("utf-8")
        except Exception:
            self.text = ""

    def iter_content(self, chunk_size: int = 1) -> Any:
        for idx in range(0, len(self._body), max(int(chunk_size), 1)):
            yield self._body[idx : idx + chunk_size]


def test_download_run_skeletons_zip_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_module()
    body = _zip_bytes()

    called: dict[str, Any] = {}

    def _fake_get(url: str, *, headers=None, stream=None, timeout=None):
        called["url"] = url
        called["headers"] = headers
        called["stream"] = stream
        called["timeout"] = timeout
        return _FakeResponse(200, body)

    monkeypatch.setattr(mod.requests, "get", _fake_get)

    out_path = tmp_path / "run_skeletons.zip"
    got = mod.download_run_skeletons_zip(
        base_url="https://wepp.cloud",
        batch_uuid="abc-123",
        browse_token="token-xyz",
        out_path=out_path,
        timeout_s=3,
        chunk_size=8,
    )

    assert got == out_path.resolve()
    assert out_path.read_bytes() == body
    assert called["url"].endswith(
        "/weppcloud/culverts/abc-123/download/weppcloud_run_skeletons.zip"
    )
    assert called["headers"]["Authorization"] == "Bearer token-xyz"
    assert called["stream"] is True


def test_download_run_skeletons_zip_http_error_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_module()

    def _fake_get(url: str, *, headers=None, stream=None, timeout=None):
        return _FakeResponse(403, b"Token not authorized for run")

    monkeypatch.setattr(mod.requests, "get", _fake_get)

    with pytest.raises(mod.DownloadError, match=r"HTTP 403"):
        mod.download_run_skeletons_zip(
            base_url="https://wepp.cloud",
            batch_uuid="abc-123",
            browse_token="token-xyz",
            out_path=tmp_path / "out.zip",
        )


def test_download_run_skeletons_zip_non_zip_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_module()

    def _fake_get(url: str, *, headers=None, stream=None, timeout=None):
        return _FakeResponse(200, b"not-a-zip")

    monkeypatch.setattr(mod.requests, "get", _fake_get)

    out_path = tmp_path / "out.zip"
    with pytest.raises(mod.DownloadError, match=r"not a ZIP"):
        mod.download_run_skeletons_zip(
            base_url="https://wepp.cloud",
            batch_uuid="abc-123",
            browse_token="token-xyz",
            out_path=out_path,
        )

    assert not out_path.exists()

