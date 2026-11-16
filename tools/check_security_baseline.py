#!/usr/bin/env python3
"""Verify accepted source policy and exact-revision publication eligibility.

Run this file from the trusted base revision, not the candidate checkout. Policy
approval is a repository Actions variable set by the owner, never candidate data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BOOTSTRAP_BASE = "420e31b97e962dd6ea79694efe89f348c27ef83f"
WORKFLOW = "integration-governance.yml"
PROTECTED = (
    "wepppy/microservices/shape_converter/",
    "tests/shape_converter/",
    ".dockerignore",
    "docker/Dockerfile.shape-converter",
    "docker/Dockerfile.shape-converter.dockerignore",
    "docker/requirements-shape-converter.txt",
    "docker/docker-compose.prod.wepp1.yml",
    "wepppy/__init__.py",
    "wepppy/microservices/__init__.py",
    "wepppy/observability/",
    "docker/docker-compose.dev.yml",
    "docker/docker-compose.prod.yml",
    "scripts/deploy-production.sh",
    "scripts/build_forest_workflows.py",
    ".github/forest_workflows/integration-governance.yml",
    ".github/workflows/integration-governance.yml",
    ".github/forest_workflows/integration-policy.yml",
    ".github/workflows/integration-policy.yml",
    ".github/workflows/publish-weppcloud-image.yml",
    ".github/workflows/publish-weppcloud-aux-images.yml",
    "tools/check_security_baseline.py",
    "tools/check_integration_history.py",
    "tools/check_deployment_governance.py",
    "tests/tools/test_deployment_governance.py",
    "tools/install_integration_hooks.py",
    "tests/tools/test_integration_history.py",
    "tools/wctl2/commands/python_tasks.py",
    "tools/wctl2/checkout_identity.py",
    "tools/wctl2/tests/test_checkout_identity.py",
    "wctl/wctl.sh",
    "wctl/install.sh",
    "tests/tools/test_security_baseline.py",
    "docs/standards/integration-history-governance.md",
)


class GateError(RuntimeError):
    """A candidate lacks required positive evidence."""


def git_environment() -> dict[str, str]:
    # Explicit --root is the only repository selector, even inside a Git hook or
    # a shell carrying stale variables from a different checkout.
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
    return env


def git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                env=git_environment(), timeout=60)
    except subprocess.TimeoutExpired as error:
        raise GateError("Git evidence timed out") from error
    if result.returncode:
        raise GateError(f"Git failed: {' '.join(args[:2])}")
    return result.stdout


def revision(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise GateError("Expected a full 40-character commit SHA")
    return value


def tree(root: Path, sha: str) -> dict[str, str]:
    revision(sha)
    records = git(root, "ls-tree", "-r", "-z", sha).split(b"\0")
    result = {}
    for record in records:
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        path = name.decode("utf-8")
        if any(path.startswith(p) if p.endswith("/") else path == p for p in PROTECTED):
            # Include mode and type so symlink and gitlink substitutions fail too.
            result[path] = metadata.decode("ascii")
    return result


def policy_delta(root: Path, base: str, candidate: str) -> tuple[list[str], str]:
    before, after = tree(root, base), tree(root, candidate)
    paths = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    material = [{"path": path, "before": before.get(path), "after": after.get(path)} for path in paths]
    digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return paths, digest


def check_policy(root: Path, base: str, candidate: str, approval: str) -> dict:
    revision(base)
    revision(candidate)
    # Accepted history must survive even when the candidate changes security code.
    git(root, "merge-base", "--is-ancestor", base, candidate)
    paths, digest = policy_delta(root, base, candidate)
    if paths and approval != f"{candidate}:{digest}":
        raise GateError(f"POLICY_APPROVAL_REQUIRED {candidate}:{digest}; paths={','.join(paths)}")
    return {"schema_version": 1, "base": base, "candidate": candidate,
            "policy_digest": digest, "changed_paths": paths, "approved_transition": bool(paths)}


def bootstrap(root: Path, base: str, candidate: str, destination: Path, digest: str) -> None:
    revision(base)
    revision(candidate)
    result = subprocess.run(["git", "-C", str(root), "show", f"{base}:tools/check_security_baseline.py"], capture_output=True,
                            env=git_environment(), timeout=60)
    if result.returncode == 0:
        payload = result.stdout
    else:
        if base != BOOTSTRAP_BASE or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise GateError("Trusted checker absent; approved bootstrap base and digest required")
        payload = git(root, "show", f"{candidate}:tools/check_security_baseline.py")
        if hashlib.sha256(payload).hexdigest() != digest:
            raise GateError("Bootstrap checker digest mismatch")
    destination.write_bytes(payload)


def api(repository: str, suffix: str, token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise GateError("Invalid repository identity")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/repos/{repository}/{suffix}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise GateError("GitHub evidence request failed") from error


def eligible_run(runs: list[dict], sha: str, workflow_id: int, repository: str) -> dict | None:
    matching = [run for run in runs if run.get("head_sha") == sha
                and run.get("workflow_id") == workflow_id
                and run.get("event") == "push" and run.get("head_branch") == "master"
                and run.get("repository", {}).get("full_name") == repository]
    if not matching:
        return None
    latest = max(matching, key=lambda run: (run["id"], run.get("run_attempt", 1)))
    if latest.get("status") != "completed":
        return None
    if latest.get("conclusion") != "success":
        raise GateError("Exact-source governance run did not succeed")
    return latest


def publication(repository: str, sha: str, token: str, wait_seconds: int) -> dict:
    revision(sha)
    workflow = api(repository, f"actions/workflows/{WORKFLOW}", token)
    if workflow.get("path") != f".github/workflows/{WORKFLOW}" or workflow.get("state") != "active":
        raise GateError("Expected active governance workflow missing")
    deadline = time.monotonic() + wait_seconds
    while True:
        remote = api(repository, "git/ref/heads/master", token)
        if remote.get("object", {}).get("sha") != sha:
            raise GateError("Publication source is not current remote master")
        data = api(repository, f"actions/workflows/{workflow['id']}/runs?head_sha={sha}&event=push&per_page=100", token)
        run = eligible_run(data.get("workflow_runs", []), sha, workflow["id"], repository)
        if run:
            return {"schema_version": 1, "candidate": sha, "workflow_id": workflow["id"],
                    "run_id": run["id"], "run_attempt": run.get("run_attempt", 1), "conclusion": "success"}
        if time.monotonic() >= deadline:
            raise GateError("Exact-source governance success missing or unfinished")
        time.sleep(min(10, max(0, deadline - time.monotonic())))


def point_fixture(root: Path, count: int = 2) -> None:
    def header(words: int) -> bytes:
        data = bytearray(100)
        struct.pack_into(">i", data, 0, 9994)
        struct.pack_into(">i", data, 24, words)
        struct.pack_into("<2i4d", data, 28, 1000, 1, 10., 20., 10., 20.)
        return bytes(data)
    (root / "point.shp").write_bytes(header((100 + 28 * count) // 2) + b"".join(
        struct.pack(">2i", i + 1, 10) + struct.pack("<i2d", 1, 10., 20.) for i in range(count)))
    (root / "point.shx").write_bytes(header((100 + 8 * count) // 2) + b"".join(
        struct.pack(">2i", 50 + 14 * i, 10) for i in range(count)))
    dbf = bytearray(32)
    dbf[0] = 3
    struct.pack_into("<IHH", dbf, 4, count, 65, 5)
    field = bytearray(32)
    field[:4] = b"NAME"
    field[11] = ord("C")
    field[16] = 4
    (root / "point.dbf").write_bytes(dbf + field + b"\r" + b" demo" * count + b"\x1a")


def smoke(binary: Path) -> dict:
    """Exercise real generated outputs; no application imports or candidate tests."""
    binary = binary.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="shape-baseline-") as temporary:
        root = Path(temporary)
        point_fixture(root)
        output = root / "payload.json"
        def run(features: int) -> subprocess.CompletedProcess:
            return subprocess.run([str(binary), "--request-root", str(root), "--shp-path", str(root / "point.shp"),
                "--output-path", str(output), "--max-payload-bytes", "1000000", "--max-input-bytes", "1000000",
                "--max-features", str(features), "--max-vertices-per-feature", "100",
                "--max-memory-bytes", "536870912", "--max-cpu-seconds", "10", "--max-open-files", "32"],
                capture_output=True, timeout=20)
        valid = run(10)
        if valid.returncode != 0:
            raise GateError("Valid point fixture rejected")
        payload = json.loads(output.read_text())
        if payload["properties"] != [{"NAME": "demo"}] * 2 or payload["geometries"] != [
                {"type": "Point", "coordinates": [10., 20.]}] * 2:
            raise GateError("Valid point output changed")
        output.unlink()
        if run(1).returncode != 4 or output.exists():
            raise GateError("Feature ceiling did not reject without output")
        data = bytearray((root / "point.shx").read_bytes())
        struct.pack_into(">i", data, 100, 999999)
        (root / "point.shx").write_bytes(data)
        if run(10).returncode == 0 or output.exists():
            raise GateError("Malformed index did not reject without output")
    return {"valid_output": "pass", "feature_limit": "pass", "malformed_index": "pass"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    policy = sub.add_parser("policy")
    policy.add_argument("--root", type=Path, default=Path.cwd())
    policy.add_argument("--base", required=True)
    policy.add_argument("--candidate", required=True)
    policy.add_argument("--digest-only", action="store_true")
    pub = sub.add_parser("publication")
    pub.add_argument("--repository", required=True)
    pub.add_argument("--candidate", required=True)
    pub.add_argument("--wait-seconds", type=int, default=600)
    probe = sub.add_parser("smoke")
    probe.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "policy":
            if args.digest_only:
                result = {"candidate": args.candidate, "policy_digest": policy_delta(args.root, args.base, args.candidate)[1]}
            else:
                result = check_policy(args.root, args.base, args.candidate, os.environ.get("INTEGRATION_POLICY_APPROVAL", ""))
        elif args.command == "publication":
            result = publication(args.repository, args.candidate, os.environ.get("GH_TOKEN", ""), args.wait_seconds)
        else:
            result = smoke(args.binary)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (GateError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"INTEGRATION_GOVERNANCE_FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
