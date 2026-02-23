from __future__ import annotations

import errno
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class DeleteRuntime:
    get_current_job: Callable[[], Any]
    get_wd: Callable[[str], str]
    publish_status: Callable[[str, str], None]
    clear_nodb_file_cache: Callable[[str], Any]
    clear_locks: Callable[[str], Any]
    rmtree: Callable[[Path], None]
    sleep: Callable[[float], None]
    logger: logging.Logger


def _publish(runtime: DeleteRuntime, channel: str, message: str) -> None:
    runtime.publish_status(channel, message)


def _try_mark_delete_state(
    *,
    wd: str,
    state: str,
    touched_by: str,
    status_channel: str,
    job_id: str,
    runtime: DeleteRuntime,
    failure_label: str,
    db_cleared: bool | None = None,
) -> bool:
    try:
        from wepppy.weppcloud.utils.run_ttl import mark_delete_state

        mark_delete_state(
            wd,
            state,
            db_cleared=db_cleared,
            touched_by=touched_by,
        )
        return True
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:48", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(
            runtime,
            status_channel,
            f"rq:{job_id} STATUS {failure_label} ({exc})",
        )
        return False


def _delete_db_record(runid: str) -> None:
    from wepppy.weppcloud.utils.helpers import get_user_models

    Run, _User, user_datastore = get_user_models()
    run = Run.query.filter(Run.runid == runid).first()
    if run is not None:
        user_datastore.delete_run(run)


def delete_run_rq(runid: str, wd: str | None = None, *, delete_files: bool = False, runtime: DeleteRuntime) -> None:
    """Delete a run database record, optionally removing the run directory."""
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "delete_run_rq"
    status_channel = f"{runid}:wepp"
    _publish(runtime, status_channel, f"rq:{job_id} STARTED {func_name}({runid})")

    target = Path(wd or runtime.get_wd(runid)).resolve()
    attempts = 5
    delay_s = 0.5
    delete_failed = False
    delete_deferred = False
    delete_error: Exception | None = None
    deferred_errnos = {errno.ENOTEMPTY, errno.EACCES, errno.EBUSY}

    mark_failed = not _try_mark_delete_state(
        wd=str(target),
        state="queued",
        touched_by="delete_rq",
        status_channel=status_channel,
        job_id=str(job_id),
        runtime=runtime,
        failure_label="TTL delete mark failed",
    )

    if delete_files and target.exists():
        for attempt in range(1, attempts + 1):
            try:
                runtime.rmtree(target)
            except FileNotFoundError:
                break
            except OSError as exc:
                delete_error = exc
                if exc.errno in deferred_errnos:
                    delete_deferred = True
                    runtime.logger.warning(
                        "delete_run_rq deferred filesystem delete for %s (attempt %s/%s): %s",
                        target,
                        attempt,
                        attempts,
                        exc,
                    )
                    if attempt < attempts:
                        runtime.sleep(delay_s)
                        delay_s = min(delay_s * 2, 5.0)
                        continue
                    break
                delete_failed = True
                delete_deferred = False
                _publish(
                    runtime,
                    status_channel,
                    f"rq:{job_id} STATUS delete failed ({exc})",
                )
                break
            else:
                if not target.exists():
                    break
        if target.exists():
            if delete_error is None:
                delete_error = OSError(errno.ENOTEMPTY, f"Failed to remove {target}")
            if delete_deferred:
                runtime.logger.warning(
                    "delete_run_rq deferred filesystem delete for %s (directory still present)",
                    target,
                )
            else:
                delete_failed = True
                _publish(
                    runtime,
                    status_channel,
                    f"rq:{job_id} STATUS delete deferred (directory still present)",
                )

    if target.exists() and (delete_failed or delete_deferred or mark_failed):
        _try_mark_delete_state(
            wd=str(target),
            state="queued",
            touched_by="delete_deferred" if delete_deferred and not delete_failed else "delete_failed",
            status_channel=status_channel,
            job_id=str(job_id),
            runtime=runtime,
            failure_label="TTL delete retry failed",
        )

    try:
        cleared = runtime.clear_nodb_file_cache(runid)
        if cleared:
            _publish(
                runtime,
                status_channel,
                f"rq:{job_id} STATUS cleared {len(cleared)} NoDb cache entries",
            )
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:160", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(
            runtime,
            status_channel,
            f"rq:{job_id} STATUS failed to clear NoDb cache ({exc})",
        )

    try:
        runtime.clear_locks(runid)
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:169", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(
            runtime,
            status_channel,
            f"rq:{job_id} STATUS failed to clear NoDb locks ({exc})",
        )

    try:
        from flask import has_app_context
        from wepppy.weppcloud.app import app as flask_app

        if has_app_context():
            _delete_db_record(runid)
        else:
            with flask_app.app_context():
                _delete_db_record(runid)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:185", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(runtime, status_channel, f"rq:{job_id} EXCEPTION {func_name}({runid})")
        raise

    if target.exists():
        _try_mark_delete_state(
            wd=str(target),
            state="queued",
            db_cleared=True,
            touched_by="delete_rq",
            status_channel=status_channel,
            job_id=str(job_id),
            runtime=runtime,
            failure_label="TTL db_cleared mark failed",
        )
        if delete_files and delete_failed and delete_error is not None and not delete_deferred:
            _publish(
                runtime,
                status_channel,
                f"rq:{job_id} STATUS delete deferred ({delete_error})",
            )

    _publish(runtime, status_channel, f"rq:{job_id} COMPLETED {func_name}({runid})")


