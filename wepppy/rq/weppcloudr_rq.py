"""RQ orchestration for deployment-neutral WEPPcloudR report rendering."""

from __future__ import annotations

import fcntl
import hashlib
import inspect
import os
import re
import shutil
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from rq import get_current_job

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.rq.weppcloudr_backends import (
    REQUEST_SCHEMA_VERSION,
    BackendConfigurationError,
    BackendError,
    BackendExecutionError,
    DockerExecBackend,
    HttpRenderControlPlaneClient,
    KubernetesJobBackend,
    KubernetesRenderError,
    RenderBackend,
    RenderRequest,
    validate_request,
)
from wepppy.runtime_paths.parquet_sidecars import list_existing_retired_root_resources


BACKEND_DOCKER_EXEC = "docker-exec"
BACKEND_KUBERNETES_JOB = "kubernetes-job"
DEFAULT_CONTAINER_NAME = os.getenv("WEPPCLOUDR_CONTAINER", "weppcloudr")
DEFAULT_TIMEOUT = int(os.getenv("WEPPCLOUDR_COMMAND_TIMEOUT", "1800"))
DEFAULT_LOG_MAX_BYTES = 1024 * 1024
DEFAULT_ALLOWED_ROOTS = (
    "/wc1/runs",
    "/geodata/weppcloud_runs",
    "/wc1/batch",
    "/wc1/culverts",
    "/workdir/wepppy-test-engine-data",
)


class WeppcloudRError(RuntimeError):
    """Stable public error raised when WEPPcloudR orchestration fails."""


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _assert_no_retired_root_resources(active_path: Path) -> None:
    retired = list_existing_retired_root_resources(active_path)
    if retired:
        raise WeppcloudRError(
            "Migration required before rendering DEVAL report: retired WD-root "
            f"resources detected ({', '.join(retired)})."
        )


def _approved_run_roots() -> tuple[Path, ...]:
    configured = os.getenv("WEPPCLOUDR_RUN_ROOTS")
    values = configured.split(os.pathsep) if configured else DEFAULT_ALLOWED_ROOTS
    return tuple(Path(value).resolve() for value in values if value)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_run_paths(run_root: str, active_root: str) -> tuple[Path, Path]:
    run_path = Path(run_root).resolve(strict=True)
    active_path = Path(active_root).resolve(strict=True)
    if not run_path.is_dir() or not active_path.is_dir():
        raise FileNotFoundError("WEPPcloudR run directory was not found.")
    if not any(_is_within(run_path, root) for root in _approved_run_roots()):
        raise WeppcloudRError("WEPPcloudR run working directory is outside approved roots.")
    if not _is_within(active_path, run_path):
        raise WeppcloudRError("WEPPcloudR active directory escapes the run working directory.")
    return run_path, active_path


def _secure_deval_paths(active_path: Path, runid: str, job_id: str) -> tuple[Path, Path]:
    export_parent = active_path / "export"
    export_dir = export_parent / "WEPPcloudR"
    log_dir = active_path / "_logs" / "weppcloudr"
    root_fd = os.open(active_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for parts in (("export", "WEPPcloudR"), ("_logs", "weppcloudr")):
            current_fd = os.dup(root_fd)
            try:
                for part in parts:
                    try:
                        os.mkdir(part, mode=0o770, dir_fd=current_fd)
                    except FileExistsError:
                        pass
                    next_fd = os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=current_fd,
                    )
                    os.close(current_fd)
                    current_fd = next_fd
            finally:
                os.close(current_fd)
    except OSError as exc:
        raise WeppcloudRError(
            "DEVAL report path contains a symlink or unsafe component."
        ) from exc
    finally:
        os.close(root_fd)
    for directory in (export_dir, log_dir):
        if not _is_within(directory.resolve(), active_path):
            raise WeppcloudRError("DEVAL report path escapes the active run root.")
    output_path = export_dir / f"deval_{runid}.htm"
    if output_path.is_symlink():
        raise WeppcloudRError("DEVAL report artifact is a symlink.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", job_id):
        raise WeppcloudRError("Invalid DEVAL job identifier.")
    for suffix in ("stdout", "stderr"):
        if (log_dir / f"render_deval_{job_id}.{suffix}").is_symlink():
            raise WeppcloudRError("DEVAL command log is a symlink.")
    return log_dir, output_path


