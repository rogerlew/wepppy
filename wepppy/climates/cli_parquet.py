"""Producer-owned CLI snapshots and coherent Parquet lineage.

Contract: docs/schemas/climate-parquet-lineage-contract.md.
"""
from __future__ import annotations

import errno
import hashlib
import json
import logging
import os
from pathlib import Path
import stat
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.file_digest import sha256_file

_METADATA_KEY = b"wepppy_cli_source"
_LOG = logging.getLogger(__name__)


def _version(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _selection(wd, source):
    source = Path(source).absolute()
    logical_root = Path(wd).absolute()
    root = logical_root.resolve()
    selected = source.relative_to(logical_root).as_posix() if source.is_relative_to(logical_root) else os.path.relpath(source, root)
    return {"source": selected,
            "resolved_source": os.path.relpath(source.resolve(), root)}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate CLI lineage field")
        result[key] = value
    return result


def _read_proof(stream, max_text):
    """Read bounded metadata from the caller's authorized opened descriptor."""
    before = os.fstat(stream.fileno())
    if before.st_size < 12:
        raise ValueError("Invalid CLI Parquet framing")
    stream.seek(0)
    header = stream.read(4)
    stream.seek(-8, os.SEEK_END)
    footer = stream.read(8)
    length = int.from_bytes(footer[:4], "little")
    if header != b"PAR1" or footer[4:] != b"PAR1" or not 0 < length <= min(max_text, before.st_size - 12):
        raise ValueError("Invalid or oversized CLI Parquet footer")
    stream.seek(0)
    raw = (pq.ParquetFile(stream).schema_arrow.metadata or {}).get(_METADATA_KEY)
    if _version(os.fstat(stream.fileno())) != _version(before):
        raise OSError(errno.ESTALE, "CLI Parquet changed while reading lineage")
    if raw is None:
        return None, _version(before)
    if len(raw) > max_text:
        raise ValueError("Oversized CLI lineage")
    proof = json.loads(raw, object_pairs_hook=_pairs)
    fields = {"version", "source", "resolved_source", "source_sha256", "producer", "interpretation"}
    if (not isinstance(proof, dict) or set(proof) != fields
            or type(proof["version"]) is not int or proof["version"] != 1
            or any(not isinstance(proof[key], str) for key in fields - {"version"})
            or (proof["producer"], proof["interpretation"]) not in {("climate", "1"), ("interchange", "1")}
            or len(proof["source_sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in proof["source_sha256"])):
        raise ValueError("Invalid or unsupported CLI lineage")
    return proof, _version(before)


class _CliParquetAttempt:
    """Retain verified parser input and publish one complete output generation."""

    def __init__(self, wd, source, output, producer):
        self.wd = Path(wd)
        self.source = Path(source).absolute()
        self.output = Path(output).absolute()
        self.producer = producer
        self.target = self.output.resolve()
        self.selected = _selection(self.wd, self.source)
        self.root = self.wd.resolve() / "climate_artifacts/cli_parquet/attempts" / uuid4().hex
        self.snapshot = self.root / "source.cli"
        self.committed = False
        self.digest = None
        self.mode = None
        self.directory = None

    def _create_directory(self):
        directory = os.open(self.wd.resolve(), os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in ("climate_artifacts", "cli_parquet", "attempts", self.root.name):
                try:
                    os.mkdir(component, 0o700 if component == self.root.name else 0o777, dir_fd=directory)
                except FileExistsError:
                    if component == self.root.name:
                        raise
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
            self.directory = directory
        except OSError:
            os.close(directory)
            raise

    def _open_payload(self, name, mode=0o600):
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             mode, dir_fd=self.directory)
        return os.fdopen(descriptor, "wb")

    def _check_directory(self):
        current = self.root.stat()
        opened = os.fstat(self.directory)
        if (self.root.resolve() != self.root
                or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)):
            raise OSError(errno.ESTALE, "CLI export attempt directory changed", str(self.root))

    def _target_mode(self):
        try:
            info = self.target.stat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode):
            raise OSError(errno.EINVAL, "CLI Parquet destination must be regular", str(self.target))
        # Atomic replacement must preserve the old direct writer's inode access.
        os.close(os.open(self.target, os.O_WRONLY | os.O_NONBLOCK))
        return stat.S_IMODE(info.st_mode) & 0o777

    def _status(self, status, error=None):
        temporary = f"status.{uuid4().hex}.json"
        payload = {"status": status, "source": self.selected, "source_sha256": self.digest,
                   "target": str(self.target), "producer": self.producer, "error": error}
        with self._open_payload(temporary) as outgoing:
            outgoing.write(json.dumps(payload, indent=2).encode())
        os.replace(temporary, "status.json", src_dir_fd=self.directory, dst_dir_fd=self.directory)

    def __enter__(self):
        # Private at creation, including partial copies and third-party work.
        self._create_directory()
        try:
            self._status("copying")
            self.mode = self._target_mode()
            checksum = hashlib.sha256()
            with self.source.open("rb") as incoming, self._open_payload("source.cli") as outgoing:
                before = os.fstat(incoming.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise OSError(errno.EINVAL, "CLI source must be regular", str(self.source))
                total = 0
                while block := incoming.read(min(1024 * 1024, before.st_size - total + 1)):
                    total += len(block)
                    if total > before.st_size:
                        raise OSError(errno.ESTALE, "CLI source grew during snapshot", str(self.source))
                    outgoing.write(block)
                    checksum.update(block)
                if (total != before.st_size or _version(os.fstat(incoming.fileno())) != _version(before)
                        or _version(self.source.stat()) != _version(before)):
                    raise OSError(errno.ESTALE, "CLI source changed during snapshot", str(self.source))
            self.digest = checksum.hexdigest()
            if sha256_file(self.source, use_cache=False) != self.digest:
                raise OSError(errno.ESTALE, "CLI source changed after snapshot", str(self.source))
            self._check_directory()
            self._status("working")
        except (OSError, ValueError):
            # __exit__ is not called when acquisition fails.
            self._record_outcome("failed", "CLI snapshot acquisition failed")
            os.close(self.directory)
            self.directory = None
            raise
        return self

    def _record_outcome(self, status, error):
        try:
            self._status(status, error)
        except OSError:
            _LOG.exception("Unable to persist CLI export status at %s", self.root)

    def __exit__(self, exc_type, exc, traceback):
        try:
            self._record_outcome("complete" if self.committed else "failed", None if exc is None else str(exc))
        finally:
            os.close(self.directory)
            self.directory = None
        return False

    def publish(self, frame, current_source):
        proof = {"version": 1, **self.selected, "source_sha256": self.digest,
                 "producer": self.producer, "interpretation": "1"}
        table = pa.Table.from_pandas(frame, preserve_index=False)
        metadata = dict(table.schema.metadata or {})
        metadata[_METADATA_KEY] = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
        with self._open_payload("candidate.parquet", 0o666 if self.mode is None else self.mode) as outgoing:
            if self.mode is not None:
                os.fchmod(outgoing.fileno(), self.mode)
            pq.write_table(table.replace_schema_metadata(metadata), outgoing)
        self._status("ready_to_publish")
        selected = Path(current_source()).absolute()
        if (_selection(self.wd, selected) != self.selected
                or sha256_file(selected, use_cache=False) != self.digest):
            raise OSError(errno.ESTALE, "Active CLI changed before export publication", str(selected))
        self.output.parent.mkdir(parents=True, exist_ok=True)
        if self.output.resolve() != self.target:
            raise OSError(errno.ESTALE, "CLI Parquet destination changed", str(self.output))
        mode = self._target_mode()
        if mode is not None:
            os.chmod("candidate.parquet", mode, dir_fd=self.directory, follow_symlinks=False)
        self._check_directory()
        os.replace("candidate.parquet", self.target, src_dir_fd=self.directory)
        self.committed = True
