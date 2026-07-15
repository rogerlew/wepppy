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

CHANWB_FILENAME = "chnwb.txt"
CHANWB_PARQUET = "chnwb.parquet"

LOGGER = logging.getLogger(__name__)

MEASUREMENT_COLUMNS: List[tuple[str, str | None, str | None]] = [
    ("P (mm)", "mm", "precipitation"),
    ("RM (mm)", "mm", "rainfall + irrigation + snowmelt"),
    ("Q (mm)", "mm", "daily runoff over effective length"),
    ("Ep (mm)", "mm", "plant transpiration"),
    ("Es (mm)", "mm", "soil evaporation"),
    ("Er (mm)", "mm", "residue evaporation"),
    ("Dp (mm)", "mm", "deep percolation"),
    ("UpStrmQ (mm)", "mm", "Runon added to OFE"),
    ("SubRIn (mm)", "mm", "Subsurface runon added to OFE"),
    ("latqcc (mm)", "mm", "lateral subsurface flow"),
    ("Total Soil Water (mm)", "mm", "Unfrozen water in soil profile"),
    ("frozwt (mm)", "mm", "Frozen water in soil profile"),
    ("Snow Water (mm)", "mm", "Water in surface snow"),
    ("QOFE (mm)", "mm", "Daily runoff scaled to single OFE"),
    ("Tile (mm)", "mm", "Tile drainage"),
    ("Irr (mm)", "mm", "Irrigation"),
    ("Surf (mm)", "mm", "Surface storage"),
    ("Base (mm)", "mm", "Portion of runon from external baseflow"),
    ("Area (m^2)", "m^2", "Area that depths apply over"),
]


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32(), description="Channel (OFE) identifier"),
            pa_field("julian", pa.int16(), description="Julian day"),
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("simulation_year", pa.int16(), description="Simulation year value from input file"),
            pa_field("month", pa.int8(), description="Calendar month"),
            pa_field("day_of_month", pa.int8(), description="Calendar day of month"),
            pa_field("water_year", pa.int16(), description="Computed water year"),
            pa_field("OFE", pa.int16(), description="Channel OFE index"),
            pa_field("J", pa.int16(), description="Julian day as reported"),
            pa_field("Y", pa.int16(), description="Simulation year as reported"),
        ]
        + [
            pa_field(name, pa.float64(), units=units, description=description)
            for name, units, description in MEASUREMENT_COLUMNS
        ]
    )
)


def run_wepp_watershed_chnwb_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    source = base / CHANWB_FILENAME
    _wait_for_path(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHANWB_PARQUET

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "watershed CHNWB",
        "watershed_chnwb_to_parquet",
        str(source),
        str(target),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=start_year,
        chunk_rows=250_000,
    )
    LOGGER.info("wepp interchange: CHNWB via WEPPpyo3")
    return target
