"""Strict output-scope contract and path mapping for report resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

OutputScope = Literal["baseline", "roads"]

DEFAULT_OUTPUT_SCOPE: OutputScope = "baseline"
VALID_OUTPUT_SCOPES: tuple[OutputScope, ...] = ("baseline", "roads")

_BASELINE_OUTPUT_PREFIX = "wepp/output"
_ROADS_OUTPUT_PREFIX = "wepp/roads/output"


@dataclass(frozen=True, slots=True)
class OutputScopePaths:
    """Resolved output/interchange roots for a report output scope."""

    output_root: Path
    interchange_root: Path


def normalize_output_scope(value: str | None, *, default: OutputScope = DEFAULT_OUTPUT_SCOPE) -> OutputScope:
    """Validate and normalize the output scope.

    Accepted values are ``baseline`` and ``roads`` (case-insensitive).
    Empty values resolve to ``default``.
    """

    token = default if value is None else str(value).strip().lower()
    if token == "":
        token = default
    if token not in VALID_OUTPUT_SCOPES:
        allowed = "|".join(VALID_OUTPUT_SCOPES)
        raise ValueError(f"Invalid output_scope '{value}'. Expected one of: {allowed}.")
    return cast(OutputScope, token)


def resolve_output_scope_paths(output_scope: str | None = None) -> OutputScopePaths:
    """Return scope-specific output roots under the run directory."""

    normalized = normalize_output_scope(output_scope)
    if normalized == "roads":
        output_root = Path(_ROADS_OUTPUT_PREFIX)
    else:
        output_root = Path(_BASELINE_OUTPUT_PREFIX)
    return OutputScopePaths(
        output_root=output_root,
        interchange_root=output_root / "interchange",
    )


def scoped_dataset_path(path: str | Path, output_scope: str | None = None) -> str:
    """Rewrite baseline output dataset paths for the requested output scope.

    Only paths under ``wepp/output`` are rewritten. Other paths are returned unchanged.
    """

    normalized_scope = normalize_output_scope(output_scope)
    path_text = str(path).replace("\\", "/")

    if normalized_scope == "baseline":
        return path_text

    if path_text == _BASELINE_OUTPUT_PREFIX:
        return _ROADS_OUTPUT_PREFIX
    baseline_prefix = f"{_BASELINE_OUTPUT_PREFIX}/"
    if path_text.startswith(baseline_prefix):
        suffix = path_text[len(baseline_prefix) :]
        return f"{_ROADS_OUTPUT_PREFIX}/{suffix}"
    return path_text


__all__ = [
    "DEFAULT_OUTPUT_SCOPE",
    "OutputScope",
    "OutputScopePaths",
    "VALID_OUTPUT_SCOPES",
    "normalize_output_scope",
    "resolve_output_scope_paths",
    "scoped_dataset_path",
]
