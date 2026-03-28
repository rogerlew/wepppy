"""Source and schema discovery helpers for key-first features-export materialization."""

from __future__ import annotations

import collections.abc as cabc
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

try:
    import pyarrow.lib as _pyarrow_lib
    import pyarrow.parquet as _pyarrow_parquet
except ModuleNotFoundError:  # pragma: no cover - runtime image normally includes pyarrow
    _pyarrow_lib = None
    _pyarrow_parquet = None

from wepppy.runtime_paths.materialize import materialize_path_if_archive

from .contracts import ExportWarning, WARNING_LAYER_UNAVAILABLE
from .join_planner import MaterializationContractError

if _pyarrow_lib is not None:
    _PARQUET_SCHEMA_EXCEPTIONS: tuple[type[Exception], ...] = (
        OSError,
        ValueError,
        _pyarrow_lib.ArrowException,
    )
else:  # pragma: no cover - pyarrow missing in non-runtime contexts
    _PARQUET_SCHEMA_EXCEPTIONS = (OSError, ValueError)


@dataclass(frozen=True)
class DiscoveredSourceFrame:
    """One resolved source dataframe with optional discovered unit metadata."""

    source_id: str
    source_kind: str
    required: bool
    dataframe: pd.DataFrame
    units_by_column: dict[str, str]


def _as_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        return {}
    normalized: dict[str, object] = {}
    for key, item in value.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        normalized[key_text] = item
    return normalized


def _as_sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, cabc.Sequence):
        return ()
    return tuple(value)


def _layer_dependency_relpath(
    dependency_entries: cabc.Sequence[object],
    *,
    dependency_role: str,
    dependency_id: str,
) -> str | None:
    for entry in dependency_entries:
        role = str(getattr(entry, "dependency_role", "") or "").strip()
        dep_id = str(getattr(entry, "dependency_id", "") or "").strip()
        relpath = str(getattr(entry, "relpath", "") or "").strip()
        if role == dependency_role and dep_id == dependency_id and relpath:
            return relpath
    return None


def resolve_geometry_relpath(dependency_entries: cabc.Sequence[object]) -> str | None:
    """Resolve canonical geometry relpath for one layer from dependency entries."""

    return _layer_dependency_relpath(
        dependency_entries,
        dependency_role="geometry",
        dependency_id="geometry",
    )


def layer_key_candidates(catalog_layer_raw: cabc.Mapping[str, object]) -> tuple[str, ...]:
    """Collect key candidates from join + geometry contracts for one layer."""

    join_contract = _as_mapping(catalog_layer_raw.get("join"))
    geometry_contract = _as_mapping(catalog_layer_raw.get("geometry"))

    seen: set[str] = set()
    ordered: list[str] = []

    def add_token(token: object) -> None:
        if not isinstance(token, str):
            return
        normalized = token.strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        ordered.append(normalized)

    add_token(join_contract.get("primary_key"))
    for token in _as_sequence(join_contract.get("fallback_keys")):
        add_token(token)
    for token in _as_sequence(geometry_contract.get("feature_id_keys")):
        add_token(token)

    return tuple(ordered)


