"""Convert WEPP watershed LOSS output through the required native writer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from ._rust_interchange import call_wepppyo3_interchange, version_args


LOGGER = logging.getLogger(__name__)

LOSS_FILENAME = "loss_pw0.txt"

AVERAGE_FILENAMES = {
    "hill": "loss_pw0.hill.parquet",
    "chn": "loss_pw0.chn.parquet",
    "out": "loss_pw0.out.parquet",
    "class_data": "loss_pw0.class_data.parquet",
}

ALL_YEARS_FILENAMES = {
    "hill": "loss_pw0.all_years.hill.parquet",
    "chn": "loss_pw0.all_years.chn.parquet",
    "out": "loss_pw0.all_years.out.parquet",
    "class_data": "loss_pw0.all_years.class_data.parquet",
}


def run_wepp_watershed_loss_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]:
    """Generate all watershed LOSS Parquet products through WEPPpyo3."""
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / LOSS_FILENAME
    if not source.exists():
        raise FileNotFoundError(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    mapping = {
        "average_hill": interchange_dir / AVERAGE_FILENAMES["hill"],
        "average_chn": interchange_dir / AVERAGE_FILENAMES["chn"],
        "average_out": interchange_dir / AVERAGE_FILENAMES["out"],
        "average_class": interchange_dir / AVERAGE_FILENAMES["class_data"],
        "all_years_hill": interchange_dir / ALL_YEARS_FILENAMES["hill"],
        "all_years_chn": interchange_dir / ALL_YEARS_FILENAMES["chn"],
        "all_years_out": interchange_dir / ALL_YEARS_FILENAMES["out"],
        "all_years_class": interchange_dir / ALL_YEARS_FILENAMES["class_data"],
    }

    major, minor = version_args()
    call_wepppyo3_interchange(
        "watershed LOSS",
        "watershed_loss_to_parquet",
        str(source),
        str(interchange_dir),
        major,
        minor,
    )
    LOGGER.info("wepp interchange: LOSS via WEPPpyo3")
    return mapping
