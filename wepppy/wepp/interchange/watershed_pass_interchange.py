from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args


PASS_FILENAME = "pass_pw0.txt"
EVENTS_PARQUET = "pass_pw0.events.parquet"
METADATA_PARQUET = "pass_pw0.metadata.parquet"
EVENT_CHUNK_SIZE = 250_000

LOGGER = logging.getLogger(__name__)


def run_wepp_watershed_pass_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    pass_path = base / PASS_FILENAME
    if not pass_path.exists():
        gz_path = pass_path.with_suffix(pass_path.suffix + ".gz")
        if gz_path.exists():
            pass_path = gz_path
        else:
            raise FileNotFoundError(base / PASS_FILENAME)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    events_path = interchange_dir / EVENTS_PARQUET
    metadata_path = interchange_dir / METADATA_PARQUET

    cli_hint = call_wepppyo3_interchange(
        "watershed PASS climate selection",
        "watershed_pass_cli_hint",
        str(pass_path),
    )
    cli_calendar_path = resolve_cli_calendar_path(base, cli_hint=cli_hint, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "watershed PASS",
        "watershed_pass_to_parquet",
        str(pass_path),
        str(events_path),
        str(metadata_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        chunk_rows=EVENT_CHUNK_SIZE,
    )
    LOGGER.info("wepp interchange: PASS via WEPPpyo3")
    return {"events": events_path, "metadata": metadata_path}
