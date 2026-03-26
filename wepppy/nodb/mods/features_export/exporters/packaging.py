"""Deterministic packaging helpers for single-layer export bundles."""

from __future__ import annotations

import collections.abc as cabc
from pathlib import Path
import zipfile


def package_files_as_zip(
    bundle_path: str | Path,
    files_by_relpath: cabc.Mapping[str, str | Path],
) -> tuple[str, ...]:
    """Write deterministic zip bundle from `relpath -> file path` mapping."""

    if not isinstance(files_by_relpath, cabc.Mapping) or not files_by_relpath:
        raise ValueError("files_by_relpath must be a non-empty mapping.")

    resolved_bundle_path = Path(bundle_path).resolve()
    resolved_bundle_path.parent.mkdir(parents=True, exist_ok=True)

    normalized_sources: dict[str, str | Path] = {}
    for relpath, source in files_by_relpath.items():
        if not isinstance(relpath, str) or not relpath:
            raise ValueError("files_by_relpath keys must be non-empty strings.")
        normalized_sources[relpath] = source

    ordered_relpaths = tuple(sorted(normalized_sources))

    with zipfile.ZipFile(resolved_bundle_path, mode="w") as zip_handle:
        for relpath in ordered_relpaths:
            source_value = normalized_sources[relpath]
            source_path = Path(source_value).resolve()
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Zip member source path does not exist for {relpath!r}: {source_path}"
                )

            payload = source_path.read_bytes()
            zip_info = zipfile.ZipInfo(filename=relpath)
            zip_info.compress_type = zipfile.ZIP_DEFLATED
            zip_info.date_time = (1980, 1, 1, 0, 0, 0)
            zip_info.external_attr = 0o644 << 16
            zip_handle.writestr(zip_info, payload)

    return ordered_relpaths


__all__ = ["package_files_as_zip"]
