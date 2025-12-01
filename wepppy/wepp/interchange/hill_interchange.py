import logging
from pathlib import Path

from .hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
from .hill_element_interchange import run_wepp_hillslope_element_interchange
from .hill_loss_interchange import run_wepp_hillslope_loss_interchange
from .hill_pass_interchange import run_wepp_hillslope_pass_interchange
from .hill_soil_interchange import run_wepp_hillslope_soil_interchange
from .hill_wat_interchange import run_wepp_hillslope_wat_interchange
from .versioning import remove_incompatible_interchange, write_version_manifest
from wepppy.nodb.core.watershed import Watershed

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except Exception:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

LOGGER = logging.getLogger(__name__)


def run_wepp_hillslope_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    run_loss_interchange: bool = True,
    run_soil_interchange: bool = True,
    run_wat_interchange: bool = True,
) -> Path:
    """Generate hillslope interchange parquet files.

    Args:
        wepp_output_dir: Path to WEPP output directory containing hillslope data files.
        start_year: Optional start year for time-series outputs.
        run_loss_interchange: When False, skip hillslope loss interchange.
            Single storm runs don't produce .loss.dat files.
        run_soil_interchange: When False, skip hillslope soil interchange.
            Single storm runs don't produce .soil.dat files.
        run_wat_interchange: When False, skip hillslope water balance interchange.
            Single storm runs don't produce .wat.dat files.

    Returns:
        Path to the interchange directory.

    Raises:
        FileNotFoundError: If required output files are missing.
    """
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    interchange_dir = base / "interchange"
    remove_incompatible_interchange(interchange_dir)

    expected_hillslopes = _expected_hillslopes(base)

    # Core outputs that exist for all run types
    results = {
        "pass": run_wepp_hillslope_pass_interchange(base, expected_hillslopes=expected_hillslopes),
        "ebe": run_wepp_hillslope_ebe_interchange(base, start_year=start_year, expected_hillslopes=expected_hillslopes),
        "element": run_wepp_hillslope_element_interchange(base, start_year=start_year, expected_hillslopes=expected_hillslopes),
    }

    # Optional outputs that may not exist for single storm runs
    if run_loss_interchange:
        results["loss"] = run_wepp_hillslope_loss_interchange(base, expected_hillslopes=expected_hillslopes)
    if run_soil_interchange:
        results["soil"] = run_wepp_hillslope_soil_interchange(base, expected_hillslopes=expected_hillslopes)
    if run_wat_interchange:
        results["wat"] = run_wepp_hillslope_wat_interchange(base, expected_hillslopes=expected_hillslopes)

    missing = [name for name, path in results.items() if path is None or not Path(path).exists()]
    if missing:
        missing_paths = {name: str(results.get(name)) for name in missing}
        raise FileNotFoundError(f"Hillslope interchange outputs missing: {missing_paths}")

    write_version_manifest(interchange_dir)

    if _update_catalog_entry is not None:
        try:
            run_root = base.parents[1]
        except IndexError:
            run_root = base
        try:
            _update_catalog_entry(run_root, str(interchange_dir))
        except Exception:  # pragma: no cover - best effort catalog sync
            LOGGER.warning("Failed to refresh query engine catalog for %s", run_root, exc_info=True)

    return interchange_dir


def _expected_hillslopes(output_dir: Path) -> int | None:
    """Return watershed.sub_n if available to validate hill file counts."""
    try:
        wd = output_dir.parents[1]
    except IndexError:
        return None
    try:
        watershed = Watershed.getInstance(str(wd))
    except Exception:
        return None
    try:
        return int(watershed.sub_n)
    except Exception:
        return None
