from __future__ import annotations

from pathlib import Path
from typing import Optional

DEFAULT_CONTAINER_NAME: str
DEFAULT_TIMEOUT: int

class WeppcloudRError(RuntimeError): ...

def _ensure_docker_client() -> None: ...

def _coerce_bool(value: object) -> bool: ...

def _write_command_logs(output_dir: Path, job_id: str, stdout: str, stderr: str) -> None: ...

def render_deval_details_rq(
    runid: str,
    config: str,
    active_root: str,
    *,
    skip_cache: bool = ...,
    container_name: Optional[str] = ...,
    timeout: Optional[int] = ...,
) -> str: ...
