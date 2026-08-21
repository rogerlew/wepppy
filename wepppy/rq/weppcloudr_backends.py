"""Execution backends for one-shot WEPPcloudR renders.

The Kubernetes backend talks only to the narrow render control plane.  It does
not import a Kubernetes client or grant an RQ worker cluster credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

import requests


REQUEST_SCHEMA_VERSION = 1
MAX_REQUEST_BYTES = 16 * 1024
MAX_CONTROL_PLANE_RESPONSE_BYTES = 64 * 1024
TERMINAL_STATES = frozenset({"terminal-success", "terminal-failure", "cleaned"})
KNOWN_STATES = frozenset(
    {
        "creating",
        "create-ambiguous",
        "active",
        "terminal-success",
        "terminal-failure",
        "cleaned",
    }
)
K8S_ERROR_CODES = frozenset(
    {
        "weppcloudr_k8s_api_unavailable",
        "weppcloudr_k8s_unauthorized",
        "weppcloudr_k8s_admission_rejected",
        "weppcloudr_k8s_unschedulable",
        "weppcloudr_k8s_image_pull_failed",
        "weppcloudr_k8s_volume_mount_failed",
        "weppcloudr_k8s_evicted",
        "weppcloudr_k8s_oom_killed",
        "weppcloudr_k8s_deadline_exceeded",
        "weppcloudr_renderer_failed",
        "weppcloudr_artifact_invalid",
        "weppcloudr_k8s_state_lost",
        "weppcloudr_k8s_cancelled",
    }
)


class BackendError(RuntimeError):
    """Base error raised by a render execution backend."""


class BackendExecutionError(BackendError):
    """Backend failure retaining bounded diagnostic source streams."""

    def __init__(self, detail: str, *, stdout: str = "", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(detail)


class BackendConfigurationError(BackendError):
    """Raised when the selected backend cannot be configured safely."""


class KubernetesRenderError(BackendError):
    """Stable Kubernetes render failure with a canonical error code."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code if code in K8S_ERROR_CODES else "weppcloudr_k8s_state_lost"
        super().__init__(f"{self.code}: {detail}")


@dataclass(frozen=True)
class RenderRequest:
    """Strict version-1 request shared with the one-shot renderer."""

    schema_version: int
    rq_job_id: str
    runid: str
    config: str
    run_root: str
    active_root: str
    skip_cache: bool
    correlation_id: str
    deployment_revision: str
    renderer_image_digest: str

    def to_json(self) -> str:
        payload = json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise BackendConfigurationError("WEPPcloudR render request exceeds 16 KiB.")
        return payload

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BackendResult:
    """Bounded diagnostics and terminal receipt returned by a backend."""

    stdout: str
    stderr: str
    receipt: Mapping[str, object] | None = None


class RenderBackend(Protocol):
    """Deployment-specific execution interface."""

    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult:
        """Execute or reconcile one render and return terminal diagnostics."""


def validate_request(request: RenderRequest) -> None:
    """Validate types and identifier constraints independent of filesystem state."""
    if request.schema_version != REQUEST_SCHEMA_VERSION:
        raise BackendConfigurationError("Unsupported WEPPcloudR request schema version.")
    if not isinstance(request.skip_cache, bool):
        raise BackendConfigurationError("skip_cache must be a JSON boolean.")
    _validate_ascii(request.rq_job_id, "rq_job_id", 64)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", request.rq_job_id):
        raise BackendConfigurationError("Invalid WEPPcloudR rq_job_id.")
    _validate_ascii(request.correlation_id, "correlation_id", 128)
    if not request.runid or len(request.runid.encode("utf-8")) > 245:
        raise BackendConfigurationError("Invalid WEPPcloudR run ID length.")
    if request.runid in {".", ".."} or any(char in request.runid for char in ("/", "\\", "\x00")):
        raise BackendConfigurationError("Invalid WEPPcloudR run ID.")
    if (
        not request.config
        or len(request.config.encode("utf-8")) > 255
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", request.config)
    ):
        raise BackendConfigurationError("Invalid WEPPcloudR configuration identifier.")
    if not request.deployment_revision or len(request.deployment_revision) > 128:
        raise BackendConfigurationError("Missing or invalid deployment revision.")
    if request.renderer_image_digest and request.deployment_revision.lower() in {
        "unknown",
        "latest",
        "unset",
    }:
        raise BackendConfigurationError(
            "kubernetes-job requires an exact reviewed deployment revision."
        )
    if request.renderer_image_digest and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", request.renderer_image_digest
    ):
        raise BackendConfigurationError("Renderer image must use an exact sha256 digest.")
    request.to_json()


def deterministic_job_name(rq_job_id: str) -> str:
    """Derive Kubernetes identity without exposing user-controlled run values."""
    return f"weppcloudr-{hashlib.sha256(rq_job_id.encode('ascii')).hexdigest()[:20]}"


def _validate_ascii(value: str, field: str, maximum: int) -> None:
    if not value or len(value) > maximum or not value.isascii() or any(ord(char) < 32 for char in value):
        raise BackendConfigurationError(f"Invalid WEPPcloudR {field}.")


