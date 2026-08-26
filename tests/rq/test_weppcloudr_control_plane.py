from __future__ import annotations

from dataclasses import replace
import os
import secrets
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from wepppy.rq.weppcloudr_backends import KubernetesRenderError, RenderRequest
from wepppy.rq.weppcloudr_control_plane import (
    ControlPlaneConfig,
    CreateAmbiguous,
    ExecutionReceipt,
    JobObservation,
    JobPhase,
    ReceiptConflict,
    ReceiptState,
    RenderControlPlane,
    build_job_spec,
)


pytestmark = pytest.mark.unit
IMAGE = "sha256:" + "a" * 64
REPO_ROOT = Path(__file__).resolve().parents[2]


def _request(job_id: str = "job-1") -> RenderRequest:
    return RenderRequest(
        schema_version=1,
        rq_job_id=job_id,
        runid="run-1",
        config="cfg",
        run_root="/wc1/runs/ru/run-1",
        active_root="/wc1/runs/ru/run-1/_pups/shared",
        skip_cache=True,
        correlation_id=job_id,
        deployment_revision="abc123",
        renderer_image_digest=IMAGE,
    )


def _config(maximum: int = 2) -> ControlPlaneConfig:
    return ControlPlaneConfig(
        namespace="weppcloudr-render",
        renderer_image_digest=IMAGE,
        renderer_image_repository="ghcr.io/open-wepp/weppcloudr",
        run_pvc="wc1-rwx",
        geodata_pvc="geodata-ro",
        service_account="weppcloudr-renderer",
        max_active_renders=maximum,
    )


class _Store:
    def __init__(self) -> None:
        self.receipts: dict[str, ExecutionReceipt] = {}
        self.permits: dict[str, str] = {}
        self.cancellations: set[tuple[str, str]] = set()
        self.fence = 0
        self.requests: dict[str, RenderRequest] = {}
        self.lock = threading.RLock()
        self.cleaned_files: list[str] = []
        self.cleanup_failures = 0
        self.delivered: set[tuple[str, str, ReceiptState, str | None]] = set()

    def get(self, rq_job_id: str):
        return self.receipts.get(rq_job_id)

    def replace(self, expected: ExecutionReceipt, updated: ExecutionReceipt):
        if self.receipts.get(expected.rq_job_id) != expected:
            raise ReceiptConflict
        self.receipts[expected.rq_job_id] = updated

    @staticmethod
    def _event_key(receipt: ExecutionReceipt):
        return (
            receipt.rq_job_id,
            receipt.request_digest,
            receipt.state,
            receipt.cleanup_state,
        )

    def acknowledge_event(self, receipt: ExecutionReceipt):
        self.delivered.add(self._event_key(receipt))

    def acquire_permit(self, rq_job_id: str, nonce: str, maximum: int):
        if rq_job_id in self.permits:
            return self.permits[rq_job_id] == nonce
        if len(self.permits) >= maximum:
            return False
        self.permits[rq_job_id] = nonce
        return True

    def release_permit(self, rq_job_id: str, nonce: str):
        if self.permits.get(rq_job_id) == nonce:
            del self.permits[rq_job_id]

    def persist_cancellation(self, rq_job_id: str, request_digest: str):
        self.cancellations.add((rq_job_id, request_digest))

    def cancellation_requested(self, rq_job_id: str, request_digest: str):
        return (rq_job_id, request_digest) in self.cancellations

    def prepare_execution_files(self, request, request_digest, fencing_generation):
        assert request_digest == request.digest
        assert fencing_generation == self.fence
        return f".weppcloudr/requests/{request.rq_job_id}.json", "fence"

    def iter_reconcilable(self):
        return [
            receipt
            for receipt in self.receipts.values()
            if receipt.state is not ReceiptState.CLEANED
            or self._event_key(receipt) not in self.delivered
        ]

    def initialize(self, request, namespace, job_name):
        with self.lock:
            existing = self.receipts.get(request.rq_job_id)
            if existing is not None:
                return existing
            self.fence += 1
            self.requests[request.rq_job_id] = request
            receipt = ExecutionReceipt(
                rq_job_id=request.rq_job_id,
                request_digest=request.digest,
                state=ReceiptState.CREATING,
                backend="kubernetes-job",
                namespace=namespace,
                job_name=job_name,
                job_uid=None,
                ownership_nonce=secrets.token_hex(32),
                spec_digest="",
                renderer_image_digest=request.renderer_image_digest,
                deployment_revision=request.deployment_revision,
                fencing_generation=self.fence,
                created_at=1000.0,
            )
            self.receipts[request.rq_job_id] = receipt
            return receipt

    def load_request(self, rq_job_id, request_digest):
        request = self.requests[rq_job_id]
        assert request.digest == request_digest
        return request

    def dispatch_lock(self, _rq_job_id):
        return self.lock

    def cleanup_execution_files(self, receipt):
        if self.cleanup_failures:
            self.cleanup_failures -= 1
            raise OSError("cleanup unavailable")
        self.cleaned_files.append(receipt.rq_job_id)


