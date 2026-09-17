"""Content observations and atomic compact-cache publication for C08/C09 reports."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import stat
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.file_digest import sha256_file

_LOG = logging.getLogger(__name__)
_METADATA_KEY = b"wepppy_report_dependencies"


def _observe_file(wd: Path, path: Path) -> dict:
    """Observe a selected ordinary file; only actual absence is historical state."""
    try:
        digest = sha256_file(path)
    except FileNotFoundError:
        digest = None
    return {"path": os.path.relpath(path.resolve(), wd.resolve()), "sha256": digest}


def _read_cache(path: Path, key: str, *, require_version: bool = True):
    if require_version:
        from .helpers import ReportCacheManager

        if ReportCacheManager._read_metadata(path.with_suffix(".meta.json")).get("version") != "1":
            return None
    try:
        incoming = path.open("rb")
    except FileNotFoundError:
        return None
    # The rows and provenance must come from the same opened generation. Report
    # writers atomically replace their output; unlinking that inode is harmless.
    with incoming:
        before = os.fstat(incoming.fileno())
        table = pq.read_table(incoming)
        after = os.fstat(incoming.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise RuntimeError("Report cache changed during read")
    raw = (table.schema.metadata or {}).get(_METADATA_KEY)
    proof = None if raw is None else json.loads(raw)
    if raw is not None and (
        not isinstance(proof, dict)
        or proof.get("version") != 1
        or proof.get("key") != key
        or not isinstance(proof.get("dependencies"), dict)
        or not isinstance(proof.get("attempt_id"), str)
    ):
        raise ValueError("Invalid or unsupported report cache provenance")
    return table, proof


def _cache_verdict(accepted: dict, observed: dict) -> str | None:
    """Return current/historical only when every available dependency agrees."""
    if accepted.keys() != observed.keys():
        raise ValueError("Invalid report cache dependency set")
    # Validate all accepted fields before missing observations can bypass them.
    for key, previous in accepted.items():
        if key.endswith(":aliases"):
            if not isinstance(previous, str):
                raise ValueError("Invalid report cache alias provenance")
        elif isinstance(previous, dict):
            if set(previous) != {"path", "sha256"} or not isinstance(previous["path"], str):
                raise ValueError("Invalid report cache file provenance")
            digest = previous["sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid report cache source digest")
        elif key != "mapping":
            raise ValueError("Invalid report cache dependency provenance")
    missing = False
    for key, value in observed.items():
        previous = accepted[key]
        if value is None:
            missing = True
        elif isinstance(value, dict) and "sha256" in value:
            if not isinstance(previous, dict):
                raise ValueError("Invalid report cache file provenance")
            if value["path"] != previous["path"]:
                return None
            if value["sha256"] is None:
                missing = True
            elif value != previous:
                return None
        elif value != previous:
            return None
    return "historical_unverified" if missing else "current"



class _CacheBuild:
    """Retain per-attempt work and commit one complete rows/provenance file."""

    def __init__(self, cache_path: Path, key: str, *, native_source: Path | None = None):
        self.cache_path = cache_path
        self.key = key
        self.native_source = native_source
        self.target = self._select_target()
        self.mode = self._target_mode()
        self.attempt_id = uuid4().hex
        self.root = cache_path.parent / f"{key}.attempts" / self.attempt_id
        self.root.parent.mkdir(parents=True, exist_ok=True)
        # Native internal staging may use the worker umask. Its enclosing
        # directory must not expose rows beyond an existing restricted cache.
        directory_mode = 0o777 if self.mode is None else 0o700 | (self.mode & 0o044) | ((self.mode & 0o044) >> 2)
        self.root.mkdir(mode=directory_mode)
        if self.mode is not None:
            self.root.chmod(directory_mode)
        self.committed = False
        self.observations = {}

    def _select_target(self) -> Path:
        if self.native_source is not None:
            try:
                info = self.cache_path.lstat()
            except FileNotFoundError:
                pass
            else:
                if not stat.S_ISREG(info.st_mode):
                    raise OSError("hillslope watbal output must be a regular file")
            if self.cache_path.resolve() == self.native_source.resolve():
                raise ValueError("hillslope watbal output must not alias its input")
        return self.cache_path.resolve()

    def _target_mode(self) -> int | None:
        try:
            info = self.target.stat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode):
            raise OSError("Report cache output must be a regular file")
        return stat.S_IMODE(info.st_mode) & 0o777

    def open_payload(self, name: str):
        path = self.root / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666 if self.mode is None else self.mode)
        try:
            if self.mode is not None:
                os.fchmod(fd, self.mode)
            return os.fdopen(fd, "wb")
        except OSError:
            os.close(fd)
            raise

    def _status(self, status: str, error: str | None = None) -> None:
        payload = {"status": status, "attempt_id": self.attempt_id, "key": self.key,
                   "target": str(self.target), "observations": self.observations, "error": error}
        temporary = f"status.{uuid4().hex}.json"
        with self.open_payload(temporary) as outgoing:
            outgoing.write(json.dumps(payload, indent=2).encode())
        os.replace(self.root / temporary, self.root / "status.json")

    def __enter__(self):
        self._status("working")
        return self

    def __exit__(self, exc_type, exc, traceback):
        # This diagnostic boundary never masks a producer/publication exception
        # or rolls back a completed atomic replacement over another request.
        try:
            self._status("complete" if self.committed else "failed", None if exc is None else str(exc))
        except OSError:
            _LOG.exception("Unable to persist report attempt status at %s", self.root)
        return False

    def publish(self, table: pa.Table, dependencies: dict, **extra) -> None:
        proof = {"version": 1, "key": self.key, "attempt_id": self.attempt_id,
                 "dependencies": dependencies, **extra}
        metadata = dict(table.schema.metadata or {})
        metadata[_METADATA_KEY] = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
        with self.open_payload("candidate.parquet") as outgoing:
            pq.write_table(table.replace_schema_metadata(metadata), outgoing)
        from .helpers import ReportCacheManager

        sidecar = self.cache_path.with_suffix(".meta.json")
        if ReportCacheManager._read_metadata(sidecar).get("version") != "1":
            try:
                sidecar_mode = stat.S_IMODE(sidecar.stat().st_mode) & 0o777
            except FileNotFoundError:
                sidecar_mode = None
            if sidecar_mode is not None:
                os.close(os.open(sidecar, os.O_WRONLY))
            with self.open_payload("version.meta.json") as outgoing:
                if sidecar_mode is not None:
                    os.fchmod(outgoing.fileno(), sidecar_mode)
                outgoing.write(b'{"version": "1"}\n')
            os.replace(self.root / "version.meta.json", sidecar.resolve())
        self._status("ready_to_publish")
        if self._select_target() != self.target:
            raise RuntimeError("Report cache destination changed before publication")
        mode = self._target_mode()
        if mode is not None:
            if self.native_source is None:
                # C09's pandas writer required inode write access. C08's native
                # atomic writer did not; preserve each existing boundary.
                os.close(os.open(self.target, os.O_WRONLY))
            (self.root / "candidate.parquet").chmod(mode)
        os.replace(self.root / "candidate.parquet", self.target)
        self.committed = True
