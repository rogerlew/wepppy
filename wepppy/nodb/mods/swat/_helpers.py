"""Internal shared helpers for SWAT NoDb assembly."""

from __future__ import annotations

import signal
from typing import Any, List, Optional, Tuple

import duckdb


def _read_parquet_columns(con: duckdb.DuckDBPyConnection, parquet_path: str) -> List[str]:
    columns_query = con.execute(
        f"SELECT * FROM read_parquet('{_escape_sql_path(parquet_path)}') LIMIT 0"
    ).description
    return [desc[0] for desc in columns_query]


def _resolve_column(columns: List[str], candidates: Tuple[str, ...], parquet_path: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Missing expected columns {candidates} in {parquet_path}")


def _resolve_column_optional(columns: List[str], candidates: Tuple[str, ...]) -> Optional[str]:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _select_or_null(column: Optional[str], alias: str) -> str:
    if column is None:
        return f"NULL as {alias}"
    return f"{_quote_ident(column)} as {alias}"


def _infer_netw_area_units(area_key: str, fieldnames: List[str]) -> Optional[str]:
    key = area_key.lower()
    if "km2" in key or "sqkm" in key or "sq_km" in key:
        return "km2"
    if "m2" in key or "sqm" in key or "sq_m" in key:
        return "m2"

    if key in ("areaup", "area_up", "area"):
        for name in fieldnames:
            lower = name.lower()
            if lower.endswith("_m") or lower.endswith("_m2") or "length_m" in lower or "drop_m" in lower:
                return "m2"
    return None


def _safe_float(value: Any, default: Optional[float]) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _escape_sql_path(path: str) -> str:
    return path.replace("'", "''")


def _quote_ident(identifier: str) -> str:
    return f"\"{identifier.replace('\"', '\"\"')}\""


def _signal_name(returncode: int) -> Optional[str]:
    if returncode >= 0:
        return None
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return None


def _tail_text(text: Optional[str], max_lines: int = 20, max_chars: int = 2000) -> str:
    if not text:
        return ""
    lines = text.rstrip().splitlines()
    tail = "\n".join(lines[-max_lines:])
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail
