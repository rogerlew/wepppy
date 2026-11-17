"""Runtime validation for the Rust parser executable provenance sidecar."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


PROVENANCE_SCHEMA = "shape-parser-binary-provenance-v1"
_MAX_SIDECAR_BYTES = 1024 * 1024


def _manifest_sha256(manifest: list[object]) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _valid_source_manifest(source_data: dict[str, object], build_data: dict[str, object]) -> bool:
    files = source_data.get("files")
    if not isinstance(files, list) or not files:
        return False
    seen: set[str] = set()
    cargo_lock_digest: str | None = None
    for item in files:
        if not isinstance(item, dict):
            return False
        path = item.get("path")
        digest = item.get("sha256")
        size = item.get("size_bytes")
        if (
            not isinstance(path, str)
            or not path
            or path in seen
            or not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(size, int)
            or size < 0
        ):
            return False
        seen.add(path)
        if path == "Cargo.lock":
            cargo_lock_digest = digest
    return (
        source_data.get("manifest_sha256") == _manifest_sha256(files)
        and cargo_lock_digest is not None
        and build_data.get("cargo_lock_sha256") == cargo_lock_digest
    )


def validate_parser_executable(binary: Path) -> tuple[bool, str | None]:
    sidecar = Path(f"{binary}.json")
    try:
        binary_stat = binary.lstat()
        sidecar_stat = sidecar.lstat()
    except OSError:
        return False, "parser_binary_or_provenance_missing"

    if (
        stat.S_ISLNK(binary_stat.st_mode)
        or stat.S_ISLNK(sidecar_stat.st_mode)
        or not stat.S_ISREG(binary_stat.st_mode)
        or not stat.S_ISREG(sidecar_stat.st_mode)
        or not os.access(binary, os.X_OK)
    ):
        return False, "parser_binary_or_provenance_invalid"
    if sidecar_stat.st_size < 2 or sidecar_stat.st_size > _MAX_SIDECAR_BYTES:
        return False, "parser_provenance_size_invalid"

    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "parser_provenance_json_invalid"
    if not isinstance(payload, dict) or payload.get("schema") != PROVENANCE_SCHEMA:
        return False, "parser_provenance_schema_invalid"

    binary_data = payload.get("binary")
    source_data = payload.get("source")
    build_data = payload.get("build")
    if not all(isinstance(section, dict) for section in (binary_data, source_data, build_data)):
        return False, "parser_provenance_incomplete"
    assert isinstance(binary_data, dict)
    assert isinstance(source_data, dict)
    assert isinstance(build_data, dict)
    if (
        binary_data.get("name") != binary.name
        or binary_data.get("size_bytes") != binary_stat.st_size
        or not _valid_source_manifest(source_data, build_data)
    ):
        return False, "parser_provenance_contract_invalid"

    try:
        digest = _sha256(binary)
    except OSError:
        return False, "parser_binary_hash_failed"
    if binary_data.get("sha256") != digest:
        return False, "parser_binary_hash_mismatch"

    try:
        result = subprocess.run(
            [os.fspath(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env={"LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False, "parser_version_probe_failed"
    if result.returncode != 0 or result.stdout.strip() != binary_data.get("version"):
        return False, "parser_version_mismatch"
    return True, None


def read_parser_provenance(binary: Path) -> dict[str, str]:
    """Return the bounded runtime identity after revalidating its sidecar."""
    valid, reason = validate_parser_executable(binary)
    if not valid:
        raise ValueError(reason or "parser provenance is invalid")
    sidecar = Path(f"{binary}.json")
    descriptor = os.open(sidecar, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        payload = json.load(stream)
    binary_data = payload["binary"]
    build_data = payload["build"]
    source_data = payload["source"]
    result = {
        "binary_name": binary_data["name"],
        "binary_version": binary_data["version"],
        "binary_sha256": binary_data["sha256"],
        "cargo_lock_sha256": build_data["cargo_lock_sha256"],
        "source_revision": source_data["revision"],
    }
    if not all(isinstance(value, str) and value for value in result.values()):
        raise ValueError("parser provenance is incomplete")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["PROVENANCE_SCHEMA", "read_parser_provenance", "validate_parser_executable"]
