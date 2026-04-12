"""ZIP archive validation and controlled extraction helpers."""

from __future__ import annotations

import io
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from starlette.datastructures import UploadFile

from .errors import ShapeConverterError

REQUIRED_SHAPEFILE_EXTENSIONS = frozenset({".shp", ".shx", ".dbf"})
OPTIONAL_SHAPEFILE_EXTENSIONS = frozenset({".prj", ".cpg", ".sbn", ".sbx", ".qix"})
ALLOWED_SHAPEFILE_EXTENSIONS = REQUIRED_SHAPEFILE_EXTENSIONS | OPTIONAL_SHAPEFILE_EXTENSIONS
_SHP_XML_SIDECAR_SUFFIX = ".shp.xml"
_QMD_SIDECAR_SUFFIX = ".qmd"

_ALLOWED_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_ALLOWED_COMPRESSION_METHODS = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:")
_UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    max_compressed_bytes: int = 100 * 1024 * 1024
    max_uncompressed_bytes: int = 600 * 1024 * 1024
    max_member_count: int = 200
    max_path_depth: int = 16
    max_name_length: int = 255
    max_path_length: int = 512


@dataclass(frozen=True, slots=True)
class ExtractedArchive:
    extraction_root: Path
    extracted_files: tuple[Path, ...]
    removed_shp_xml_sidecars: tuple[str, ...] = ()


async def read_upload_bytes_with_limit(
    *,
    upload: UploadFile,
    max_bytes: int,
) -> bytes:
    """Read upload content with explicit byte cap enforcement."""

    declared_size = getattr(upload, "size", None)
    if isinstance(declared_size, int) and declared_size > max_bytes:
        await upload.close()
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Archive exceeds compressed byte limit.",
            details=(
                f"Upload declared size is {declared_size} bytes, exceeding "
                f"limit {max_bytes} bytes."
            ),
            status_code=413,
        )

    chunks: list[bytes] = []
    total_bytes = 0
    try:
        while True:
            chunk = await upload.read(_UPLOAD_READ_CHUNK_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise ShapeConverterError(
                    code="archive_quota_exceeded",
                    message="Archive exceeds compressed byte limit.",
                    details=(
                        f"Archive payload exceeded {max_bytes} bytes while streaming upload read."
                    ),
                    status_code=413,
                )
            chunks.append(chunk)
    finally:
        await upload.close()

    return b"".join(chunks)


def validate_and_extract_zip_archive(
    *,
    archive_name: str,
    archive_bytes: bytes,
    extraction_root: Path,
    limits: ArchiveLimits | None = None,
) -> ExtractedArchive:
    """Validate and extract a ZIP archive into ``extraction_root``."""

    active_limits = limits or ArchiveLimits()
    _validate_archive_file_type(archive_name=archive_name, archive_bytes=archive_bytes)

    if len(archive_bytes) > active_limits.max_compressed_bytes:
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Archive exceeds compressed byte limit.",
            details=(
                f"Archive payload is {len(archive_bytes)} bytes, exceeding the "
                f"{active_limits.max_compressed_bytes} byte compressed limit."
            ),
            status_code=413,
        )

    extraction_root.mkdir(parents=True, exist_ok=True)
    extraction_root_resolved = extraction_root.resolve()

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = archive.infolist()
            if not members:
                raise ShapeConverterError(
                    code="invalid_archive",
                    message="Archive contains no entries.",
                    details="ZIP archive is empty.",
                )

            if len(members) > active_limits.max_member_count:
                raise ShapeConverterError(
                    code="archive_quota_exceeded",
                    message="Archive member count exceeds configured limit.",
                    details=(
                        f"Archive contains {len(members)} members, exceeding limit "
                        f"{active_limits.max_member_count}."
                    ),
                    status_code=413,
                )

            validated_members: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            normalized_paths_seen: set[str] = set()
            total_compressed_bytes = 0
            total_uncompressed_bytes = 0

            for member in members:
                normalized_path = _validate_member_path(member.filename, limits=active_limits)
                normalized_key = normalized_path.as_posix().lower()
                if normalized_key in normalized_paths_seen:
                    raise ShapeConverterError(
                        code="invalid_archive",
                        message="Archive contains duplicate member paths.",
                        details=f"Duplicate member path detected: '{member.filename}'.",
                    )
                normalized_paths_seen.add(normalized_key)

                _validate_member_safety(member, normalized_path)

                total_compressed_bytes += int(member.compress_size)
                total_uncompressed_bytes += int(member.file_size)
                if total_compressed_bytes > active_limits.max_compressed_bytes:
                    raise ShapeConverterError(
                        code="archive_quota_exceeded",
                        message="Archive compressed size exceeds configured limit.",
                        details=(
                            f"Archive compressed bytes exceed limit "
                            f"{active_limits.max_compressed_bytes}."
                        ),
                        status_code=413,
                    )
                if total_uncompressed_bytes > active_limits.max_uncompressed_bytes:
                    raise ShapeConverterError(
                        code="archive_quota_exceeded",
                        message="Archive uncompressed size exceeds configured limit.",
                        details=(
                            f"Archive uncompressed bytes exceed limit "
                            f"{active_limits.max_uncompressed_bytes}."
                        ),
                        status_code=413,
                    )

                validated_members.append((member, normalized_path))

            extracted_files: list[Path] = []
            for member, normalized_path in validated_members:
                target_path = extraction_root / Path(normalized_path.as_posix())
                resolved_target = target_path.resolve()
                if extraction_root_resolved not in resolved_target.parents and resolved_target != extraction_root_resolved:
                    raise ShapeConverterError(
                        code="archive_path_traversal",
                        message="Archive member path escapes extraction root.",
                        details=f"Refused extraction path '{member.filename}'.",
                    )

                if member.is_dir():
                    resolved_target.mkdir(parents=True, exist_ok=True)
                    continue

                resolved_target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, resolved_target.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 64)
                extracted_files.append(resolved_target)

    except zipfile.BadZipFile as exc:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive is not a valid ZIP file.",
            details=str(exc),
        ) from exc

    kept_files, removed_shp_xml_sidecars = _strip_sanitized_sidecars(
        extracted_files=extracted_files,
        extraction_root=extraction_root_resolved,
    )

    return ExtractedArchive(
        extraction_root=extraction_root_resolved,
        extracted_files=kept_files,
        removed_shp_xml_sidecars=removed_shp_xml_sidecars,
    )


