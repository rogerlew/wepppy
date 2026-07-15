from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa

from ._rust_interchange import call_wepppyo3_interchange, version_args
from .schema_utils import pa_field
from .versioning import schema_with_version


LOGGER = logging.getLogger(__name__)

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("class_id", pa.int8()),
            pa_field("Class", pa.int8(), description="Sediment particle size class"),
            pa_field("Diameter", pa.float64(), units="mm"),
            pa_field("Specific Gravity", pa.float64()),
            pa_field("% Sand", pa.float64(), units="%"),
            pa_field("% Silt", pa.float64(), units="%"),
            pa_field("% Clay", pa.float64(), units="%"),
            pa_field("% O.M.", pa.float64(), units="%"),
            pa_field("Sediment Fraction", pa.float64()),
            pa_field("In Flow Exiting", pa.float64()),
        ]
    )
)


def run_wepp_hillslope_loss_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = None,
    max_workers: int | None = None,
) -> Path:
    """Generate ``H.loss.parquet`` through the required native writer."""
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    loss_files = sorted(base.glob("H*.loss.dat"))
    if expected_hillslopes is not None and len(loss_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope loss files but found {len(loss_files)} in {base}"
        )

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.loss.parquet"

    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope LOSS",
        "hillslope_loss_files_to_parquet",
        [str(path) for path in loss_files],
        str(target_path),
        major,
        minor,
        compression="snappy",
    )
    LOGGER.info("wepp interchange: hillslope LOSS direct-to-Parquet via WEPPpyo3")
    return target_path
