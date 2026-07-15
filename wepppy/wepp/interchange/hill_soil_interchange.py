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
            pa_field("ofe_id", pa.int16()),
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("OFE", pa.int16()),
            pa_field("Poros", pa.float64(), units="%", description="Soil porosity"),
            pa_field(
                "Keff",
                pa.float64(),
                units="mm/hr",
                description="Effective hydraulic conductivity",
            ),
            pa_field(
                "Suct",
                pa.float64(),
                units="mm",
                description="Suction across wetting front",
            ),
            pa_field("FC", pa.float64(), units="mm/mm", description="Field capacity"),
            pa_field("WP", pa.float64(), units="mm/mm", description="Wilting point"),
            pa_field(
                "Rough",
                pa.float64(),
                units="mm",
                description="Surface roughness",
            ),
            pa_field(
                "Ki",
                pa.float64(),
                units="adjsmt",
                description="Interrill erodibility adjustment factor",
            ),
            pa_field(
                "Kr",
                pa.float64(),
                units="adjsmt",
                description="Rill erodibility adjustment factor",
            ),
            pa_field(
                "Tauc",
                pa.float64(),
                units="adjsmt",
                description="Critical shear stress adjustment factor",
            ),
            pa_field(
                "Saturation",
                pa.float64(),
                units="frac",
                description="Saturation as fraction (10mm profile)",
            ),
            pa_field("TSW", pa.float64(), units="mm", description="Total soil water"),
            pa_field(
                "TSMF",
                pa.float64(),
                units="frac",
                description="True soil moisture fraction (full profile)",
            ),
        ]
    )
)


def run_wepp_hillslope_soil_interchange(
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

    soil_files = sorted(base.glob("H*.soil.dat"))
    if expected_hillslopes is not None and len(soil_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope soil files but found {len(soil_files)} in {base}"
        )

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.soil.parquet"

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope SOIL",
        "hillslope_soil_files_to_parquet",
        [str(path) for path in soil_files],
        str(target_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        compression="snappy",
    )
    LOGGER.info("wepp interchange: hillslope SOIL direct-to-Parquet via WEPPpyo3")
    return target_path
