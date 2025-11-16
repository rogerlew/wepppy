"""RQ helpers for rendering reports via the Dockerized weppcloudR service."""

from __future__ import annotations

import inspect
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rq import get_current_job

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging


DEFAULT_CONTAINER_NAME = os.getenv("WEPPCLOUDR_CONTAINER", "weppcloudr")
DEFAULT_TIMEOUT = int(os.getenv("WEPPCLOUDR_COMMAND_TIMEOUT", "1800"))


class WeppcloudRError(RuntimeError):
    """Raised when invoking the weppcloudR container fails."""


def _ensure_docker_client() -> None:
    """Ensure the Docker CLI is available before attempting to exec commands."""
    if shutil.which("docker") is None:
        raise WeppcloudRError(
            "Docker CLI not found in PATH. Install Docker or expose the CLI to the worker container."
        )


def _coerce_bool(value: object) -> bool:
    """Coerce arbitrary truthy values into canonical booleans."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _write_command_logs(output_dir: Path, job_id: str, stdout: str, stderr: str) -> None:
    """Persist stdout/stderr output from docker exec invocations."""
    try:
        (output_dir / f"render_deval_{job_id}.stdout").write_text(stdout, encoding="utf-8")
        (output_dir / f"render_deval_{job_id}.stderr").write_text(stderr, encoding="utf-8")
    except Exception:
        # Best effort logging; avoid masking the main error path.
        pass


@with_exception_logging
def render_deval_details_rq(
    runid: str,
    config: str,
    active_root: str,
    *,
    skip_cache: bool = False,
    container_name: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Render the DEVAL Details report inside the weppcloudR container.

    Args:
        runid: Identifier used to locate the working directory.
        config: Configuration stem associated with the run.
        active_root: Absolute path to the active run directory.
        skip_cache: When True, force a re-render even if the cache exists.
        container_name: Optional Docker container override.
        timeout: Optional timeout (seconds) for the `docker exec` command.

    Returns:
        Absolute path to the rendered HTML document.

    Raises:
        FileNotFoundError: If the active directory or rendered output is missing.
        WeppcloudRError: When Docker is unavailable or the render command fails.
        subprocess.TimeoutExpired: If the container command exceeds `timeout`.
    """

    job = get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:weppcloudr"

    StatusMessenger.publish(
        status_channel,
        f"rq:{job_id} STARTED {func_name}({runid}, config={config}, skip_cache={skip_cache})",
    )

    try:
        _ensure_docker_client()

        active_path = Path(active_root).resolve()
        if not active_path.is_dir():
            raise FileNotFoundError(f"Active run directory not found: {active_path}")

        export_dir = active_path / "export" / "WEPPcloudR"
        export_dir.mkdir(parents=True, exist_ok=True)

        output_path = export_dir / f"deval_{runid}.htm"

        skip_cache_flag = _coerce_bool(skip_cache)
        if skip_cache_flag and output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                # If removal fails we'll let the R renderer overwrite the file.
                pass

        payload = {
            "run_path": str(active_path),
            "runid": runid,
            "config": config,
            "skip_cache": bool(skip_cache_flag),
        }
        payload_json = json.dumps(payload, ensure_ascii=False)
        escaped_payload = payload_json.replace("\\", "\\\\").replace("'", "\\'")

        r_expression = (
            "suppressPackageStartupMessages(library(jsonlite));"
            f"payload <- jsonlite::fromJSON('{escaped_payload}');"
            "source('/srv/weppcloudr/plumber.R');"
            "render_deval(payload$run_path, payload$runid, payload$config, skip_cache = payload$skip_cache);"
        )

        exec_container = container_name or DEFAULT_CONTAINER_NAME
        exec_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

        command = [
            "docker",
            "exec",
            exec_container,
            "Rscript",
            "-e",
            r_expression,
        ]

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=exec_timeout,
        )

        _write_command_logs(export_dir, job_id, result.stdout, result.stderr)

        if result.returncode != 0:
            raise WeppcloudRError(
                "Failed to render DEVAL report via weppcloudR container.\n"
                f"Command: {' '.join(shlex.quote(part) for part in command)}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )

        if not output_path.exists():
            raise FileNotFoundError(
                f"DEVAL report was rendered but not found at expected path: {output_path}"
            )

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} COMPLETED {func_name}({runid}, config={config}, skip_cache={skip_cache_flag}) -> {output_path}",
        )
        return str(output_path)
    except Exception:
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({runid}, config={config}, skip_cache={skip_cache})",
        )
        raise
