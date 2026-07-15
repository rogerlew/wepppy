import logging
from datetime import datetime, timezone
from pathlib import Path

from .hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
from .hill_element_interchange import run_wepp_hillslope_element_interchange
from .hill_loss_interchange import run_wepp_hillslope_loss_interchange
from .hill_pass_interchange import run_wepp_hillslope_pass_interchange
from .hill_soil_interchange import run_wepp_hillslope_soil_interchange
from .hill_wat_interchange import run_wepp_hillslope_wat_interchange
from .versioning import remove_incompatible_interchange, write_version_manifest

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except Exception:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

LOGGER = logging.getLogger(__name__)
PASS_FAMILY_HBP = "hbp"

__all__ = [
    "cleanup_hillslope_sources_for_completed_interchange",
    "run_wepp_hillslope_interchange",
]

_CORE_HILLSLOPE_INTERCHANGE_TARGETS = (
    ("pass", "H*.pass.dat", "H.pass.parquet"),
    ("ebe", "H*.ebe.dat", "H.ebe.parquet"),
    ("element", "H*.element.dat", "H.element.parquet"),
)
_OPTIONAL_HILLSLOPE_INTERCHANGE_TARGETS = (
    ("loss", "H*.loss.dat", "H.loss.parquet"),
    ("soil", "H*.soil.dat", "H.soil.parquet"),
    ("wat", "H*.wat.dat", "H.wat.parquet"),
)


def _audit_log(log_path: Path, message: str) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")
    except Exception:
        LOGGER.warning("Failed to write interchange audit log: %s", log_path, exc_info=True)


def _unlink_sources(paths, *, log_path: Path) -> None:
    for path in paths:
        try:
            path.unlink()
            _audit_log(log_path, f"removed {path}")
        except FileNotFoundError:
            continue
        except Exception:
            LOGGER.warning("Failed to remove interchange source %s", path, exc_info=True)


def _cleanup_hillslope_sources(
    base: Path,
    *,
    pass_family: str | None = None,
    run_loss_interchange: bool,
    run_soil_interchange: bool,
    run_wat_interchange: bool,
) -> None:
    log_path = base / "interchange.log"
    _audit_log(log_path, "delete_after_interchange enabled for hillslope outputs")
    normalized_pass_family = _normalize_pass_family(pass_family)
    pass_pattern = "H*.hbp" if normalized_pass_family == PASS_FAMILY_HBP else "H*.pass.dat"
    patterns = [pass_pattern, "H*.ebe.dat", "H*.element.dat"]
    if run_loss_interchange:
        patterns.append("H*.loss.dat")
    if run_soil_interchange:
        patterns.append("H*.soil.dat")
    if run_wat_interchange:
        patterns.append("H*.wat.dat")

    for pattern in patterns:
        _unlink_sources(base.glob(pattern), log_path=log_path)


def cleanup_hillslope_sources_for_completed_interchange(
    wepp_output_dir: Path | str,
    *,
    pass_family: str | None = None,
    run_loss_interchange: bool = True,
    run_soil_interchange: bool = True,
    run_wat_interchange: bool = True,
) -> list[str]:
    """Delete raw hillslope outputs only when their interchange parquet exists.

    This supports deferred cleanup paths where interchange finished earlier but
    watershed routing still needed the raw H*.dat files. Each output family is
    checked independently so missing parquet files preserve their raw sources.
    """
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    log_path = base / "interchange.log"
    interchange_dir = base / "interchange"
    normalized_pass_family = _normalize_pass_family(pass_family)
    pass_pattern = "H*.hbp" if normalized_pass_family == PASS_FAMILY_HBP else "H*.pass.dat"
    enabled_targets = list(_CORE_HILLSLOPE_INTERCHANGE_TARGETS)
    enabled_targets[0] = ("pass", pass_pattern, "H.pass.parquet")
    if run_loss_interchange:
        enabled_targets.append(_OPTIONAL_HILLSLOPE_INTERCHANGE_TARGETS[0])
    if run_soil_interchange:
        enabled_targets.append(_OPTIONAL_HILLSLOPE_INTERCHANGE_TARGETS[1])
    if run_wat_interchange:
        enabled_targets.append(_OPTIONAL_HILLSLOPE_INTERCHANGE_TARGETS[2])

    cleaned_groups: list[str] = []
    for name, pattern, target_name in enabled_targets:
        target_path = interchange_dir / target_name
        if not target_path.exists():
            _audit_log(
                log_path,
                f"retained {pattern}; missing completed interchange target {target_path}",
            )
            continue
        _audit_log(
            log_path,
            f"deferred cleanup removing {pattern} after successful watershed using {target_path.name}",
        )
        _unlink_sources(base.glob(pattern), log_path=log_path)
        cleaned_groups.append(name)

    return cleaned_groups


