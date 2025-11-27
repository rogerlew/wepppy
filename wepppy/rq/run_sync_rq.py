"""RQ task to sync remote runs and register provenance."""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from rq import get_current_job

from wepppy.nodb.base import lock_statuses
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.nodb.version import read_version
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.oauth import utc_now

DEFAULT_TARGET_ROOT = "/wc1/runs"
DEFAULT_CONFIG = "cfg"
STATUS_CHANNEL_SUFFIX = "run_sync"
STATUS_EVENTS = (
    "ENQUEUED",
    "DOWNLOADING",
    "CHECKSUM_OK",
    "REGISTERED",
    "COMPLETE",
    "EXCEPTION",
)


def _status_channel(runid: str) -> str:
    return f"{runid}:{STATUS_CHANNEL_SUFFIX}"


def _publish_status(channel: str, job_id: str, label: str, detail: str | None = None) -> None:
    message = f"rq:{job_id} {label}"
    if detail:
        message = f"{message} {detail}"
    StatusMessenger.publish(channel, message)


def _normalize_host(source_host: str) -> str:
    if not source_host:
        raise ValueError("source_host is required")
    parsed = urlparse(source_host if "://" in source_host else f"https://{source_host}")
    host = parsed.netloc or parsed.path
    if not host:
        raise ValueError(f"Invalid source_host: {source_host}")
    return host.rstrip("/")


def _require_component_safe(component: str, label: str) -> str:
    candidate = Path(component).name
    if not candidate or candidate != component or candidate in {".", ".."}:
        raise ValueError(f"Invalid {label}: {component}")
    return candidate


def _resolve_run_root(target_root: str, runid: str, config: str) -> Path:
    """Resolve the run root directory following the standard layout.
    
    Runs are organized as: {target_root}/{first_two_chars}/{runid}/
    e.g., /wc1/runs/rl/rlew-forested-advisory/
    """
    base = Path(target_root).expanduser().resolve()
    prefix = runid[:2].lower()
    run_root = (base / prefix / runid).resolve()
    if base not in run_root.parents:
        raise ValueError("Resolved run path escapes target root")
    return run_root


def _download_spec(spec_url: str, headers: dict[str, str] | None, target_dir: Path | None = None) -> Path:
    """Download aria2c spec file.
    
    Args:
        spec_url: URL to fetch the spec from
        headers: Optional HTTP headers
        target_dir: Directory to write spec file to (uses system temp if None)
    """
    response = requests.get(spec_url, headers=headers or {}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch aria2c spec from {spec_url} (status {response.status_code})")
    
    # Write spec file to target_dir if provided (avoids snap/container filesystem issues)
    if target_dir is not None:
        target_dir.mkdir(parents=True, exist_ok=True)
        spec_file = target_dir / ".aria2c.spec"
        spec_file.write_bytes(response.content)
        return spec_file
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".aria2")
    with tmp_file:
        tmp_file.write(response.content)
        return Path(tmp_file.name)


