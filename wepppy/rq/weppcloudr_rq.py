"""RQ helpers for rendering reports via the Dockerized weppcloudR service."""

from __future__ import annotations

import inspect
import json
import os
import re
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

_CLIMATE_SIDECAR_RE = re.compile(r"^climate\.([^/]+)\.parquet$")
_WATERSHED_SIDECAR_RE = re.compile(r"^watershed\.([^/]+)\.parquet$")


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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/weppcloudr_rq.py:50", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        # Best effort logging; avoid masking the main error path.
        pass


def _sidecar_to_logical_parquet(name: str) -> Optional[str]:
    """Translate WD-level NoDir parquet sidecar names into logical parquet ids."""
    if name == "landuse.parquet":
        return "landuse/landuse.parquet"
    if name == "soils.parquet":
        return "soils/soils.parquet"
    climate_match = _CLIMATE_SIDECAR_RE.match(name)
    if climate_match:
        return f"climate/{climate_match.group(1)}.parquet"
    watershed_match = _WATERSHED_SIDECAR_RE.match(name)
    if watershed_match:
        return f"watershed/{watershed_match.group(1)}.parquet"
    return None


def _discover_nodir_parquet_overrides(active_path: Path) -> dict[str, str]:
    """Return logical parquet ids mapped to existing WD-level sidecar paths."""
    overrides: dict[str, str] = {}
    try:
        entries = list(active_path.iterdir())
    except OSError:
        return overrides

    for entry in entries:
        if not entry.is_file():
            continue
        logical_path = _sidecar_to_logical_parquet(entry.name)
        if logical_path is None:
            continue
        overrides[logical_path] = str(entry)

    return dict(sorted(overrides.items()))


def _build_render_deval_expression(escaped_payload: str) -> str:
    """Build an R expression that invokes render_deval with version-safe args."""
    return (
        "suppressPackageStartupMessages(library(jsonlite));"
        f"payload <- jsonlite::fromJSON('{escaped_payload}');"
        "source('/srv/weppcloudr/plumber.R');"
        "render_args <- list(payload$run_path, payload$runid, payload$config, "
        "skip_cache = payload$skip_cache);"
        "supports_parquet_overrides <- 'parquet_overrides' %in% names(formals(render_deval));"
        "if (supports_parquet_overrides) {"
        "render_args$parquet_overrides <- payload$parquet_overrides;"
        "};"
        "do.call(render_deval, render_args);"
    )


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
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/weppcloudr_rq.py:110", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                # If removal fails we'll let the R renderer overwrite the file.
                pass

        payload = {
            "run_path": str(active_path),
            "runid": runid,
            "config": config,
            "skip_cache": bool(skip_cache_flag),
            "parquet_overrides": _discover_nodir_parquet_overrides(active_path),
        }
        payload_json = json.dumps(payload, ensure_ascii=False)
        escaped_payload = payload_json.replace("\\", "\\\\").replace("'", "\\'")
        r_expression = _build_render_deval_expression(escaped_payload)

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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/weppcloudr_rq.py:170", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({runid}, config={config}, skip_cache={skip_cache})",
        )
        raise
