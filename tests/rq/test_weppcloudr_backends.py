from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
import requests

from wepppy.rq.weppcloudr_backends import (
    BackendConfigurationError,
    HttpRenderControlPlaneClient,
    KubernetesJobBackend,
    KubernetesRenderError,
    RenderRequest,
    validate_request,
)


pytestmark = pytest.mark.unit

IMAGE_DIGEST = "sha256:" + "a" * 64
REPO_ROOT = Path(__file__).resolve().parents[2]


def _request(**overrides: object) -> RenderRequest:
    values: dict[str, object] = {
        "schema_version": 1,
        "rq_job_id": "job-1",
        "runid": "run-1",
        "config": "disturbed9002_wbt",
        "run_root": "/wc1/runs/br/branching-hubbub",
        "active_root": "/wc1/runs/br/branching-hubbub/_pups/shared",
        "skip_cache": True,
        "correlation_id": "job-1",
        "deployment_revision": "abc123",
        "renderer_image_digest": IMAGE_DIGEST,
    }
    values.update(overrides)
    return RenderRequest(**values)  # type: ignore[arg-type]


def _receipt(request: RenderRequest, state: str, **extra: object) -> dict[str, object]:
    return {
        "rq_job_id": request.rq_job_id,
        "request_digest": request.digest,
        "state": state,
        "backend": "kubernetes-job",
        "namespace": "weppcloudr-render",
        "job_name": "weppcloudr-" + hashlib.sha256(request.rq_job_id.encode()).hexdigest()[:20],
        "job_uid": "uid-1",
        "ownership_nonce": "c" * 64,
        "spec_digest": "d" * 64,
        "renderer_image_digest": request.renderer_image_digest,
        "deployment_revision": request.deployment_revision,
        "fencing_generation": 1,
        **extra,
    }


def _success_receipt(request: RenderRequest, state: str = "terminal-success", **extra: object) -> dict[str, object]:
    return _receipt(
        request,
        state,
        artifact_path=f"{request.active_root}/export/WEPPcloudR/deval_{request.runid}.htm",
        artifact_sha256="b" * 64,
        artifact_size=12,
        **extra,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("rq_job_id", "bad/id"),
        ("runid", "../escape"),
        ("config", ""),
        ("renderer_image_digest", "latest"),
        ("deployment_revision", "unknown"),
    ],
)
def test_render_request_rejects_invalid_contract_values(field: str, value: object) -> None:
    with pytest.raises(BackendConfigurationError):
        validate_request(_request(**{field: value}))


def test_render_request_json_is_canonical_and_bounded() -> None:
    request = _request()
    validate_request(request)

    payload = json.loads(request.to_json())

    assert payload["schema_version"] == 1
    assert payload["run_root"] == request.run_root
    assert len(request.to_json().encode("utf-8")) <= 16 * 1024
    assert len(request.digest) == 64


class _FakeClient:
    def __init__(self, receipts: list[dict[str, object]]) -> None:
        self.receipts = receipts
        self.submitted = 0
        self.observed = 0

    def submit(self, _request_value: RenderRequest) -> dict[str, object]:
        self.submitted += 1
        return self.receipts[0]

    def observe(self, _rq_job_id: str, _request_digest: str) -> dict[str, object]:
        self.observed += 1
        return self.receipts[self.observed]

    def cancel(self, _rq_job_id: str, _request_digest: str) -> dict[str, object]:
        return self.receipts[-1]


def _backend(client: _FakeClient, **kwargs: object) -> KubernetesJobBackend:
    return KubernetesJobBackend(
        client, expected_namespace="weppcloudr-render", **kwargs
    )


def test_kubernetes_backend_reconciles_existing_job_to_success() -> None:
    request = _request()
    client = _FakeClient(
        [
            _receipt(request, "active"),
            _success_receipt(request, stdout="done", stderr=""),
        ]
    )
    clock = iter([0.0, 0.0])
    backend = _backend(
        client,
        poll_interval=0,
        monotonic=lambda: next(clock),
        sleeper=lambda _seconds: None,
    )

    result = backend.render(request, timeout=30)

    assert result.stdout == "done"
    assert client.submitted == 1
    assert client.observed == 1


