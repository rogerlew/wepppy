from __future__ import annotations

import os
import shutil
import threading
import time
from collections import deque
from glob import glob
import json
from subprocess import PIPE, Popen
import tempfile
from typing import Any, Callable, TextIO


FORK_RSYNC_HEARTBEAT_PREFIX = "FORK_HEARTBEAT "
FORK_RSYNC_HEARTBEAT_SECONDS = 10.0
FORK_RSYNC_TAIL_LINES = 200


def _clean_env_for_system_tools() -> dict[str, str]:
    """Return a sanitized environment for invoking system binaries."""
    return {
        "PATH": "/usr/sbin:/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
    }


def _build_fork_rsync_cmd(
    run_right: str,
    *,
    undisturbify: bool,
    skip_wepp_runs_output: bool = False,
) -> list[str]:
    cmd = ["rsync", "-a", "--stats"]
    skip_wepp_copy = undisturbify or skip_wepp_runs_output
    # Archive staging artifacts are ephemeral and should not be synced into forked runs.
    if skip_wepp_copy:
        cmd.extend(["--exclude", "wepp/runs", "--exclude", "wepp/output"])
    cmd.extend([".", run_right])
    return cmd


def _ensure_wepp_run_and_output_dirs(new_wd: str) -> None:
    os.makedirs(os.path.join(new_wd, "wepp", "runs"), exist_ok=True)
    os.makedirs(os.path.join(new_wd, "wepp", "output"), exist_ok=True)


