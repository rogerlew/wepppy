"""Join planning and cardinality guardrails for key-first carrier materialization."""

from __future__ import annotations

import collections.abc as cabc
import string

import pandas as pd

JOIN_KEY_COLUMN = "__features_export_join_key__"

_CARRIER_KEY_PREFERENCE: dict[str, tuple[str, ...]] = {
    "sbs_map-subcatchments": ("topaz_id", "wepp_id", "TopazID"),
    "chan_map-channels": ("chn_id", "channel_id", "TopazID", "topaz_id"),
}

_GENERIC_KEY_FALLBACK: tuple[str, ...] = (
    "topaz_id",
    "TopazID",
    "wepp_id",
    "chn_id",
    "channel_id",
    "id",
)


class MaterializationContractError(RuntimeError):
    """Raised when key-first materialization contracts are violated."""

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.details = details or message


def normalize_join_token(value: str) -> str:
    """Normalize one join token for robust case/punctuation-insensitive matching."""

    return "".join(ch for ch in value.lower() if ch in string.ascii_lowercase + string.digits)


def canonical_join_value(value: object) -> str | None:
    """Canonicalize one candidate key value into a stable join token."""

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")

    text = str(value).strip()
    if not text:
        return None

    try:
        float_value = float(text)
    except ValueError:
        return text

    if float_value.is_integer():
        return str(int(float_value))
    return format(float_value, ".15g")


def normalized_column_lookup(columns: cabc.Iterable[object]) -> dict[str, str]:
    """Build normalized->original column lookup for one dataframe."""

    lookup: dict[str, str] = {}
    for column in columns:
        token = str(column).strip()
        if not token:
            continue
        normalized = normalize_join_token(token)
        if not normalized or normalized in lookup:
            continue
        lookup[normalized] = token
    return lookup


def dedupe_column_name(candidate: str, used_names: set[object]) -> str:
    """Return one non-colliding column name with deterministic suffixing."""

    base = candidate
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _as_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        return {}
    normalized: dict[str, object] = {}
    for key, item in value.items():
        key_token = str(key).strip()
        if not key_token:
            continue
        normalized[key_token] = item
    return normalized


def _as_string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        token = value.strip()
        return (token,) if token else ()
    if not isinstance(value, cabc.Sequence):
        return ()
    normalized: list[str] = []
    for entry in value:
        token = str(entry).strip() if isinstance(entry, str) else ""
        if token:
            normalized.append(token)
    return tuple(normalized)


def carrier_key_candidates(
    *,
    carrier_layer: str | None,
    join_contract: cabc.Mapping[str, object] | None,
    source_id: str | None = None,
) -> tuple[str, ...]:
    """Return ordered key candidates honoring source map + carrier precedence."""

    join_map = _as_mapping(join_contract)
    source_key_map = _as_mapping(join_map.get("source_key_map"))

    seen: set[str] = set()
    ordered: list[str] = []

    def add_token(token: str) -> None:
        normalized = normalize_join_token(token)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        ordered.append(token)

    if source_id is not None:
        source_preferred = _as_string_sequence(source_key_map.get(source_id))
        for token in source_preferred:
            add_token(token)

    for token in _CARRIER_KEY_PREFERENCE.get(str(carrier_layer or ""), ()):  # carrier-first
        add_token(token)

    primary_key = join_map.get("primary_key")
    if isinstance(primary_key, str) and primary_key.strip():
        add_token(primary_key.strip())

    for token in _as_string_sequence(join_map.get("fallback_keys")):
        add_token(token)

    for token in _GENERIC_KEY_FALLBACK:
        add_token(token)

    return tuple(ordered)


def resolve_source_key(
    *,
    source_columns: cabc.Iterable[object],
    join_contract: cabc.Mapping[str, object] | None,
    source_id: str,
    carrier_layer: str | None,
) -> str | None:
    """Resolve one source dataframe join key column from contract candidates."""

    lookup = normalized_column_lookup(source_columns)
    for candidate in carrier_key_candidates(
        carrier_layer=carrier_layer,
        join_contract=join_contract,
        source_id=source_id,
    ):
        normalized = normalize_join_token(candidate)
        if normalized in lookup:
            return lookup[normalized]
    return None


def resolve_geometry_key(
    *,
    geometry_columns: cabc.Iterable[object],
    carrier_layer: str | None,
    candidate_tokens: cabc.Sequence[str],
) -> str | None:
    """Resolve one geometry key from carrier defaults plus layer-derived candidates."""

    lookup = normalized_column_lookup(geometry_columns)
    seen: set[str] = set()

    ordered_candidates: list[str] = []
    for token in (*_CARRIER_KEY_PREFERENCE.get(str(carrier_layer or ""), ()), *candidate_tokens, *_GENERIC_KEY_FALLBACK):
        normalized = normalize_join_token(str(token))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_candidates.append(str(token))

    for candidate in ordered_candidates:
        normalized = normalize_join_token(candidate)
        if normalized in lookup:
            return lookup[normalized]
    return None


def with_canonical_join_key(
    frame: pd.DataFrame,
    *,
    source_key: str,
) -> pd.DataFrame:
    """Return a copy with canonical join-key column appended."""

    if source_key not in frame.columns:
        raise MaterializationContractError(
            "Resolved join key is not present in dataframe.",
            details=f"join_key={source_key!r}",
        )

    result = frame.copy()
    result[JOIN_KEY_COLUMN] = result[source_key].map(canonical_join_value)
    return result


def ensure_unique_keys(
    frame: pd.DataFrame,
    *,
    context_label: str,
) -> pd.DataFrame:
    """Collapse benign duplicates and fail explicit many-to-many key conflicts."""

    if JOIN_KEY_COLUMN not in frame.columns:
        raise MaterializationContractError(
            "Materialized table is missing canonical join key.",
            details=f"context={context_label}",
        )

    working = frame.copy()
    working = working.loc[working[JOIN_KEY_COLUMN].notna()].reset_index(drop=True)
    if working.empty:
        raise MaterializationContractError(
            "Materialized table has no usable join keys.",
            details=f"context={context_label}",
        )

    duplicate_mask = working.duplicated(subset=[JOIN_KEY_COLUMN], keep=False)
    if not duplicate_mask.any():
        return working

    duplicate_rows = working.loc[duplicate_mask]
    non_key_columns = [column for column in working.columns if column != JOIN_KEY_COLUMN]
    conflicting_keys: list[str] = []

    for key_value, group in duplicate_rows.groupby(JOIN_KEY_COLUMN, dropna=False, sort=False):
        if group.empty:
            continue
        for column_name in non_key_columns:
            if group[column_name].nunique(dropna=False) > 1:
                conflicting_keys.append(str(key_value))
                break

    if conflicting_keys:
        preview = ", ".join(sorted(set(conflicting_keys))[:8])
        raise MaterializationContractError(
            "Unresolved many-to-many key cardinality detected during materialization.",
            details=(
                f"context={context_label}; conflicting_keys={preview}; "
                "explicit pre-aggregation or selector narrowing is required"
            ),
        )

    # Benign duplicates (same attribute payload) are collapsed deterministically.
    return working.drop_duplicates(subset=[JOIN_KEY_COLUMN], keep="first").reset_index(drop=True)


__all__ = [
    "JOIN_KEY_COLUMN",
    "MaterializationContractError",
    "canonical_join_value",
    "carrier_key_candidates",
    "dedupe_column_name",
    "ensure_unique_keys",
    "normalize_join_token",
    "normalized_column_lookup",
    "resolve_geometry_key",
    "resolve_source_key",
    "with_canonical_join_key",
]
