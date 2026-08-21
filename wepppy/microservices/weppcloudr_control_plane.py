"""Deployable internal control plane for one-shot WEPPcloudR Kubernetes Jobs."""

from __future__ import annotations

import fcntl
import hmac
import json
import logging
import os
import secrets
import stat
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Mapping
from urllib.parse import quote

import redis
import requests
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
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
)


_LOGGER = logging.getLogger(__name__)
_PREFIX = "weppcloudr:control-plane:v1"
_LABEL_NAME = "app.kubernetes.io/name"
_LABEL_VALUE = "weppcloudr-render"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}.")
    return value


def _read_protected_file(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Protected file is unavailable: {path}")
    mode = path.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError(f"Protected file is writable by group/other: {path}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Protected file is empty: {path}")
    return value


def _receipt_from_json(raw: str | bytes) -> ExecutionReceipt:
    payload = json.loads(raw)
    payload["state"] = ReceiptState(payload["state"])
    return ExecutionReceipt(**payload)


class RedisReceiptStore:
    """Redis durability plus descriptor-safe request/fence files on the run PVC."""

    def __init__(self, connection: redis.Redis, *, pvc_root: Path = Path("/wc1")) -> None:
        self._redis = connection
        self._pvc_root = pvc_root.resolve(strict=True)

    @staticmethod
    def _receipt_key(rq_job_id: str) -> str:
        return f"{_PREFIX}:receipt:{rq_job_id}"

    @staticmethod
    def _request_key(rq_job_id: str) -> str:
        return f"{_PREFIX}:request:{rq_job_id}"

    @staticmethod
    def _cancel_key(rq_job_id: str) -> str:
        return f"{_PREFIX}:cancel:{rq_job_id}"

    def get(self, rq_job_id: str) -> ExecutionReceipt | None:
        raw = self._redis.get(self._receipt_key(rq_job_id))
        return _receipt_from_json(raw) if raw is not None else None

    def replace(self, expected: ExecutionReceipt, updated: ExecutionReceipt) -> None:
        key = self._receipt_key(expected.rq_job_id)
        expected_raw = json.dumps(asdict(expected), sort_keys=True, separators=(",", ":"))
        updated_raw = json.dumps(asdict(updated), sort_keys=True, separators=(",", ":"))
        script = """
        local current = redis.call('GET', KEYS[1])
        if current ~= ARGV[1] then return 0 end
        redis.call('SET', KEYS[1], ARGV[2])
        return 1
        """
        if int(self._redis.eval(script, 1, key, expected_raw, updated_raw)) != 1:
            raise ReceiptConflict("receipt compare-and-swap failed")

    def acquire_permit(self, rq_job_id: str, nonce: str, maximum: int) -> bool:
        key = f"{_PREFIX}:permits"
        member = f"{rq_job_id}:{nonce}"
        script = """
        if redis.call('SISMEMBER', KEYS[1], ARGV[1]) == 1 then return 1 end
        if redis.call('SCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
        redis.call('SADD', KEYS[1], ARGV[1])
        return 1
        """
        return int(self._redis.eval(script, 1, key, member, maximum)) == 1

    def release_permit(self, rq_job_id: str, nonce: str) -> None:
        self._redis.srem(f"{_PREFIX}:permits", f"{rq_job_id}:{nonce}")

    def persist_cancellation(self, rq_job_id: str, request_digest: str) -> None:
        self._redis.set(self._cancel_key(rq_job_id), request_digest)

    def cancellation_requested(self, rq_job_id: str, request_digest: str) -> bool:
        raw = self._redis.get(self._cancel_key(rq_job_id))
        return raw is not None and raw.decode() == request_digest

    def initialize(
        self, request: RenderRequest, namespace: str, job_name: str
    ) -> ExecutionReceipt:
        with self._publish_lock(request.active_root, request.runid) as fence_dir:
            existing = self.get(request.rq_job_id)
            if existing is not None:
                return existing
            fence_path = fence_dir / f"deval_{request.runid}.fence"
            generation = 1
            if fence_path.exists():
                if fence_path.is_symlink() or not fence_path.is_file():
                    raise KubernetesRenderError(
                        "weppcloudr_k8s_state_lost", "unsafe fencing record"
                    )
                generation = int(fence_path.read_text(encoding="ascii").strip() or "0") + 1
            self._atomic_write(fence_path, f"{generation}\n".encode("ascii"), 0o660)
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
                fencing_generation=generation,
                created_at=time.time(),
            )
            raw = json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":"))
            # Store the immutable request first. A crash can leave an inert
            # request record, but never a receipt that cannot be reconstructed.
            self._redis.set(self._request_key(request.rq_job_id), request.to_json())
            if not self._redis.set(self._receipt_key(request.rq_job_id), raw, nx=True):
                existing = self.get(request.rq_job_id)
                if existing is None:
                    raise ReceiptConflict("receipt initialization raced")
                return existing
            return receipt

    def prepare_execution_files(
        self, request: RenderRequest, request_digest: str, fencing_generation: int
    ) -> tuple[str, str]:
        active = self._validated_active(request.active_root)
        request_dir = active / "_requests" / "weppcloudr"
        request_dir.mkdir(mode=0o770, parents=True, exist_ok=True)
        request_path = request_dir / f"{request.rq_job_id}.{request_digest}.json"
        self._atomic_write(request_path, request.to_json().encode("utf-8"), 0o440)
        fence_path = active / "_locks" / "weppcloudr" / f"deval_{request.runid}.fence"
        if int(fence_path.read_text(encoding="ascii").strip()) != fencing_generation:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "fence changed")
        return (
            str(request_path.relative_to(self._pvc_root)),
            str(fence_path.relative_to(self._pvc_root)),
        )

    def load_request(self, rq_job_id: str, request_digest: str) -> RenderRequest:
        raw = self._redis.get(self._request_key(rq_job_id))
        if raw is None:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "request missing")
        request = RenderRequest(**json.loads(raw))
        if request.digest != request_digest:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "request digest mismatch")
        return request

    @contextmanager
    def dispatch_lock(self, rq_job_id: str) -> Iterator[None]:
        key = f"{_PREFIX}:dispatch:{rq_job_id}"
        token = secrets.token_hex(16)
        deadline = time.monotonic() + 15
        while not self._redis.set(key, token, nx=True, px=30_000):
            if time.monotonic() >= deadline:
                raise ReceiptConflict("dispatch lock timeout")
            time.sleep(0.05)
        try:
            yield
        finally:
            script = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0"
            self._redis.eval(script, 1, key, token)

    def cleanup_execution_files(self, receipt: ExecutionReceipt) -> None:
        try:
            request = self.load_request(receipt.rq_job_id, receipt.request_digest)
        except KubernetesRenderError:
            return
        active = self._validated_active(request.active_root)
        path = active / "_requests" / "weppcloudr" / f"{receipt.rq_job_id}.{receipt.request_digest}.json"
        if path.is_symlink():
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "unsafe request path")
        path.unlink(missing_ok=True)

    def iter_reconcilable(self) -> Iterator[ExecutionReceipt]:
        for key in self._redis.scan_iter(f"{_PREFIX}:receipt:*"):
            raw = self._redis.get(key)
            if raw is not None:
                receipt = _receipt_from_json(raw)
                if receipt.state is not ReceiptState.CLEANED or not self._redis.exists(
                    f"{_PREFIX}:event-ack:{receipt.rq_job_id}"
                ):
                    yield receipt

    def acknowledge_event(self, receipt: ExecutionReceipt) -> None:
        self._redis.set(
            f"{_PREFIX}:event-ack:{receipt.rq_job_id}",
            f"{receipt.state}:{receipt.cleanup_state or ''}",
        )

    def _validated_active(self, value: str) -> Path:
        active = Path(value).resolve(strict=True)
        try:
            active.relative_to(self._pvc_root)
        except ValueError as exc:
            raise KubernetesRenderError(
                "weppcloudr_k8s_admission_rejected", "run path escapes PVC root"
            ) from exc
        return active

    @contextmanager
    def _publish_lock(self, active_root: str, runid: str) -> Iterator[Path]:
        active = self._validated_active(active_root)
        fence_dir = active / "_locks" / "weppcloudr"
        fence_dir.mkdir(mode=0o770, parents=True, exist_ok=True)
        lock_path = fence_dir / f"deval_{runid}.fence.publish.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o660)
        with os.fdopen(descriptor, "a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield fence_dir
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            remaining = memoryview(payload)
            while remaining:
                remaining = remaining[os.write(descriptor, remaining) :]
            os.fsync(descriptor)
            os.fchmod(descriptor, mode)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            os.close(descriptor)
        os.replace(temporary, path)


class KubernetesApiGateway:
    """Minimal in-cluster Batch API adapter with strict ownership checks."""

    def __init__(self, namespace: str) -> None:
        self._namespace = namespace
        self._base = os.getenv("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
        port = os.getenv("KUBERNETES_SERVICE_PORT_HTTPS", "443")
        self._url = f"https://{self._base}:{port}"
        self._token_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        self._ca = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        token = self._token_path.read_text(encoding="utf-8").strip()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        response = requests.request(
            method,
            f"{self._url}{path}",
            headers=headers,
            verify=self._ca,
            timeout=10,
            allow_redirects=False,
            **kwargs,
        )
        return response

    def _job_path(self, namespace: str, name: str | None = None) -> str:
        if namespace != self._namespace:
            raise KubernetesRenderError("weppcloudr_k8s_unauthorized", "namespace denied")
        base = f"/apis/batch/v1/namespaces/{quote(namespace, safe='')}/jobs"
        return f"{base}/{quote(name, safe='')}" if name else base

    @staticmethod
    def _assert_owned(job: Mapping[str, object]) -> None:
        metadata = job.get("metadata") or {}
        labels = metadata.get("labels") or {}
        if labels.get(_LABEL_NAME) != _LABEL_VALUE:
            raise KubernetesRenderError("weppcloudr_k8s_unauthorized", "Job is not controller-owned")

    def get(self, namespace: str, name: str) -> JobObservation:
        response = self._request("GET", self._job_path(namespace, name))
        if response.status_code == 404:
            return JobObservation(JobPhase.ABSENT)
        if not response.ok:
            raise KubernetesRenderError("weppcloudr_k8s_api_unavailable", f"Job GET HTTP {response.status_code}")
        job = response.json()
        self._assert_owned(job)
        return self._observation(job)

    def create(self, namespace: str, spec: Mapping[str, object]) -> JobObservation:
        self._assert_owned(spec)
        try:
            response = self._request("POST", self._job_path(namespace), json=spec)
        except requests.RequestException as exc:
            raise CreateAmbiguous("Job create response unavailable") from exc
        if response.status_code == 409:
            name = str((spec.get("metadata") or {}).get("name"))
            return self.get(namespace, name)
        if not response.ok:
            raise KubernetesRenderError("weppcloudr_k8s_admission_rejected", f"Job create HTTP {response.status_code}")
        job = response.json()
        self._assert_owned(job)
        return self._observation(job)

    def delete_foreground(self, namespace: str, name: str, uid: str) -> None:
        current = self.get(namespace, name)
        if current.phase is JobPhase.ABSENT:
            return
        if current.uid != uid:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "Job UID mismatch")
        body = {
            "apiVersion": "v1",
            "kind": "DeleteOptions",
            "propagationPolicy": "Foreground",
            "preconditions": {"uid": uid},
        }
        response = self._request("DELETE", self._job_path(namespace, name), json=body)
        if response.status_code not in {200, 202, 404}:
            raise KubernetesRenderError("weppcloudr_k8s_api_unavailable", f"Job delete HTTP {response.status_code}")

    def patch_completed_ttl(self, namespace: str, name: str, uid: str, ttl: int) -> None:
        current = self.get(namespace, name)
        if current.phase is JobPhase.ABSENT:
            return
        if current.uid != uid:
            raise KubernetesRenderError("weppcloudr_k8s_state_lost", "Job UID mismatch")
        response = self._request(
            "PATCH",
            self._job_path(namespace, name),
            headers={"Content-Type": "application/merge-patch+json"},
            json={"spec": {"ttlSecondsAfterFinished": ttl}},
        )
        if not response.ok:
            raise KubernetesRenderError("weppcloudr_k8s_api_unavailable", f"Job TTL patch HTTP {response.status_code}")

    def _observation(self, job: Mapping[str, object]) -> JobObservation:
        metadata = job.get("metadata") or {}
        annotations = metadata.get("annotations") or {}
        status = job.get("status") or {}
        deletion = metadata.get("deletionTimestamp")
        phase = JobPhase.PENDING
        if deletion:
            phase = JobPhase.DELETING
        elif status.get("succeeded"):
            phase = JobPhase.SUCCEEDED
        elif status.get("failed"):
            phase = JobPhase.FAILED
        elif status.get("active"):
            phase = JobPhase.RUNNING
        reason = self._condition_reason(status)
        receipt: dict[str, object] = {}
        stdout_ref = stderr_ref = None
        if phase in {JobPhase.SUCCEEDED, JobPhase.FAILED}:
            logs = self._pod_logs(str(metadata.get("name")))
            stdout_ref = f"kubernetes://{self._namespace}/{metadata.get('name')}/logs"
            stderr_ref = stdout_ref
            for line in reversed(logs.splitlines()):
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and candidate.get("schema_version") == 1:
                    receipt = candidate
                    break
        return JobObservation(
            phase=phase,
            uid=metadata.get("uid"),
            ownership_nonce=annotations.get("weppcloud.org/ownership-nonce"),
            request_digest=annotations.get("weppcloud.org/request-digest"),
            spec_digest=annotations.get("weppcloud.org/spec-digest"),
            renderer_image_digest=annotations.get("weppcloud.org/renderer-image-digest"),
            deployment_revision=annotations.get("weppcloud.org/deployment-revision"),
            reason=reason,
            artifact_path=receipt.get("artifact_path"),
            artifact_sha256=receipt.get("artifact_sha256"),
            artifact_size=receipt.get("artifact_size"),
            result_rq_job_id=receipt.get("rq_job_id"),
            result_request_digest=receipt.get("request_digest"),
            result_fencing_generation=receipt.get("fencing_generation"),
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
        )

    @staticmethod
    def _condition_reason(status: Mapping[str, object]) -> str | None:
        conditions = status.get("conditions") or []
        for condition in reversed(conditions):
            if condition.get("status") == "True":
                return str(condition.get("reason") or condition.get("message") or "")
        return None

    def _pod_logs(self, job_name: str) -> str:
        selector = quote(f"job-name={job_name}", safe="")
        path = f"/api/v1/namespaces/{quote(self._namespace, safe='')}/pods?labelSelector={selector}"
        response = self._request("GET", path)
        if not response.ok:
            return ""
        items = response.json().get("items") or []
        if not items:
            return ""
        pod_name = str(items[0]["metadata"]["name"])
        log_path = f"/api/v1/namespaces/{quote(self._namespace, safe='')}/pods/{quote(pod_name, safe='')}/log?container=renderer&tailLines=200"
        logs = self._request("GET", log_path)
        return logs.text[-65536:] if logs.ok else ""


class LoggingEventSink:
    def publish(self, receipt: ExecutionReceipt) -> None:
        _LOGGER.info("WEPPcloudR receipt %s state=%s cleanup=%s", receipt.rq_job_id, receipt.state, receipt.cleanup_state)

    def publish_error(self, receipt: ExecutionReceipt, error: KubernetesRenderError) -> None:
        _LOGGER.error("WEPPcloudR receipt %s reconcile error: %s", receipt.rq_job_id, error)


def _config() -> ControlPlaneConfig:
    image_ref = _required_env("WEPPCLOUDR_RENDERER_IMAGE")
    repository, digest = image_ref.rsplit("@", 1)
    return ControlPlaneConfig(
        namespace=_required_env("WEPPCLOUDR_K8S_NAMESPACE"),
        renderer_image_repository=repository,
        renderer_image_digest=digest,
        run_pvc=_required_env("WEPPCLOUDR_RUN_PVC"),
        geodata_pvc=_required_env("WEPPCLOUDR_GEODATA_PVC"),
        service_account=_required_env("WEPPCLOUDR_RENDERER_SERVICE_ACCOUNT"),
        max_active_renders=int(os.getenv("WEPPCLOUDR_MAX_ACTIVE_RENDERS", "4")),
        active_deadline_seconds=int(os.getenv("WEPPCLOUDR_K8S_ACTIVE_DEADLINE", "600")),
        pending_timeout_seconds=int(os.getenv("WEPPCLOUDR_K8S_PENDING_TIMEOUT", "120")),
        completed_ttl_seconds=int(os.getenv("WEPPCLOUDR_K8S_COMPLETED_TTL", "1200")),
    )


def create_app() -> FastAPI:
    connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    config = _config()
    store = RedisReceiptStore(connection)
    control = RenderControlPlane(
        store,
        KubernetesApiGateway(config.namespace),
        config,
        event_sink=LoggingEventSink(),
    )
    expected_token = _read_protected_file(_required_env("WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE"))
    application = FastAPI(title="WEPPcloudR Render Control Plane", docs_url=None, redoc_url=None)

    def authenticate(authorization: str | None) -> None:
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not supplied or not hmac.compare_digest(supplied, expected_token):
            raise HTTPException(status_code=401, detail="unauthorized")

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        connection.ping()
        return {"status": "ok"}

    @application.post("/v1/renders")
    async def submit(request: Request, authorization: str | None = Header(default=None)) -> dict[str, object]:
        authenticate(authorization)
        payload = await request.json()
        render_request = RenderRequest(**payload)
        digest = request.headers.get("X-WEPPcloudR-Request-SHA256", "")
        if not hmac.compare_digest(render_request.digest, digest):
            raise HTTPException(status_code=409, detail="request digest mismatch")
        return control.submit(render_request).payload()

    @application.get("/v1/renders/{rq_job_id}")
    def observe(rq_job_id: str, request: Request, authorization: str | None = Header(default=None)) -> dict[str, object]:
        authenticate(authorization)
        return control.observe(rq_job_id, request.headers.get("X-WEPPcloudR-Request-SHA256", "")).payload()

    @application.post("/v1/renders/{rq_job_id}/cancel")
    def cancel(rq_job_id: str, request: Request, authorization: str | None = Header(default=None)) -> Mapping[str, object]:
        authenticate(authorization)
        return control.cancel(rq_job_id, request.headers.get("X-WEPPcloudR-Request-SHA256", ""))

    @application.on_event("startup")
    def start_reaper() -> None:
        def loop() -> None:
            while True:
                try:
                    control.reap()
                except Exception:
                    _LOGGER.exception("WEPPcloudR reconciliation loop failed")
                time.sleep(5)
        threading.Thread(target=loop, name="weppcloudr-reaper", daemon=True).start()

    return application


def main() -> None:
    uvicorn.run(
        "wepppy.microservices.weppcloudr_control_plane:create_app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8443")),
        ssl_keyfile=_required_env("WEPPCLOUDR_TLS_KEY_FILE"),
        ssl_certfile=_required_env("WEPPCLOUDR_TLS_CERT_FILE"),
        workers=1,
        factory=True,
    )


if __name__ == "__main__":
    main()
