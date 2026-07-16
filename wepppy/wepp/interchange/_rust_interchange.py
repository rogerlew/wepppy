from __future__ import annotations

import importlib
import logging
from pathlib import Path

from ._utils import _ensure_cli_parquet
from .versioning import INTERCHANGE_VERSION


REQUIRED_WEPPPYO3_INTERCHANGE_API = frozenset(
    {
        "ag_fields_hillslope_ebe_files_to_parquet",
        "ag_fields_hillslope_element_files_to_parquet",
        "ag_fields_hillslope_loss_files_to_parquet",
        "ag_fields_hillslope_pass_files_to_parquet",
        "ag_fields_hillslope_soil_files_to_parquet",
        "ag_fields_hillslope_wat_files_to_parquet",
        "catalog_scan",
        "hillslope_ebe_files_to_parquet",
        "hillslope_element_files_to_parquet",
        "hillslope_loss_files_to_parquet",
        "hillslope_pass_files_to_parquet",
        "hillslope_soil_files_to_parquet",
        "hillslope_wat_files_to_parquet",
        "watershed_chan_peak_to_parquet",
        "watershed_chanwb_to_parquet",
        "watershed_chnwb_to_parquet",
        "watershed_ebe_to_parquet",
        "watershed_loss_to_parquet",
        "watershed_pass_cli_hint",
        "watershed_pass_to_parquet",
        "watershed_soil_to_parquet",
        "watershed_tc_out_to_parquet",
    }
)


class WeppInterchangeNativeError(RuntimeError):
    """Base error for the required WEPPpyo3 interchange boundary."""


class WeppInterchangeUnavailableError(WeppInterchangeNativeError):
    """Raised when the paired native release is missing or incomplete."""


class WeppInterchangeExecutionError(WeppInterchangeNativeError):
    """Raised when a required native interchange operation fails."""


def _import_wepppyo3_interchange() -> object:
    return importlib.import_module("wepppyo3.wepp_interchange")


def require_wepppyo3_interchange(operation: str, *required_symbols: str) -> object:
    """Load the paired native release and verify an operation's API contract."""

    try:
        module = _import_wepppyo3_interchange()
    except Exception as exc:  # broad-except: required Python/native import boundary
        # This is the deliberate Python/native import boundary. Extension-load
        # failures can surface as ImportError, OSError, or module-init errors.
        raise WeppInterchangeUnavailableError(
            f"WEPP interchange requires wepppyo3 for {operation}; native module import failed"
        ) from exc

    missing = sorted(
        symbol for symbol in required_symbols if not callable(getattr(module, symbol, None))
    )
    if missing:
        cause = AttributeError(f"missing native API: {', '.join(missing)}")
        raise WeppInterchangeUnavailableError(
            f"WEPP interchange requires a current wepppyo3 release for {operation}; "
            f"missing native API: {', '.join(missing)}"
        ) from cause

    return module


def call_wepppyo3_interchange(operation: str, symbol: str, /, *args, **kwargs):
    """Call one required native operation and retain its failure as the cause."""

    module = require_wepppyo3_interchange(operation, symbol)
    native_call = getattr(module, symbol)
    try:
        return native_call(*args, **kwargs)
    except Exception as exc:  # broad-except: required Python/native execution boundary
        # This is the deliberate Python/native execution boundary. PyO3 maps
        # parse, I/O, Arrow, and signature failures to multiple Python classes.
        raise WeppInterchangeExecutionError(
            f"WEPPpyo3 interchange operation {operation!r} failed via {symbol}: {exc}"
        ) from exc


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

    parquet_path = _ensure_cli_parquet(cli_dir, cli_file_hint=cli_hint, log=log)
    if parquet_path is None or not parquet_path.exists():
        return None

    import pyarrow.parquet as pq

    pq.ParquetFile(parquet_path)

    return parquet_path
