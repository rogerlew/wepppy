import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .watershed_chanwb_interchange import run_wepp_watershed_chanwb_interchange
from .watershed_chan_peak_interchange import run_wepp_watershed_chan_peak_interchange
from .watershed_chnwb_interchange import run_wepp_watershed_chnwb_interchange
from .watershed_ebe_interchange import run_wepp_watershed_ebe_interchange
from .watershed_loss_interchange import run_wepp_watershed_loss_interchange
from .watershed_pass_interchange import run_wepp_watershed_pass_interchange
from .watershed_soil_interchange import run_wepp_watershed_soil_interchange
from .versioning import remove_incompatible_interchange, write_version_manifest

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except Exception:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

LOGGER = logging.getLogger(__name__)


def run_wepp_watershed_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    run_soil_interchange: bool = True,
    run_chnwb_interchange: bool = True,
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)
    
    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    interchange_dir = base / "interchange"
    remove_incompatible_interchange(interchange_dir)

    start_year_kwargs = {"start_year": start_year} if start_year is not None else {}

    tasks = [
        (run_wepp_watershed_pass_interchange, {}),
        (run_wepp_watershed_ebe_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_chanwb_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_chan_peak_interchange, dict(start_year_kwargs)),
    ]
    if run_chnwb_interchange:
        tasks.append((run_wepp_watershed_chnwb_interchange, dict(start_year_kwargs)))
    if run_soil_interchange:
        tasks.append((run_wepp_watershed_soil_interchange, {}))
    tasks.append((run_wepp_watershed_loss_interchange, {}))

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(func, base, **kwargs): func for func, kwargs in tasks}
        for future in as_completed(futures):
            func = futures[future]
            try:
                future.result()
            except Exception as exc:
                raise RuntimeError(f"Watershed interchange task {func.__name__} failed") from exc

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
