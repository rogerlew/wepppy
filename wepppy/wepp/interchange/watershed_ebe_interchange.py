from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import pyarrow as pa

from ._utils import _wait_for_path
from .schema_utils import pa_field
from .versioning import schema_with_version
from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args

EBE_FILENAME = "ebe_pw0.txt"
EBE_PARQUET = "ebe_pw0.parquet"
CHUNK_SIZE = 250_000
LOGGER = logging.getLogger(__name__)


MEASUREMENT_COLUMNS: List[str] = [
    "precip",
    "runoff_volume",
    "peak_runoff",
    "sediment_yield",
    "soluble_pollutant",
    "particulate_pollutant",
    "total_pollutant",
]


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
            pa_field("simulation_year", pa.int16(), description="WEPP simulation year reported in output"),
            pa_field("month", pa.int8(), description="Calendar month"),
            pa_field("day_of_month", pa.int8(), description="Calendar day of month"),
            pa_field("julian", pa.int16(), description="Julian day from WEPP output"),
            pa_field("water_year", pa.int16(), description="Water year derived from year/julian"),
            pa_field("precip", pa.float64(), units="mm", description="Watershed precipitation depth for the event"),  # sedout.for:3100
            pa_field("runoff_volume", pa.float64(), units="m^3", description="Watershed runoff volume for the event"),  # sedout.for:3100
            pa_field("peak_runoff", pa.float64(), units="m^3/s", description="Peak watershed discharge"),  # sedout.for:3100
            pa_field("sediment_yield", pa.float64(), units="kg", description="Sediment yield at the watershed outlet"),  # sedout.for:3100
            pa_field("soluble_pollutant", pa.float64(), units="kg", description="Soluble pollutant mass delivered at watershed outlet"),
            pa_field("particulate_pollutant", pa.float64(), units="kg", description="Particulate pollutant mass delivered at watershed outlet"),
            pa_field("total_pollutant", pa.float64(), units="kg", description="Total pollutant mass delivered (soluble + particulate)"),
            pa_field("element_id", pa.int32(), description="Channel element identifier (Elmt_ID)"),
        ]
    )
)


def run_wepp_watershed_ebe_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    ebe_path = base / EBE_FILENAME
    _wait_for_path(ebe_path)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / EBE_PARQUET
    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "watershed EBE",
        "watershed_ebe_to_parquet",
        str(ebe_path),
        str(target),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        chan_path=str(base / "chan.out"),
        chunk_rows=CHUNK_SIZE,
    )
    LOGGER.info("wepp interchange: EBE via WEPPpyo3")
    return target
