from __future__ import annotations

import json
import os
import sys
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence, Tuple

ZERO_SHA = "0" * 40
MAX_FILE_BYTES = 50 * 1024 * 1024
ALLOWED_PREFIXES = ("wepp/runs/", "swat/TxtInOut/")
IGNORED_PATHS = {"wepp/runs/tc_out.txt"}
PARSER_EXTS = {".cli", ".sol", ".man", ".slp"}


def _run_git(args: Sequence[str], *, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
    )


def _git_output(args: Sequence[str], *, text: bool = True) -> str | bytes:
    result = _run_git(args, text=text)
    if result.returncode != 0:
        stderr = result.stderr.strip() if text else result.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def _parse_updates(lines: Iterable[str]) -> list[Tuple[str, str, str]]:
    updates: list[Tuple[str, str, str]] = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) != 3:
            continue
        updates.append((parts[0], parts[1], parts[2]))
    return updates


def _parse_name_status(payload: bytes) -> list[Tuple[str, str, str | None]]:
    entries: list[Tuple[str, str, str | None]] = []
    parts = payload.split(b"\x00")
    idx = 0
    while idx < len(parts):
        if not parts[idx]:
            idx += 1
            continue
        status = parts[idx].decode("utf-8", errors="ignore")
        idx += 1
        if status.startswith(("R", "C")):
            if idx + 1 >= len(parts):
                break
            old_path = parts[idx].decode("utf-8", errors="ignore")
            new_path = parts[idx + 1].decode("utf-8", errors="ignore")
            entries.append((status, old_path, new_path))
            idx += 2
        else:
            if idx >= len(parts):
                break
            path = parts[idx].decode("utf-8", errors="ignore")
            entries.append((status, path, None))
            idx += 1
    return entries


def _diff_paths(old_sha: str, new_sha: str) -> list[Tuple[str, str, str | None]]:
    if old_sha == ZERO_SHA:
        payload = _git_output(["diff-tree", "--no-commit-id", "-r", "--name-status", "-z", new_sha], text=False)
    else:
        payload = _git_output(
            ["diff-tree", "--no-commit-id", "-r", "--name-status", "-z", old_sha, new_sha],
            text=False,
        )
    return _parse_name_status(payload)


def _resolve_auth_user() -> str:
    user = os.environ.get("HTTP_X_AUTH_USER") or os.environ.get("REMOTE_USER")
    if not user:
        raise RuntimeError("Missing authenticated user for bootstrap push")
    return user


def _git_dir() -> Path:
    output = _git_output(["rev-parse", "--git-dir"]).strip()
    path = Path(output)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _push_log_path() -> Path:
    return _git_dir() / "bootstrap" / "push-log.ndjson"