class DockerExecBackend:
    """Behavior-preserving adapter for the existing Compose renderer."""

    def __init__(self, container_name: str, fencing_generation: int) -> None:
        if not container_name or Path(container_name).name != container_name:
            raise BackendConfigurationError("Invalid WEPPcloudR container name.")
        self._container_name = container_name
        if fencing_generation < 1:
            raise BackendConfigurationError("Invalid Compose fencing generation.")
        self._fencing_generation = fencing_generation

    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult:
        if shutil.which("docker") is None:
            raise BackendConfigurationError(
                "Docker CLI not found in PATH for selected docker-exec backend."
            )
        payload = json.dumps(
            {
                "run_path": request.active_root,
                "runid": request.runid,
                "config": request.config,
                "skip_cache": request.skip_cache,
                "fencing_generation": self._fencing_generation,
            },
            ensure_ascii=False,
        )
        command = [
            "docker",
            "exec",
            "-i",
            self._container_name,
            "Rscript",
            "/srv/weppcloudr/render-compose-request.R",
        ]
        try:
            result = subprocess.run(
                command,
                input=payload,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendExecutionError(
                "WEPPcloudR Docker render exceeded its configured timeout.",
                stdout=str(exc.stdout or ""),
                stderr=str(exc.stderr or ""),
            ) from exc
        if result.returncode != 0:
            raise BackendExecutionError(
                "Failed to render DEVAL report via the selected Docker container "
                f"(exit {result.returncode}).",
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return BackendResult(stdout=result.stdout, stderr=result.stderr)


class RenderControlPlaneClient(Protocol):
    """Narrow, replay-safe interface implemented by the future controller."""

    def submit(self, request: RenderRequest) -> Mapping[str, object]: ...

    def observe(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...

    def cancel(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...


class HttpRenderControlPlaneClient:
    """Authenticated HTTP client; it never accepts arbitrary Job specifications."""

    def __init__(self, endpoint: str, token_file: Path, *, request_timeout: float = 10.0) -> None:
        if not endpoint.startswith("https://"):
            raise BackendConfigurationError("Render control-plane endpoint must use HTTPS.")
        if not token_file.is_file() or token_file.is_symlink():
            raise BackendConfigurationError("Render control-plane identity token is unavailable.")
        token_stat = token_file.stat()
        if token_stat.st_size > 16 * 1024 or token_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise BackendConfigurationError("Render control-plane identity token is not protected.")
        if token_stat.st_uid not in {0, os.geteuid()}:
            raise BackendConfigurationError("Render control-plane identity token owner is invalid.")
        self._endpoint = endpoint.rstrip("/")
        self._token_file = token_file
        self._request_timeout = request_timeout

    def submit(self, request: RenderRequest) -> Mapping[str, object]:
        return self._request("POST", "/v1/renders", json.loads(request.to_json()), request.digest)

    def observe(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]:
        return self._request("GET", f"/v1/renders/{rq_job_id}", None, request_digest)

    def cancel(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]:
        return self._request("POST", f"/v1/renders/{rq_job_id}/cancel", {}, request_digest)

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None,
        request_digest: str,
    ) -> Mapping[str, object]:
        token = self._token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise BackendConfigurationError("Render control-plane identity token is empty.")
        try:
            response = requests.request(
                method,
                f"{self._endpoint}{path}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-WEPPcloudR-Request-SHA256": request_digest,
                },
                timeout=self._request_timeout,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise KubernetesRenderError(
                "weppcloudr_k8s_api_unavailable", "render control plane is unavailable"
            ) from exc
        if response.status_code in {401, 403}:
            raise KubernetesRenderError("weppcloudr_k8s_unauthorized", "request denied")
        if response.status_code in {409, 422, 429}:
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "render admission rejected"
            )
        if not response.ok:
            raise KubernetesRenderError(
                "weppcloudr_k8s_api_unavailable", f"control plane returned HTTP {response.status_code}"
            )
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_CONTROL_PLANE_RESPONSE_BYTES:
            response.close()
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "control plane response is too large"
            )
        body_bytes = response.raw.read(MAX_CONTROL_PLANE_RESPONSE_BYTES + 1, decode_content=True)
        response.close()
        if len(body_bytes) > MAX_CONTROL_PLANE_RESPONSE_BYTES:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "control plane response is too large"
            )
        try:
            body = json.loads(body_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "control plane returned malformed JSON"
            ) from exc
        if not isinstance(body, dict):
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "control plane returned an invalid receipt"
            )
        return body


