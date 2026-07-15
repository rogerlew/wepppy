from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from ._rust_interchange import (
    WeppInterchangeExecutionError,
    call_wepppyo3_interchange,
    resolve_cli_calendar_path,
    version_args,
)
from .schema_utils import pa_field
from .versioning import schema_with_version


SOIL_FILENAME = "soil_pw0.txt"
SOIL_PARQUET = "soil_pw0.parquet"
CHUNK_SIZE = 250_000

LOGGER = logging.getLogger(__name__)

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("ofe_id", pa.int16()),
            pa_field("year", pa.int16()),
            pa_field("day", pa.int16()),
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
            pa_field("Rough", pa.float64(), units="mm", description="Surface roughness"),
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
                description="Saturation as fraction",
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


def _validate_native_schema(actual: pa.Schema) -> None:
    if actual.names != SCHEMA.names:
        raise ValueError(
            f"WEPPpyo3 SOIL schema mismatch: expected {SCHEMA.names} but got {actual.names}"
        )

    for expected_field in SCHEMA:
        actual_field = actual.field(expected_field.name)
        if actual_field.type != expected_field.type:
            raise ValueError(
                "WEPPpyo3 SOIL schema type mismatch for "
                f"{expected_field.name}: expected {expected_field.type} but got {actual_field.type}"
            )


def run_wepp_watershed_soil_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    soil_path = base / SOIL_FILENAME
    if not soil_path.exists():
        gz_path = soil_path.with_suffix(soil_path.suffix + ".gz")
        if gz_path.exists():
            soil_path = gz_path
        else:
            raise FileNotFoundError(base / SOIL_FILENAME)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / SOIL_PARQUET
    staged_fd, staged_name = tempfile.mkstemp(
        dir=interchange_dir,
        prefix=f".{SOIL_PARQUET}.",
        suffix=".stage",
    )
    os.close(staged_fd)
    staged_target = Path(staged_name)

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    try:
        call_wepppyo3_interchange(
            "watershed SOIL",
            "watershed_soil_to_parquet",
            str(soil_path),
            str(staged_target),
            major,
            minor,
            cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
            chunk_rows=CHUNK_SIZE,
        )
        try:
            _validate_native_schema(pq.read_schema(staged_target))
            staged_target.replace(target)
        except Exception as exc:  # broad-except: staged native output validation boundary
            raise WeppInterchangeExecutionError(
                "WEPPpyo3 interchange operation 'watershed SOIL' failed during "
                f"staged schema validation/publication: {exc}"
            ) from exc
    finally:
        staged_target.unlink(missing_ok=True)

    LOGGER.info("wepp interchange: SOIL via WEPPpyo3")
    return target