def _normalize_interactive_fork_nodb_identity(
    text: str,
    *,
    path: str,
) -> tuple[str, str | None]:
    """Clear copied grouped-run identity in one root NoDb JSON payload."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid NoDb JSON after fork copy: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in forked NoDb payload: {path}")

    state = payload.get("py/state", payload)
    if not isinstance(state, dict):
        raise ValueError(f"Expected object-valued py/state in forked NoDb payload: {path}")

    run_group = state.get("_run_group")
    group_name = state.get("_group_name")
    if run_group is None and group_name in (None, ""):
        return text, None

    if run_group is None:
        raise ValueError(
            f"Inconsistent grouped-run identity in forked NoDb payload: {path}"
        )
    if run_group != "batch":
        raise ValueError(
            f"Refusing to normalize non-batch run_group {run_group!r} in {path}"
        )
    if not isinstance(group_name, str) or not group_name.strip():
        raise ValueError(f"Batch controller lacks a valid group_name in {path}")

    state["_run_group"] = None
    state["_group_name"] = None

    normalized = json.dumps(payload, ensure_ascii=False)
    if text.endswith("\n"):
        normalized += "\n"
    return normalized, group_name


def _require_regular_fork_root_nodb(path: str) -> None:
    """Reject root NoDb symlinks and irregular files before any rewrite."""
    if os.path.islink(path) or not os.path.isfile(path):
        raise ValueError(
            f"Forked root NoDb path must be a regular non-symlink file: {path}"
        )


def _atomic_write_fork_text(path: str, text: str) -> None:
    """Publish one rewritten fork file without exposing partial JSON."""
    source_stat = os.stat(path)
    parent = os.path.dirname(path)
    fd, temp_path = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", dir=parent)
    try:
        os.fchmod(fd, source_stat.st_mode & 0o7777)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except OSError:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def _batch_name_from_runid(runid: str, *, context: str) -> str | None:
    """Return a validated batch name encoded in a run ID, when present."""
    if not runid.startswith("batch;;"):
        return None
    parts = runid.split(";;")
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise ValueError(f"Malformed batch runid in {context}: {runid!r}")
    return parts[1]


def _copied_batch_run_metadata_plan(
    new_wd: str,
    source_runid: str,
) -> tuple[str, str, str] | None:
    """Preflight copied execution metadata and identify validated batch metadata."""
    source_batch_name = _batch_name_from_runid(
        source_runid,
        context="fork source",
    )
    metadata_path = os.path.join(new_wd, "run_metadata.json")
    if not os.path.lexists(metadata_path):
        return None
    if os.path.islink(metadata_path) or not os.path.isfile(metadata_path):
        raise ValueError(
            f"Copied run metadata must be a regular non-symlink file: {metadata_path}"
        )

    try:
        with open(metadata_path, encoding="utf-8") as stream:
            original_text = stream.read()
        payload = json.loads(original_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid copied run metadata JSON: {metadata_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in copied run metadata: {metadata_path}")

    metadata_runid = payload.get("runid")
    if metadata_runid is not None and not isinstance(metadata_runid, str):
        raise ValueError(f"Invalid runid in copied run metadata: {metadata_path}")
    metadata_batch_name = payload.get("batch_name")
    if metadata_batch_name is not None and (
        not isinstance(metadata_batch_name, str) or not metadata_batch_name.strip()
    ):
        raise ValueError(f"Invalid batch_name in copied run metadata: {metadata_path}")

    encoded_batch_name = (
        _batch_name_from_runid(metadata_runid, context=metadata_path)
        if isinstance(metadata_runid, str)
        else None
    )
    has_batch_marker = encoded_batch_name is not None or metadata_batch_name is not None
    if has_batch_marker and (
        encoded_batch_name is None or metadata_batch_name is None
    ):
        raise ValueError(
            f"Incomplete batch identity in copied run metadata: {metadata_path}"
        )
    if (
        encoded_batch_name is not None
        and encoded_batch_name != metadata_batch_name
    ):
        raise ValueError(
            f"Conflicting batch names in copied run metadata: {metadata_path}"
        )
    if (
        source_batch_name is not None
        and encoded_batch_name is not None
        and source_batch_name != encoded_batch_name
    ):
        raise ValueError(
            f"Copied batch metadata does not match fork source: {metadata_path}"
        )
    if source_batch_name is not None and encoded_batch_name is None:
        raise ValueError(
            f"Batch fork source has non-batch copied run metadata: {metadata_path}"
        )

    if encoded_batch_name is None:
        return None
    return metadata_path, original_text, encoded_batch_name


def _remove_copied_batch_run_metadata(new_wd: str, source_runid: str) -> bool:
    """Remove source execution metadata when the fork source is a batch leaf."""
    plan = _copied_batch_run_metadata_plan(new_wd, source_runid)
    if plan is None:
        return False
    metadata_path, original_text, _batch_name = plan
    with open(metadata_path, encoding="utf-8") as stream:
        if stream.read() != original_text:
            raise RuntimeError(
                f"Copied run metadata changed after fork preflight: {metadata_path}"
            )
    os.unlink(metadata_path)
    return True


def _rollback_fork_nodb_rewrites(
    written: list[tuple[str, str, str]],
) -> None:
    """Restore already-published root rewrites unless another writer intervened."""
    conflicts: list[str] = []
    for path, original_text, rewritten_text in reversed(written):
        try:
            with open(path, encoding="utf-8") as stream:
                current_text = stream.read()
        except OSError as exc:
            conflicts.append(f"{path}: cannot verify rollback target ({exc})")
            continue
        if current_text != rewritten_text:
            conflicts.append(f"{path}: changed after fork rewrite")
            continue
        try:
            _atomic_write_fork_text(path, original_text)
        except OSError as exc:
            conflicts.append(f"{path}: restore failed ({exc})")

    if conflicts:
        raise RuntimeError(
            "Fork root rollback requires manual recovery: " + "; ".join(conflicts)
        )


def _clear_reports_cache(
    run_wd: str,
    *,
    status_channel: str,
    publish_status: Callable[[str, str], None],
) -> None:
    cache_root = os.path.join(run_wd, "wepp", "reports", "cache")
    publish_status(status_channel, "Clearing WEPP reports cache...\n")
    if os.path.isdir(cache_root):
        shutil.rmtree(cache_root)
        publish_status(status_channel, "Clearing WEPP reports cache... done.\n")
        return
    publish_status(status_channel, "No WEPP reports cache directory to clear.\n")


def _clear_export_dir(
    run_wd: str,
    *,
    status_channel: str,
    publish_status: Callable[[str, str], None],
) -> None:
    export_root = os.path.join(run_wd, "export")
    publish_status(status_channel, "Clearing export directory...\n")
    if os.path.isdir(export_root):
        shutil.rmtree(export_root)
    os.makedirs(export_root, exist_ok=True)
    publish_status(status_channel, "Clearing export directory... done.\n")


def _clear_query_engine_catalog_cache(
    run_wd: str,
    *,
    status_channel: str,
    publish_status: Callable[[str, str], None],
) -> None:
    query_engine_root = os.path.join(run_wd, "_query_engine")
    catalog_path = os.path.join(query_engine_root, "catalog.json")
    cache_dir = os.path.join(query_engine_root, "cache")

    publish_status(status_channel, "Clearing query engine catalog cache...\n")
    removed = False
    if os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)
        removed = True
    if os.path.isfile(catalog_path):
        os.remove(catalog_path)
        removed = True

    if removed:
        publish_status(status_channel, "Clearing query engine catalog cache... done.\n")
        return
    publish_status(status_channel, "No query engine catalog cache artifacts to clear.\n")


def _stream_reader(stream: TextIO, output_tail: deque[str]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output_tail.append(line)
    finally:
        stream.close()


def _format_elapsed(elapsed_seconds: float) -> str:
    total_seconds = max(0, int(elapsed_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_output_tail(output_tail: deque[str]) -> str:
    lines = [line.strip() for line in output_tail if line.strip()]
    return "\n".join(lines)


def _run_rsync_with_bounded_output(
    *,
    cmd: list[str],
    run_left: str,
    status_channel: str,
    publish_status: Callable[[str, str], None],
    env: dict[str, str],
) -> None:
    p = Popen(
        cmd,
        stdout=PIPE,
        stderr=PIPE,
        cwd=run_left,
        text=True,
        bufsize=1,
        env=env,
    )

    assert p.stdout is not None
    assert p.stderr is not None
    stdout_tail: deque[str] = deque(maxlen=FORK_RSYNC_TAIL_LINES)
    stderr_tail: deque[str] = deque(maxlen=FORK_RSYNC_TAIL_LINES)
    stdout_thread = threading.Thread(target=_stream_reader, args=(p.stdout, stdout_tail))
    stderr_thread = threading.Thread(target=_stream_reader, args=(p.stderr, stderr_tail))
    stdout_thread.start()
    stderr_thread.start()

    started_at = time.monotonic()
    next_heartbeat_at = started_at + FORK_RSYNC_HEARTBEAT_SECONDS

    while p.poll() is None:
        now = time.monotonic()
        if now >= next_heartbeat_at:
            elapsed = _format_elapsed(now - started_at)
            publish_status(
                status_channel,
                f"{FORK_RSYNC_HEARTBEAT_PREFIX}Copy in progress - elapsed {elapsed}",
            )
            next_heartbeat_at = now + FORK_RSYNC_HEARTBEAT_SECONDS
        time.sleep(0.1)

    p.wait()
    stdout_thread.join()
    stderr_thread.join()

    stdout_summary = _format_output_tail(stdout_tail)
    stderr_summary = _format_output_tail(stderr_tail)

    if p.returncode != 0:
        error_msg = (
            f"ERROR: rsync failed with return code {p.returncode}:\n"
            f"stdout tail:\n---\n{stdout_summary or '<no stdout captured>'}\n---\n"
            f"stderr tail:\n---\n{stderr_summary or '<no stderr captured>'}\n---"
        )
        publish_status(status_channel, error_msg)
        raise RuntimeError(error_msg)

    if stdout_summary:
        publish_status(status_channel, f"rsync summary:\n{stdout_summary}")
    if stderr_summary:
        publish_status(status_channel, f"rsync stderr summary:\n{stderr_summary}")


def prepare_fork_run(
    runid: str,
    new_runid: str,
    *,
    undisturbify: bool,
    skip_wepp_runs_output: bool = False,
    status_channel: str,
    publish_status: Callable[[str, str], None],
    get_wd: Callable[[str], str],
    get_primary_wd: Callable[[str], str],
    wait_for_paths: Callable[..., Any],
    ron_cls: Any,
    disturbed_cls: Any,
    landuse_cls: Any,
    soils_cls: Any,
    initialize_ttl: Callable[[str], None] | None,
    format_ttl_failure: Callable[[Exception], str] | None = None,
    mutate_root_fn: Callable[..., Any] | None = None,
    clear_nodb_cache_fn: Callable[..., Any] | None = None,
    build_rsync_cmd: Callable[[str, bool, bool], list[str]] = (
        lambda run_right, undisturbify, skip_wepp_runs_output: _build_fork_rsync_cmd(
            run_right,
            undisturbify=undisturbify,
            skip_wepp_runs_output=skip_wepp_runs_output,
        )
    ),
    clean_env_for_system_tools: Callable[[], dict[str, str]] = _clean_env_for_system_tools,
) -> str:
    if mutate_root_fn is None:
        from wepppy.runtime_paths.mutations import mutate_root as mutate_root_fn
    if clear_nodb_cache_fn is None:
        from wepppy.nodb.base import clear_nodb_file_cache as clear_nodb_cache_fn

    # 1. Verify rsync exists
    rsync_path = shutil.which("rsync")
    publish_status(status_channel, "Checking for rsync...")
    if not rsync_path:
        error_msg = "ERROR: 'rsync' command not found in PATH for rqworker user."
        publish_status(status_channel, error_msg)
        raise FileNotFoundError(error_msg)
    publish_status(status_channel, f"Found rsync at: {rsync_path}")

    wd = get_wd(runid)
    new_wd = get_primary_wd(new_runid)

    run_left = wd if wd.endswith("/") else f"{wd}/"
    run_right = new_wd if new_wd.endswith("/") else f"{new_wd}/"

    # 2. Verify destination directory can be created
    right_parent = os.path.dirname(run_right.rstrip("/"))
    publish_status(status_channel, f"Destination parent directory: {right_parent}")
    if not os.path.exists(right_parent):
        publish_status(status_channel, "Parent does not exist. Creating...")
        os.makedirs(right_parent)
    else:
        publish_status(status_channel, "Parent already exists.")

    if not os.path.exists(right_parent):
        error_msg = f"FATAL: Failed to create parent directory: {right_parent}"
        publish_status(status_channel, error_msg)
        raise FileNotFoundError(error_msg)

    skip_wepp_copy = undisturbify or skip_wepp_runs_output
    cmd = build_rsync_cmd(run_right, undisturbify, skip_wepp_runs_output)

    _cmd = " ".join(cmd)
    publish_status(status_channel, f"Running cmd: {_cmd}")
    publish_status(status_channel, f"In directory: {run_left}")

    env = clean_env_for_system_tools()
    publish_status(status_channel, "Copying project files...")
    _run_rsync_with_bounded_output(
        cmd=cmd,
        run_left=run_left,
        status_channel=status_channel,
        publish_status=publish_status,
        env=env,
    )
    publish_status(status_channel, "Copying project files... done.")

    if skip_wepp_copy:
        _ensure_wepp_run_and_output_dirs(new_wd)
        publish_status(
            status_channel,
            "Ensured empty directories exist: wepp/runs and wepp/output.\n",
        )

    publish_status(status_channel, "rsync successful. Setting wd in .nodbs...\n")

    nodbs = sorted(glob(os.path.join(new_wd, "*.nodb")))
    rewrite_plan: list[tuple[str, str, str, str | None]] = []
    observed_batch_names: set[str] = set()
    source_batch_name = _batch_name_from_runid(runid, context="fork source")
    if source_batch_name is not None:
        observed_batch_names.add(source_batch_name)
    normalized_identity_count = 0
    for fn in nodbs:
        publish_status(status_channel, f"  {fn}")
        _require_regular_fork_root_nodb(fn)
        with open(fn, encoding="utf-8") as fp:
            original_text = fp.read()

        rewritten_text = original_text.replace(wd, new_wd).replace(runid, new_runid)

        # Normalize legacy path patterns to canonical /wc1/runs/ format
        # This handles cases where source nodb files contain old paths.
        for src_pattern, dst_pattern in [
            ("/geodata/wc1/runs/", "/wc1/runs/"),
            ("/geodata/weppcloud_runs/", "/wc1/runs/"),
        ]:
            rewritten_text = rewritten_text.replace(src_pattern, dst_pattern)

        rewritten_text, normalized_batch_name = _normalize_interactive_fork_nodb_identity(
            rewritten_text,
            path=fn,
        )
        if normalized_batch_name is not None:
            normalized_identity_count += 1
            observed_batch_names.add(normalized_batch_name)
        rewrite_plan.append(
            (fn, original_text, rewritten_text, normalized_batch_name)
        )

    metadata_plan = _copied_batch_run_metadata_plan(new_wd, runid)
    if metadata_plan is not None:
        observed_batch_names.add(metadata_plan[2])
    if len(observed_batch_names) > 1:
        raise ValueError(
            "Conflicting batch names across fork source state: "
            f"{sorted(observed_batch_names)!r}"
        )
    written: list[tuple[str, str, str]] = []
    try:
        for fn, original_text, rewritten_text, _identity_normalized in rewrite_plan:
            with open(fn, encoding="utf-8") as stream:
                if stream.read() != original_text:
                    raise RuntimeError(
                        f"Forked root NoDb changed after preflight: {fn}"
                    )
            _atomic_write_fork_text(fn, rewritten_text)
            written.append((fn, original_text, rewritten_text))

        if metadata_plan is not None:
            metadata_path, original_metadata, _metadata_batch_name = metadata_plan
            with open(metadata_path, encoding="utf-8") as stream:
                if stream.read() != original_metadata:
                    raise RuntimeError(
                        "Copied run metadata changed after fork preflight: "
                        f"{metadata_path}"
                    )
            os.unlink(metadata_path)
    except (OSError, RuntimeError) as exc:
        try:
            _rollback_fork_nodb_rewrites(written)
        except RuntimeError as rollback_exc:
            raise RuntimeError(f"{exc}; {rollback_exc}") from rollback_exc
        raise

    publish_status(status_channel, "Setting wd in .nodbs... done.\n")
    publish_status(
        status_channel,
        f"Normalized grouped-run identity in {normalized_identity_count} root .nodb files.\n",
    )

    if metadata_plan is not None:
        publish_status(status_channel, "Removed copied batch run_metadata.json.\n")

    publish_status(status_channel, "Cleanup locks, READONLY, PUBLIC...\n")

    for lock_file in glob(os.path.join(new_wd, "*.lock")):
        os.remove(lock_file)

    for special_file in ["READONLY", "PUBLIC"]:
        fn = os.path.join(new_wd, special_file)
        if os.path.exists(fn):
            os.remove(fn)

    publish_status(status_channel, "Cleanup locks, READONLY, PUBLIC... done.\n")

    if initialize_ttl is not None:
        try:
            initialize_ttl(new_wd)
        except Exception as exc:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/project_rq_fork.py:217", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            if format_ttl_failure is not None:
                message = format_ttl_failure(exc)
            else:
                message = f"STATUS TTL initialization failed ({exc})"
            publish_status(
                status_channel,
                message,
            )

    if undisturbify:
        publish_status(status_channel, "Waiting for forked .nodb files to settle...\n")
        required_nodbs = [
            os.path.join(new_wd, "ron.nodb"),
            os.path.join(new_wd, "wepp.nodb"),
            os.path.join(new_wd, "landuse.nodb"),
            os.path.join(new_wd, "soils.nodb"),
            os.path.join(new_wd, "disturbed.nodb"),
        ]
        wait_for_paths(required_nodbs, timeout_s=60.0)
        publish_status(status_channel, "Forked .nodb files ready.\n")
        _clear_reports_cache(
            new_wd,
            status_channel=status_channel,
            publish_status=publish_status,
        )
        _clear_export_dir(
            new_wd,
            status_channel=status_channel,
            publish_status=publish_status,
        )
        _clear_query_engine_catalog_cache(
            new_wd,
            status_channel=status_channel,
            publish_status=publish_status,
        )

        publish_status(status_channel, "Undisturbifying Project...\n")
        clear_nodb_cache_fn(new_runid, pup_relpath="ron.nodb")
        ron = ron_cls.getInstance(new_wd)
        ron.scenario = "Undisturbed"

        publish_status(status_channel, "Removing SBS...\n")
        clear_nodb_cache_fn(new_runid, pup_relpath="disturbed.nodb")
        disturbed = disturbed_cls.getInstance(new_wd)
        disturbed.remove_sbs()
        publish_status(status_channel, "Removing SBS... done.\n")

        publish_status(status_channel, "Rebuilding Landuse...\n")
        clear_nodb_cache_fn(new_runid, pup_relpath="landuse.nodb")
        landuse = landuse_cls.getInstance(new_wd)
        mutate_root_fn(
            new_wd,
            "landuse",
            lambda: landuse.build(),
            purpose="fork-undisturbify-build-landuse",
        )
        publish_status(status_channel, "Rebuilding Landuse... done.\n")

        publish_status(status_channel, "Rebuilding Soils...\n")
        clear_nodb_cache_fn(new_runid, pup_relpath="soils.nodb")
        soils = soils_cls.getInstance(new_wd)
        mutate_root_fn(
            new_wd,
            "soils",
            lambda: soils.build(),
            purpose="fork-undisturbify-build-soils",
        )
        publish_status(status_channel, "Rebuilding Soils... done.\n")

    return new_wd
