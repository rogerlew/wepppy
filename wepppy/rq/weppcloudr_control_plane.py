"""Pure control-plane state machine for isolated WEPPcloudR Kubernetes Jobs.

Deployment adapters supply durable storage, Kubernetes API access, authenticated
HTTP routing, and request/fence file materialization.  This module owns the
reviewable state transitions and fixed Job specification without importing a
Kubernetes SDK.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Callable, Iterable, Mapping, Protocol

from wepppy.rq.weppcloudr_backends import (
    KubernetesRenderError,
    RenderRequest,
    deterministic_job_name,
    validate_request,
)


_LOGGER = logging.getLogger(__name__)


class ReceiptState(StrEnum):
    CREATING = "creating"
    CREATE_AMBIGUOUS = "create-ambiguous"
    ACTIVE = "active"
    TERMINAL_SUCCESS = "terminal-success"
    TERMINAL_FAILURE = "terminal-failure"
    CLEANED = "cleaned"


class JobPhase(StrEnum):
    ABSENT = "absent"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELETING = "deleting"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class ControlPlaneConfig:
    namespace: str
    renderer_image_digest: str
    renderer_image_repository: str
    run_pvc: str
    geodata_pvc: str
    service_account: str
    max_active_renders: int
    active_deadline_seconds: int = 600
    pending_timeout_seconds: int = 120
    completed_ttl_seconds: int = 1200
    create_reconcile_grace_seconds: int = 30
    cancellation_grace_seconds: int = 120
    run_root_mappings: tuple[tuple[str, str], ...] = (
        ("/wc1/runs", "runs"),
        ("/wc1/batch", "batch"),
        ("/wc1/culverts", "culverts"),
    )
    cpu_request: str = "1"
    cpu_limit: str = "2"
    memory_request: str = "2Gi"
    memory_limit: str = "8Gi"

    def validate(self) -> None:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.renderer_image_digest):
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected",
                "renderer image digest is invalid",
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*", self.renderer_image_repository):
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "renderer image repository is invalid"
            )
        if (
            self.max_active_renders < 1
            or self.active_deadline_seconds < 1
            or self.pending_timeout_seconds < 1
            or self.create_reconcile_grace_seconds < 1
            or self.cancellation_grace_seconds < 1
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "invalid render admission configuration"
            )
        for value in (
            self.namespace,
            self.run_pvc,
            self.geodata_pvc,
            self.service_account,
        ):
            if not value:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_admission_rejected", "incomplete render configuration"
                )
        if not self.run_root_mappings or any(
            not root.startswith("/")
            or not subpath
            or subpath.startswith("/")
            or ".." in subpath.split("/")
            for root, subpath in self.run_root_mappings
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "invalid run PVC root mapping"
            )


@dataclass(frozen=True)
class ExecutionReceipt:
    rq_job_id: str
    request_digest: str
    state: ReceiptState
    backend: str
    namespace: str
    job_name: str
    job_uid: str | None
    ownership_nonce: str
    spec_digest: str
    renderer_image_digest: str
    deployment_revision: str
    fencing_generation: int
    created_at: float
    create_attempted_at: float | None = None
    job_created_at: float | None = None
    started_at: float | None = None
    ended_at: float | None = None
    cancellation_requested: bool = False
    cancellation_requested_at: float | None = None
    cleanup_state: str | None = None
    terminal_state: str | None = None
    error_code: str | None = None
    reason: str | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    artifact_size: int | None = None
    never_created: bool = False
    stdout_ref: str | None = None
    stderr_ref: str | None = None

    def payload(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class JobObservation:
    phase: JobPhase
    uid: str | None = None
    ownership_nonce: str | None = None
    request_digest: str | None = None
    spec_digest: str | None = None
    renderer_image_digest: str | None = None
    deployment_revision: str | None = None
    reason: str | None = None
    exit_code: int | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    artifact_size: int | None = None
    result_rq_job_id: str | None = None
    result_request_digest: str | None = None
    result_fencing_generation: int | None = None
    stdout_ref: str | None = None
    stderr_ref: str | None = None


class CreateAmbiguous(RuntimeError):
    """The API response was lost and create outcome requires reconciliation."""


class ReceiptConflict(RuntimeError):
    """A durable compare-and-swap or ownership operation failed."""


class ReceiptStore(Protocol):
    def get(self, rq_job_id: str) -> ExecutionReceipt | None: ...
    def replace(self, expected: ExecutionReceipt, updated: ExecutionReceipt) -> None: ...
    def acquire_permit(self, rq_job_id: str, nonce: str, maximum: int) -> bool: ...
    def release_permit(self, rq_job_id: str, nonce: str) -> None: ...
    def persist_cancellation(self, rq_job_id: str, request_digest: str) -> None: ...
    def cancellation_requested(self, rq_job_id: str, request_digest: str) -> bool: ...
    def prepare_execution_files(
        self, request: RenderRequest, request_digest: str, fencing_generation: int
    ) -> tuple[str, str]: ...
    def iter_reconcilable(self) -> Iterable[ExecutionReceipt]: ...
    def acknowledge_event(self, receipt: ExecutionReceipt) -> None: ...
    def initialize(
        self,
        request: RenderRequest,
        namespace: str,
        job_name: str,
    ) -> ExecutionReceipt:
        """Atomically reserve nonce/fence/snapshot under the artifact publish lock.

        The implementation must use the same ``*.fence.publish.lock`` observed
        by ``publish-fenced.sh`` while it advances and persists the generation.
        It must also persist ``created_at`` from a wall clock before returning.
        """
        ...
    def load_request(self, rq_job_id: str, request_digest: str) -> RenderRequest: ...
    def dispatch_lock(self, rq_job_id: str) -> AbstractContextManager[None]: ...
    def cleanup_execution_files(self, receipt: ExecutionReceipt) -> None: ...


class KubernetesGateway(Protocol):
    def get(self, namespace: str, name: str) -> JobObservation: ...
    def create(self, namespace: str, spec: Mapping[str, object]) -> JobObservation: ...
    def delete_foreground(self, namespace: str, name: str, uid: str) -> None: ...
    def patch_completed_ttl(
        self, namespace: str, name: str, uid: str, _ttl_seconds: int
    ) -> None: ...


class ReceiptEventSink(Protocol):
    def publish(self, receipt: ExecutionReceipt) -> None:
        """Idempotently publish the receipt transition to RQ and alerting.

        Implementations deduplicate by RQ ID, request digest, state, and cleanup
        state before sending a stop command or operator alert.
        """
        ...

    def publish_error(self, receipt: ExecutionReceipt, error: KubernetesRenderError) -> None:
        """Idempotently alert a failed reconciliation without starving peers."""
        ...


def _canonical_digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pvc_subpath(request: RenderRequest, config: ControlPlaneConfig) -> str:
    run_root = request.run_root.rstrip("/")
    active_root = request.active_root.rstrip("/")
    if (
        not run_root.startswith("/")
        or ".." in run_root.split("/")
        or "." in run_root.split("/")
        or ".." in active_root.split("/")
        or "." in active_root.split("/")
    ):
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "invalid run PVC subPath"
        )
    if active_root != run_root and not active_root.startswith(f"{run_root}/"):
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "active root escapes run root"
        )
    matches = [
        (root.rstrip("/"), prefix.rstrip("/"))
        for root, prefix in config.run_root_mappings
        if run_root == root.rstrip("/") or run_root.startswith(f"{root.rstrip('/')}/")
    ]
    if len(matches) != 1:
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "run root has no unique PVC mapping"
        )
    root, prefix = matches[0]
    relative = run_root[len(root) :].lstrip("/")
    if not relative:
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "approved root itself is not a run"
        )
    return "/".join(part for part in (prefix, relative) if part)


def build_job_spec(
    request: RenderRequest,
    config: ControlPlaneConfig,
    *,
    ownership_nonce: str,
    request_digest: str,
    fencing_generation: int,
    request_subpath: str,
) -> tuple[dict[str, object], str]:
    """Build the fixed, admission-reviewable Job and its canonical digest."""
    config.validate()
    if request.renderer_image_digest != config.renderer_image_digest:
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "renderer image snapshot mismatch"
        )
    name = deterministic_job_name(request.rq_job_id)
    if (
        not request_subpath
        or request_subpath.startswith("/")
        or ".." in request_subpath.split("/")
    ):
        raise KubernetesRenderError(
            "weppcloudr_k8s_admission_rejected", "invalid request PVC subPath"
        )
    # Preserve the allowlisted run-root admission check even though the NFS
    # volume is mounted without a Kubernetes subPath. Talos kubelet runs
    # subPath preparation as root; root_squash maps that identity to nobody and
    # rejects protected WEPPcloud directory traversal before the container can
    # start. The short-lived, immutable renderer therefore receives the same
    # /wc1 volume boundary as existing WEPPcloud workers and remains confined
    # by its fixed request, tokenless identity, and no-egress policy.
    _pvc_subpath(request, config)
    labels = {
        "app.kubernetes.io/name": "weppcloudr-render",
        "weppcloud.org/rq-id-hash": hashlib.sha256(
            request.rq_job_id.encode("ascii")
        ).hexdigest()[:32],
    }
    annotations = {
        "weppcloud.org/ownership-nonce": ownership_nonce,
        "weppcloud.org/request-digest": request_digest,
        "weppcloud.org/deployment-revision": request.deployment_revision,
        "weppcloud.org/renderer-image-digest": request.renderer_image_digest,
    }
    pod_spec: dict[str, object] = {
        "automountServiceAccountToken": False,
        "serviceAccountName": config.service_account,
        "restartPolicy": "Never",
        # The retained NFS exports are root-squashed.  A pod-level fsGroup asks
        # kubelet to recursively mutate the mounted run tree and fails before
        # the renderer starts.  Match the established WEPPcloud workload
        # identity directly instead.
        "securityContext": {
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 993,
        },
        "containers": [
            {
                "name": "renderer",
                "image": f"{config.renderer_image_repository}@{config.renderer_image_digest}",
                "imagePullPolicy": "IfNotPresent",
                "command": ["Rscript", "/srv/weppcloudr/render-request-v1.R"],
                "args": [
                    f"/wc1/{request_subpath}",
                    request_digest,
                    str(fencing_generation),
                ],
                # OCI runtime prepares workingDir before switching to the
                # application UID. A protected root-squashed NFS path therefore
                # fails during container init even though UID 1000 can access it.
                # The renderer consumes absolute paths from the signed request.
                "workingDir": "/tmp",
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True,
                    "capabilities": {"drop": ["ALL"]},
                    "seccompProfile": {"type": "RuntimeDefault"},
                },
                "resources": {
                    "requests": {
                        "cpu": config.cpu_request,
                        "memory": config.memory_request,
                    },
                    "limits": {"cpu": config.cpu_limit, "memory": config.memory_limit},
                },
                "volumeMounts": [
                    {
                        "name": "run",
                        "mountPath": "/wc1",
                    },
                    {"name": "geodata", "mountPath": "/geodata", "readOnly": True},
                    {"name": "tmp", "mountPath": "/tmp"},
                ],
            }
        ],
        "volumes": [
            {"name": "run", "persistentVolumeClaim": {"claimName": config.run_pvc}},
            {
                "name": "geodata",
                "persistentVolumeClaim": {"claimName": config.geodata_pvc, "readOnly": True},
            },
            {"name": "tmp", "emptyDir": {"sizeLimit": "2Gi"}},
        ],
    }
    spec: dict[str, object] = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "namespace": config.namespace, "labels": labels, "annotations": annotations},
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": config.active_deadline_seconds,
            "template": {"metadata": {"labels": labels, "annotations": annotations}, "spec": pod_spec},
        },
    }
    spec_digest = _canonical_digest(spec)
    annotations["weppcloud.org/spec-digest"] = spec_digest
    return spec, spec_digest


class RenderControlPlane:
    """Crash-recoverable state machine over durable and Kubernetes adapters."""

    def __init__(
        self,
        store: ReceiptStore,
        kubernetes: KubernetesGateway,
        config: ControlPlaneConfig,
        *,
        event_sink: ReceiptEventSink,
        clock: Callable[[], float] = time.time,
    ) -> None:
        config.validate()
        self._store = store
        self._kubernetes = kubernetes
        self._config = config
        self._event_sink = event_sink
        self._clock = clock

    def submit(self, request: RenderRequest) -> ExecutionReceipt:
        validate_request(request)
        existing = self._store.get(request.rq_job_id)
        if existing is not None:
            self._assert_request(existing, request)
            if not existing.spec_digest:
                existing, _spec = self._ensure_spec(existing, request)
            return self._reconcile(existing)
        receipt = self._store.initialize(
            request,
            self._config.namespace,
            deterministic_job_name(request.rq_job_id),
        )
        self._assert_request(receipt, request)
        if receipt.state is not ReceiptState.CREATING or receipt.spec_digest:
            return self._reconcile(receipt)
        receipt, spec = self._ensure_spec(receipt, request)
        return self._dispatch_create(receipt, request, spec)

    def _ensure_spec(
        self, receipt: ExecutionReceipt, request: RenderRequest
    ) -> tuple[ExecutionReceipt, Mapping[str, object]]:
        request_subpath, _fence_path = self._store.prepare_execution_files(
            request, request.digest, receipt.fencing_generation
        )
        spec, spec_digest = build_job_spec(
            request,
            self._config,
            ownership_nonce=receipt.ownership_nonce,
            request_digest=request.digest,
            fencing_generation=receipt.fencing_generation,
            request_subpath=request_subpath,
        )
        if receipt.spec_digest:
            if receipt.spec_digest != spec_digest:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_state_lost", "reconstructed Job spec mismatch"
                )
            return receipt, spec
        initialized = replace(receipt, spec_digest=spec_digest)
        try:
            self._store.replace(receipt, initialized)
        except ReceiptConflict:
            initialized = self._require_receipt(receipt.rq_job_id, receipt.request_digest)
            if initialized.spec_digest != spec_digest:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_state_lost", "concurrent Job spec mismatch"
                )
        return initialized, spec

    def _dispatch_create(
        self,
        receipt: ExecutionReceipt,
        request: RenderRequest,
        spec: Mapping[str, object] | None = None,
    ) -> ExecutionReceipt:
        if not self._store.acquire_permit(
            receipt.rq_job_id, receipt.ownership_nonce, self._config.max_active_renders
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "render concurrency limit reached"
            )
        with self._store.dispatch_lock(receipt.rq_job_id):
            current = self._require_receipt(receipt.rq_job_id, receipt.request_digest)
            if self._store.cancellation_requested(current.rq_job_id, current.request_digest):
                return self._terminal_cancel_without_job(current)
            observed = self._kubernetes.get(current.namespace, current.job_name)
            if observed.phase is JobPhase.ABSENT:
                if spec is None:
                    request_subpath, _fence_path = self._store.prepare_execution_files(
                        request, request.digest, current.fencing_generation
                    )
                    spec, digest = build_job_spec(
                        request,
                        self._config,
                        ownership_nonce=current.ownership_nonce,
                        request_digest=current.request_digest,
                        fencing_generation=current.fencing_generation,
                        request_subpath=request_subpath,
                    )
                    if digest != current.spec_digest:
                        raise KubernetesRenderError(
                            "weppcloudr_k8s_state_lost", "reconstructed Job spec mismatch"
                        )
                try:
                    if current.create_attempted_at is None:
                        attempted = replace(current, create_attempted_at=self._clock())
                        self._store.replace(current, attempted)
                        current = attempted
                    observed = self._kubernetes.create(current.namespace, spec)
                except CreateAmbiguous:
                    updated = replace(current, state=ReceiptState.CREATE_AMBIGUOUS)
                    self._store.replace(current, updated)
                    return updated
            return self._bind_and_reconcile(current, observed)

    def observe(self, rq_job_id: str, request_digest: str) -> ExecutionReceipt:
        receipt = self._require_receipt(rq_job_id, request_digest)
        return self._reconcile(receipt)

    def cancel(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]:
        self._store.persist_cancellation(rq_job_id, request_digest)
        with self._store.dispatch_lock(rq_job_id):
            receipt = self._store.get(rq_job_id)
            if receipt is None:
                return {
                    "rq_job_id": rq_job_id,
                    "request_digest": request_digest,
                    "cleanup_state": "complete",
                }
            if receipt.request_digest != request_digest:
                raise KubernetesRenderError(
                    "weppcloudr_k8s_state_lost", "cancellation digest mismatch"
                )
            if not receipt.cancellation_requested:
                updated = replace(
                    receipt,
                    cancellation_requested=True,
                    cancellation_requested_at=self._clock(),
                )
                self._store.replace(receipt, updated)
                receipt = updated
            if receipt.job_uid is None:
                observed = self._kubernetes.get(receipt.namespace, receipt.job_name)
                if observed.phase is JobPhase.ABSENT:
                    terminal = self._terminal_cancel_without_job(receipt)
                    return {**terminal.payload(), "cleanup_state": "complete"}
                receipt = self._bind_and_reconcile(receipt, observed)
            if receipt.state in {ReceiptState.TERMINAL_SUCCESS, ReceiptState.TERMINAL_FAILURE, ReceiptState.CLEANED}:
                return {**receipt.payload(), "cleanup_state": "complete"}
            assert receipt.job_uid is not None
            observed = self._kubernetes.get(receipt.namespace, receipt.job_name)
            if observed.phase is JobPhase.ABSENT:
                terminal = self._terminal_cancel_without_job(receipt)
                return {**terminal.payload(), "cleanup_state": "complete"}
            self._assert_observation(receipt, observed)
            self._kubernetes.delete_foreground(receipt.namespace, receipt.job_name, receipt.job_uid)
            updated = replace(
                receipt,
                cancellation_requested=True,
                cancellation_requested_at=receipt.cancellation_requested_at
                or self._clock(),
                cleanup_state="deleting",
            )
            self._store.replace(receipt, updated)
            return {**updated.payload(), "cleanup_state": "deleting"}

    def reap(self) -> list[ExecutionReceipt]:
        reconciled: list[ExecutionReceipt] = []
        for receipt in self._store.iter_reconcilable():
            try:
                try:
                    updated = self._reconcile(receipt)
                except (KubernetesRenderError, ReceiptConflict) as exc:
                    error = (
                        exc
                        if isinstance(exc, KubernetesRenderError)
                        else KubernetesRenderError(
                            "weppcloudr_k8s_state_lost", "receipt reconciliation conflict"
                        )
                    )
                    self._event_sink.publish_error(receipt, error)
                    continue
                self._event_sink.publish(updated)
                self._store.acknowledge_event(updated)
                reconciled.append(updated)
            except Exception:  # broad-except: isolate external delivery at batch boundary
                _LOGGER.exception(
                    "WEPPcloudR reaper event delivery failed for RQ job %s",
                    receipt.rq_job_id,
                )
        return reconciled

    def _reconcile(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        if receipt.state in {ReceiptState.TERMINAL_SUCCESS, ReceiptState.TERMINAL_FAILURE, ReceiptState.CLEANED}:
            return self._finalize_terminal(receipt)
        if (
            self._store.cancellation_requested(receipt.rq_job_id, receipt.request_digest)
            and not receipt.cancellation_requested
        ):
            updated = replace(
                receipt,
                cancellation_requested=True,
                cancellation_requested_at=self._clock(),
            )
            self._store.replace(receipt, updated)
            receipt = updated
        observed = self._kubernetes.get(receipt.namespace, receipt.job_name)
        if receipt.job_uid is None:
            if observed.phase is JobPhase.ABSENT:
                if receipt.state is ReceiptState.CREATE_AMBIGUOUS and (
                    self._clock() - (receipt.create_attempted_at or receipt.created_at)
                    < self._config.create_reconcile_grace_seconds
                ):
                    return receipt
                request = self._store.load_request(receipt.rq_job_id, receipt.request_digest)
                if not receipt.spec_digest:
                    receipt, _spec = self._ensure_spec(receipt, request)
                return self._dispatch_create(receipt, request)
            return self._bind_and_reconcile(receipt, observed)
        if observed.phase is JobPhase.ABSENT:
            if receipt.cleanup_state == "deleting" and receipt.error_code:
                return self._terminal_failure(
                    receipt, receipt.error_code, receipt.reason or "render cleanup complete"
                )
            if receipt.cancellation_requested or receipt.cleanup_state == "deleting":
                return self._terminal_cancel_without_job(receipt)
            return self._terminal_failure(
                receipt, "weppcloudr_k8s_state_lost", "UID-bound Job disappeared"
            )
        self._assert_observation(receipt, observed)
        if receipt.cancellation_requested and receipt.cleanup_state not in {
            "deleting",
            "cleanup_timeout",
        }:
            assert receipt.job_uid is not None
            self._kubernetes.delete_foreground(
                receipt.namespace, receipt.job_name, receipt.job_uid
            )
            updated = replace(receipt, cleanup_state="deleting")
            self._store.replace(receipt, updated)
            return updated
        return self._apply_observation(receipt, observed)

    def _bind_and_reconcile(
        self, receipt: ExecutionReceipt, observed: JobObservation
    ) -> ExecutionReceipt:
        if receipt.job_uid is not None:
            self._assert_observation(receipt, observed)
            return self._apply_observation(receipt, observed)
        self._assert_observation(receipt, observed, allow_unbound=True)
        if observed.uid is None:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "observed Job has no UID"
            )
        updated = replace(
            receipt,
            state=ReceiptState.ACTIVE,
            job_uid=observed.uid,
            job_created_at=receipt.job_created_at or self._clock(),
        )
        if observed.phase is JobPhase.RUNNING:
            updated = replace(updated, started_at=updated.started_at or self._clock())
        self._store.replace(receipt, updated)
        return self._apply_observation(updated, observed)

    def _apply_observation(
        self, receipt: ExecutionReceipt, observed: JobObservation
    ) -> ExecutionReceipt:
        now = self._clock()
        if receipt.cleanup_state in {
            "deleting",
            "cleanup_timeout",
        }:
            requested_at = receipt.cancellation_requested_at or now
            if now - requested_at >= self._config.cancellation_grace_seconds:
                if receipt.cleanup_state == "cleanup_timeout":
                    return receipt
                updated = replace(
                    receipt,
                    cleanup_state="cleanup_timeout",
                    cancellation_requested_at=requested_at,
                )
                self._store.replace(receipt, updated)
                return updated
            return receipt
        if observed.phase is JobPhase.PENDING:
            pending_since = receipt.job_created_at or receipt.create_attempted_at or receipt.created_at
            if now - pending_since >= self._config.pending_timeout_seconds:
                return self._begin_failure_cleanup(
                    receipt,
                    "weppcloudr_k8s_unschedulable",
                    "render did not start before its deadline",
                )
            return receipt
        if observed.phase is JobPhase.RUNNING:
            if receipt.started_at is None:
                updated = replace(receipt, started_at=now)
                self._store.replace(receipt, updated)
                return updated
            return receipt
        if observed.phase is JobPhase.SUSPENDED:
            return self._begin_failure_cleanup(
                receipt, "weppcloudr_k8s_unschedulable", "render Job was suspended"
            )
        if observed.phase is JobPhase.DELETING:
            if not receipt.cancellation_requested:
                return self._begin_failure_cleanup(
                    receipt,
                    "weppcloudr_k8s_state_lost",
                    "render Job entered deletion without cancellation intent",
                )
            return receipt
        if observed.phase is JobPhase.SUCCEEDED:
            if (
                not observed.artifact_path
                or not observed.artifact_sha256
                or not observed.artifact_size
                or observed.result_rq_job_id != receipt.rq_job_id
                or observed.result_request_digest != receipt.request_digest
                or observed.result_fencing_generation != receipt.fencing_generation
            ):
                return self._terminal_failure(
                    receipt,
                    "weppcloudr_artifact_invalid",
                    "terminal artifact metadata is missing",
                    stdout_ref=observed.stdout_ref,
                    stderr_ref=observed.stderr_ref,
                )
            updated = replace(
                receipt,
                state=ReceiptState.TERMINAL_SUCCESS,
                terminal_state=ReceiptState.TERMINAL_SUCCESS,
                artifact_path=observed.artifact_path,
                artifact_sha256=observed.artifact_sha256,
                artifact_size=observed.artifact_size,
                ended_at=now,
                stdout_ref=observed.stdout_ref,
                stderr_ref=observed.stderr_ref,
            )
            self._store.replace(receipt, updated)
            return self._finalize_terminal(updated)
        return self._terminal_failure(
            receipt,
            _failure_code(observed),
            observed.reason or "render failed",
            stdout_ref=observed.stdout_ref,
            stderr_ref=observed.stderr_ref,
        )

    def _begin_failure_cleanup(
        self, receipt: ExecutionReceipt, code: str, reason: str
    ) -> ExecutionReceipt:
        if receipt.job_uid is None:
            return self._terminal_failure(receipt, code, reason)
        self._kubernetes.delete_foreground(
            receipt.namespace, receipt.job_name, receipt.job_uid
        )
        updated = replace(
            receipt,
            error_code=code,
            reason=reason,
            cleanup_state="deleting",
            cancellation_requested_at=self._clock(),
        )
        self._store.replace(receipt, updated)
        return updated

    def _terminal_failure(
        self,
        receipt: ExecutionReceipt,
        code: str,
        reason: str,
        *,
        stdout_ref: str | None = None,
        stderr_ref: str | None = None,
    ) -> ExecutionReceipt:
        updated = replace(
            receipt,
            state=ReceiptState.TERMINAL_FAILURE,
            terminal_state=ReceiptState.TERMINAL_FAILURE,
            error_code=code,
            reason=reason,
            ended_at=self._clock(),
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
        )
        self._store.release_permit(receipt.rq_job_id, receipt.ownership_nonce)
        self._store.replace(receipt, updated)
        return self._finalize_terminal(updated)

    def _terminal_cancel_without_job(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        updated = replace(
            receipt,
            state=ReceiptState.CLEANED,
            terminal_state=ReceiptState.TERMINAL_FAILURE,
            cancellation_requested=True,
            cleanup_state="complete",
            error_code="weppcloudr_k8s_cancelled",
            reason="render cancelled",
            ended_at=self._clock(),
            never_created=receipt.job_uid is None,
        )
        self._store.release_permit(receipt.rq_job_id, receipt.ownership_nonce)
        self._store.cleanup_execution_files(updated)
        self._store.replace(receipt, updated)
        return updated

    def _finalize_terminal(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        self._store.release_permit(receipt.rq_job_id, receipt.ownership_nonce)
        if receipt.state is ReceiptState.CLEANED:
            return receipt
        if receipt.job_uid is None:
            self._store.cleanup_execution_files(receipt)
            cleaned = replace(receipt, state=ReceiptState.CLEANED)
            self._store.replace(receipt, cleaned)
            return cleaned
        observed = self._kubernetes.get(receipt.namespace, receipt.job_name)
        if observed.phase is JobPhase.ABSENT:
            self._store.cleanup_execution_files(receipt)
            cleaned = replace(receipt, state=ReceiptState.CLEANED, cleanup_state="complete")
            self._store.replace(receipt, cleaned)
            return cleaned
        self._assert_observation(receipt, observed)
        if receipt.cleanup_state == "ttl-active":
            return receipt
        self._kubernetes.patch_completed_ttl(
            receipt.namespace,
            receipt.job_name,
            receipt.job_uid,
            self._config.completed_ttl_seconds,
        )
        collecting = replace(receipt, cleanup_state="ttl-active")
        self._store.replace(receipt, collecting)
        return collecting

    def _assert_request(self, receipt: ExecutionReceipt, request: RenderRequest) -> None:
        expected = (
            request.digest,
            request.renderer_image_digest,
            request.deployment_revision,
            deterministic_job_name(request.rq_job_id),
        )
        actual = (
            receipt.request_digest,
            receipt.renderer_image_digest,
            receipt.deployment_revision,
            receipt.job_name,
        )
        if (
            actual != expected
            or receipt.backend != "kubernetes-job"
            or receipt.namespace != self._config.namespace
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "durable execution snapshot mismatch"
            )

    @staticmethod
    def _assert_observation(
        receipt: ExecutionReceipt,
        observed: JobObservation,
        *,
        allow_unbound: bool = False,
    ) -> None:
        if (
            observed.ownership_nonce != receipt.ownership_nonce
            or observed.request_digest != receipt.request_digest
            or observed.spec_digest != receipt.spec_digest
            or observed.renderer_image_digest != receipt.renderer_image_digest
            or observed.deployment_revision != receipt.deployment_revision
        ):
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "Kubernetes ownership marker mismatch"
            )
        if not allow_unbound and observed.uid != receipt.job_uid:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "Kubernetes Job UID mismatch"
            )

    def _require_receipt(self, rq_job_id: str, request_digest: str) -> ExecutionReceipt:
        receipt = self._store.get(rq_job_id)
        if receipt is None or receipt.request_digest != request_digest:
            raise KubernetesRenderError(
                "weppcloudr_k8s_state_lost", "durable render receipt is unavailable"
            )
        return receipt


def _failure_code(observed: JobObservation) -> str:
    reason = (observed.reason or "").lower()
    if "oomkilled" in reason:
        return "weppcloudr_k8s_oom_killed"
    if "imagepull" in reason or "errimagepull" in reason:
        return "weppcloudr_k8s_image_pull_failed"
    if "mount" in reason or "volume" in reason:
        return "weppcloudr_k8s_volume_mount_failed"
    if "evict" in reason:
        return "weppcloudr_k8s_evicted"
    if "deadline" in reason:
        return "weppcloudr_k8s_deadline_exceeded"
    if "unschedul" in reason:
        return "weppcloudr_k8s_unschedulable"
    return "weppcloudr_renderer_failed"