def test_kubernetes_backend_accepts_collected_success_after_ttl_cleanup() -> None:
    request = _request()
    client = _FakeClient(
        [_success_receipt(request, "cleaned", terminal_state="terminal-success", stdout="collected")]
    )

    result = _backend(client).render(request, timeout=30)

    assert result.stdout == "collected"


@pytest.mark.parametrize(
    ("receipt_overrides", "match"),
    [
        ({"rq_job_id": "other"}, "identity mismatch"),
        ({"request_digest": "0" * 64}, "digest mismatch"),
        ({"state": "mystery"}, "unknown receipt state"),
    ],
)
def test_kubernetes_backend_fails_closed_on_receipt_mismatch(
    receipt_overrides: dict[str, object], match: str
) -> None:
    request = _request()
    receipt = _receipt(request, "active")
    receipt.update(receipt_overrides)

    with pytest.raises(KubernetesRenderError, match=match):
        _backend(_FakeClient([receipt])).render(request, timeout=30)


@pytest.mark.parametrize(
    ("state", "uid"),
    [
        ("creating", "uid-1"),
        ("create-ambiguous", "uid-1"),
        ("active", None),
        ("terminal-success", None),
        ("terminal-failure", None),
        ("cleaned", None),
    ],
)
def test_kubernetes_backend_enforces_phase_exclusive_uid(state: str, uid: object) -> None:
    request = _request()
    receipt = _receipt(request, state, job_uid=uid)

    with pytest.raises(KubernetesRenderError, match="UID"):
        _backend(_FakeClient([receipt])).render(request, timeout=30)


def test_kubernetes_backend_preserves_canonical_terminal_code() -> None:
    request = _request()
    receipt = _receipt(
        request,
        "terminal-failure",
        error_code="weppcloudr_k8s_oom_killed",
        reason="container terminated",
    )

    with pytest.raises(KubernetesRenderError) as exc_info:
        _backend(_FakeClient([receipt])).render(request, timeout=30)

    assert exc_info.value.code == "weppcloudr_k8s_oom_killed"


def test_kubernetes_backend_rejects_incomplete_success_receipt() -> None:
    request = _request()

    with pytest.raises(KubernetesRenderError, match="incomplete"):
        _backend(
            _FakeClient([_receipt(request, "terminal-success")])
        ).render(request, timeout=30)


def test_kubernetes_backend_times_out_without_creating_again() -> None:
    request = _request()
    client = _FakeClient([_receipt(request, "active")])
    clock = iter([0.0, 31.0])
    backend = _backend(
        client,
        poll_interval=0,
        monotonic=lambda: next(clock),
        sleeper=lambda _seconds: None,
    )

    with pytest.raises(KubernetesRenderError, match="timed out"):
        backend.render(request, timeout=30)

    assert client.submitted == 1
    assert client.observed == 0


def test_kubernetes_backend_validates_durable_cancellation_state() -> None:
    request = _request()
    receipt = _receipt(request, "active", cleanup_state="deleting")

    result = _backend(_FakeClient([receipt])).cancel(request)

    assert result["cleanup_state"] == "deleting"


def test_kubernetes_backend_accepts_exact_no_receipt_cancellation_schema() -> None:
    request = _request()
    receipt = {
        "rq_job_id": request.rq_job_id,
        "request_digest": request.digest,
        "cleanup_state": "complete",
    }

    result = _backend(_FakeClient([receipt])).cancel(request)

    assert result == receipt


@pytest.mark.parametrize(
    "mutation",
    [
        {"extra": True},
        {"cleanup_state": "deleting"},
        {"request_digest": "0" * 64},
    ],
)
def test_kubernetes_backend_rejects_near_miss_no_receipt_cancellation_schema(
    mutation: dict[str, object],
) -> None:
    request = _request()
    receipt: dict[str, object] = {
        "rq_job_id": request.rq_job_id,
        "request_digest": request.digest,
        "cleanup_state": "complete",
    }
    receipt.update(mutation)

    with pytest.raises(KubernetesRenderError):
        _backend(_FakeClient([receipt])).cancel(request)


def test_kubernetes_backend_rejects_unknown_cancellation_state() -> None:
    request = _request()
    receipt = _receipt(request, "active", cleanup_state="gone-maybe")

    with pytest.raises(KubernetesRenderError, match="cleanup state"):
        _backend(_FakeClient([receipt])).cancel(request)


