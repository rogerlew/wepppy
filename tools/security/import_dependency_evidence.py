#!/usr/bin/env python3
"""Retain a manually collected bundle; success is never policy clearance."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import uuid


class EvidenceError(ValueError):
    """The collected evidence does not satisfy the import contract."""


HEX = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")
MANIFEST_LIMIT = 4 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _directory(path: Path, stack: ExitStack) -> int:
    """Hold directory descriptors so renamed ancestors cannot redirect access."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open("/", flags)
    stack.callback(os.close, descriptor)
    for part in path.parts[1:]:
        descriptor = os.open(part, flags, dir_fd=descriptor)
        stack.callback(os.close, descriptor)
    return descriptor


def _read_file(directory: int, name: str):
    descriptor = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
        dir_fd=directory,
    )
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise EvidenceError(f"not a regular file: {name}")
    return os.fdopen(descriptor, "rb")


def _validate_manifest(raw: bytes, expected_hash: str, expected_image: str):
    if not HEX.fullmatch(expected_hash):
        raise EvidenceError("invalid expected manifest hash")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_image):
        raise EvidenceError("invalid expected image ID")
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise EvidenceError("manifest hash mismatch")
    manifest = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "image_id", "files"
    }:
        raise EvidenceError("unsupported manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise EvidenceError("unsupported manifest schema")
    if manifest["image_id"] != expected_image:
        raise EvidenceError("image identity mismatch")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise EvidenceError("manifest must contain files")
    for name, record in files.items():
        if not NAME.fullmatch(name) or name == "manifest.json":
            raise EvidenceError(f"invalid artifact filename: {name!r}")
        if not isinstance(record, dict) or set(record) != {"sha256", "size_bytes"}:
            raise EvidenceError(f"invalid artifact record: {name}")
        if not isinstance(record["sha256"], str) or not HEX.fullmatch(record["sha256"]):
            raise EvidenceError(f"invalid artifact hash: {name}")
        if type(record["size_bytes"]) is not int or record["size_bytes"] <= 0:
            raise EvidenceError(f"invalid artifact size: {name}")
    return manifest


def _write_file(directory: int, name: str):
    descriptor = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600, dir_fd=directory,
    )
    os.fchmod(descriptor, 0o600)
    return os.fdopen(descriptor, "wb")


def _copy_artifact(source: int, destination: int, name: str, record: dict):
    hasher = hashlib.sha256()
    size = 0
    with _read_file(source, name) as reader, _write_file(destination, name) as writer:
        before = os.fstat(reader.fileno())
        if before.st_size != record["size_bytes"]:
            raise EvidenceError(f"artifact size mismatch: {name}")
        while chunk := reader.read(CHUNK_SIZE):
            size += len(chunk)
            if size > record["size_bytes"]:
                raise EvidenceError(f"artifact grew during import: {name}")
            hasher.update(chunk)
            writer.write(chunk)
        after = os.fstat(reader.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise EvidenceError(f"artifact changed during import: {name}")
        if size != record["size_bytes"] or hasher.hexdigest() != record["sha256"]:
            raise EvidenceError(f"artifact hash/size mismatch: {name}")
        writer.flush()
        os.fsync(writer.fileno())


def import_bundle(source: Path, store: Path, expected_hash: str, expected_image: str) -> Path:
    # Preserve the actual selected roots in the result even if an alias changes.
    source = source.resolve(strict=True)
    store = store.resolve(strict=True)
    with ExitStack() as stack:
        source_fd = _directory(source, stack)
        store_fd = _directory(store, stack)
        store_stat = os.fstat(store_fd)
        if store_stat.st_uid != os.geteuid() or stat.S_IMODE(store_stat.st_mode) != 0o700:
            raise EvidenceError("store must be owned by the invoking user with mode 0700")
        with _read_file(source_fd, "manifest.json") as reader:
            raw = reader.read(MANIFEST_LIMIT + 1)
        if len(raw) > MANIFEST_LIMIT:
            raise EvidenceError("manifest exceeds size limit")
        manifest = _validate_manifest(raw, expected_hash, expected_image)
        members = set(manifest["files"]) | {"manifest.json"}
        if set(os.listdir(source_fd)) != members:
            raise EvidenceError("collected directory members do not match manifest")

        # Exclusive reservation prevents concurrent imports from overwriting evidence.
        os.mkdir(expected_hash, 0o700, dir_fd=store_fd)
        try:
            target_fd = os.open(expected_hash, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=store_fd)
        except OSError:
            os.rmdir(expected_hash, dir_fd=store_fd)
            raise
        stack.callback(os.close, target_fd)
        stage = f".import-{uuid.uuid4().hex}"
        working_name = stage
        published = False
        try:
            os.fchmod(target_fd, 0o700)
            os.mkdir(stage, 0o700, dir_fd=target_fd)
            stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=target_fd)
            stack.callback(os.close, stage_fd)
            os.fchmod(stage_fd, 0o700)
            for name, record in manifest["files"].items():
                _copy_artifact(source_fd, stage_fd, name, record)
            with _write_file(stage_fd, "manifest.json") as writer:
                writer.write(raw)
                writer.flush()
                os.fsync(writer.fileno())
            if set(os.listdir(source_fd)) != members:
                raise EvidenceError("collected directory changed during import")
            os.fsync(stage_fd)
            os.rename(stage, "bundle", src_dir_fd=target_fd, dst_dir_fd=target_fd)
            working_name = "bundle"
            os.fsync(target_fd)
            os.fsync(store_fd)
            published = True
        finally:
            # Deliberate cleanup boundary; do not suppress copy or filesystem errors.
            if not published:
                if working_name in os.listdir(target_fd):
                    shutil.rmtree(working_name, dir_fd=target_fd)
                os.rmdir(expected_hash, dir_fd=store_fd)
    return store / expected_hash / "bundle"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-image-id", required=True)
    args = parser.parse_args(argv)
    try:
        result = import_bundle(args.source, args.store, args.expected_manifest_sha256,
                               args.expected_image_id)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Evidence import failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "retained-not-approved", "path": str(result),
                      "manifest_sha256": args.expected_manifest_sha256}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
