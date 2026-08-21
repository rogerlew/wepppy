from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.rq.weppcloudr_backends import RenderRequest
from wepppy.microservices import weppcloudr_control_plane as module


pytestmark = pytest.mark.unit


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value, nx: bool = False, **_kwargs):
        if nx and key in self.values:
            return False
        self.values[key] = value.encode() if isinstance(value, str) else value
        return True


def _request(active: Path) -> RenderRequest:
    return RenderRequest(
        schema_version=1,
        rq_job_id="01234567-89ab-cdef-0123-456789abcdef",
        runid="sample-run",
        config="disturbed9002",
        run_root=str(active),
        active_root=str(active),
        skip_cache=False,
        correlation_id="01234567-89ab-cdef-0123-456789abcdef",
        deployment_revision="80e621164869b8773c26660eb1f488e78898e14e",
        renderer_image_digest="sha256:" + "a" * 64,
    )


def test_initialize_is_idempotent_without_advancing_fence(tmp_path: Path) -> None:
    active = tmp_path / "runs" / "sa" / "sample-run"
    active.mkdir(parents=True)
    connection = FakeRedis()
    store = module.RedisReceiptStore(connection, pvc_root=tmp_path)
    request = _request(active)

    first = store.initialize(request, "weppcloud", "weppcloudr-test")
    second = store.initialize(request, "weppcloud", "weppcloudr-test")

    assert second == first
    assert first.fencing_generation == 1
    fence = active / "_locks" / "weppcloudr" / "deval_sample-run.fence"
    assert fence.read_text(encoding="ascii") == "1\n"


def test_prepare_execution_file_is_pvc_relative_and_digest_bound(tmp_path: Path) -> None:
    active = tmp_path / "runs" / "sa" / "sample-run"
    active.mkdir(parents=True)
    store = module.RedisReceiptStore(FakeRedis(), pvc_root=tmp_path)
    request = _request(active)
    receipt = store.initialize(request, "weppcloud", "weppcloudr-test")

    request_subpath, fence_subpath = store.prepare_execution_files(
        request, request.digest, receipt.fencing_generation
    )

    assert request_subpath == (
        f"runs/sa/sample-run/_requests/weppcloudr/{request.rq_job_id}.{request.digest}.json"
    )
    assert fence_subpath == "runs/sa/sample-run/_locks/weppcloudr/deval_sample-run.fence"
    payload = json.loads((tmp_path / request_subpath).read_text(encoding="utf-8"))
    assert payload["rq_job_id"] == request.rq_job_id
    assert (tmp_path / request_subpath).stat().st_mode & 0o777 == 0o440


def test_store_rejects_active_path_outside_pvc(tmp_path: Path) -> None:
    pvc = tmp_path / "pvc"
    active = tmp_path / "outside"
    pvc.mkdir()
    active.mkdir()
    store = module.RedisReceiptStore(FakeRedis(), pvc_root=pvc)

    with pytest.raises(module.KubernetesRenderError, match="escapes PVC root"):
        store.initialize(_request(active), "weppcloud", "weppcloudr-test")


def test_gateway_rejects_non_owned_job(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = module.KubernetesApiGateway("weppcloud")

    class Response:
        status_code = 200
        ok = True

        @staticmethod
        def json():
            return {"metadata": {"labels": {"app.kubernetes.io/name": "foreign"}}}

    monkeypatch.setattr(gateway, "_request", lambda *_args, **_kwargs: Response())

    with pytest.raises(module.KubernetesRenderError, match="not controller-owned"):
        gateway.get("weppcloud", "foreign-job")