def discover_layer_sources(
    *,
    wd: Path,
    layer_id: str,
    scope: str,
    catalog_layer_raw: cabc.Mapping[str, object],
    dependency_entries: cabc.Sequence[object],
    skip_vector_relpath: str | None = None,
) -> tuple[tuple[DiscoveredSourceFrame, ...], tuple[ExportWarning, ...]]:
    """Load all resolvable layer sources into dataframes plus warning metadata."""

    source_entries = _as_sequence(catalog_layer_raw.get("sources"))
    warnings: list[ExportWarning] = []
    resolved_sources: list[DiscoveredSourceFrame] = []

    for source_entry in source_entries:
        source_map = _as_mapping(source_entry)
        source_id = str(source_map.get("source_id") or "").strip()
        source_kind = str(source_map.get("kind") or "").strip().lower()
        source_required = bool(source_map.get("required", False))

        if not source_id:
            continue

        source_relpath = _layer_dependency_relpath(
            dependency_entries,
            dependency_role="source",
            dependency_id=source_id,
        )
        if source_relpath is None:
            if source_required:
                raise MaterializationContractError(
                    "Required source dependency is missing for carrier layer materialization.",
                    details=(
                        f"layer={layer_id!r}; source_id={source_id!r}; "
                        "reason=dependency_missing"
                    ),
                )
            continue

        source_path = (wd / source_relpath).resolve()
        if not source_path.exists():
            if source_required:
                raise MaterializationContractError(
                    "Required source file does not exist for carrier layer materialization.",
                    details=(
                        f"layer={layer_id!r}; source_id={source_id!r}; "
                        f"source_relpath={source_relpath!r}; reason=file_missing"
                    ),
                )
            continue

        if (
            source_kind == "vector"
            and isinstance(skip_vector_relpath, str)
            and skip_vector_relpath
            and source_relpath == skip_vector_relpath
        ):
            continue

        if source_kind == "vector":
            dataframe = _load_vector_attributes_dataframe(wd, source_relpath)
            units_by_column: dict[str, str] = {}
        elif source_kind == "parquet":
            dataframe, units_by_column = _load_parquet_dataframe(source_path)
        else:
            if source_required:
                raise MaterializationContractError(
                    "Required source kind is unsupported for carrier layer materialization.",
                    details=(
                        f"layer={layer_id!r}; source_id={source_id!r}; "
                        f"source_kind={source_kind!r}; reason=unsupported_source_kind"
                    ),
                )
            continue

        resolved_sources.append(
            DiscoveredSourceFrame(
                source_id=source_id,
                source_kind=source_kind,
                required=source_required,
                dataframe=dataframe,
                units_by_column=units_by_column,
            )
        )

    return tuple(resolved_sources), tuple(warnings)


def _load_vector_attributes_dataframe(wd: Path, relpath: str) -> pd.DataFrame:
    source_path = materialize_path_if_archive(str(wd), relpath, purpose="export")
    try:
        frame = gpd.read_file(source_path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise MaterializationContractError(
            "Failed to read vector export source.",
            details=f"source={relpath!r}; error={exc}",
        ) from exc

    geometry_name = frame.geometry.name
    if geometry_name not in frame.columns:
        raise MaterializationContractError(
            "Vector export source is missing geometry column.",
            details=f"source={relpath!r}",
        )

    return pd.DataFrame(frame.drop(columns=[geometry_name], errors="ignore"))


def _load_parquet_dataframe(path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    try:
        frame = pd.read_parquet(path)
    except (ImportError, OSError, ValueError) as exc:
        raise MaterializationContractError(
            "Failed to read parquet export source.",
            details=f"path={path.as_posix()!r}; error={exc}",
        ) from exc
    return frame, _parquet_column_units(path)


def _parquet_column_units(path: Path) -> dict[str, str]:
    if _pyarrow_parquet is None:
        return {}

    try:
        schema = _pyarrow_parquet.read_schema(path)
    except _PARQUET_SCHEMA_EXCEPTIONS:
        return {}

    units_by_column: dict[str, str] = {}
    for field in schema:
        column_name = str(field.name).strip()
        if not column_name:
            continue

        metadata = field.metadata if isinstance(field.metadata, dict) else {}
        unit_raw = metadata.get(b"units") if metadata else None
        if isinstance(unit_raw, bytes):
            unit_token = unit_raw.decode("utf-8", errors="ignore").strip()
        elif isinstance(unit_raw, str):
            unit_token = unit_raw.strip()
        else:
            unit_token = ""

        if unit_token:
            units_by_column[column_name] = unit_token
    return units_by_column


__all__ = [
    "DiscoveredSourceFrame",
    "discover_layer_sources",
    "layer_key_candidates",
    "resolve_geometry_relpath",
]
