"""RQ task to run migrations on a working directory."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from rq import get_current_job

from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging

STATUS_CHANNEL_SUFFIX = "migrations"
# Also publish to run_sync channel so the UI sees migration progress
SYNC_CHANNEL_SUFFIX = "run_sync"

__all__ = [
    "migrations_rq",
    "STATUS_CHANNEL_SUFFIX",
]


def _status_channel(runid: str) -> str:
    return f"{runid}:{STATUS_CHANNEL_SUFFIX}"


def _sync_channel(runid: str) -> str:
    return f"{runid}:{SYNC_CHANNEL_SUFFIX}"


def _publish_status(channel: str, job_id: str, label: str, detail: str | None = None) -> None:
    message = f"rq:{job_id} {label}"
    if detail:
        message = f"{message} {detail}"
    StatusMessenger.publish(channel, message)


def _setup_file_logger(wd: str) -> logging.Logger:
    """Set up a file logger for migrations in the working directory."""
    log_path = Path(wd) / "migrations.log"
    logger = logging.getLogger(f"migrations.{wd}")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


@with_exception_logging
def migrations_rq(
    wd: str,
    runid: str,
    *,
    archive_before: bool = False,
    migrations: Optional[List[str]] = None,
) -> dict:
    """
    Run all applicable migrations on a working directory.
    
    Args:
        wd: Working directory path
        runid: Run identifier for status channel
        archive_before: If True, create archive backup before migrations
        migrations: Optional list of specific migrations to run (defaults to all)
        
    Returns:
        Dictionary with migration results
    """
    job = get_current_job()
    job_id = job.id if job else "no-job"
    func_name = inspect.currentframe().f_code.co_name
    channel = _status_channel(runid)
    sync_channel = _sync_channel(runid)
    
    # Set up file logger
    file_logger = _setup_file_logger(wd)
    
    def publish_and_log(label: str, detail: str | None = None) -> None:
        """Publish to both channels and log to file."""
        _publish_status(channel, job_id, label, detail)
        _publish_status(sync_channel, job_id, label, detail)
        log_msg = f"{label}"
        if detail:
            log_msg = f"{label} {detail}"
        file_logger.info(log_msg)
    
    publish_and_log("STARTED", f"{func_name}({runid})")
    file_logger.info(f"Working directory: {wd}")
    file_logger.info(f"Archive before: {archive_before}")
    file_logger.info(f"Specific migrations: {migrations or 'all'}")
    
    try:
        # Archive before migrations if requested
        if archive_before:
            publish_and_log("ARCHIVING", "Creating backup archive before migrations")
            try:
                _run_archive_inline(wd, runid, job_id, channel, sync_channel, file_logger)
                publish_and_log("ARCHIVE_COMPLETE", "Backup archive created")
            except Exception as e:
                publish_and_log("ARCHIVE_FAILED", str(e))
                file_logger.error(f"Archive failed: {e}", exc_info=True)
                # Continue with migrations even if archive fails - just log the warning
        
        # Import migration runner
        from wepppy.tools.migrations.runner import run_all_migrations, MigrationResult
        
        def progress_callback(migration_name: str, message: str) -> None:
            publish_and_log("PROGRESS", message)
        
        publish_and_log("MIGRATING", "Running migrations")
        
        result: MigrationResult = run_all_migrations(
            wd,
            dry_run=False,
            migrations=migrations,
            on_progress=progress_callback,
        )
        
        if result.success:
            applied_str = ", ".join(result.applied) if result.applied else "none"
            publish_and_log("COMPLETED", f"Applied: {applied_str}")
            file_logger.info(f"Migrations completed successfully. Applied: {result.applied}, Skipped: {result.skipped}")
        else:
            errors_str = "; ".join(f"{k}: {v}" for k, v in result.errors.items())
            publish_and_log("FAILED", f"Errors: {errors_str}")
            file_logger.error(f"Migrations failed. Errors: {result.errors}")
        
        publish_and_log("TRIGGER", "migrations MIGRATION_COMPLETE")
        
        return result.to_dict()
        
    except Exception as e:
        publish_and_log("EXCEPTION", str(e))
        file_logger.error(f"Migration exception: {e}", exc_info=True)
        raise


def _run_archive_inline(wd: str, runid: str, job_id: str, channel: str, sync_channel: str, file_logger: logging.Logger) -> None:
    """
    Create an archive backup inline (not as separate RQ job).
    
    This is a simplified version of archive_rq that runs synchronously.
    """
    import os
    import zipfile
    from datetime import datetime
    from pathlib import Path
    
    archives_dir = Path(wd) / "archives"
    archives_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    archive_name = f'{runid}.pre_migration.{timestamp}.zip'
    archive_path = archives_dir / archive_name
    archive_path_tmp = archive_path.with_suffix('.zip.tmp')
    
    # Clean up any existing temp file
    if archive_path_tmp.exists():
        archive_path_tmp.unlink()
    
    _publish_status(channel, job_id, "ARCHIVING", f"Creating {archive_name}")
    _publish_status(sync_channel, job_id, "ARCHIVING", f"Creating {archive_name}")
    file_logger.info(f"Creating archive: {archive_name}")
    
    file_count = 0
    with zipfile.ZipFile(archive_path_tmp, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(wd):
            rel_root = os.path.relpath(root, wd)
            
            # Skip archives directory
            if rel_root.startswith('archives'):
                dirs[:] = []
                continue
            
            dirs[:] = [d for d in dirs if not os.path.relpath(os.path.join(root, d), wd).startswith('archives')]
            
            for filename in files:
                abs_path = os.path.join(root, filename)
                arcname = os.path.relpath(abs_path, wd)
                if not arcname.startswith('archives'):
                    zf.write(abs_path, arcname)
                    file_count += 1
    
    # Atomic rename
    archive_path_tmp.rename(archive_path)
    
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    _publish_status(channel, job_id, "ARCHIVING", f"Archive ready: {archive_name}")
    _publish_status(sync_channel, job_id, "ARCHIVING", f"Archive ready: {archive_name}")
    file_logger.info(f"Archive ready: {archive_name} ({file_count} files, {size_mb:.2f} MB)")