def _bounded_log(value: str, maximum: int) -> str:
    sanitized = "".join(char for char in value if char in "\n\r\t" or ord(char) >= 32)
    encoded = sanitized.encode("utf-8", errors="replace")
    if len(encoded) <= maximum:
        return sanitized
    marker = b"[WEPPcloudR log truncated; retained tail]\n"
    tail = encoded[-(maximum - len(marker)) :].decode("utf-8", errors="ignore")
    return marker.decode("ascii") + tail


def _open_child_directory(parent_fd: int, name: str) -> int:
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)


def _write_command_logs(active_path: Path, job_id: str, stdout: str, stderr: str) -> None:
    maximum = int(os.getenv("WEPPCLOUDR_LOG_MAX_BYTES", str(DEFAULT_LOG_MAX_BYTES)))
    if maximum < 1024:
        raise BackendConfigurationError("WEPPCLOUDR_LOG_MAX_BYTES must be at least 1024.")
    root_fd = os.open(active_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    directory_fd = -1
    try:
        logs_fd = _open_child_directory(root_fd, "_logs")
        try:
            directory_fd = _open_child_directory(logs_fd, "weppcloudr")
        finally:
            os.close(logs_fd)
        for suffix, value in (("stdout", stdout), ("stderr", stderr)):
            name = f"render_deval_{job_id}.{suffix}"
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                0o660,
                dir_fd=directory_fd,
            )
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise WeppcloudRError("DEVAL command log is not a regular file.")
                os.fchmod(descriptor, 0o660)
                payload = _bounded_log(value, maximum).encode("utf-8")
                view = memoryview(payload)
                while view:
                    view = view[os.write(descriptor, view) :]
            finally:
                os.close(descriptor)
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        os.close(root_fd)