def run_wepp_hillslope_interchange(
    wepp_output_dir: Path | str,
    *,
    pass_family: str | None = None,
    start_year: int | None = None,
    run_loss_interchange: bool = True,
    run_soil_interchange: bool = True,
    run_wat_interchange: bool = True,
    delete_after_interchange: bool = False,
    max_workers: int | None = None,
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
        delete_after_interchange: When True, remove source WEPP text outputs
            after successful conversion.
        max_workers: Optional process-pool bound forwarded to every hillslope
            converter. Omitted values preserve the existing interchange default.

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
        "pass": run_wepp_hillslope_pass_interchange(
            base,
            expected_hillslopes=expected_hillslopes,
            pass_family=pass_family,
            max_workers=max_workers,
        ),
        "ebe": run_wepp_hillslope_ebe_interchange(
            base,
            start_year=start_year,
            expected_hillslopes=expected_hillslopes,
            max_workers=max_workers,
        ),
        "element": run_wepp_hillslope_element_interchange(
            base,
            start_year=start_year,
            expected_hillslopes=expected_hillslopes,
            max_workers=max_workers,
        ),
    }

    # Optional outputs that may not exist for single storm runs
    if run_loss_interchange:
        results["loss"] = run_wepp_hillslope_loss_interchange(
            base,
            expected_hillslopes=expected_hillslopes,
            max_workers=max_workers,
        )
    if run_soil_interchange:
        results["soil"] = run_wepp_hillslope_soil_interchange(
            base,
            start_year=start_year,
            expected_hillslopes=expected_hillslopes,
            max_workers=max_workers,
        )
    if run_wat_interchange:
        results["wat"] = run_wepp_hillslope_wat_interchange(
            base,
            expected_hillslopes=expected_hillslopes,
            max_workers=max_workers,
        )

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

    if delete_after_interchange:
        _cleanup_hillslope_sources(
            base,
            pass_family=pass_family,
            run_loss_interchange=run_loss_interchange,
            run_soil_interchange=run_soil_interchange,
            run_wat_interchange=run_wat_interchange,
        )

    return interchange_dir


def _expected_hillslopes(output_dir: Path) -> int | None:
    """Return watershed.sub_n if available to validate hill file counts."""
    try:
        wd = output_dir.parents[1]
    except IndexError:
        return None

    # Import lazily to avoid module-load circular imports with
    # wepppy.nodb.wepp_nodb_post_utils -> wepppy.wepp.interchange.
    from wepppy.nodb.core.watershed import Watershed

    try:
        watershed = Watershed.getInstance(str(wd))
    except Exception:
        return None
    try:
        return int(watershed.sub_n)
    except Exception:
        return None


def _normalize_pass_family(pass_family: str | None) -> str:
    normalized = (pass_family or "legacy_ascii").strip().lower()
    if normalized == PASS_FAMILY_HBP:
        return PASS_FAMILY_HBP
    if normalized == "legacy_ascii":
        return "legacy_ascii"
    raise ValueError("pass_family must be 'legacy_ascii' or 'hbp'")
