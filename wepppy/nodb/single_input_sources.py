"""Immutable, run-scoped accepted WEPP source generations."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import os
import errno
import logging
from itertools import islice
from pathlib import Path
import re
import stat
import uuid

from wepppy.nodb.base import NoDbStaleWriteError
from wepppy.nodb.single_input_policy import require_single_input_policy
from wepppy.wepp.single_input import (
    MAX_SOURCE_BYTES, SingleInputError, canonical_management, decode_source,
    read_uploaded_management, validate_filename, validate_soil_text,
)

__all__ = ["accept_source", "read_source", "source_metadata", "write_generated_source"]
_DIRECTORY = "single-user-defined"
_SOURCE_NAME = re.compile(r"^[0-9a-f]{64}\.(man|sol)$")


def source_metadata(controller):
    return getattr(controller, "_single_user_defined_source", None)


def _valid_metadata(metadata, kind):
    if not isinstance(metadata, dict):
        return False
    relative = metadata.get("relative_path")
    digest = metadata.get("sha256")
    extension = "man" if kind == "landuse" else "sol"
    return (isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
            and relative == f"{_DIRECTORY}/{digest}.{extension}"
            and type(metadata.get("size_bytes")) is int
            and 0 < metadata["size_bytes"] <= MAX_SOURCE_BYTES
            and isinstance(metadata.get("filename"), str))


@contextmanager
def _directory(controller, kind, *, create=False):
    root = Path(controller.wd) / kind
    if create:
        root.mkdir(exist_ok=True)
    resolved = root.resolve()
    run_root = Path(controller.wd).resolve()
    permitted = [run_root / kind, run_root / ".nodir" / "lower" / kind,
                 run_root / ".nodir" / "upper" / kind]
    if not any(resolved == candidate or resolved.is_relative_to(candidate) for candidate in permitted):
        raise SingleInputError("The module directory is not a managed run directory.",
                               code="single_input_unavailable", status_code=409)
    root_fd = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    directory_fd = None
    try:
        if create:
            try:
                os.mkdir(_DIRECTORY, dir_fd=root_fd)
            except FileExistsError:
                pass
        directory_fd = os.open(_DIRECTORY, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        yield directory_fd
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        os.close(root_fd)


def _read_regular(directory_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise SingleInputError("The accepted source is not a regular file.", code="single_input_unavailable", status_code=409)
        return stream.read(MAX_SOURCE_BYTES + 1)


def _remove_interrupted_staging(directory_fd):
    """Caller owns idle admission and module maintenance; bound crash cleanup."""
    pattern = re.compile(r"^(?:\.source-[0-9a-f]{32}|\.validate-[0-9a-f]{32}\.man)$")
    with os.scandir(directory_fd) as entries:
        for entry in islice(entries, 256):
            if pattern.fullmatch(entry.name) and entry.is_file(follow_symlinks=False):
                os.unlink(entry.name, dir_fd=directory_fd)


def _canonical_text(directory_fd, raw, kind):
    text = decode_source(raw)
    if kind == "soils":
        validate_soil_text(text)
        # Soil stacking counts noncomment rows, so write a normalized derived copy.
        return "\n".join(line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")) + "\n"
    name = f".validate-{uuid.uuid4().hex}.man"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        management = read_uploaded_management(f"/proc/self/fd/{directory_fd}/{name}")
        canonical = canonical_management(management)
        # Validate the serialized file, not only the parsed object.
        fd = os.open(name, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=directory_fd)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(canonical)
        read_uploaded_management(f"/proc/self/fd/{directory_fd}/{name}")
        return canonical
    finally:
        os.unlink(name, dir_fd=directory_fd)


def accept_source(controller, kind: str, raw: bytes, filename: str):
    try:
        return _accept_source(controller, kind, raw, filename)
    except NoDbStaleWriteError as exc:
        raise SingleInputError("Source state changed; reload and retry the upload.", code="conflict", status_code=409) from exc
    except OSError as exc:
        logging.getLogger(__name__).exception("Single-input source publication failed for %s", kind)
        unavailable = exc.errno in {errno.ELOOP, errno.ENOTDIR, errno.EISDIR, errno.ENXIO}
        raise SingleInputError(
            "The source directory is unavailable." if unavailable else "Unable to store the uploaded source; retry the upload.",
            code="single_input_unavailable" if unavailable else "single_input_storage_failed",
            status_code=409 if unavailable else 500,
        ) from exc


def _accept_source(controller, kind: str, raw: bytes, filename: str):
    """Caller holds module maintenance and run submission locks before acceptance."""
    if (Path(controller.wd) / "READONLY").exists():
        raise SingleInputError("This project is read-only.", code="forbidden", status_code=403)
    require_single_input_policy(controller, require_enabled=True)
    filename = validate_filename(filename, kind)
    decode_source(raw)
    extension = "man" if kind == "landuse" else "sol"
    digest = sha256(raw).hexdigest()
    name = f"{digest}.{extension}"
    with _directory(controller, kind, create=True) as directory_fd:
        _remove_interrupted_staging(directory_fd)
        canonical = _canonical_text(directory_fd, raw, kind)
        created = False
        committed = False
        controller.lock()
        try:
            controller = type(controller).getInstance(controller.wd)
            require_single_input_policy(controller, require_enabled=True)
            previous = source_metadata(controller)
            if not _valid_metadata(previous, kind):
                previous = None
            staging = f".source-{uuid.uuid4().hex}"
            fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=directory_fd)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(staging, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
                    created = True
                    os.fsync(directory_fd)
                except FileExistsError:
                    if _read_regular(directory_fd, name) != raw:
                        raise SingleInputError("The stored source identity conflicts with this upload.", code="single_input_unavailable", status_code=409)
            finally:
                os.unlink(staging, dir_fd=directory_fd)
            metadata = {"filename": filename, "sha256": digest, "size_bytes": len(raw),
                        "version": "98.4" if kind == "landuse" else f"{float(canonical.splitlines()[0]):g}",
                        "relative_path": f"{_DIRECTORY}/{name}"}
            if previous and previous.get("relative_path") != metadata["relative_path"]:
                metadata["previous_relative_path"] = previous["relative_path"]
            elif previous and "previous_relative_path" in previous:
                previous_name = str(previous["previous_relative_path"]).removeprefix(_DIRECTORY + "/")
                if _SOURCE_NAME.fullmatch(previous_name):
                    metadata["previous_relative_path"] = _DIRECTORY + "/" + previous_name
            controller._single_user_defined_source = metadata
            controller.dump()
            committed = True
        finally:
            try:
                if not committed:
                    # Inspect durable state before removing a candidate: dump may
                    # have replaced the NoDb file before raising an I/O error.
                    durable = type(controller).load_detached(controller.wd)
                    selected = source_metadata(durable)
                    controller._single_user_defined_source = selected
                    if created and (not isinstance(selected, dict) or selected.get("relative_path") != f"{_DIRECTORY}/{name}"):
                        os.unlink(name, dir_fd=directory_fd)
            finally:
                controller.unlock()
        # Only idle, unreferenced immutable generations are removed.
        retained = {Path(metadata[key]).name for key in ("relative_path", "previous_relative_path") if key in metadata}
        for entry in os.listdir(directory_fd):
            if _SOURCE_NAME.fullmatch(entry) and entry not in retained:
                if stat.S_ISREG(os.stat(entry, dir_fd=directory_fd, follow_symlinks=False).st_mode):
                    os.unlink(entry, dir_fd=directory_fd)
    return metadata


def read_source(controller, kind: str) -> tuple[bytes, str]:
    require_single_input_policy(controller, require_enabled=True)
    metadata = source_metadata(controller)
    if metadata is None:
        raise SingleInputError("Upload a source file before building Single User-Defined inputs.", code="single_input_required")
    try:
        if not _valid_metadata(metadata, kind):
            raise ValueError("invalid source metadata")
        relative = metadata["relative_path"]
        name = relative.removeprefix(_DIRECTORY + "/")
        expected_extension = ".man" if kind == "landuse" else ".sol"
        if relative != _DIRECTORY + "/" + name or not _SOURCE_NAME.fullmatch(name) or not name.endswith(expected_extension):
            raise ValueError("invalid source path")
        with _directory(controller, kind) as directory_fd:
            raw = _read_regular(directory_fd, name)
            if len(raw) != metadata["size_bytes"] or sha256(raw).hexdigest() != metadata["sha256"]:
                raise ValueError("source identity changed")
            return raw, _canonical_text(directory_fd, raw, kind)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise SingleInputError("The accepted source is unavailable or changed; upload it again.", code="single_input_unavailable", status_code=409) from exc


def write_generated_source(controller, kind: str) -> str:
    """Prepare a normalized copy; accepted bytes remain immutable."""
    _, canonical = read_source(controller, kind)
    extension = "man" if kind == "landuse" else "sol"
    path = Path(controller.wd) / kind / f"single-user-defined.{extension}"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise SingleInputError("Generated source must be a regular file.")
        stream.truncate(0)
        stream.write(canonical)
    return str(path)
