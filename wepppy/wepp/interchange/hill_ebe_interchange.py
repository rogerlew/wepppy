from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa

from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args
from .schema_utils import pa_field
from .versioning import schema_with_version


LOGGER = logging.getLogger(__name__)

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("julian", pa.int16()),
            pa_field("water_year", pa.int16()),
            pa_field(
                "Precip",
                pa.float64(),
                units="mm",
                description="Storm precipitation depth",
            ),
            pa_field(
                "Runoff",
                pa.float64(),
                units="mm",
                description="Runoff depth scaled by effective flow length",
            ),
            pa_field(
                "IR-det",
                pa.float64(),
                units="kg/m^2",
                description="Weighted interrill detachment over the hillslope",
            ),
            pa_field(
                "Av-det",
                pa.float64(),
                units="kg/m^2",
                description="Average soil detachment across detachment regions",
            ),
            pa_field(
                "Mx-det",
                pa.float64(),
                units="kg/m^2",
                description="Maximum soil detachment across detachment regions",
            ),
            pa_field(
                "Det-point",
                pa.float64(),
                units="m",
                description="Location of maximum soil detachment along hillslope",
            ),
            pa_field(
                "Av-dep",
                pa.float64(),
                units="kg/m^2",
                description="Average sediment deposition across deposition regions",
            ),
            pa_field(
                "Max-dep",
                pa.float64(),
                units="kg/m^2",
                description="Maximum sediment deposition across deposition regions",
            ),
            pa_field(
                "Dep-point",
                pa.float64(),
                units="m",
                description="Location of maximum sediment deposition along hillslope",
            ),
            pa_field(
                "Sed.Del",
                pa.float64(),
                units="kg/m",
                description="Storm sediment load per unit width at hillslope outlet",
            ),
            pa_field(
                "ER",
                pa.float64(),
                description="Specific surface enrichment ratio for event sediment",
            ),
            pa_field(
                "Det-Len",
                pa.float64(),
                units="m",
                description="Effective detachment flow length",
            ),
            pa_field(
                "Dep-Len",
                pa.float64(),
                units="m",
                description="Effective deposition flow length",
            ),
        ]
    )
)


def run_wepp_hillslope_ebe_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    expected_hillslopes: int | None = None,
    max_workers: int | None = None,
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        start_year = None

    ebe_files = sorted(base.glob("H*.ebe.dat"))
    if expected_hillslopes is not None and len(ebe_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope ebe files but found {len(ebe_files)} in {base}"
        )

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.ebe.parquet"

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope EBE",
        "hillslope_ebe_files_to_parquet",
        [str(path) for path in ebe_files],
        str(target_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        compression="snappy",
    )
    LOGGER.info("wepp interchange: hillslope EBE direct-to-Parquet via WEPPpyo3")
    return target_path
