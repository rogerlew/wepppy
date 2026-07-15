from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pyarrow as pa

from ._rust_interchange import call_wepppyo3_interchange, version_args
from .schema_utils import pa_field
from .versioning import schema_with_version


LOGGER = logging.getLogger(__name__)

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("ofe_id", pa.int16()),
            pa_field("year", pa.int16()),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("OFE", pa.int16()),
            pa_field("Precip", pa.float64(), units="mm"),
            pa_field("Runoff", pa.float64(), units="mm"),
            pa_field(
                "EffInt",
                pa.float64(),
                units="mm/h",
                description="Effective rainfall intensity",
            ),
            pa_field(
                "PeakRO",
                pa.float64(),
                units="mm/h",
                description="Peak runoff rate",
            ),
            pa_field("EffDur", pa.float64(), units="h"),
            pa_field("Enrich", pa.float64(), description="Sediment enrichment ratio"),
            pa_field(
                "Keff",
                pa.float64(),
                units="mm/h",
                description="Effective hydraulic conductivity",
            ),
            pa_field("Sm", pa.float64(), units="mm"),
            pa_field("LeafArea", pa.float64(), description="Leaf area index"),
            pa_field("CanHgt", pa.float64(), units="m", description="Canopy height"),
            pa_field("Cancov", pa.float64(), units="%", description="Canopy cover"),
            pa_field("IntCov", pa.float64(), units="%", description="Interrill cover"),
            pa_field("RilCov", pa.float64(), units="%", description="Rill cover"),
            pa_field("LivBio", pa.float64(), units="kg/m^2"),
            pa_field("DeadBio", pa.float64(), units="kg/m^2"),
            pa_field(
                "Ki",
                pa.float64(),
                units="kg s/m^4",
                description="Interrill erodibility",
            ),
            pa_field("Kr", pa.float64(), units="s/m", description="Rill erodibility"),
            pa_field("Tcrit", pa.float64()),
            pa_field("RilWid", pa.float64(), units="m"),
            pa_field("SedLeave", pa.float64(), units="kg/m"),
            pa_field("QRain", pa.float64(), units="mm"),
            pa_field("QSnow", pa.float64(), units="mm"),
        ]
    )
)


def run_wepp_hillslope_element_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = None,
    expected_hillslopes: int | None = None,
    max_workers: int | None = None,
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    element_files = sorted(base.glob("H*.element.dat"))
    if expected_hillslopes is not None and len(element_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope element files but found {len(element_files)} in {base}"
        )

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.element.parquet"

    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope ELEMENT",
        "hillslope_element_files_to_parquet",
        [str(path) for path in element_files],
        str(target_path),
        major,
        minor,
        start_year=start_year,
        compression="snappy",
    )
    LOGGER.info("wepp interchange: hillslope ELEMENT direct-to-Parquet via WEPPpyo3")
    return target_path
