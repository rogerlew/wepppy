import logging
from datetime import datetime, timezone
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wepppy.all_your_base import NCPU

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

def _audit_log(log_path: Path, message: str) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")
    except Exception:
        LOGGER.warning("Failed to write interchange audit log: %s", log_path, exc_info=True)

def _unlink_source(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        LOGGER.warning("Failed to remove interchange source %s", path, exc_info=True)
        return False


def _unlink_source_with_gzip(path: Path) -> None:
    _unlink_source(path)
    suffix = path.suffix
    if suffix:
        gz_path = path.with_suffix(f"{suffix}.gz")
    else:
        gz_path = Path(f"{path}.gz")
    _unlink_source(gz_path)


def run_wepp_watershed_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: int | None = None,
    run_ebe_interchange: bool = True,
    run_chan_out_interchange: bool = True,
    run_soil_interchange: bool = True,
    run_chnwb_interchange: bool = True,
    delete_after_interchange: bool = False,
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
    ]
    if run_ebe_interchange:
        tasks.append((run_wepp_watershed_ebe_interchange, dict(start_year_kwargs)))
    if run_chan_out_interchange:
        tasks.append((run_wepp_watershed_chanwb_interchange, dict(start_year_kwargs)))
        tasks.append((run_wepp_watershed_chan_peak_interchange, dict(start_year_kwargs)))
    # tc_out is handled by post-run cleanup after the file is moved into output.
    if run_chnwb_interchange:
        tasks.append((run_wepp_watershed_chnwb_interchange, dict(start_year_kwargs)))
    if run_soil_interchange:
        tasks.append((run_wepp_watershed_soil_interchange, {}))
    tasks.append((run_wepp_watershed_loss_interchange, {}))

    max_workers = len(tasks)
    if os.getenv("WEPPPY_NCPU"):
        max_workers = min(max_workers, NCPU)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
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

    if delete_after_interchange:
        log_path = base / "interchange.log"
        _audit_log(log_path, "delete_after_interchange enabled for watershed outputs")
        for path in (
            base / "pass_pw0.txt",
            base / "ebe_pw0.txt",
            base / "loss_pw0.txt",
        ):
            if path.exists():
                if _unlink_source(path):
                    _audit_log(log_path, f"removed {path}")
            gz_path = path.with_suffix(f"{path.suffix}.gz")
            if gz_path.exists():
                if _unlink_source(gz_path):
                    _audit_log(log_path, f"removed {gz_path}")

        for path in (base / "chanwb.out", base / "chan.out"):
            if path.exists():
                if _unlink_source(path):
                    _audit_log(log_path, f"removed {path}")
        if run_chnwb_interchange:
            chn_path = base / "chnwb.txt"
            if chn_path.exists():
                if _unlink_source(chn_path):
                    _audit_log(log_path, f"removed {chn_path}")
        if run_soil_interchange:
            soil_path = base / "soil_pw0.txt"
            if soil_path.exists():
                if _unlink_source(soil_path):
                    _audit_log(log_path, f"removed {soil_path}")
            soil_gz_path = soil_path.with_suffix(f"{soil_path.suffix}.gz")
            if soil_gz_path.exists():
                if _unlink_source(soil_gz_path):
                    _audit_log(log_path, f"removed {soil_gz_path}")

    return interchange_dir