class _Kubernetes:
    def __init__(self) -> None:
        self.observation = JobObservation(JobPhase.ABSENT)
        self.created = 0
        self.deleted = 0
        self.ttls: list[int] = []
        self.ambiguous = False

    def get(self, _namespace, _name):
        return self.observation

    def create(self, _namespace, spec):
        self.created += 1
        if self.ambiguous:
            raise CreateAmbiguous
        annotations = spec["metadata"]["annotations"]
        self.observation = JobObservation(
            JobPhase.RUNNING,
            uid="uid-1",
            ownership_nonce=annotations["weppcloud.org/ownership-nonce"],
            request_digest=annotations["weppcloud.org/request-digest"],
            spec_digest=annotations["weppcloud.org/spec-digest"],
            renderer_image_digest=annotations["weppcloud.org/renderer-image-digest"],
            deployment_revision=annotations["weppcloud.org/deployment-revision"],
        )
        return self.observation

    def delete_foreground(self, _namespace, _name, uid):
        assert uid == self.observation.uid
        self.deleted += 1

    def patch_completed_ttl(self, _namespace, _name, _uid, ttl_seconds):
        self.ttls.append(ttl_seconds)


class _EventSink:
    def __init__(self) -> None:
        self.receipts: list[ExecutionReceipt] = []
        self.errors: list[tuple[ExecutionReceipt, KubernetesRenderError]] = []

    def publish(self, receipt: ExecutionReceipt) -> None:
        self.receipts.append(receipt)

    def publish_error(
        self, receipt: ExecutionReceipt, error: KubernetesRenderError
    ) -> None:
        self.errors.append((receipt, error))


def _controller(maximum: int = 2, now: list[float] | None = None):
    store = _Store()
    kubernetes = _Kubernetes()
    current_time = now if now is not None else [1000.0]
    return (
        RenderControlPlane(
            store,
            kubernetes,
            _config(maximum),
            event_sink=_EventSink(),
            clock=lambda: current_time[0],
        ),
        store,
        kubernetes,
    )