def _validate_archive_file_type(*, archive_name: str, archive_bytes: bytes) -> None:
    lowered_name = archive_name.lower()
    if not lowered_name.endswith(".zip"):
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive must use .zip extension.",
            details=f"Received filename '{archive_name}'.",
        )

    if len(archive_bytes) < 4 or archive_bytes[:4] not in _ALLOWED_ZIP_SIGNATURES:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive signature is invalid.",
            details="ZIP signature check failed.",
        )

    if not zipfile.is_zipfile(io.BytesIO(archive_bytes)):
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive payload is not a valid ZIP.",
            details="zipfile parser rejected payload.",
        )


def _validate_member_path(raw_name: str, *, limits: ArchiveLimits) -> PurePosixPath:
    normalized = raw_name.replace("\\", "/")
    normalized = normalized.strip()

    if not normalized:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive member name is empty.",
            details="ZIP contains an entry with an empty name.",
        )

    if len(normalized) > limits.max_path_length:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive member path is too long.",
            details=(
                f"Path '{raw_name}' length exceeds configured "
                f"{limits.max_path_length} character limit."
            ),
        )

    if normalized.startswith("/") or _DRIVE_PATH_RE.match(normalized):
        raise ShapeConverterError(
            code="archive_path_traversal",
            message="Archive member path is absolute.",
            details=f"Refused absolute path '{raw_name}'.",
        )

    if any(ord(ch) < 32 for ch in normalized):
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive member path contains control characters.",
            details=f"Refused path '{raw_name}'.",
        )

    pure_path = PurePosixPath(normalized)
    parts = pure_path.parts
    if len(parts) > limits.max_path_depth:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive member path depth exceeds configured limit.",
            details=(
                f"Path '{raw_name}' depth {len(parts)} exceeds "
                f"limit {limits.max_path_depth}."
            ),
        )

    for segment in parts:
        if segment in {"", ".", ".."}:
            raise ShapeConverterError(
                code="archive_path_traversal",
                message="Archive member path contains traversal segment.",
                details=f"Refused path '{raw_name}'.",
            )
        if len(segment) > limits.max_name_length:
            raise ShapeConverterError(
                code="invalid_archive",
                message="Archive member name exceeds configured limit.",
                details=(
                    f"Path segment '{segment}' exceeds "
                    f"{limits.max_name_length} characters."
                ),
            )

    return pure_path