def _run_aria2c(input_file: Path, target_dir: Path, headers: dict[str, str] | None) -> None:
    if shutil.which("aria2c") is None:
        raise RuntimeError("aria2c is required to sync runs but was not found on PATH")

    cmd = [
        "aria2c",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "--continue=true",
        "--check-integrity=true",
        "--max-connection-per-server=4",
        "--retry-wait=3",
        "--max-tries=5",
        "--dir",
        str(target_dir),
        "--input-file",
        str(input_file),
    ]
    if headers:
        for key, value in headers.items():
            cmd.extend(["--header", f"{key}: {value}"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"aria2c failed ({result.returncode}): {result.stderr or result.stdout}")


def _hash_directory(run_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(run_root.rglob("*")):
        if not path.is_file():
            continue
        digest.update(path.relative_to(run_root).as_posix().encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _verify_download(
    run_root: Path,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> None:
    if expected_size is not None:
        total = sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file())
        if total != expected_size:
            raise ValueError(f"Size check failed: expected {expected_size} bytes, found {total}")
    if expected_sha256:
        observed = _hash_directory(run_root)
        if observed.lower() != expected_sha256.lower():
            raise ValueError(f"Checksum mismatch: expected {expected_sha256}, observed {observed}")


def _write_provenance(
    run_root: Path,
    provenance: Dict[str, Any],
) -> Path:
    target = run_root / ".provenance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _upsert_migration_row(
    run_root: Path,
    runid: str,
    config: str,
    source_host: str,
    original_url: str,
    owner_email: str | None,
    pulled_at: datetime,
    last_status: str | None,
    version_at_pull: int | None,
) -> None:
    # Import inside the function to avoid circular imports during app bootstrap.
    from wepppy.weppcloud.app import RunMigration, app, db

    with app.app_context():
        record = RunMigration.query.filter_by(runid=runid, config=config).first()
        if record is None:
            record = RunMigration(runid=runid, config=config, local_path=str(run_root))
            db.session.add(record)
        record.local_path = str(run_root)
        record.source_host = source_host
        record.original_url = original_url
        record.owner_email = owner_email
        record.pulled_at = pulled_at
        record.last_status = last_status
        record.version_at_pull = version_at_pull
        record.updated_at = utc_now()
        db.session.commit()


@with_exception_logging
def run_sync_rq(
    runid: str,
    source_host: str,
    owner_email: Optional[str] = None,
    target_root: str = DEFAULT_TARGET_ROOT,
    config: Optional[str] = None,
) -> Dict[str, Any]:
    """Download a run from a remote WEPPcloud host and register provenance."""
    job = get_current_job()
    job_id = getattr(job, "id", "unknown")
    func_name = inspect.currentframe().f_code.co_name
    status_channel = _status_channel(runid)
    _publish_status(status_channel, job_id, f"STARTED {func_name}({runid})")

    normalized_runid = _require_component_safe(runid, "runid")
    normalized_config = _require_component_safe(config or DEFAULT_CONFIG, "config")
    normalized_host = _normalize_host(source_host)

    if job is not None:
        job.meta["runid"] = normalized_runid
        job.meta["config"] = normalized_config
        job.meta["source_host"] = normalized_host
        job.save()

    headers: dict[str, str] = {}

    run_root = _resolve_run_root(target_root, normalized_runid, normalized_config)
    pulled_at = datetime.now(timezone.utc)
    original_url = f"https://{normalized_host}/weppcloud/runs/{normalized_runid}/{normalized_config}"

    run_root.mkdir(parents=True, exist_ok=True)
    _upsert_migration_row(
        run_root,
        normalized_runid,
        normalized_config,
        normalized_host,
        original_url,
        owner_email,
        pulled_at,
        "DOWNLOADING",
        None,
    )

    spec_url = f"{original_url}/aria2c.spec"
    spec_file: Path | None = None
    try:
        spec_file = _download_spec(spec_url, headers, target_dir=run_root)
        _publish_status(status_channel, job_id, "DOWNLOADING", spec_url)

        _run_aria2c(spec_file, run_root, headers)
        _verify_download(run_root)
        _publish_status(status_channel, job_id, "CHECKSUM_OK")

        version_at_pull = read_version(run_root)
        provenance = {
            "runid": normalized_runid,
            "config": normalized_config,
            "source_host": normalized_host,
            "pulled_at": pulled_at.isoformat(),
            "original_url": original_url,
            "owner_email": owner_email,
            "version_at_pull": version_at_pull,
        }
        _write_provenance(run_root, provenance)

        _upsert_migration_row(
            run_root,
            normalized_runid,
            normalized_config,
            normalized_host,
            original_url,
            owner_email,
            pulled_at,
            "REGISTERED",
            version_at_pull,
        )
        _publish_status(status_channel, job_id, "REGISTERED", str(run_root))
        _publish_status(status_channel, job_id, "COMPLETE", f"{func_name}({normalized_runid}, {normalized_config})")
        return {
            "runid": normalized_runid,
            "config": normalized_config,
            "local_path": str(run_root),
            "source_host": normalized_host,
            "original_url": original_url,
            "version_at_pull": version_at_pull,
            "pulled_at": pulled_at.isoformat(),
        }
    except Exception:
        _publish_status(status_channel, job_id, "EXCEPTION", f"{func_name}({normalized_runid}, {normalized_config})")
        _upsert_migration_row(
            run_root,
            normalized_runid,
            normalized_config,
            normalized_host,
            original_url,
            owner_email,
            pulled_at,
            "EXCEPTION",
            None,
        )
        raise
    finally:
        if spec_file and hasattr(spec_file, "exists") and hasattr(spec_file, "unlink"):
            try:
                if spec_file.exists():
                    spec_file.unlink()
            except OSError:
                pass