def test_job_spec_is_fixed_hardened_and_uses_root_squash_safe_mount() -> None:
    request = _request()

    spec, digest = build_job_spec(
        request,
        _config(),
        ownership_nonce="b" * 64,
        request_digest=request.digest,
        fencing_generation=3,
        request_subpath=".weppcloudr/requests/job-1.json",
    )

    job = spec["spec"]
    pod = job["template"]["spec"]
    container = pod["containers"][0]
    assert job["backoffLimit"] == 0
    assert "ttlSecondsAfterFinished" not in job
    assert pod["automountServiceAccountToken"] is False
    assert pod["securityContext"] == {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "runAsGroup": 993,
    }
    assert "fsGroup" not in pod["securityContext"]
    assert container["image"] == f"ghcr.io/open-wepp/weppcloudr@{IMAGE}"
    assert container["workingDir"] == "/tmp"
    assert container["env"] == [
        {
            "name": "TEMPLATE_ROOT",
            "value": "/srv/weppcloudr/templates/scripts/users/chinmay",
        },
        {
            "name": "DEVAL_TEMPLATE",
            "value": "/srv/weppcloudr/templates/scripts/users/chinmay/new_report.Rmd",
        },
    ]
    assert container["command"] == ["/bin/sh", "-c"]
    assert container["args"] == [
        (
            'cd -- "$1" && exec Rscript '
            '/srv/weppcloudr/render-request-v1.R "$2" "$3" "$4"'
        ),
        "weppcloudr-entrypoint",
        request.run_root,
        "/run/weppcloudr/request.json",
        request.digest,
        "3",
    ]
    assert container["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    assert container["args"][-1] == "3"
    assert container["volumeMounts"][0] == {
        "name": "run",
        "mountPath": "/wc1",
    }
    assert all("subPath" not in mount for mount in container["volumeMounts"])
    assert [volume["name"] for volume in pod["volumes"]].count("run") == 1
    request_volume = next(
        volume for volume in pod["volumes"] if volume["name"] == "request"
    )
    assert request_volume == {"name": "request", "emptyDir": {"sizeLimit": "1Mi"}}
    init = pod["initContainers"][0]
    assert init["image"] == container["image"]
    assert init["command"] == ["cp"]
    assert init["args"] == [
        "/wc1/.weppcloudr/requests/job-1.json",
        "/request/request.json",
    ]
    assert init["workingDir"] == "/tmp"
    assert init["securityContext"] == container["securityContext"]
    assert all("subPath" not in mount for mount in init["volumeMounts"])
    assert len(digest) == 64


def test_job_spec_hashes_max_length_rq_id_and_rejects_hostile_request_subpath() -> None:
    request = _request("a" * 64)
    spec, _digest = build_job_spec(
        request,
        _config(),
        ownership_nonce="b" * 64,
        request_digest=request.digest,
        fencing_generation=1,
        request_subpath=".weppcloudr/requests/request.json",
    )
    labels = spec["metadata"]["labels"]
    assert len(labels["weppcloud.org/rq-id-hash"]) == 32
    assert request.rq_job_id not in labels.values()

    with pytest.raises(KubernetesRenderError, match="request PVC subPath"):
        build_job_spec(
            request,
            _config(),
            ownership_nonce="b" * 64,
            request_digest=request.digest,
            fencing_generation=1,
            request_subpath="../escape",
        )


@pytest.mark.parametrize(
    ("run_root", "active_root"),
    [
        ("/etc", "/etc"),
        ("/wc1", "/wc1"),
        ("/wc1/runs/ru/run-1", "/wc1/runs/other"),
    ],
)
def test_job_spec_rejects_unapproved_or_escaping_run_paths(
    run_root: str, active_root: str
) -> None:
    request = replace(_request(), run_root=run_root, active_root=active_root)

    with pytest.raises(KubernetesRenderError, match="root|mapping"):
        build_job_spec(
            request,
            _config(),
            ownership_nonce="b" * 64,
            request_digest=request.digest,
            fencing_generation=1,
            request_subpath=".weppcloudr/requests/request.json",
        )


def test_job_spec_validates_explicit_pvc_mapping_without_kubelet_subpaths() -> None:
    request = _request()
    spec, _digest = build_job_spec(
        request,
        _config(),
        ownership_nonce="b" * 64,
        request_digest=request.digest,
        fencing_generation=1,
        request_subpath=".weppcloudr/requests/request.json",
    )

    container = spec["spec"]["template"]["spec"]["containers"][0]
    assert container["workingDir"] == "/tmp"
    assert container["volumeMounts"][0] == {"name": "run", "mountPath": "/wc1"}


def test_submit_creates_once_binds_uid_and_reuses_receipt() -> None:
    controller, store, kubernetes = _controller()
    request = _request()

    first = controller.submit(request)
    second = controller.submit(request)

    assert first.state is ReceiptState.ACTIVE
    assert first.job_uid == "uid-1"
    assert second == first
    assert kubernetes.created == 1
    assert len(store.permits) == 1


def test_concurrent_same_id_submit_creates_one_job() -> None:
    controller, store, kubernetes = _controller()
    request = _request()
    barrier = threading.Barrier(2)

    def submit() -> ExecutionReceipt:
        barrier.wait()
        return controller.submit(request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _index: submit(), range(2)))

    assert {receipt.job_uid for receipt in receipts} == {"uid-1"}
    assert kubernetes.created == 1
    assert len(store.receipts) == 1


