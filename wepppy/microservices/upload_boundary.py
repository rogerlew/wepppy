"""Shared non-ZIP upload boundary helpers."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Callable, Optional, Sequence

from werkzeug.utils import secure_filename

UPLOAD_STREAM_CHUNK_BYTES = 64 * 1024
RASTER_EXTENSION_DRIVERS = {
    ".tif": "GTiff",
    ".tiff": "GTiff",
    ".img": "HFA",
}


class UploadBoundaryError(ValueError):
    """Raised when upload boundary validation fails."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RasterUploadIdentity:
    """Identity of bytes that completed restricted raster decoding."""

    driver: str
    sha256: str
    size: int
    device: int
    inode: int
    mtime_ns: int


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def raster_driver_for_path(path: Path | str) -> str:
    driver = RASTER_EXTENSION_DRIVERS.get(Path(path).suffix.lower())
    if driver is None:
        raise UploadBoundaryError(
            "Invalid raster extension. Allowed: .img, .tif, .tiff"
        )
    return driver


def resolve_contained_raster_path(path: Path | str, root: Path | str) -> Path:
    """Resolve an existing nonsymlink raster without permitting root escape."""
    root_path = Path(root).resolve(strict=True)
    candidate_path = Path(path)
    if not candidate_path.is_absolute():
        candidate_path = root_path / candidate_path
    try:
        candidate = candidate_path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise UploadBoundaryError("Stored raster is unavailable; upload it again.") from exc
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise UploadBoundaryError("Stored raster is outside the approved upload root.") from exc
    _regular_nonsymlink_stat(candidate_path)
    raster_driver_for_path(candidate)
    return candidate


def raster_companion_paths(path: Path | str) -> tuple[Path, ...]:
    """Return adjacent GDAL sidecars that could alter a later raster open."""
    raster_path = Path(path)
    if not raster_path.parent.is_dir():
        return ()
    name = raster_path.name.lower()
    stem = raster_path.stem.lower()
    bases = {name, stem}
    suffixes = {
        ".prj", ".wld", ".tfw", ".tifw", ".tab", ".hdr", ".aux",
        ".aux.xml", ".xml", ".rpb", "_rpc.txt", ".rpc.txt", ".imd",
        ".rrd", ".ige", ".msk", ".ovr",
    }
    extension = raster_path.suffix.lower().lstrip(".")
    if extension:
        suffixes.update({f".{extension}w", f".{extension[0]}{extension[-1]}w"})
    candidate_names = {base + suffix for base in bases for suffix in suffixes}
    return tuple(
        sorted(
            entry
            for entry in raster_path.parent.iterdir()
            if entry != raster_path and entry.name.lower() in candidate_names
        )
    )


def reject_raster_companions(path: Path | str) -> None:
    """Require a raster snapshot to remain independent of adjacent sidecars."""
    if any(candidate.exists() or candidate.is_symlink() for candidate in raster_companion_paths(path)):
        raise UploadBoundaryError(
            "Uploaded raster has companion files; provide a self-contained file."
        )


def _regular_nonsymlink_stat(path: Path) -> os.stat_result:
    try:
        result = path.lstat()
    except FileNotFoundError as exc:
        raise UploadBoundaryError("Uploaded raster is unavailable.") from exc
    if path.is_symlink() or not stat.S_ISREG(result.st_mode):
        raise UploadBoundaryError("Uploaded raster must be a regular nonsymlink file.")
    return result


def open_raster_with_expected_driver(path: Path | str):
    """Open a raster with only the extension-selected GDAL driver enabled."""
    from osgeo import gdal

    raster_path = Path(path)
    expected_driver = raster_driver_for_path(raster_path)
    _regular_nonsymlink_stat(raster_path)
    try:
        with gdal.ExceptionMgr(useExceptions=True):
            dataset = gdal.OpenEx(
                str(raster_path),
                gdal.OF_RASTER | gdal.OF_READONLY,
                allowed_drivers=[expected_driver],
            )
    except RuntimeError as exc:
        raise UploadBoundaryError(
            f"Raster content does not match {raster_path.suffix.lower()} ({expected_driver})."
        ) from exc
    if dataset is None or dataset.GetDriver().ShortName != expected_driver:
        dataset = None
        raise UploadBoundaryError(
            f"Raster content does not match {raster_path.suffix.lower()} ({expected_driver})."
        )
    return dataset


