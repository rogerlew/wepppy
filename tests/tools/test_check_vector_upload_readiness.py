from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "check_vector_upload_readiness.py"


def _module():
    spec = importlib.util.spec_from_file_location("check_vector_upload_readiness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Redis:
    pending: int = 0

    def ping(self) -> bool:
        return True

    def hgetall(self, _key: str) -> dict[str, str]:
        return {"initialized": "1", "committed": "0", "reserved": "0", "inflight": "0"}

    def scard(self, _key: str) -> int:
        return self.pending


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _MalformedResponse(_Response):
    def json(self) -> dict[str, object]:
        raise ValueError("malformed json")


def _configure(monkeypatch: pytest.MonkeyPatch, module, root: Path) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "test-fs")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(root))
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "http://converter/v1/convert")
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_EXPECTED_GEOPARQUET_BINARY_SHA256", "a" * 64)
    monkeypatch.setenv("VECTOR_UPLOAD_EXPECTED_GEOPARQUET_CARGO_LOCK_SHA256", "b" * 64)
    monkeypatch.setenv("VECTOR_UPLOAD_EXPECTED_SHAPE_CONVERTER_REVISION", "c" * 40)
    monkeypatch.setattr(Path, "is_mount", lambda _self: True)
    monkeypatch.setattr(module.redis, "Redis", lambda **_kwargs: _Redis())
    monkeypatch.setattr(module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})


def _healthy() -> dict[str, object]:
    return {
        "status": "ok",
        "check": "ready",
        "geoparquet_parser": "ready",
        "geoparquet_parser_provenance": {
            "binary_sha256": "a" * 64,
            "cargo_lock_sha256": "b" * 64,
            "source_revision": "c" * 40,
        },
    }


def test_readiness_accepts_exact_healthy_parser_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    _configure(monkeypatch, module, tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module.requests,
        "get",
        lambda *_args, **kwargs: calls.append(kwargs) or _Response(_healthy()),
    )
    assert module.main() == 0
    assert calls == [{"timeout": (3.0, 10.0), "allow_redirects": False}]


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "not_ready"},
        {"geoparquet_parser": "unavailable"},
        {"geoparquet_parser_provenance": None},
        {
            "geoparquet_parser_provenance": {
                "binary_sha256": "d" * 64,
                "cargo_lock_sha256": "b" * 64,
                "source_revision": "c" * 40,
            }
        },
    ],
)
def test_readiness_rejects_unhealthy_or_wrong_parser_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: dict[str, object],
) -> None:
    module = _module()
    _configure(monkeypatch, module, tmp_path)
    payload = _healthy()
    payload.update(mutation)
    monkeypatch.setattr(module.requests, "get", lambda *_args, **_kwargs: _Response(payload))
    with pytest.raises(SystemExit):
        module.main()


def test_readiness_rejects_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    _configure(monkeypatch, module, tmp_path)
    monkeypatch.setattr(module.requests, "get", lambda *_args, **_kwargs: _MalformedResponse({}))
    with pytest.raises(ValueError, match="malformed json"):
        module.main()


def test_readiness_rejects_pending_rebuild_obligation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    _configure(monkeypatch, module, tmp_path)
    obligations = tmp_path / ".vector-upload-rebuild-pending"
    obligations.mkdir()
    (obligations / "pending.json").write_text("{}")
    monkeypatch.setattr(module.requests, "get", lambda *_args, **_kwargs: _Response(_healthy()))
    with pytest.raises(SystemExit, match="rebuild is pending"):
        module.main()


def test_readiness_rejects_redis_pending_rebuild_obligation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    _configure(monkeypatch, module, tmp_path)
    connection = _Redis()
    connection.pending = 1
    monkeypatch.setattr(module.redis, "Redis", lambda **_kwargs: connection)
    monkeypatch.setattr(module.requests, "get", lambda *_args, **_kwargs: _Response(_healthy()))
    with pytest.raises(SystemExit, match="rebuild is pending"):
        module.main()
