from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa

from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args
from .schema_utils import pa_field
from .versioning import schema_with_version


LOGGER = logging.getLogger(__name__)

PASS_FAMILY_AUTO = "auto"
PASS_FAMILY_LEGACY_ASCII = "legacy_ascii"
PASS_FAMILY_HBP = "hbp"
PASS_FAMILY_CHOICES = {
    PASS_FAMILY_AUTO,
    PASS_FAMILY_LEGACY_ASCII,
    PASS_FAMILY_HBP,
}
INVALID_PROCESS_HBP_SUFFIXES = (".pass.hbp", ".pass.dat.hbp")

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("event", pa.string(), description="Record type: EVENT, SUBEVENT, NO EVENT"),
            pa_field("year", pa.int16()),
            pa_field(
                "sim_day_index",
                pa.int32(),
                description="1-indexed simulation day since start year",
            ),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("dur", pa.float64(), units="s", description="Storm duration"),
            pa_field(
                "tcs",
                pa.float64(),
                units="h",
                description="Overland flow time of concentration",
            ),
            pa_field(
                "oalpha",
                pa.float64(),
                units="unitless",
                description="Overland flow alpha parameter",
            ),
            pa_field("runoff", pa.float64(), units="m", description="Runoff depth"),
            pa_field("runvol", pa.float64(), units="m^3", description="Runoff volume"),
            pa_field(
                "sbrunf",
                pa.float64(),
                units="m",
                description="Subsurface runoff depth",
            ),
            pa_field(
                "sbrunv",
                pa.float64(),
                units="m^3",
                description="Subsurface runoff volume",
            ),
            pa_field("drainq", pa.float64(), units="m/day", description="Drainage flux"),
            pa_field(
                "drrunv",
                pa.float64(),
                units="m^3",
                description="Tile Drainage volume",
            ),
            pa_field("peakro", pa.float64(), units="m^3/s", description="Peak runoff rate"),
            pa_field("tdet", pa.float64(), units="kg", description="Total detachment"),
            pa_field("tdep", pa.float64(), units="kg", description="Total deposition"),
            pa_field(
                "sedcon_1",
                pa.float64(),
                units="kg/m^3",
                description="Sediment concentration 1",
            ),
            pa_field(
                "sedcon_2",
                pa.float64(),
                units="kg/m^3",
                description="Sediment concentration 2",
            ),
            pa_field(
                "sedcon_3",
                pa.float64(),
                units="kg/m^3",
                description="Sediment concentration 3",
            ),
            pa_field(
                "sedcon_4",
                pa.float64(),
                units="kg/m^3",
                description="Sediment concentration 4",
            ),
            pa_field(
                "sedcon_5",
                pa.float64(),
                units="kg/m^3",
                description="Sediment concentration 5",
            ),
            pa_field("clot", pa.float64(), units="m^3/s", description="Friction flow 1"),
            pa_field(
                "slot",
                pa.float64(),
                units="%",
                description="% of exiting sediment in the silt size class",
            ),
            pa_field(
                "saot",
                pa.float64(),
                units="%",
                description="% of exiting sediment in the small aggregate size class",
            ),
            pa_field(
                "laot",
                pa.float64(),
                units="%",
                description="% of exiting sediment in the large aggregate size class",
            ),
            pa_field(
                "sdot",
                pa.float64(),
                units="%",
                description="% of exiting sediment in the sand size class",
            ),
            pa_field("gwbfv", pa.float64(), description="Groundwater baseflow"),
            pa_field("gwdsv", pa.float64(), description="Groundwater deep seepage"),
        ]
    )
)


def run_wepp_hillslope_pass_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = None,
    pass_family: str | None = None,
    max_workers: int | None = None,
) -> Path:
    """Convert ordered hillslope PASS/HBP files through the native writer."""
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    selected_pass_family = _normalize_pass_family(pass_family)
    pass_files, selected_pass_family = _select_pass_files(base, selected_pass_family)
    if expected_hillslopes is not None and len(pass_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope pass files but found {len(pass_files)} in {base}"
        )
    if not pass_files and selected_pass_family == PASS_FAMILY_HBP:
        raise FileNotFoundError(
            f"No hillslope pass files found for pass_family={selected_pass_family} in {base}"
        )

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.pass.parquet"

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope PASS",
        "hillslope_pass_files_to_parquet",
        [str(path) for path in pass_files],
        str(target_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        pass_family=selected_pass_family,
        compression="snappy",
    )
    LOGGER.info(
        "wepp interchange: hillslope PASS direct-to-Parquet via WEPPpyo3 "
        "(pass_family=%s)",
        selected_pass_family,
    )
    return target_path


def _normalize_pass_family(pass_family: str | None) -> str:
    if pass_family is None:
        return PASS_FAMILY_AUTO
    normalized = str(pass_family).strip().lower()
    if not normalized:
        return PASS_FAMILY_AUTO
    if normalized not in PASS_FAMILY_CHOICES:
        options = ", ".join(sorted(PASS_FAMILY_CHOICES))
        raise ValueError(
            f"Unsupported pass_family '{pass_family}'. Expected one of: {options}"
        )
    return normalized


def _collect_invalid_hbp_names(base: Path) -> list[Path]:
    return sorted(
        candidate
        for candidate in base.glob("H*.hbp")
        if candidate.name.lower().endswith(INVALID_PROCESS_HBP_SUFFIXES)
    )


def _select_pass_files(base: Path, pass_family: str) -> tuple[list[Path], str]:
    invalid_hbp_names = _collect_invalid_hbp_names(base)

    if pass_family == PASS_FAMILY_LEGACY_ASCII:
        return sorted(base.glob("H*.pass.dat")), PASS_FAMILY_LEGACY_ASCII

    if pass_family == PASS_FAMILY_HBP:
        if invalid_hbp_names:
            invalid_display = ", ".join(path.name for path in invalid_hbp_names)
            raise ValueError(
                "Invalid process HBP name(s) detected. "
                f"Use H*.hbp and reject H*.pass.hbp / H*.pass.dat.hbp: {invalid_display}"
            )
        return sorted(base.glob("H*.hbp")), PASS_FAMILY_HBP

    legacy_files = sorted(base.glob("H*.pass.dat"))
    hbp_files = sorted(base.glob("H*.hbp"))
    if invalid_hbp_names:
        invalid_display = ", ".join(path.name for path in invalid_hbp_names)
        raise ValueError(
            "Invalid process HBP name(s) detected. "
            f"Use H*.hbp and reject H*.pass.hbp / H*.pass.dat.hbp: {invalid_display}"
        )
    if legacy_files and hbp_files:
        raise ValueError(
            "Ambiguous hillslope pass families in output directory: both H*.pass.dat and H*.hbp "
            "are present. Set pass_family explicitly to 'legacy_ascii' or 'hbp'."
        )
    if hbp_files:
        return hbp_files, PASS_FAMILY_HBP
    return legacy_files, PASS_FAMILY_LEGACY_ASCII