def _validate_member_safety(member: zipfile.ZipInfo, normalized_path: PurePosixPath) -> None:
    if member.flag_bits & 0x1:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive contains encrypted entries.",
            details=f"Entry '{member.filename}' is encrypted.",
        )

    if member.compress_type not in _ALLOWED_COMPRESSION_METHODS:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive uses unsupported compression method.",
            details=(
                f"Entry '{member.filename}' uses compression type "
                f"{member.compress_type}."
            ),
        )

    if _is_symlink_or_special(member):
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive contains symlink or special file entries.",
            details=f"Entry '{member.filename}' is not a regular file/directory.",
        )

    if not member.is_dir() and normalized_path.suffix.lower() == ".zip":
        raise ShapeConverterError(
            code="invalid_archive",
            message="Nested archives are not permitted.",
            details=f"Entry '{member.filename}' is a nested archive.",
        )

    if member.is_dir():
        return

    if _is_sanitized_sidecar_name(normalized_path.name):
        return

    suffix = normalized_path.suffix.lower()
    if suffix not in ALLOWED_SHAPEFILE_EXTENSIONS:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive contains unsupported file extension.",
            details=(
                f"Entry '{member.filename}' uses extension '{suffix}'. Allowed: "
                f"{sorted(ALLOWED_SHAPEFILE_EXTENSIONS)}"
            ),
        )


def _strip_sanitized_sidecars(
    *,
    extracted_files: list[Path],
    extraction_root: Path,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    kept_files: list[Path] = []
    removed_sidecars: list[str] = []

    for extracted_file in extracted_files:
        if _is_sanitized_sidecar_name(extracted_file.name):
            try:
                extracted_file.unlink(missing_ok=True)
            except OSError as exc:
                raise ShapeConverterError(
                    code="invalid_archive",
                    message="Failed to sanitize extracted metadata sidecar.",
                    details=(
                        f"Unable to delete sanitized sidecar "
                        f"'{extracted_file.relative_to(extraction_root).as_posix()}': {exc}"
                    ),
                    status_code=500,
                ) from exc

            if _is_shp_xml_sidecar_name(extracted_file.name):
                removed_sidecars.append(extracted_file.relative_to(extraction_root).as_posix())
            continue

        kept_files.append(extracted_file)

    return tuple(kept_files), tuple(removed_sidecars)


def _is_shp_xml_sidecar_name(name: str) -> bool:
    return name.lower().endswith(_SHP_XML_SIDECAR_SUFFIX)


def _is_qmd_sidecar_name(name: str) -> bool:
    return name.lower().endswith(_QMD_SIDECAR_SUFFIX)


def _is_sanitized_sidecar_name(name: str) -> bool:
    return _is_shp_xml_sidecar_name(name) or _is_qmd_sidecar_name(name)


def shp_xml_sidecar_warning_message(*, removed_sidecars: tuple[str, ...]) -> str | None:
    if not removed_sidecars:
        return None

    listed_sidecars = ", ".join(sorted(removed_sidecars))
    return (
        f"Removed .shp.xml metadata sidecar(s): {listed_sidecars}. "
        "It is generally not advisable to pack .shp.xml files in shapefile ZIP archives because "
        "they may contain sensitive metadata such as usernames, file paths, contact information, "
        "or processing history."
    )


def _is_symlink_or_special(member: zipfile.ZipInfo) -> bool:
    unix_mode = (member.external_attr >> 16) & 0xFFFF

    if member.create_system == 3 and unix_mode:
        file_type = stat.S_IFMT(unix_mode)
        if file_type in {stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK}:
            return True
        if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
            return True

    return False


__all__ = [
    "ALLOWED_SHAPEFILE_EXTENSIONS",
    "ArchiveLimits",
    "ExtractedArchive",
    "OPTIONAL_SHAPEFILE_EXTENSIONS",
    "REQUIRED_SHAPEFILE_EXTENSIONS",
    "read_upload_bytes_with_limit",
    "shp_xml_sidecar_warning_message",
    "validate_and_extract_zip_archive",
]