def test_pending_timeout_deletes_before_releasing_permit() -> None:
    now = [1000.0]
    controller, store, kubernetes = _controller(now=now)
    receipt = controller.submit(_request())
    kubernetes.observation = replace(kubernetes.observation, phase=JobPhase.PENDING)
    now[0] += 121.0

    deleting = controller.observe(receipt.rq_job_id, receipt.request_digest)

    assert deleting.state is ReceiptState.ACTIVE
    assert deleting.cleanup_state == "deleting"
    assert deleting.error_code == "weppcloudr_k8s_unschedulable"
    assert len(store.permits) == 1
    assert kubernetes.deleted == 1

    kubernetes.observation = JobObservation(JobPhase.ABSENT)
    terminal = controller.observe(receipt.rq_job_id, receipt.request_digest)
    assert terminal.state is ReceiptState.CLEANED
    assert store.permits == {}


def test_ambiguous_create_is_durable_and_does_not_eagerly_duplicate() -> None:
    controller, store, kubernetes = _controller()
    kubernetes.ambiguous = True

    receipt = controller.submit(_request())

    assert receipt.state is ReceiptState.CREATE_AMBIGUOUS
    assert receipt.job_uid is None
    assert kubernetes.created == 1
    assert len(store.permits) == 1

    kubernetes.ambiguous = False
    waiting = controller.observe(receipt.rq_job_id, receipt.request_digest)

    assert waiting.state is ReceiptState.CREATE_AMBIGUOUS
    assert kubernetes.created == 1

    store.receipts[receipt.rq_job_id] = replace(waiting, create_attempted_at=900.0)
    recovered = controller.observe(receipt.rq_job_id, receipt.request_digest)

    assert recovered.state is ReceiptState.ACTIVE
    assert recovered.job_uid == "uid-1"
    assert kubernetes.created == 2


def test_crash_after_atomic_receipt_initialization_recovers_identical_create() -> None:
    controller, store, kubernetes = _controller()
    request = _request()
    initialized = store.initialize(
        request, "weppcloudr-render", "weppcloudr-026ab639c21df8aa80e5"
    )
    assert initialized.spec_digest == ""

    recovered = controller.submit(request)

    assert recovered.state is ReceiptState.ACTIVE
    assert recovered.fencing_generation == initialized.fencing_generation
    assert kubernetes.created == 1


def test_uid_and_snapshot_mismatch_fail_closed() -> None:
    controller, _store, kubernetes = _controller()
    receipt = controller.submit(_request())
    kubernetes.observation = replace(kubernetes.observation, uid="replacement")

    with pytest.raises(KubernetesRenderError, match="UID mismatch"):
        controller.observe(receipt.rq_job_id, receipt.request_digest)


def test_success_collects_artifact_releases_permit_then_activates_ttl() -> None:
    controller, store, kubernetes = _controller()
    receipt = controller.submit(_request())
    kubernetes.observation = replace(
        kubernetes.observation,
        phase=JobPhase.SUCCEEDED,
        artifact_path="/wc1/runs/ru/run-1/_pups/shared/export/WEPPcloudR/deval_run-1.htm",
        artifact_sha256="e" * 64,
        artifact_size=42,
        result_rq_job_id=receipt.rq_job_id,
        result_request_digest=receipt.request_digest,
        result_fencing_generation=receipt.fencing_generation,
    )

    terminal = controller.observe(receipt.rq_job_id, receipt.request_digest)

    assert terminal.state is ReceiptState.TERMINAL_SUCCESS
    assert terminal.cleanup_state == "ttl-active"
    assert terminal.terminal_state == ReceiptState.TERMINAL_SUCCESS
    assert terminal.fencing_generation == 1
    assert store.permits == {}
    assert kubernetes.ttls == [1200]


