#!/usr/bin/env python3
"""Validate and install a CLIGEN optimized binary/sidecar release pair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Protocol


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_MODULE_PATH = (
    REPO_ROOT / "wepppy" / "climates" / "cligen" / "binary_provenance.py"
)


class _Identity(Protocol):
    binary_path: str
    binary_sha256: str
    sidecar_sha256: str
    release_label: str
    source_commit: str
    source_git_tree: str


def _load_provenance_module():
    module_name = "_wepppy_cligen_binary_provenance"
    spec = importlib.util.spec_from_file_location(module_name, PROVENANCE_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load provenance module: {PROVENANCE_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_PROVENANCE = _load_provenance_module()
collect_cligen_binary_identity = _PROVENANCE.collect_cligen_binary_identity


DEFAULT_DESTINATION = REPO_ROOT / "wepppy" / "climates" / "cligen" / "bin" / "cligen532"
DEFAULT_SOURCE_BINARY = Path("release/linux/gfortran/cligen532")
EXPECTED_INTERPRETER = "/lib64/ld-linux-x86-64.so.2"
EXPECTED_COMPILER = Path("/usr/bin/gfortran")


class VendorError(RuntimeError):
    """Raised when a candidate cannot be safely vendored."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(source_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=source_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_bytes(source_root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=source_root,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _is_ancestor(source_root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=source_root,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise VendorError(
            f"cannot compare source commits {ancestor} and {descendant}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return result.returncode == 0


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VendorError(message)


def _load_sidecar(sidecar: Path) -> dict[str, Any]:
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VendorError(f"cannot read sidecar {sidecar}: {exc}") from exc
    _require(isinstance(payload, dict), f"sidecar must contain a JSON object: {sidecar}")
    return payload


def validate_source_release(
    *,
    source_root: Path,
    source_binary: Path,
    expected_source_commit: str | None,
    expected_release_label: str | None,
) -> _Identity:
    """Validate the candidate pair and its exact source checkout."""

    source_root = source_root.resolve()
    source_binary = source_binary.resolve()
    sidecar = Path(f"{source_binary}.json")
    _require(source_root.is_dir(), f"source root is not a directory: {source_root}")
    _require(source_binary.is_file(), f"source binary is missing: {source_binary}")
    _require(sidecar.is_file(), f"source sidecar is missing: {sidecar}")

    identity = collect_cligen_binary_identity(source_binary)
    payload = _load_sidecar(sidecar)
    source_data = payload["source"]
    build_data = payload.get("build")
    binary_data = payload["binary"]
    _require(isinstance(build_data, dict), "sidecar build section is required")

    source_commit = identity.source_commit
    source_tree = _git(source_root, "rev-parse", f"{source_commit}^{{tree}}")
    head = _git(source_root, "rev-parse", "HEAD")
    default_ref = _git(source_root, "symbolic-ref", "refs/remotes/origin/HEAD")
    default_head = _git(source_root, "rev-parse", default_ref)
    _require(
        _is_ancestor(source_root, source_commit, head),
        f"sidecar source commit {source_commit} is not an ancestor of HEAD {head}",
    )
    _require(
        _is_ancestor(source_root, source_commit, default_head),
        f"sidecar source commit {source_commit} is not reachable from "
        f"remote-default {default_ref} at {default_head}",
    )
    _require(
        identity.source_git_tree == source_tree,
        "sidecar source tree does not match its recorded source commit",
    )
    if expected_source_commit is not None:
        _require(
            source_commit == expected_source_commit,
            f"sidecar source commit {source_commit} does not match expected "
            f"commit {expected_source_commit}",
        )
    if expected_release_label is not None:
        _require(
            identity.release_label == expected_release_label,
            f"release label {identity.release_label} does not match expected "
            f"{expected_release_label}",
        )

    manifest = source_data["files"]
    relative_paths: list[str] = []
    for entry in manifest:
        relative = Path(entry["path"])
        path = source_root / relative
        _require(path.is_file(), f"source manifest input is missing: {path}")
        _require(_sha256(path) == entry["sha256"], f"source manifest SHA-256 mismatch: {path}")
        _require(path.stat().st_size == entry["size_bytes"], f"source manifest size mismatch: {path}")
        committed_bytes = _git_bytes(
            source_root,
            "show",
            f"{source_commit}:{relative.as_posix()}",
        )
        _require(
            hashlib.sha256(committed_bytes).hexdigest() == entry["sha256"],
            f"source manifest SHA-256 does not match {source_commit}:{relative}",
        )
        _require(
            len(committed_bytes) == entry["size_bytes"],
            f"source manifest size does not match {source_commit}:{relative}",
        )
        relative_paths.append(relative.as_posix())

    status = _git(
        source_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *relative_paths,
    )
    _require(not status, f"source manifest inputs are dirty:\n{status}")
    _require(
        binary_data.get("elf_interpreter") == EXPECTED_INTERPRETER,
        f"ELF interpreter must be {EXPECTED_INTERPRETER}",
    )

    compiler = EXPECTED_COMPILER.resolve()
    _require(compiler.is_file(), f"required compiler is missing: {compiler}")
    _require(
        build_data.get("compiler_path") == str(compiler),
        f"sidecar compiler_path must be {compiler}",
    )
    _require(
        build_data.get("compiler_sha256") == _sha256(compiler),
        "compiler SHA-256 mismatch",
    )
    return identity