def test_http_control_plane_requires_https_and_regular_token(tmp_path: Path) -> None:
    token = tmp_path / "token"
    token.write_text("identity", encoding="utf-8")

    with pytest.raises(BackendConfigurationError, match="HTTPS"):
        HttpRenderControlPlaneClient("http://controller", token)
    with pytest.raises(BackendConfigurationError, match="unavailable"):
        HttpRenderControlPlaneClient("https://controller", tmp_path / "missing")


def test_http_control_plane_maps_authorization_without_leaking_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "token"
    token.write_text("identity", encoding="utf-8")
    monkeypatch.setattr(
        requests,
        "request",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=403, ok=False),
    )

    with pytest.raises(KubernetesRenderError) as exc_info:
        HttpRenderControlPlaneClient("https://controller", token).submit(_request())

    assert exc_info.value.code == "weppcloudr_k8s_unauthorized"


def test_one_shot_renderer_has_strict_fixed_request_contract() -> None:
    source = (REPO_ROOT / "weppcloudR/render-request-v1.R").read_text(
        encoding="utf-8"
    )

    assert '"/run/weppcloudr/request.json"' in source
    assert "request fields do not match schema version 1" in source
    assert "sha256sum" in source
    assert 'system2(\n  "python3"' in source
    assert "/srv/weppcloudr/publish_fenced.py" in source
    assert "!is.na(target) && nzchar(target)" in source
    assert "Sys.readlink(final_output) !=" not in source


def test_weppcloudr_uses_checksum_pinned_local_fontawesome() -> None:
    dockerfile = (REPO_ROOT / "weppcloudR/Dockerfile").read_text(encoding="utf-8")
    renderer = (REPO_ROOT / "weppcloudR/plumber.R").read_text(encoding="utf-8")
    templates = list((REPO_ROOT / "weppcloudR/templates").rglob("*.Rmd"))

    expected = "8cb270b4d9485a93b31df98113fda8723ffc067fa7bfa90cedd47b76f7b10be1"
    assert expected in dockerfile
    assert expected in renderer
    assert "/srv/weppcloudr/vendor/fontawesome/5.3.1/all.js" in renderer
    assert "use_fontawesome = FALSE" in renderer
    assert "local_fontawesome_header" in renderer
    assert all(
        "use_fontawesome: true" not in path.read_text(encoding="utf-8")
        for path in templates
    )


def test_fenced_publisher_preserves_foreign_staging_file_and_retry_succeeds(
    tmp_path: Path,
) -> None:
    approved_root = tmp_path / "runs"
    active_root = approved_root / "run"
    output_dir = active_root / "export" / "WEPPcloudR"
    fence_dir = active_root / "_locks" / "weppcloudr"
    output_dir.mkdir(parents=True)
    fence_dir.mkdir(parents=True)
    runid = "publisher-retry"
    (fence_dir / f"deval_{runid}.fence").write_text("1\n", encoding="ascii")
    (fence_dir / f"deval_{runid}.fence.publish.lock").touch()

    temporary_name = f".deval_{runid}.{tmp_path.name}.tmp.htm"
    temporary_path = Path("/tmp") / temporary_name
    temporary_path.write_text("<!DOCTYPE html>retry", encoding="utf-8")
    publishing_path = output_dir / f".{temporary_name}.publishing"
    publishing_path.write_text("owned by another invocation", encoding="utf-8")
    command = [
        "python3",
        str(REPO_ROOT / "weppcloudR/publish_fenced.py"),
        str(active_root),
        runid,
        "1",
        temporary_name,
    ]
    environment = {**os.environ, "WEPPCLOUDR_RUN_ROOTS": str(approved_root)}

    try:
        failed = subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False
        )
        assert failed.returncode != 0
        assert publishing_path.read_text(encoding="utf-8") == "owned by another invocation"

        publishing_path.unlink()
        final_path = output_dir / f"deval_{runid}.htm"
        final_path.mkdir()
        failed_after_create = subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False
        )
        assert failed_after_create.returncode != 0
        assert not publishing_path.exists()

        final_path.rmdir()
        subprocess.run(command, env=environment, capture_output=True, text=True, check=True)
        assert final_path.read_text(encoding="utf-8") == "<!DOCTYPE html>retry"
        assert not publishing_path.exists()
    finally:
        temporary_path.unlink(missing_ok=True)