def test_uid_bound_absence_never_recreates_job() -> None:
    controller, store, kubernetes = _controller()
    receipt = controller.submit(_request())
    kubernetes.observation = JobObservation(JobPhase.ABSENT)

    terminal = controller.observe(receipt.rq_job_id, receipt.request_digest)

    assert terminal.error_code == "weppcloudr_k8s_state_lost"
    assert kubernetes.created == 1
    assert store.permits == {}


def test_cancellation_intent_before_submit_prevents_create() -> None:
    controller, store, kubernetes = _controller()
    request = _request()
    store.persist_cancellation(request.rq_job_id, request.digest)

    receipt = controller.submit(request)

    assert receipt.error_code == "weppcloudr_k8s_cancelled"
    assert kubernetes.created == 0
    assert store.permits == {}


def test_cancel_active_job_waits_for_foreground_absence() -> None:
    controller, _store, kubernetes = _controller()
    receipt = controller.submit(_request())

    deleting = controller.cancel(receipt.rq_job_id, receipt.request_digest)
    kubernetes.observation = JobObservation(JobPhase.ABSENT)
    complete = controller.cancel(receipt.rq_job_id, receipt.request_digest)

    assert deleting["cleanup_state"] == "deleting"
    assert complete["cleanup_state"] == "complete"
    assert kubernetes.deleted == 1


def test_reaper_applies_durable_cancellation_and_publishes_state() -> None:
    controller, store, kubernetes = _controller()
    receipt = controller.submit(_request())
    store.persist_cancellation(receipt.rq_job_id, receipt.request_digest)
    sink = controller._event_sink

    reconciled = controller.reap()

    assert reconciled[0].cancellation_requested is True
    assert reconciled[0].cleanup_state == "deleting"
    assert kubernetes.deleted == 1
    assert sink.receipts == reconciled


def test_reaper_cancellation_timeout_retains_permit_then_absence_emits_once() -> None:
    now = [1000.0]
    controller, store, kubernetes = _controller(now=now)
    receipt = controller.submit(_request())
    store.persist_cancellation(receipt.rq_job_id, receipt.request_digest)

    controller.reap()
    now[0] += 121.0
    timed_out = controller.reap()[0]

    assert timed_out.cleanup_state == "cleanup_timeout"
    assert receipt.rq_job_id in store.permits

    kubernetes.observation = JobObservation(JobPhase.ABSENT)
    completed = controller.reap()[0]

    assert completed.state is ReceiptState.CLEANED
    assert completed.cleanup_state == "complete"
    assert completed.error_code == "weppcloudr_k8s_cancelled"
    assert receipt.rq_job_id not in store.permits
    assert store._event_key(completed) in store.delivered
    assert controller.reap() == []


def test_cancel_absence_retries_cleanup_before_persisting_cleaned() -> None:
    controller, store, kubernetes = _controller()
    receipt = controller.submit(_request())
    store.persist_cancellation(receipt.rq_job_id, receipt.request_digest)
    controller.reap()
    kubernetes.observation = JobObservation(JobPhase.ABSENT)
    store.cleanup_failures = 1

    assert controller.reap() == []
    after_failure = store.get(receipt.rq_job_id)
    assert after_failure is not None
    assert after_failure.state is ReceiptState.ACTIVE
    assert after_failure.cleanup_state == "deleting"

    recovered = controller.reap()[0]

    assert recovered.state is ReceiptState.CLEANED
    assert store.cleaned_files == [receipt.rq_job_id]


def test_hard_permit_cap_rejects_second_active_render() -> None:
    controller, _store, kubernetes = _controller(maximum=1)
    controller.submit(_request("job-1"))
    kubernetes.observation = JobObservation(JobPhase.ABSENT)

    with pytest.raises(KubernetesRenderError, match="concurrency limit"):
        controller.submit(_request("job-2"))


