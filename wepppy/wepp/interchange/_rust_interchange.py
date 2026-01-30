from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Optional, Tuple

from ._utils import _ensure_cli_parquet
from .versioning import INTERCHANGE_VERSION


def load_rust_interchange() -> tuple[object | None, Exception | None]:
    try:
        return importlib.import_module("wepppyo3.wepp_interchange"), None
    except Exception as exc:
        try:
            return importlib.import_module("wepppyo3.wepp_interchange.wepp_interchange_rust"), None
        except Exception:
            return None, exc


def version_args() -> tuple[int, int]:
    return INTERCHANGE_VERSION.major, INTERCHANGE_VERSION.minor


def resolve_cli_calendar_path(
    wepp_output_dir: Path,
    *,
    cli_hint: str | None = None,
    log: logging.Logger | None = None,
) -> Path | None:
    base = Path(wepp_output_dir)
    cli_dir: Path | None = None
    for candidate in (base, *base.parents):
        maybe_cli = candidate / "climate"
        if maybe_cli.exists():
            cli_dir = maybe_cli
            break

    if cli_dir is None:
        return None

    return _ensure_cli_parquet(cli_dir, cli_file_hint=cli_hint, log=log)
