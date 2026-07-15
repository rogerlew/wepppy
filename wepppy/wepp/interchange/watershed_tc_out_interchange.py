from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa

from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args
from .schema_utils import pa_field
from .versioning import schema_with_version

TC_OUT_FILENAME = "tc_out.txt"
TC_OUT_PARQUET = "tc_out.parquet"
CHUNK_SIZE = 250_000

LOGGER = logging.getLogger(__name__)

def _audit_log(log_path: Path, message: str) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")
    except OSError:
        LOGGER.warning("Failed to write interchange audit log: %s", log_path, exc_info=True)


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("day", pa.int16(), description="Julian day from tc_out.txt"),
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
            pa_field(
                "julian",
                pa.int16(),
                description="Julian day from tc_out.txt (alias of day)",
            ),
            pa_field(
                "Time of Conc (hr)",
                pa.float64(),
                units="hr",
                description="Event time of concentration at the outlet channel",
            ),
            pa_field(
                "Storm Duration (hr)",
                pa.float64(),
                units="hr",
                description="Storm duration for the event",
            ),
            pa_field(
                "Storm Peak (hr)",
                pa.float64(),
                units="hr",
                description="Time to storm peak for the event",
            ),
        ]
    )
)


def run_wepp_watershed_tc_out_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    delete_after_interchange: bool = False,
) -> Path | None:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    source = base / TC_OUT_FILENAME
    if not source.exists():
        LOGGER.info("tc_out.txt not found in %s; skipping tc_out parquet.", base)
        return None

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / TC_OUT_PARQUET
    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    summary = call_wepppyo3_interchange(
        "watershed TC_OUT",
        "watershed_tc_out_to_parquet",
        str(source),
        str(target),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        chunk_rows=CHUNK_SIZE,
        compression="snappy",
    )
    if not summary["output_paths"]:
        LOGGER.info("tc_out.txt has no channel rows; skipping tc_out parquet.")
        return None

    if delete_after_interchange:
        try:
            source.unlink()
            _audit_log(base / "interchange.log", f"removed {source}")
        except FileNotFoundError:
            LOGGER.debug("tc_out.txt already removed before cleanup: %s", source)
    return target
