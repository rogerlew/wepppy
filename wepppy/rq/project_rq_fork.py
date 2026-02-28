from __future__ import annotations

import os
import queue
import shutil
import threading
import time
from glob import glob
from subprocess import PIPE, Popen
from typing import Any, Callable, TextIO


def _clean_env_for_system_tools() -> dict[str, str]:
    """Return a sanitized environment for invoking system binaries."""
    return {
        "PATH": "/usr/sbin:/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
    }


def _build_fork_rsync_cmd(run_right: str, *, undisturbify: bool) -> list[str]:
    cmd = ["rsync", "-av", "--progress"]
    # Archive staging artifacts are ephemeral and should not be synced into forked runs.
    if undisturbify:
        cmd.extend(["--exclude", "wepp/runs", "--exclude", "wepp/output"])
    cmd.extend([".", run_right])
    return cmd


def _stream_reader(stream: TextIO, output_queue: queue.Queue[str]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output_queue.put(line)
    finally:
        stream.close()


def _run_rsync_with_live_output(
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

    stdout_q: queue.Queue[str] = queue.Queue()
    stderr_q: queue.Queue[str] = queue.Queue()
    stdout_thread = threading.Thread(target=_stream_reader, args=(p.stdout, stdout_q))
    stderr_thread = threading.Thread(target=_stream_reader, args=(p.stderr, stderr_q))
    stdout_thread.start()
    stderr_thread.start()

    stdout_output: list[str] = []
    stderr_output: list[str] = []

    while p.poll() is None:
        while not stdout_q.empty():
            line = stdout_q.get()
            publish_status(status_channel, line)
            stdout_output.append(line)

        while not stderr_q.empty():
            line = stderr_q.get()
            publish_status(status_channel, f"rsync stderr: {line}")
            stderr_output.append(line)

        time.sleep(0.01)

    p.wait()
    stdout_thread.join()
    stderr_thread.join()

    while not stdout_q.empty():
        line = stdout_q.get()
        stripped_line = line.strip()
        if stripped_line:
            publish_status(status_channel, stripped_line)
        stdout_output.append(line)

    while not stderr_q.empty():
        line = stderr_q.get()
        stripped_line = line.strip()
        if stripped_line:
            publish_status(status_channel, f"rsync stderr: {stripped_line}")
        stderr_output.append(line)

    if p.returncode != 0:
        full_stdout = "".join(stdout_output).strip()
        full_stderr = "".join(stderr_output).strip()
        error_msg = (
            f"ERROR: rsync failed with return code {p.returncode}:\n"
            f"stdout:\n---\n{full_stdout}\n---\n"
            f"stderr:\n---\n{full_stderr}\n---"
        )
        publish_status(status_channel, error_msg)
        raise RuntimeError(error_msg)


def prepare_fork_run(
    runid: str,
    new_runid: str,
    *,
    undisturbify: bool,
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
    build_rsync_cmd: Callable[[str, bool], list[str]] = (
        lambda run_right, undisturbify: _build_fork_rsync_cmd(
            run_right,
            undisturbify=undisturbify,
        )
    ),
    clean_env_for_system_tools: Callable[[], dict[str, str]] = _clean_env_for_system_tools,
) -> str:
    if mutate_root_fn is None:
        from wepppy.runtime_paths.mutations import mutate_root as mutate_root_fn

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

    cmd = build_rsync_cmd(run_right, undisturbify)

    _cmd = " ".join(cmd)
    publish_status(status_channel, f"Running cmd: {_cmd}")
    publish_status(status_channel, f"In directory: {run_left}")

    env = clean_env_for_system_tools()
    _run_rsync_with_live_output(
        cmd=cmd,
        run_left=run_left,
        status_channel=status_channel,
        publish_status=publish_status,
        env=env,
    )

    publish_status(status_channel, "rsync successful. Setting wd in .nodbs...\n")

    nodbs = glob(os.path.join(new_wd, "*.nodb"))
    for fn in nodbs:
        publish_status(status_channel, f"  {fn}")
        with open(fn) as fp:
            s = fp.read()

        s = s.replace(wd, new_wd).replace(runid, new_runid)

        # Normalize legacy path patterns to canonical /wc1/runs/ format
        # This handles cases where source nodb files contain old paths.
        for src_pattern, dst_pattern in [
            ("/geodata/wc1/runs/", "/wc1/runs/"),
            ("/geodata/weppcloud_runs/", "/wc1/runs/"),
        ]:
            s = s.replace(src_pattern, dst_pattern)

        with open(fn, "w") as fp:
            fp.write(s)

    publish_status(status_channel, "Setting wd in .nodbs... done.\n")
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

        publish_status(status_channel, "Undisturbifying Project...\n")
        ron = ron_cls.getInstance(new_wd)
        ron.scenario = "Undisturbed"

        publish_status(status_channel, "Removing SBS...\n")
        disturbed = disturbed_cls.getInstance(new_wd)
        disturbed.remove_sbs()
        publish_status(status_channel, "Removing SBS... done.\n")

        publish_status(status_channel, "Rebuilding Landuse...\n")
        landuse = landuse_cls.getInstance(new_wd)
        mutate_root_fn(
            new_wd,
            "landuse",
            lambda: landuse.build(),
            purpose="fork-undisturbify-build-landuse",
        )
        publish_status(status_channel, "Rebuilding Landuse... done.\n")

        publish_status(status_channel, "Rebuilding Soils...\n")
        soils = soils_cls.getInstance(new_wd)
        mutate_root_fn(
            new_wd,
            "soils",
            lambda: soils.build(),
            purpose="fork-undisturbify-build-soils",
        )
        publish_status(status_channel, "Rebuilding Soils... done.\n")

    return new_wd