def _copy_with_mode(source: Path, destination: Path, mode: int) -> None:
    shutil.copyfile(source, destination)
    destination.chmod(mode)


def _restore_file(backup: Path | None, destination: Path, staging_dir: Path) -> None:
    if backup is None:
        destination.unlink(missing_ok=True)
        return
    recovery = staging_dir / f"recover-{destination.name}"
    shutil.copyfile(backup, recovery)
    recovery.chmod(backup.stat().st_mode & 0o777)
    os.replace(recovery, destination)


def install_release_pair(
    *,
    source_binary: Path,
    destination: Path,
) -> _Identity:
    """Stage, validate, and replace a binary/sidecar pair fail closed."""

    source_binary = source_binary.resolve()
    source_sidecar = Path(f"{source_binary}.json")
    destination = destination.resolve()
    destination_sidecar = Path(f"{destination}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".cligen-vendor.", dir=destination.parent) as temporary:
        staging_dir = Path(temporary)
        staged_binary = staging_dir / destination.name
        staged_sidecar = Path(f"{staged_binary}.json")
        _copy_with_mode(source_binary, staged_binary, 0o755)
        _copy_with_mode(source_sidecar, staged_sidecar, 0o644)
        collect_cligen_binary_identity(staged_binary)

        backup_binary = staging_dir / "previous-cligen532" if destination.is_file() else None
        backup_sidecar = staging_dir / "previous-cligen532.json" if destination_sidecar.is_file() else None
        if backup_binary is not None:
            shutil.copy2(destination, backup_binary)
        if backup_sidecar is not None:
            shutil.copy2(destination_sidecar, backup_sidecar)

        try:
            os.replace(staged_sidecar, destination_sidecar)
            os.replace(staged_binary, destination)
            identity = collect_cligen_binary_identity(destination)
        except Exception:
            _restore_file(backup_sidecar, destination_sidecar, staging_dir)
            _restore_file(backup_binary, destination, staging_dir)
            raise

    return identity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-binary", type=Path, default=DEFAULT_SOURCE_BINARY)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--expect-source-commit")
    parser.add_argument("--expect-release-label")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_root = args.source_root.resolve()
    source_binary = args.source_binary
    if not source_binary.is_absolute():
        source_binary = source_root / source_binary

    validate_source_release(
        source_root=source_root,
        source_binary=source_binary,
        expected_source_commit=args.expect_source_commit,
        expected_release_label=args.expect_release_label,
    )
    identity = install_release_pair(
        source_binary=source_binary,
        destination=args.destination,
    )
    print(
        "cligen_release_vendored "
        f"binary={identity.binary_path} "
        f"sha256={identity.binary_sha256} "
        f"sidecar_sha256={identity.sidecar_sha256} "
        f"release_label={identity.release_label} "
        f"source_commit={identity.source_commit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
