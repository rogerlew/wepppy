#!/usr/bin/env python3
"""Observe remote integration without modifying a checkout or claiming release approval."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import uuid


class IntegrationError(RuntimeError):
    """An explicit integration proof failure, safe to print without Git credentials."""


def git(repo: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> str:
    # --repo, or the hook working directory, is the sole repository selector.
    # Git hooks export repository variables; callers may also have stale values
    # from another checkout. Neither may redirect this subprocess elsewhere.
    selection = {
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE",
        "GIT_PREFIX", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
        "GIT_CONFIG",
    }
    env = {key: value for key, value in os.environ.items()
           if key not in selection and not key.startswith("GIT_CONFIG_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1")
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], env=env,
                                capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise IntegrationError("GIT_TIMEOUT: remote truth is unavailable") from exc
    if result.returncode not in allowed:
        raise IntegrationError(f"GIT_FAILED: {args[0]} failed; no integration proof")
    return result.stdout.strip()


def ancestor(repo: Path, older: str, newer: str) -> bool:
    # rev-list avoids treating an execution error as an ordinary ancestry miss.
    return git(repo, "rev-list", "--count", f"{newer}..{older}") == "0"


def remote_identity(repo: Path, remote: str) -> str:
    if remote not in git(repo, "remote").splitlines():
        raise IntegrationError("UNKNOWN_REMOTE: require a configured remote name")
    value = git(repo, "remote", "get-url", remote)
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.password or parsed.query or parsed.fragment or (
            parsed.username and parsed.scheme != "ssh"
        ):
            raise IntegrationError("REMOTE_CREDENTIALS: use a credential-free remote URL")
    elif not re.match(r"[^/]+@[^:]+:", value):
        value = str((repo / value).resolve())
    return value


def observe(repo: Path, remote: str, branch: str, accepted: str,
            expected: str | None = None) -> dict[str, object]:
    git(repo, "check-ref-format", f"refs/heads/{branch}")
    if git(repo, "rev-parse", "--is-shallow-repository") != "false":
        raise IntegrationError("SHALLOW_HISTORY: a complete history is required")
    identity = remote_identity(repo, remote)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", accepted):
        raise IntegrationError("ACCEPTED_SHA_REQUIRED: use a full immutable commit ID")
    accepted = git(repo, "rev-parse", "--verify", f"{accepted}^{{commit}}")
    ref = f"refs/integration-observations/{uuid.uuid4().hex}"
    try:
        git(repo, "fetch", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules",
            remote, f"refs/heads/{branch}:{ref}")
        observed = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
        if expected is not None and observed != expected:
            raise IntegrationError("REMOTE_MOVED: observed target differs from expected SHA")
        if not ancestor(repo, accepted, observed):
            raise IntegrationError("NOT_INTEGRATED: accepted commit is absent from remote history")
        return {"schema_version": 1, "claim": "remote_integration_snapshot",
                "integration_mode": "merge-preserving", "remote": remote,
                "repository": identity, "branch": branch, "accepted_sha": accepted,
                "observed_remote_sha": observed,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "validation_scope": "ancestry-only; not behavioral acceptance or release approval"}
    finally:
        git(repo, "update-ref", "-d", ref)


def write_receipt(path: Path, receipt: dict[str, object]) -> None:
    path = path.absolute()
    fd, temporary = tempfile.mkstemp(prefix=".integration-receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Link publishes an already complete file and atomically refuses clobber.
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def read_receipt(path: Path) -> dict[str, object]:
    if path.stat().st_size > 16384:
        raise IntegrationError("INVALID_RECEIPT: oversized record")
    receipt = json.loads(path.read_text())
    required = {"schema_version", "claim", "integration_mode", "remote", "repository",
                "branch", "accepted_sha", "observed_remote_sha", "observed_at", "validation_scope"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise IntegrationError("INVALID_RECEIPT: unknown or missing fields")
    if receipt["schema_version"] != 1 or receipt["claim"] != "remote_integration_snapshot" \
            or receipt["integration_mode"] != "merge-preserving":
        raise IntegrationError("INVALID_RECEIPT: unsupported claim or integration mode")
    if any(not isinstance(receipt[key], str) for key in required - {"schema_version"}):
        raise IntegrationError("INVALID_RECEIPT: invalid field types")
    for field in ("accepted_sha", "observed_remote_sha"):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", receipt[field]):
            raise IntegrationError("INVALID_RECEIPT: invalid commit identity")
    timestamp = datetime.fromisoformat(receipt["observed_at"])
    if timestamp.utcoffset() is None:
        raise IntegrationError("INVALID_RECEIPT: observation requires a timezone")
    return receipt


def protect_reference_transaction(state: str) -> None:
    if state != "prepared":
        return
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 3:
            raise IntegrationError("INVALID_REF_TRANSACTION")
        old, new, ref = fields
        if ref != "refs/heads/master":
            continue
        if set(new) == {"0"}:
            raise IntegrationError("PROTECTED_MASTER: deletion is prohibited")
        if set(old) == {"0"}:
            old = git(Path.cwd(), "rev-parse", "--verify", "--quiet", ref, allowed=(0, 1))
        if old and not ancestor(Path.cwd(), old, new):
            raise IntegrationError("PROTECTED_MASTER: preserve history with a merge; rewrite refused")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    hook = commands.add_parser("reference-transaction", help=argparse.SUPPRESS)
    hook.add_argument("state")
    for name in ("receipt", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("--repo", type=Path, default=Path.cwd())
        sub.add_argument("--remote", default="origin")
        sub.add_argument("--branch", default="master")
        sub.add_argument("--expected-remote-sha")
        if name == "receipt":
            sub.add_argument("--accepted", required=True)
            sub.add_argument("--output", required=True, type=Path)
        else:
            sub.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "reference-transaction":
            protect_reference_transaction(args.state)
            return 0
        repo = args.repo.resolve()
        if args.command == "receipt":
            snapshot = observe(repo, args.remote, args.branch, args.accepted, args.expected_remote_sha)
            write_receipt(args.output, snapshot)
        else:
            saved = read_receipt(args.receipt)
            if (saved["repository"], saved["remote"], saved["branch"]) != (
                remote_identity(repo, args.remote), args.remote, args.branch
            ):
                raise IntegrationError("WRONG_TARGET: receipt repository/remote/branch mismatch")
            snapshot = observe(repo, args.remote, args.branch, saved["accepted_sha"], args.expected_remote_sha)
            if not ancestor(repo, saved["observed_remote_sha"], snapshot["observed_remote_sha"]):
                raise IntegrationError("REMOTE_HISTORY_CHANGED: saved snapshot no longer reachable")
            snapshot["remote_advanced_since_receipt"] = saved["observed_remote_sha"] != snapshot["observed_remote_sha"]
        print(json.dumps(snapshot, sort_keys=True))
        return 0
    except (IntegrationError, OSError, ValueError) as exc:
        # Boundary failure is explicit; Git stderr/argv may contain credentials.
        print(f"integration proof refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
