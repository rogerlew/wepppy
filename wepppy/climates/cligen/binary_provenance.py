"""Validate and log identities for packaged CLIGEN executables."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, TextIO


CLIGEN_SIDECAR_SCHEMA = "cligen-binary-provenance-v1"
_STRICT_BINARY_NAMES = frozenset({"cligen532"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40}$")


class CligenProvenanceError(RuntimeError):
    """Raised when a strict CLIGEN release cannot prove its identity."""


@dataclass(frozen=True)
class CligenBinaryIdentity:
    """Verified or explicitly legacy identity for one CLIGEN executable."""

    binary_path: str
    binary_sha256: str
    binary_size_bytes: int
    binary_mtime_ns: int
    sidecar_path: str
    sidecar_sha256: str
    cligen_version: str
    release_label: str
    source_commit: str
    source_git_tree: str
    source_manifest_sha256: str
    binary_identity_status: str


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, binary_path: Path, message: str) -> None:
    if not condition:
        raise CligenProvenanceError(
            f'CLIGEN binary provenance check failed for "{binary_path}": {message}'
        )


def _require_dict(value: Any, binary_path: Path, field: str) -> dict[str, Any]:
    _require(isinstance(value, dict), binary_path, f"{field} must be an object")
    return value


def _require_text(value: Any, binary_path: Path, field: str) -> str:
    _require(isinstance(value, str) and bool(value), binary_path, f"{field} must be a non-empty string")
    return value


def _manifest_sha256(manifest: list[Any], binary_path: Path) -> str:
    for index, entry_value in enumerate(manifest):
        entry = _require_dict(entry_value, binary_path, f"source.files[{index}]")
        relative_text = _require_text(
            entry.get("path"), binary_path, f"source.files[{index}].path"
        )
        relative = Path(relative_text)
        _require(
            not relative.is_absolute() and ".." not in relative.parts,
            binary_path,
            f"source.files[{index}].path must be relative and traversal-free",
        )
        digest = _require_text(
            entry.get("sha256"), binary_path, f"source.files[{index}].sha256"
        )
        _require(bool(_SHA256_RE.fullmatch(digest)), binary_path, f"source.files[{index}].sha256 is invalid")
        size = entry.get("size_bytes")
        _require(
            isinstance(size, int) and not isinstance(size, bool) and size >= 0,
            binary_path,
            f"source.files[{index}].size_bytes must be a non-negative integer",
        )

    canonical = json.dumps(
        manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def collect_cligen_binary_identity(
    binary_path: str | os.PathLike[str],
) -> CligenBinaryIdentity:
    """Return a verified identity, requiring a sidecar for CLIGEN 5.3.2."""

    binary = Path(binary_path).expanduser().resolve()
    try:
        binary_payload = binary.read_bytes()
        stat_result = binary.stat()
    except OSError as exc:
        raise CligenProvenanceError(
            f'Cannot read CLIGEN binary "{binary}": {exc.__class__.__name__}: {exc}'
        ) from exc

    binary_digest = _sha256_bytes(binary_payload)
    binary_size = len(binary_payload)
    strict = binary.name in _STRICT_BINARY_NAMES
    sidecar = Path(f"{binary}.json")

    if not strict:
        return CligenBinaryIdentity(
            binary_path=str(binary),
            binary_sha256=binary_digest,
            binary_size_bytes=binary_size,
            binary_mtime_ns=stat_result.st_mtime_ns,
            sidecar_path="",
            sidecar_sha256="",
            cligen_version="unknown",
            release_label="legacy",
            source_commit="",
            source_git_tree="",
            source_manifest_sha256="",
            binary_identity_status="legacy_unverified",
        )

    _require(sidecar.is_file(), binary, f"required sidecar is missing: {sidecar}")
    try:
        sidecar_payload = sidecar.read_bytes()
        decoded = json.loads(sidecar_payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CligenProvenanceError(
            f'Cannot read CLIGEN sidecar "{sidecar}": {exc.__class__.__name__}: {exc}'
        ) from exc

    root = _require_dict(decoded, binary, "sidecar")
    _require(root.get("schema") == CLIGEN_SIDECAR_SCHEMA, binary, f"schema must be {CLIGEN_SIDECAR_SCHEMA}")
    release_label = _require_text(root.get("release_label"), binary, "release_label")
    binary_data = _require_dict(root.get("binary"), binary, "binary")
    source_data = _require_dict(root.get("source"), binary, "source")

    _require(binary_data.get("name") == binary.name, binary, "binary.name mismatch")
    _require(binary_data.get("role") == "optimized", binary, "binary.role must be optimized")
    _require(binary_data.get("sha256") == binary_digest, binary, "binary SHA-256 mismatch")
    _require(binary_data.get("size_bytes") == binary_size, binary, "binary size mismatch")
    cligen_version = _require_text(binary_data.get("cligen_version"), binary, "binary.cligen_version")

    _require(source_data.get("dirty") is False, binary, "source.dirty must be false")
    source_commit = _require_text(source_data.get("commit"), binary, "source.commit")
    source_tree = _require_text(source_data.get("git_tree"), binary, "source.git_tree")
    _require(bool(_GIT_OBJECT_RE.fullmatch(source_commit)), binary, "source.commit must be a 40-character lowercase Git object ID")
    _require(bool(_GIT_OBJECT_RE.fullmatch(source_tree)), binary, "source.git_tree must be a 40-character lowercase Git object ID")
    manifest = source_data.get("files")
    _require(isinstance(manifest, list) and bool(manifest), binary, "source.files must be a non-empty array")
    manifest_digest = _manifest_sha256(manifest, binary)
    _require(
        source_data.get("manifest_sha256") == manifest_digest,
        binary,
        "source manifest SHA-256 mismatch",
    )

    return CligenBinaryIdentity(
        binary_path=str(binary),
        binary_sha256=binary_digest,
        binary_size_bytes=binary_size,
        binary_mtime_ns=stat_result.st_mtime_ns,
        sidecar_path=str(sidecar),
        sidecar_sha256=_sha256_bytes(sidecar_payload),
        cligen_version=cligen_version,
        release_label=release_label,
        source_commit=source_commit,
        source_git_tree=source_tree,
        source_manifest_sha256=manifest_digest,
        binary_identity_status="verified",
    )


def _quote(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def format_cligen_binary_identity(*, runner: str, identity: CligenBinaryIdentity) -> str:
    """Format the stable one-line CLIGEN identity contract."""

    runner_text = (
        str(runner)
        .replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("]", "\\]")
    )
    return (
        f"[{runner_text}] binary_identity "
        f"binary_path={_quote(identity.binary_path)} "
        f"binary_sha256={identity.binary_sha256} "
        f"binary_size_bytes={identity.binary_size_bytes} "
        f"binary_mtime_ns={identity.binary_mtime_ns} "
        f"sidecar_path={_quote(identity.sidecar_path)} "
        f"sidecar_sha256={identity.sidecar_sha256 or '<unavailable>'} "
        f"cligen_version={_quote(identity.cligen_version)} "
        f"release_label={_quote(identity.release_label)} "
        f"source_commit={identity.source_commit or '<unavailable>'} "
        f"source_git_tree={identity.source_git_tree or '<unavailable>'} "
        f"source_manifest_sha256={identity.source_manifest_sha256 or '<unavailable>'} "
        f"binary_identity_status={identity.binary_identity_status}"
    )


def write_cligen_binary_identity(
    log_fp: TextIO,
    *,
    runner: str,
    binary_path: str | os.PathLike[str],
) -> CligenBinaryIdentity:
    """Verify ``binary_path`` and append its identity to ``log_fp``."""

    identity = collect_cligen_binary_identity(binary_path)
    log_fp.write(format_cligen_binary_identity(runner=runner, identity=identity) + "\n")
    log_fp.flush()
    return identity