def _next_compose_fencing_generation(active_path: Path, runid: str) -> int:
    root_fd = os.open(active_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        current_fd = root_fd
        for part in ("_locks", "weppcloudr"):
            try:
                os.mkdir(part, mode=0o770, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd
            )
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        lock_fd = os.open(
            f"deval_{runid}.fence.publish.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o660,
            dir_fd=current_fd,
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            fence_name = f"deval_{runid}.fence"
            fence_fd = os.open(
                fence_name,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                0o660,
                dir_fd=current_fd,
            )
            try:
                raw = os.read(fence_fd, 64).decode("ascii", errors="strict").strip()
                generation = (int(raw) if raw else 0) + 1
                os.lseek(fence_fd, 0, os.SEEK_SET)
                os.ftruncate(fence_fd, 0)
                os.write(fence_fd, f"{generation}\n".encode("ascii"))
                os.fsync(fence_fd)
                os.fchmod(fence_fd, 0o660)
                return generation
            finally:
                os.close(fence_fd)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            os.close(current_fd)
    except (OSError, UnicodeError, ValueError) as exc:
        raise WeppcloudRError("DEVAL fencing state is invalid or unsafe.") from exc
    finally:
        os.close(root_fd)


@contextmanager
def _artifact_lock(active_path: Path, runid: str) -> Iterator[None]:
    root_fd = os.open(active_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir("_locks", mode=0o770, dir_fd=root_fd)
        except FileExistsError:
            pass
        lock_directory_fd = os.open(
            "_locks", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
    except OSError as exc:
        raise WeppcloudRError("DEVAL lock path contains an unsafe component.") from exc
    finally:
        os.close(root_fd)
    descriptor = os.open(
        f"deval_{runid}.lock",
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o660,
        dir_fd=lock_directory_fd,
    )
    os.close(lock_directory_fd)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise WeppcloudRError("DEVAL lock is not a regular file.")
    with os.fdopen(descriptor, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _select_backend(
    backend_name: str,
    *,
    container_name: str,
    control_plane_url: Optional[str],
    control_plane_token_file: Optional[str],
    control_plane_namespace: Optional[str],
    docker_fencing_generation: Optional[int] = None,
) -> RenderBackend:
    if backend_name == BACKEND_DOCKER_EXEC:
        if docker_fencing_generation is None:
            raise BackendConfigurationError("Compose fencing generation is unavailable.")
        return DockerExecBackend(container_name, docker_fencing_generation)
    if backend_name == BACKEND_KUBERNETES_JOB:
        if not control_plane_url or not control_plane_token_file or not control_plane_namespace:
            raise BackendConfigurationError(
                "kubernetes-job requires control-plane URL and workload identity token file."
            )
        client = HttpRenderControlPlaneClient(
            control_plane_url,
            Path(control_plane_token_file),
        )
        return KubernetesJobBackend(client, expected_namespace=control_plane_namespace)
    raise BackendConfigurationError(f"Unknown WEPPcloudR execution backend: {backend_name!r}.")


def _open_artifact(active_path: Path, artifact_name: str) -> int:
    root_fd = os.open(active_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        export_fd = _open_child_directory(root_fd, "export")
        try:
            report_fd = _open_child_directory(export_fd, "WEPPcloudR")
            try:
                return os.open(
                    artifact_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=report_fd
                )
            finally:
                os.close(report_fd)
        finally:
            os.close(export_fd)
    finally:
        os.close(root_fd)


def _validate_artifact(output_path: Path, active_path: Path) -> None:
    try:
        descriptor = _open_artifact(active_path, output_path.name)
    except OSError as exc:
        raise FileNotFoundError(
            "DEVAL renderer did not produce a regular report artifact."
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise FileNotFoundError(
                "DEVAL renderer did not produce a regular report artifact."
            )
    finally:
        os.close(descriptor)


def _validate_receipt_artifact(
    output_path: Path, active_path: Path, receipt: object
) -> None:
    if not isinstance(receipt, dict):
        return
    if receipt.get("artifact_path") != str(output_path):
        raise WeppcloudRError("Kubernetes receipt artifact path mismatch.")
    descriptor = _open_artifact(active_path, output_path.name)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise WeppcloudRError("Kubernetes receipt artifact is not regular.")
        with os.fdopen(descriptor, "rb", closefd=False) as artifact_file:
            content = artifact_file.read()
    finally:
        os.close(descriptor)
    if receipt.get("artifact_size") != len(content):
        raise WeppcloudRError("Kubernetes receipt artifact size mismatch.")
    if receipt.get("artifact_sha256") != hashlib.sha256(content).hexdigest():
        raise WeppcloudRError("Kubernetes receipt artifact digest mismatch.")


def _record_kubernetes_error(job: object, exc: KubernetesRenderError) -> None:
    meta = getattr(job, "meta", None)
    if not isinstance(meta, dict):
        return
    retries_left = getattr(job, "retries_left", 0) or 0
    if exc.code == "weppcloudr_k8s_api_unavailable" and retries_left > 0:
        meta.pop("error", None)
        meta.pop("error_id", None)
        save_meta = getattr(job, "save_meta", None)
        if callable(save_meta):
            save_meta()
        return
    if exc.code != "weppcloudr_k8s_api_unavailable" and hasattr(job, "retries_left"):
        job.retries_left = 0
        save_job = getattr(job, "save", None)
        if callable(save_job):
            save_job()
    meta["error"] = {"code": exc.code, "message": "WEPPcloudR render failed."}
    meta["error_id"] = getattr(job, "id", None)
    save_meta = getattr(job, "save_meta", None)
    if callable(save_meta):
        save_meta()


def _disable_job_retries(job: object) -> None:
    if hasattr(job, "retries_left"):
        job.retries_left = 0
        save_job = getattr(job, "save", None)
        if callable(save_job):
            save_job()


@with_exception_logging
def render_deval_details_rq(
    runid: str,
    config: str,
    active_root: str,
    *,
    skip_cache: bool = False,
    run_root: Optional[str] = None,
    backend: Optional[str] = None,
    container_name: Optional[str] = None,
    timeout: Optional[int] = None,
    control_plane_url: Optional[str] = None,
    control_plane_token_file: Optional[str] = None,
    control_plane_namespace: Optional[str] = None,
    renderer_image_digest: Optional[str] = None,
    deployment_revision: Optional[str] = None,
    parquet_overrides: Optional[dict[str, str]] = None,
) -> str:
    """Render DEVAL through the explicitly selected deployment backend."""
    job = get_current_job()
    job_id = str(getattr(job, "id", "sync"))
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:weppcloudr"
    selected_backend = backend or os.getenv(
        "WEPPCLOUDR_EXECUTION_BACKEND", BACKEND_DOCKER_EXEC
    )
    effective_run_root = run_root or active_root
    _ = parquet_overrides

    StatusMessenger.publish(
        status_channel,
        f"rq:{job_id} STARTED {func_name}({runid}, config={config}, "
        f"skip_cache={skip_cache}, backend={selected_backend})",
    )
    try:
        if run_root is None and selected_backend != BACKEND_DOCKER_EXEC:
            raise WeppcloudRError("kubernetes-job rejects legacy jobs without run_root.")
        _, active_path = _validate_run_paths(effective_run_root, active_root)
        _assert_no_retired_root_resources(active_path)
        _log_dir, output_path = _secure_deval_paths(active_path, runid, job_id)
        skip_cache_flag = _coerce_bool(skip_cache)
        image_digest = (
            renderer_image_digest or os.getenv("WEPPCLOUDR_K8S_IMAGE", "")
            if selected_backend == BACKEND_KUBERNETES_JOB
            else ""
        )
        request = RenderRequest(
            schema_version=REQUEST_SCHEMA_VERSION,
            rq_job_id=job_id,
            runid=runid,
            config=config,
            run_root=str(Path(effective_run_root).resolve()),
            active_root=str(active_path),
            skip_cache=skip_cache_flag,
            correlation_id=job_id,
            deployment_revision=deployment_revision
            or os.getenv("WEPPCLOUDR_DEPLOYMENT_REVISION", "unknown"),
            renderer_image_digest=image_digest,
        )
        validate_request(request)
        if selected_backend == BACKEND_KUBERNETES_JOB and isinstance(
            getattr(job, "meta", None), dict
        ):
            job.meta["render_backend"] = BACKEND_KUBERNETES_JOB
            job.meta["render_request_digest"] = request.digest
            job.meta["render_cleanup_state"] = "active"
            save_meta = getattr(job, "save_meta", None)
            if callable(save_meta):
                save_meta()
        exec_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        with _artifact_lock(active_path, runid):
            docker_fence = (
                _next_compose_fencing_generation(active_path, runid)
                if selected_backend == BACKEND_DOCKER_EXEC
                else None
            )
            executor = _select_backend(
                selected_backend,
                container_name=container_name or DEFAULT_CONTAINER_NAME,
                control_plane_url=control_plane_url
                or os.getenv("WEPPCLOUDR_K8S_CONTROL_PLANE_URL"),
                control_plane_token_file=control_plane_token_file
                or os.getenv("WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE"),
                control_plane_namespace=control_plane_namespace
                or os.getenv("WEPPCLOUDR_K8S_NAMESPACE"),
                docker_fencing_generation=docker_fence,
            )
            if selected_backend == BACKEND_KUBERNETES_JOB and bool(
                getattr(job, "meta", {}).get("cancel_requested")
            ):
                if not isinstance(executor, KubernetesJobBackend):
                    raise WeppcloudRError("Invalid Kubernetes render backend state.")
                executor.cancel(request)
                raise WeppcloudRError("WEPPcloudR render was cancelled before dispatch.")
            try:
                result = executor.render(request, timeout=exec_timeout)
            except BackendExecutionError as exc:
                _write_command_logs(active_path, job_id, exc.stdout, exc.stderr)
                raise
            _write_command_logs(active_path, job_id, result.stdout, result.stderr)
            _validate_artifact(output_path, active_path)
            _validate_receipt_artifact(output_path, active_path, result.receipt)

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} COMPLETED {func_name}({runid}, config={config}, "
            f"skip_cache={skip_cache_flag}, backend={selected_backend}) -> {output_path}",
        )
        return str(output_path)
    except KubernetesRenderError as exc:
        _record_kubernetes_error(job, exc)
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({runid}, config={config}, "
            f"backend={selected_backend}, error={exc.code})",
        )
        raise WeppcloudRError(str(exc)) from exc
    except (BackendError, OSError, ValueError, WeppcloudRError) as exc:
        if selected_backend == BACKEND_KUBERNETES_JOB:
            _disable_job_retries(job)
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({runid}, config={config}, "
            f"backend={selected_backend})",
        )
        if isinstance(exc, WeppcloudRError):
            raise
        raise WeppcloudRError(str(exc)) from exc
