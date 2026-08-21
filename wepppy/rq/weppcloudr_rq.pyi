from __future__ import annotations

from pathlib import Path
from typing import Optional

BACKEND_DOCKER_EXEC: str
BACKEND_KUBERNETES_JOB: str
DEFAULT_CONTAINER_NAME: str
DEFAULT_TIMEOUT: int
DEFAULT_LOG_MAX_BYTES: int
DEFAULT_ALLOWED_ROOTS: tuple[str, ...]

class WeppcloudRError(RuntimeError): ...

def _coerce_bool(value: object) -> bool: ...
def _write_command_logs(active_path: Path, job_id: str, stdout: str, stderr: str) -> None: ...

def render_deval_details_rq(
    runid: str,
    config: str,
    active_root: str,
    *,
    skip_cache: bool = ...,
    run_root: Optional[str] = ...,
    backend: Optional[str] = ...,
    container_name: Optional[str] = ...,
    timeout: Optional[int] = ...,
    control_plane_url: Optional[str] = ...,
    control_plane_token_file: Optional[str] = ...,
    control_plane_namespace: Optional[str] = ...,
    renderer_image_digest: Optional[str] = ...,
    deployment_revision: Optional[str] = ...,
    parquet_overrides: Optional[dict[str, str]] = ...,
) -> str: ...