class KubernetesJobBackend:
    """Submit once and reconcile a deterministic Job through the control plane."""

    def __init__(
        self,
        client: RenderControlPlaneClient,
        *,
        expected_namespace: str,
        poll_interval: float = 2.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        if not expected_namespace:
            raise BackendConfigurationError("Kubernetes render namespace is required.")
        self._expected_namespace = expected_namespace
        self._poll_interval = poll_interval
        self._monotonic = monotonic
        self._sleeper = sleeper

    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult:
        if not request.renderer_image_digest:
            raise BackendConfigurationError(
                "kubernetes-job requires WEPPCLOUDR_K8S_IMAGE pinned by digest."
            )
        receipt = self._client.submit(request)
        snapshot = self._validate_receipt(receipt, request, None)
        deadline = self._monotonic() + timeout
        while True:
            snapshot = self._validate_receipt(receipt, request, snapshot)
            state = str(receipt["state"])
            if state in TERMINAL_STATES:
                return self._terminal_result(receipt)
            if self._monotonic() >= deadline:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_api_unavailable",
                    "timed out waiting for terminal render reconciliation",
                )
            self._sleeper(self._poll_interval)
            receipt = self._client.observe(request.rq_job_id, request.digest)

    def cancel(self, request: RenderRequest) -> Mapping[str, object]:
        """Persist cancellation intent through the controller and validate ownership."""
        receipt = self._client.cancel(request.rq_job_id, request.digest)
        if (
            set(receipt) == {"rq_job_id", "request_digest", "cleanup_state"}
            and receipt.get("rq_job_id") == request.rq_job_id
            and receipt.get("request_digest") == request.digest
            and receipt.get("cleanup_state") == "complete"
        ):
            return receipt
        self._validate_receipt(receipt, request, None)
        cleanup_state = receipt.get("cleanup_state")
        if cleanup_state not in {"deleting", "complete", "cleanup_timeout"}:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "unknown cancellation cleanup state"
            )
        return receipt

    def _validate_receipt(
        self,
        receipt: Mapping[str, object],
        request: RenderRequest,
        prior_snapshot: Mapping[str, object] | None,
    ) -> Mapping[str, object]:
        if receipt.get("rq_job_id") != request.rq_job_id:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "receipt RQ identity mismatch")
        if receipt.get("request_digest") != request.digest:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "receipt digest mismatch")
        if receipt.get("state") not in KNOWN_STATES:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "unknown receipt state")
        expected = {
            "backend": "kubernetes-job",
            "job_name": deterministic_job_name(request.rq_job_id),
            "renderer_image_digest": request.renderer_image_digest,
            "deployment_revision": request.deployment_revision,
        }
        for field, value in expected.items():
            if receipt.get(field) != value:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_state_lost", f"receipt {field} mismatch"
                )
        namespace = receipt.get("namespace")
        nonce = receipt.get("ownership_nonce")
        spec_digest = receipt.get("spec_digest")
        fencing_generation = receipt.get("fencing_generation")
        if (
            not isinstance(namespace, str)
            or not re.fullmatch(
                r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*",
                namespace,
            )
            or not re.fullmatch(r"[0-9a-f]{64}", str(nonce))
            or not re.fullmatch(r"[0-9a-f]{64}", str(spec_digest))
            or not isinstance(fencing_generation, int)
            or fencing_generation < 1
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "receipt execution snapshot is incomplete"
            )
        if namespace != self._expected_namespace:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "receipt namespace mismatch"
            )
        uid = receipt.get("job_uid")
        if uid is not None and (not isinstance(uid, str) or not uid):
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "receipt UID is invalid")
        state = str(receipt["state"])
        if state in {"creating", "create-ambiguous"} and uid is not None:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "unbound receipt unexpectedly carries a UID"
            )
        never_created = receipt.get("never_created") is True
        if (
            state in {"active", "terminal-success", "terminal-failure", "cleaned"}
            and uid is None
            and not (never_created and state in {"terminal-failure", "cleaned"})
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "UID-bound receipt is missing its UID"
            )
        snapshot = {
            **expected,
            "namespace": namespace,
            "ownership_nonce": nonce,
            "spec_digest": spec_digest,
            "fencing_generation": fencing_generation,
            "job_uid": uid,
        }
        if prior_snapshot is not None:
            for field, previous in prior_snapshot.items():
                current = snapshot[field]
                if field == "job_uid" and previous is None and current is not None:
                    continue
                if current != previous:
                    raise KubernetesRenderError(
                        "weppcloudr_k8s_state_lost", f"receipt {field} changed"
                    )
        return snapshot

    @staticmethod
    def _terminal_result(receipt: Mapping[str, object]) -> BackendResult:
        state = str(receipt["state"])
        if state == "terminal-success" or (
            state == "cleaned" and receipt.get("terminal_state") == "terminal-success"
        ):
            artifact_path = receipt.get("artifact_path")
            artifact_sha256 = receipt.get("artifact_sha256")
            artifact_size = receipt.get("artifact_size")
            fencing_generation = receipt.get("fencing_generation")
            if (
                not isinstance(artifact_path, str)
                or not re.fullmatch(r"[0-9a-f]{64}", str(artifact_sha256))
                or not isinstance(artifact_size, int)
                or artifact_size < 1
                or not isinstance(fencing_generation, int)
                or fencing_generation < 1
            ):
                raise KubernetesRenderError(
                    "weppcloudr_k8s_state_lost", "terminal receipt is incomplete"
                )
            return BackendResult(
                stdout=str(receipt.get("stdout", "")),
                stderr=str(receipt.get("stderr", "")),
                receipt=receipt,
            )
        code = str(receipt.get("error_code", "weppcloudr_k8s_state_lost"))
        raise KubernetesRenderError(code, str(receipt.get("reason", "render failed")))
