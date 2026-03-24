from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OutputScope = Literal["baseline", "roads"]

DEFAULT_OUTPUT_SCOPE: OutputScope
VALID_OUTPUT_SCOPES: tuple[OutputScope, ...]


@dataclass(frozen=True, slots=True)
class OutputScopePaths:
    output_root: Path
    interchange_root: Path


def normalize_output_scope(value: str | None, *, default: OutputScope = DEFAULT_OUTPUT_SCOPE) -> OutputScope: ...


def resolve_output_scope_paths(output_scope: str | None = ...) -> OutputScopePaths: ...


def scoped_dataset_path(path: str | Path, output_scope: str | None = ...) -> str: ...


__all__ = [
    "DEFAULT_OUTPUT_SCOPE",
    "OutputScope",
    "OutputScopePaths",
    "VALID_OUTPUT_SCOPES",
    "normalize_output_scope",
    "resolve_output_scope_paths",
    "scoped_dataset_path",
]