def gc_runs_rq(
    *,
    root: str = "/wc1/runs",
    limit: int = 200,
    dry_run: bool = False,
    runtime: DeleteRuntime,
) -> Mapping[str, Any]:
    """Delete runs whose TTL expiration has elapsed or are flagged for deletion."""
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "gc_runs_rq"
    status_channel = "gc:ttl"

    _publish(
        runtime,
        status_channel,
        f"rq:{job_id} STARTED {func_name}(root={root}, limit={limit}, dry_run={dry_run})",
    )

    try:
        from wepppy.weppcloud.utils.run_ttl import collect_gc_candidates, mark_delete_state
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:231", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(
            runtime,
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({exc})",
        )
        raise

    candidates = collect_gc_candidates(root=root, limit=limit)
    deleted = 0
    deferred = 0
    errors: list[dict[str, str]] = []

    for entry in candidates:
        runid = entry.get("runid")
        wd = entry.get("wd")
        reason = entry.get("reason", "unknown")
        if not runid or not wd:
            continue
        if dry_run:
            _publish(
                runtime,
                status_channel,
                f"rq:{job_id} STATUS dry-run delete {runid} ({reason})",
            )
            continue
        try:
            mark_delete_state(str(wd), "queued", touched_by="gc")
            delete_run_rq(str(runid), str(wd), delete_files=True, runtime=runtime)
            if Path(str(wd)).exists():
                deferred += 1
                runtime.logger.warning(
                    "gc_runs_rq deferred filesystem delete for %s (directory still present)",
                    runid,
                )
            else:
                deleted += 1
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:268", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            errors.append({"runid": str(runid), "error": str(exc)})
            _publish(
                runtime,
                status_channel,
                f"rq:{job_id} STATUS delete failed for {runid} ({exc})",
            )

    _publish(
        runtime,
        status_channel,
        f"rq:{job_id} COMPLETED {func_name}(expired={len(candidates)}, deleted={deleted}, deferred={deferred}, errors={len(errors)})",
    )

    return {
        "expired": len(candidates),
        "deleted": deleted,
        "deferred": deferred,
        "errors": errors,
    }


def compile_dot_logs_rq(
    *,
    access_log_path: str | None = None,
    run_locations_path: str | None = None,
    run_roots: list[str] | None = None,
    legacy_roots: list[str] | None = None,
    runtime: DeleteRuntime,
) -> Mapping[str, Any]:
    """Compile access logs and landing run-locations cache."""
    job = runtime.get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = "compile_dot_logs_rq"
    status_channel = "maintenance:access_log"

    _publish(
        runtime,
        status_channel,
        f"rq:{job_id} STARTED {func_name}",
    )

    try:
        from wepppy.weppcloud._scripts.compile_dot_logs import compile_dot_logs
    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_delete.py:312", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        _publish(
            runtime,
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({exc})",
        )
        raise

    result = compile_dot_logs(
        access_log_path=access_log_path,
        run_locations_path=run_locations_path,
        run_roots=run_roots,
        legacy_roots=legacy_roots,
    )

    _publish(
        runtime,
        status_channel,
        f"rq:{job_id} COMPLETED {func_name}",
    )

    return result