def test_reaper_reconciles_orphaned_terminal_job() -> None:
    controller, _store, kubernetes = _controller()
    controller.submit(_request())
    kubernetes.observation = replace(
        kubernetes.observation,
        phase=JobPhase.FAILED,
        reason="OOMKilled",
        stdout_ref="run://logs/stdout",
        stderr_ref="run://logs/stderr",
    )

    receipts = controller.reap()

    assert receipts[0].error_code == "weppcloudr_k8s_oom_killed"
    assert receipts[0].stdout_ref == "run://logs/stdout"
    assert receipts[0].stderr_ref == "run://logs/stderr"


def test_reaper_repairs_terminal_permit_and_ttl_after_crash() -> None:
    controller, store, kubernetes = _controller()
    active = controller.submit(_request())
    terminal = replace(
        active,
        state=ReceiptState.TERMINAL_SUCCESS,
        terminal_state=ReceiptState.TERMINAL_SUCCESS,
        artifact_path="/artifact",
        artifact_sha256="f" * 64,
        artifact_size=1,
    )
    store.replace(active, terminal)

    receipts = controller.reap()

    assert receipts[0].state is ReceiptState.TERMINAL_SUCCESS
    assert receipts[0].cleanup_state == "ttl-active"
    assert store.permits == {}
    assert kubernetes.ttls == [1200]


def test_reaper_event_delivery_failure_does_not_starve_later_receipts() -> None:
    class _FailFirstSink(_EventSink):
        def __init__(self) -> None:
            super().__init__()
            self.attempts: list[str] = []

        def _deliver(self, receipt: ExecutionReceipt) -> None:
            self.attempts.append(receipt.rq_job_id)
            if len(self.attempts) == 1:
                raise RuntimeError("event transport unavailable")

        def publish(self, receipt: ExecutionReceipt) -> None:
            self._deliver(receipt)
            self.receipts.append(receipt)

        def publish_error(
            self, receipt: ExecutionReceipt, error: KubernetesRenderError
        ) -> None:
            self._deliver(receipt)
            self.errors.append((receipt, error))

    controller, store, kubernetes = _controller()
    first = controller.submit(_request("job-1"))
    kubernetes.observation = JobObservation(JobPhase.ABSENT)
    second = controller.submit(_request("job-2"))
    for receipt in (first, second):
        store.replace(
            receipt,
            replace(
                receipt,
                state=ReceiptState.TERMINAL_FAILURE,
                terminal_state=ReceiptState.TERMINAL_FAILURE,
                error_code="weppcloudr_k8s_failed",
                job_uid=None,
            ),
        )
    sink = _FailFirstSink()
    controller._event_sink = sink

    reconciled = controller.reap()

    assert sink.attempts == ["job-1", "job-2"]
    assert [receipt.rq_job_id for receipt in sink.receipts] == ["job-2"]
    assert [receipt.rq_job_id for receipt in reconciled] == ["job-2"]

    retried = controller.reap()

    assert sink.attempts == ["job-1", "job-2", "job-1"]
    assert [receipt.rq_job_id for receipt in retried] == ["job-1"]


def test_fenced_publication_rejects_stale_generation(tmp_path: Path) -> None:
    active = tmp_path / "run-1"
    output = active / "export" / "WEPPcloudR"
    locks = active / "_locks" / "weppcloudr"
    output.mkdir(parents=True)
    locks.mkdir(parents=True)
    fence = locks / "deval_run-1.fence"
    lock = locks / "deval_run-1.fence.publish.lock"
    old = Path("/tmp") / f".deval_run-1.{tmp_path.name}.tmp.htm"
    final = output / "deval_run-1.htm"
    fence.write_text("2\n", encoding="utf-8")
    lock.write_text("", encoding="utf-8")
    old.write_text("old", encoding="utf-8")
    final.write_text("new", encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "weppcloudR/publish_fenced.py"),
            str(active),
            "run-1",
            "1",
            old.name,
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "WEPPCLOUDR_RUN_ROOTS": str(tmp_path)},
    )

    assert result.returncode != 0
    assert final.read_text(encoding="utf-8") == "new"
    old.unlink(missing_ok=True)
