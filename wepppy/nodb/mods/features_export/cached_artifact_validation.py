"""Format checks for existing cached Features Export artifacts."""

from __future__ import annotations

import collections.abc as cabc
from pathlib import Path
import sqlite3
import zipfile

_GPKG_APPLICATION_ID = 0x47504B47


def cached_artifact_matches_format(
    artifact_path: Path,
    cache_entry: cabc.Mapping[str, object],
    *,
    format_token: str,
) -> bool:
    """Check the requested format after the service resolves the artifact path."""
    normalized_format = format_token.strip().lower()
    if normalized_format == "f_esri":
        normalized_format = "geodatabase"

    if normalized_format == "geopackage":
        return _is_valid_cached_geopackage_artifact(
            artifact_path=artifact_path,
            packaged_member_relpaths=_cache_entry_packaged_member_relpaths(cache_entry),
        )
    if normalized_format == "geodatabase":
        return _is_valid_cached_geodatabase_artifact(
            artifact_path=artifact_path,
        )
    if normalized_format == "csv":
        return _is_valid_cached_csv_artifact(
            artifact_path=artifact_path,
            packaged_member_relpaths=_cache_entry_packaged_member_relpaths(cache_entry),
        )

    return True


def _cache_entry_packaged_member_relpaths(cache_entry: cabc.Mapping[str, object]) -> tuple[str, ...]:
    raw = cache_entry.get("packaged_member_relpaths")
    if not isinstance(raw, list):
        return ()
    normalized: list[str] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            normalized.append(entry.strip())
    return tuple(normalized)


def _is_valid_cached_geopackage_artifact(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    if artifact_path.suffix.lower() == ".zip":
        return _is_valid_cached_geopackage_zip(
            artifact_path=artifact_path,
            packaged_member_relpaths=packaged_member_relpaths,
        )
    return _is_valid_cached_geopackage_file(artifact_path)


def _is_valid_cached_geopackage_zip(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False

            candidate_members = [
                member
                for member in packaged_member_relpaths
                if member.lower().endswith(".gpkg") and member in names
            ]
            if not candidate_members:
                candidate_members = [
                    member for member in names if member.lower().endswith(".gpkg")
                ]
            if not candidate_members:
                return False

            with zip_handle.open(sorted(candidate_members)[0], mode="r") as handle:
                return handle.read(16).startswith(b"SQLite format 3\x00")
    except (OSError, zipfile.BadZipFile, KeyError):
        return False


def _is_valid_cached_geopackage_file(artifact_path: Path) -> bool:
    try:
        with artifact_path.open("rb") as handle:
            if not handle.read(16).startswith(b"SQLite format 3\x00"):
                return False
    except OSError:
        return False

    try:
        with sqlite3.connect(str(artifact_path)) as conn:
            application_id_row = conn.execute("PRAGMA application_id").fetchone()
            if not application_id_row:
                return False
            try:
                application_id = int(application_id_row[0])
            except (TypeError, ValueError):
                return False
            if application_id != _GPKG_APPLICATION_ID:
                return False

            gpkg_contents_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gpkg_contents'"
            ).fetchone()
            return gpkg_contents_exists is not None
    except sqlite3.Error:
        return False


def _is_valid_cached_geodatabase_artifact(
    *,
    artifact_path: Path,
) -> bool:
    if artifact_path.suffix.lower() != ".zip":
        return False
    return _is_valid_cached_geodatabase_zip(artifact_path)


def _is_valid_cached_geodatabase_zip(artifact_path: Path) -> bool:
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False
            if artifact_path.name.lower().endswith(".gdb.zip"):
                return True
            lowered_names = tuple(name.lower() for name in names)
            if any(".gdb/" in name for name in lowered_names):
                return True
            if any(name.endswith(".gdbtable") for name in lowered_names):
                return True
            return False
    except (OSError, zipfile.BadZipFile):
        return False


def _is_valid_cached_csv_artifact(
    *,
    artifact_path: Path,
    packaged_member_relpaths: cabc.Sequence[str],
) -> bool:
    if artifact_path.suffix.lower() != ".zip":
        return artifact_path.suffix.lower() == ".csv"
    try:
        with zipfile.ZipFile(artifact_path, mode="r") as zip_handle:
            names = tuple(zip_handle.namelist())
            if not names:
                return False
            candidate_members = [
                member
                for member in packaged_member_relpaths
                if member.lower().endswith(".csv") and member in names
            ]
            if not candidate_members:
                candidate_members = [member for member in names if member.lower().endswith(".csv")]
            return bool(candidate_members)
    except (OSError, zipfile.BadZipFile):
        return False


__all__ = ["cached_artifact_matches_format"]
