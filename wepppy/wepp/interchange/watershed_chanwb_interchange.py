from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from .schema_utils import pa_field
from ._utils import _wait_for_path
from .versioning import schema_with_version
from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args

CHAN_FILENAME = "chanwb.out"
CHAN_PARQUET = "chanwb.parquet"

LOGGER = logging.getLogger(__name__)


MEASUREMENT_COLUMNS: List[tuple[str, str, str]] = [
    ("Inflow (m^3)", "m^3", "Total inflow above channel outlet, includes baseflow, all sources"),
    ("Outflow (m^3)", "m^3", "Water flow out of channel outlet"),
    ("Storage (m^3)", "m^3", "Water surface storage at the end of the day"),
    ("Baseflow (m^3)", "m^3", "Portion of inflow from baseflow"),
    ("Loss (m^3)", "m^3", "Transmission loss in channel, infiltration"),
    ("Balance (m^3)", "m^3", "Water balance error at end of day (inflow - outflow - loss - Δstorage)"),
]


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("simulation_year", pa.int16(), description="Simulation year from chanwb.out"),
            pa_field("julian", pa.int16(), description="Julian day reported by WEPP"),
            pa_field("month", pa.int8(), description="Calendar month derived from Julian day"),
            pa_field("day_of_month", pa.int8(), description="Calendar day-of-month derived from Julian day"),
            pa_field("water_year", pa.int16(), description="Water year computed from Julian day"),
            pa_field("Elmt_ID", pa.int32(), description="Channel element identifier"),
            pa_field("Chan_ID", pa.int32(), description="Channel ID reported by WEPP"),
        ]
        + [pa_field(name, pa.float64(), units=units, description=description) for name, units, description in MEASUREMENT_COLUMNS]
    )
)


def run_wepp_watershed_chanwb_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    source = base / CHAN_FILENAME
    _wait_for_path(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHAN_PARQUET

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "watershed CHANWB",
        "watershed_chanwb_to_parquet",
        str(source),
        str(target),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        chunk_rows=500_000,
    )
    LOGGER.info("wepp interchange: CHANWB via WEPPpyo3")
    return target