def validate_raster_upload(path: Path | str) -> RasterUploadIdentity:
    """Fully decode a self-contained GTiff/HFA and record its immutable identity."""
    from osgeo import gdal

    raster_path = Path(path)
    reject_raster_companions(raster_path)
    before = _regular_nonsymlink_stat(raster_path)
    before_hash = _file_sha256(raster_path)
    previous_readdir = gdal.GetThreadLocalConfigOption("GDAL_DISABLE_READDIR_ON_OPEN")
    previous_vrt_python = gdal.GetThreadLocalConfigOption("GDAL_VRT_ENABLE_PYTHON")
    gdal.SetThreadLocalConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    gdal.SetThreadLocalConfigOption("GDAL_VRT_ENABLE_PYTHON", "NO")
    dataset = None
    try:
        dataset = open_raster_with_expected_driver(raster_path)
        if dataset.RasterCount < 1 or dataset.RasterXSize < 1 or dataset.RasterYSize < 1:
            raise UploadBoundaryError("Uploaded raster has no readable raster cells.")
        files = dataset.GetFileList() or []
        primary = raster_path.resolve(strict=True)
        dependencies = []
        for item in files:
            try:
                candidate = Path(item).resolve(strict=True)
            except (FileNotFoundError, OSError):
                dependencies.append(item)
                continue
            if candidate != primary:
                dependencies.append(item)
        if dependencies:
            raise UploadBoundaryError(
                "Uploaded raster depends on companion files; provide a self-contained file."
            )
        try:
            with gdal.ExceptionMgr(useExceptions=True):
                for band_number in range(1, dataset.RasterCount + 1):
                    dataset.GetRasterBand(band_number).Checksum()
        except RuntimeError as exc:
            raise UploadBoundaryError("Uploaded raster data could not be read.") from exc
        driver = dataset.GetDriver().ShortName
    finally:
        dataset = None
        gdal.SetThreadLocalConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", previous_readdir)
        gdal.SetThreadLocalConfigOption("GDAL_VRT_ENABLE_PYTHON", previous_vrt_python)

    after = _regular_nonsymlink_stat(raster_path)
    after_hash = _file_sha256(raster_path)
    identity = RasterUploadIdentity(
        driver=driver,
        sha256=before_hash,
        size=before.st_size,
        device=before.st_dev,
        inode=before.st_ino,
        mtime_ns=before.st_mtime_ns,
    )
    if (
        after_hash != identity.sha256
        or after.st_size != identity.size
        or after.st_dev != identity.device
        or after.st_ino != identity.inode
        or after.st_mtime_ns != identity.mtime_ns
    ):
        raise UploadBoundaryError("Uploaded raster changed during validation.")
    return identity


def assert_raster_upload_identity(
    path: Path | str,
    identity: RasterUploadIdentity,
) -> None:
    """Reject replacement or mutation after restricted raster validation."""
    raster_path = Path(path)
    reject_raster_companions(raster_path)
    current = _regular_nonsymlink_stat(raster_path)
    if (
        current.st_size != identity.size
        or current.st_dev != identity.device
        or current.st_ino != identity.inode
        or current.st_mtime_ns != identity.mtime_ns
        or _file_sha256(raster_path) != identity.sha256
    ):
        raise UploadBoundaryError("Uploaded raster changed after validation.")


def normalize_extensions(allowed_extensions: Sequence[str]) -> set[str]:
    normalized: set[str] = set()
    for ext in allowed_extensions:
        if not ext:
            continue
        cleaned = str(ext).lower().lstrip(".")
        if cleaned:
            normalized.add(cleaned)
    return normalized


def prepare_filename(
    raw_name: str | None,
    *,
    filename_transform: Optional[Callable[[str], str]] = None,
    lowercase_by_default: bool = True,
) -> str:
    value = "" if raw_name is None else str(raw_name)
    if value.strip() == "":
        raise UploadBoundaryError("no filename specified")

    safe_name = secure_filename(value)
    if not safe_name:
        raise UploadBoundaryError("Invalid filename")

    if filename_transform is None:
        transformed = safe_name.lower() if lowercase_by_default else safe_name
    else:
        transformed = filename_transform(safe_name)

    transformed = transformed.strip()
    if not transformed:
        raise UploadBoundaryError("Invalid filename")

    return transformed


def enforce_extension(filename: str, allowed_extensions: Sequence[str] | set[str]) -> None:
    allowed = normalize_extensions(tuple(allowed_extensions))
    if not allowed:
        return

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed:
        allowed_list = ", ".join(sorted(f".{token}" for token in allowed))
        raise UploadBoundaryError(f"Invalid file extension. Allowed: {allowed_list}")


def _rewind_stream(stream: IO[bytes]) -> None:
    seek = getattr(stream, "seek", None)
    if callable(seek):
        seek(0)


