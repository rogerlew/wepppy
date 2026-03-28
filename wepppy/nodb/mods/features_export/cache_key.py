"""Cache key and persistent cache index helpers for features export WP-2."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from .contracts import DEFAULT_SWAT_RUN_ID, ResolvedExportPlan

CACHE_INDEX_RELPATH = "export/features/cache/index.json"
CACHE_INDEX_SCHEMA_VERSION = 1
DEFAULT_CONVERSION_VERSION_MARKER = "unitizer-v1"
DEFAULT_EXPORT_VERSION_MARKER = "features-export-wp11-key-first-v2"


@dataclass(frozen=True)
class CacheKeyParts:
    """Deterministic cache key components."""

    request_hash: str
    dependency_fingerprint: str
    cache_key: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "request_hash": self.request_hash,
            "dependency_fingerprint": self.dependency_fingerprint,
            "cache_key": self.cache_key,
        }


def build_request_hash(
    plan: ResolvedExportPlan,
    *,
    unitizer_preferences_fingerprint: str | None = None,
    conversion_version_marker: str = DEFAULT_CONVERSION_VERSION_MARKER,
    export_version_marker: str = DEFAULT_EXPORT_VERSION_MARKER,
) -> str:
    """Build canonical request hash from normalized payload and version markers."""

    request = plan.request
    if not request.swat_run_id or request.swat_run_id == DEFAULT_SWAT_RUN_ID:
        raise ValueError(
            "Cache request hash requires a concrete swat_run_id; "
            "resolve 'latest' to a concrete run id before hashing."
        )

    payload: dict[str, object] = {
        "request": request.to_mapping(),
        "version_markers": {
            "catalog_version": plan.catalog_version,
            "catalog_schema_version": plan.schema_version,
            "conversion_version": conversion_version_marker,
            "export_version": export_version_marker,
        },
    }

    if request.units == "project":
        if not isinstance(unitizer_preferences_fingerprint, str) or not unitizer_preferences_fingerprint:
            raise ValueError(
                "units=project requires a non-empty Unitizer preferences fingerprint "
                "for cache request hashing."
            )
        payload["unitizer_preferences_fingerprint"] = unitizer_preferences_fingerprint

    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_payload.encode("utf-8")).hexdigest()


def build_cache_key(
    plan: ResolvedExportPlan,
    dependency_fingerprint: str,
    *,
    unitizer_preferences_fingerprint: str | None = None,
    conversion_version_marker: str = DEFAULT_CONVERSION_VERSION_MARKER,
    export_version_marker: str = DEFAULT_EXPORT_VERSION_MARKER,
) -> CacheKeyParts:
    """Build final cache key from request hash and dependency fingerprint."""

    if not isinstance(dependency_fingerprint, str) or not dependency_fingerprint:
        raise ValueError("dependency_fingerprint must be a non-empty string.")

    request_hash = build_request_hash(
        plan,
        unitizer_preferences_fingerprint=unitizer_preferences_fingerprint,
        conversion_version_marker=conversion_version_marker,
        export_version_marker=export_version_marker,
    )
    cache_key = f"{request_hash}+{dependency_fingerprint}"
    return CacheKeyParts(
        request_hash=request_hash,
        dependency_fingerprint=dependency_fingerprint,
        cache_key=cache_key,
    )


def cache_index_path(wd: str | Path) -> Path:
    """Return persistent features export cache index path for a run workspace."""

    return Path(wd).resolve() / CACHE_INDEX_RELPATH


def load_cache_index(wd: str | Path) -> dict[str, object]:
    """Load cache index payload from disk; return default when file is absent."""

    path = cache_index_path(wd)
    if not path.exists():
        return _default_cache_index_payload()

    text = path.read_text(encoding="utf-8")
    data = json.loads(text)

    if not isinstance(data, cabc.Mapping):
        raise ValueError("Cache index payload must be an object.")

    schema_version = data.get("schema_version")
    if schema_version != CACHE_INDEX_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported cache index schema_version {schema_version!r}; "
            f"expected {CACHE_INDEX_SCHEMA_VERSION}."
        )

    entries_raw = data.get("entries")
    if not isinstance(entries_raw, cabc.Mapping):
        raise ValueError("Cache index payload must include object field 'entries'.")

    entries: dict[str, dict[str, object]] = {}
    for key, value in entries_raw.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Cache index entry keys must be non-empty strings.")
        entries[key] = _normalize_entry_mapping(value)

    return {
        "schema_version": CACHE_INDEX_SCHEMA_VERSION,
        "entries": {key: entries[key] for key in sorted(entries)},
    }


def get_cache_index_entry(wd: str | Path, cache_key: str) -> dict[str, object] | None:
    """Return cache index entry for `cache_key` when present."""

    if not cache_key:
        raise ValueError("cache_key must be a non-empty string.")

    index_payload = load_cache_index(wd)
    entries = index_payload["entries"]
    if not isinstance(entries, cabc.Mapping):
        raise ValueError("Cache index payload entries must be an object.")

    value = entries.get(cache_key)
    if value is None:
        return None
    if not isinstance(value, cabc.Mapping):
        raise ValueError(f"Cache index entry for {cache_key!r} must be an object.")
    return dict(value)


def upsert_cache_index_entry(
    wd: str | Path,
    cache_key: str,
    entry: cabc.Mapping[str, object],
) -> dict[str, object]:
    """Insert or replace one cache index entry and persist deterministically."""

    if not isinstance(cache_key, str) or not cache_key:
        raise ValueError("cache_key must be a non-empty string.")

    normalized_entry = _normalize_entry_mapping(entry)

    payload = load_cache_index(wd)
    entries = payload.get("entries")
    if not isinstance(entries, cabc.Mapping):
        raise ValueError("Cache index payload entries must be an object.")

    merged_entries = {str(key): _normalize_entry_mapping(value) for key, value in entries.items()}
    merged_entries[cache_key] = normalized_entry

    final_payload = {
        "schema_version": CACHE_INDEX_SCHEMA_VERSION,
        "entries": {key: merged_entries[key] for key in sorted(merged_entries)},
    }

    _write_cache_index(wd, final_payload)
    return final_payload


def _default_cache_index_payload() -> dict[str, object]:
    return {
        "schema_version": CACHE_INDEX_SCHEMA_VERSION,
        "entries": {},
    }


def _normalize_entry_mapping(entry: object) -> dict[str, object]:
    if not isinstance(entry, cabc.Mapping):
        raise ValueError("Cache index entry must be an object.")

    normalized = dict(entry)
    if "updated_at_utc" not in normalized:
        normalized["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    decoded = json.loads(serialized)
    if not isinstance(decoded, dict):
        raise ValueError("Cache index entry normalization produced a non-object payload.")
    return decoded


def _write_cache_index(wd: str | Path, payload: cabc.Mapping[str, object]) -> None:
    path = cache_index_path(wd)
    path.parent.mkdir(parents=True, exist_ok=True)

    serialized = json.dumps(dict(payload), indent=2, sort_keys=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(serialized + "\n", encoding="utf-8")
    tmp_path.replace(path)


__all__ = [
    "CACHE_INDEX_RELPATH",
    "CACHE_INDEX_SCHEMA_VERSION",
    "DEFAULT_CONVERSION_VERSION_MARKER",
    "DEFAULT_EXPORT_VERSION_MARKER",
    "CacheKeyParts",
    "build_cache_key",
    "build_request_hash",
    "cache_index_path",
    "get_cache_index_entry",
    "load_cache_index",
    "upsert_cache_index_entry",
]