def _list_new_commits(old_sha: str, new_sha: str) -> list[str]:
    if old_sha == ZERO_SHA:
        output = _git_output(["rev-list", "--reverse", new_sha])
    else:
        output = _git_output(["rev-list", "--reverse", f"{old_sha}..{new_sha}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def _append_push_log(user: str, updates: list[Tuple[str, str, str]]) -> None:
    entries: list[Tuple[str, str]] = []
    seen: set[str] = set()
    for old_sha, new_sha, ref in updates:
        for sha in _list_new_commits(old_sha, new_sha):
            if sha in seen:
                continue
            seen.add(sha)
            entries.append((sha, ref))

    if not entries:
        return

    log_path = _push_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(log_path, "a") as handle:
        for sha, ref in entries:
            handle.write(json.dumps({"sha": sha, "user": user, "ref": ref, "time": timestamp}) + "\n")


def _list_run_files(commit: str) -> list[str]:
    output = _git_output(["ls-tree", "-r", "--name-only", commit])
    return [line.strip() for line in output.splitlines() if line.strip().endswith(".run")]


def _blob_id(commit: str, path: str) -> str | None:
    output = _git_output(["ls-tree", commit, "--", path])
    if not output.strip():
        return None
    parts = output.strip().split()
    if len(parts) < 3:
        return None
    return parts[2]


def _ensure_run_files_unchanged(new_sha: str, baseline_sha: str) -> None:
    baseline = set(_list_run_files(baseline_sha))
    current = set(_list_run_files(new_sha))
    for path in sorted(baseline | current):
        base_blob = _blob_id(baseline_sha, path)
        new_blob = _blob_id(new_sha, path)
        if base_blob != new_blob:
            raise RuntimeError(f".run files are read-only; change detected in {path}")


def _validate_path(path: str) -> None:
    if ".." in Path(path).parts:
        raise RuntimeError(f"Invalid path '{path}'")
    if path in IGNORED_PATHS:
        raise RuntimeError(f"{path} is not allowed")
    if not any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise RuntimeError(f"Path '{path}' is outside allowed directories")


def _tree_entry_mode(commit: str, path: str) -> str:
    output = _git_output(["ls-tree", "-z", commit, "--", path], text=False)
    if not output:
        return ""
    header = output.split(b"\t", 1)[0].decode("utf-8", errors="ignore")
    return header.split()[0] if header else ""


def _load_blob(commit: str, path: str) -> bytes:
    output = _git_output(["cat-file", "-p", f"{commit}:{path}"], text=False)
    return output


def _validate_blob(commit: str, path: str) -> Tuple[str, bytes] | None:
    _validate_path(path)

    mode = _tree_entry_mode(commit, path)
    if mode == "120000":
        raise RuntimeError(f"Symlinks are not allowed: {path}")
    if mode == "160000":
        raise RuntimeError(f"Submodules are not allowed: {path}")

    size_raw = _git_output(["cat-file", "-s", f"{commit}:{path}"])
    size = int(size_raw.strip())
    if size > MAX_FILE_BYTES:
        raise RuntimeError(f"{path} exceeds {MAX_FILE_BYTES} bytes")

    data = _load_blob(commit, path)
    if b"\x00" in data:
        raise RuntimeError(f"{path} appears to be binary")

    suffix = Path(path).suffix.lower()
    if suffix in PARSER_EXTS:
        return path, data
    return None


def _parse_file(entry: Tuple[str, bytes]) -> None:
    path, data = entry
    suffix = Path(path).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(data)
        handle.flush()
        tmp_name = handle.name
    try:
        if suffix == ".cli":
            from wepppy.climates.cligen.cligen import ClimateFile

            ClimateFile(tmp_name)
        elif suffix == ".sol":
            from wepppy.wepp.soils.utils.wepp_soil_util import WeppSoilUtil

            WeppSoilUtil(tmp_name)
        elif suffix == ".man":
            from wepppy.wepp.management.managements import read_management

            read_management(tmp_name)
        elif suffix == ".slp":
            from wepppy.topo.watershed_abstraction.slope_file import SlopeFile, mofe_distance_fractions

            try:
                SlopeFile(tmp_name)
            except AssertionError:
                mofe_distance_fractions(tmp_name)
        else:
            raise RuntimeError(f"Unsupported validation type for {path}")
    finally:
        os.unlink(tmp_name)


def _validate_with_pool(entries: list[Tuple[str, bytes]]) -> None:
    if not entries:
        return
    max_workers = min(len(entries), max(os.cpu_count() or 1, 1))
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_parse_file, entry): entry[0] for entry in entries}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                for pending in futures:
                    if not pending.done():
                        pending.cancel()
                raise RuntimeError(f"{futures[future]} failed validation: {exc}") from exc


def main() -> int:
    auth_user = _resolve_auth_user()
    updates = _parse_updates(sys.stdin)
    if not updates:
        return 0

    baseline_main = _git_output(["rev-parse", "refs/heads/main"]).strip()

    parser_entries: list[Tuple[str, bytes]] = []
    for old_sha, new_sha, ref in updates:
        if new_sha == ZERO_SHA:
            raise RuntimeError(f"Ref deletion not allowed: {ref}")

        _ensure_run_files_unchanged(new_sha, baseline_main)

        for status, path, path2 in _diff_paths(old_sha, new_sha):
            if status.startswith(("R", "C")):
                raise RuntimeError(f"Rename/copy not allowed: {path} -> {path2}")
            if status.startswith("D"):
                if path and any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                    raise RuntimeError(f"Deleting inputs is not allowed: {path}")
                continue
            if not path:
                continue
            entry = _validate_blob(new_sha, path)
            if entry is not None:
                parser_entries.append(entry)

    _validate_with_pool(parser_entries)
    _append_push_log(auth_user, updates)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        sys.stderr.write(f"Bootstrap validation failed: {exc}\n")
        sys.exit(1)