def write_stream_to_destination(
    stream: IO[bytes],
    destination: Path,
    *,
    overwrite: bool = False,
    max_bytes: int | None = None,
    chunk_bytes: int = UPLOAD_STREAM_CHUNK_BYTES,
    size_error_message: str = "File exceeds maximum allowed size",
) -> int:
    if destination.exists() and not overwrite:
        raise UploadBoundaryError("File already exists")
    _rewind_stream(stream)
    # Transport validation owns temporary storage. Do not unlink an accepted
    # source (or create its parent) until the entire incoming stream is valid.
    with tempfile.TemporaryFile() as buffered:
        bytes_written = 0
        while True:
            chunk = stream.read(chunk_bytes)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            bytes_written += len(chunk)
            if max_bytes is not None and bytes_written > max_bytes:
                raise UploadBoundaryError(size_error_message, status_code=413)
            buffered.write(chunk)
        buffered.seek(0)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.upload")
        try:
            # Normal open preserves the existing umask-based creation policy.
            with staged.open("xb") as handle:
                while chunk := buffered.read(chunk_bytes):
                    handle.write(chunk)
            if overwrite:
                os.replace(staged, destination)
            else:
                try:
                    os.link(staged, destination)
                except FileExistsError as exc:
                    raise UploadBoundaryError("File already exists") from exc
        finally:
            staged.unlink(missing_ok=True)
    return bytes_written


def save_upload_from_stream(
    *,
    raw_filename: str | None,
    stream: IO[bytes] | None,
    dest_dir: Path,
    allowed_extensions: Sequence[str],
    filename_transform: Optional[Callable[[str], str]] = None,
    lowercase_by_default: bool = True,
    overwrite: bool = False,
    max_bytes: int | None = None,
    post_save: Optional[Callable[[Path], None]] = None,
    isolated_post_save: bool = False,
    size_error_message: str = "File exceeds maximum allowed size",
    chunk_bytes: int = UPLOAD_STREAM_CHUNK_BYTES,
) -> Path:
    """Validate transport and optional staged content before promoting a source.

    The legacy ``post_save`` callback receives a temporary sibling path, not the
    accepted destination. It must finish validation before returning and must not
    retain that temporary pathname in metadata. Only successful validation permits
    destination replacement; the return value is the accepted final path.
    """
    if stream is None:
        raise UploadBoundaryError("Uploaded file stream is unavailable.")

    filename = prepare_filename(
        raw_filename,
        filename_transform=filename_transform,
        lowercase_by_default=lowercase_by_default,
    )
    enforce_extension(filename, allowed_extensions)

    destination = dest_dir / filename
    if destination.exists() and not overwrite:
        raise UploadBoundaryError("File already exists")
    if post_save is not None:
        # A sibling preserves relative VRT dependencies without replacing the
        # accepted source. All transport staging is removed on every exit.
        created_parents = []
        parent = dest_dir
        while not parent.exists():
            created_parents.append(parent)
            parent = parent.parent
        validation_dir: Path | None = None
        if isolated_post_save:
            dest_dir.mkdir(parents=True, exist_ok=True)
            validation_dir = Path(
                tempfile.mkdtemp(prefix=".upload-validation-", dir=dest_dir)
            )
            validation_dir.chmod(0o700)
            staged = validation_dir / filename
        else:
            staged = dest_dir / f".{uuid.uuid4().hex}.{filename}"
        try:
            write_stream_to_destination(stream, staged, max_bytes=max_bytes,
                                        chunk_bytes=chunk_bytes, size_error_message=size_error_message)
            post_save(staged)
            if isolated_post_save:
                reject_raster_companions(destination)
            with staged.open("rb") as validated:
                write_stream_to_destination(validated, destination, overwrite=overwrite,
                                            chunk_bytes=chunk_bytes)
        finally:
            staged.unlink(missing_ok=True)
            if validation_dir is not None:
                shutil.rmtree(validation_dir)
            for parent in created_parents:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
    else:
        write_stream_to_destination(stream, destination, overwrite=overwrite,
                                    max_bytes=max_bytes, chunk_bytes=chunk_bytes,
                                    size_error_message=size_error_message)
    return destination


__all__ = [
    "UPLOAD_STREAM_CHUNK_BYTES",
    "RASTER_EXTENSION_DRIVERS",
    "RasterUploadIdentity",
    "UploadBoundaryError",
    "assert_raster_upload_identity",
    "enforce_extension",
    "normalize_extensions",
    "open_raster_with_expected_driver",
    "prepare_filename",
    "raster_companion_paths",
    "reject_raster_companions",
    "raster_driver_for_path",
    "resolve_contained_raster_path",
    "save_upload_from_stream",
    "validate_raster_upload",
    "write_stream_to_destination",
]
