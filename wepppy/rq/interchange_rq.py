from __future__ import annotations

import inspect
from os.path import join as _join
from pathlib import Path
from typing import Iterable, Optional

from rq import get_current_job

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.nodb.core import Climate, Wepp

from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
    run_totalwatsed3,
    generate_interchange_documentation,
)

TIMEOUT = 43_200  # 12 hours, matches long-running WEPP tasks

_REQUIRED_WATERSHED_OUTPUTS: tuple[str, ...] = (
    "pass_pw0.txt",
    "chan.out",
    "chanwb.out",
    "chnwb.txt",
    "ebe_pw0.txt",
    "soil_pw0.txt",
    "loss_pw0.txt",
)


def _with_gzip(path: Path) -> Path:
    if path.suffix:
        return path.with_suffix(path.suffix + ".gz")
    return Path(f"{path}.gz")


def _missing_wepp_outputs(base: Path, filenames: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for name in filenames:
        candidate = base / name
        if candidate.exists():
            continue
        gz_candidate = _with_gzip(candidate)
        if gz_candidate.exists():
            continue
        missing.append(name)
    return missing


def run_interchange_migration(runid: str, wepp_output_subpath: Optional[str] = None) -> bool:
    """Execute the full interchange migration workflow for a run.

    Parameters
    ----------
    runid : str
        Unique identifier for the project run.
    wepp_output_subpath : Optional[str]
        Optional subdirectory under ``wepp/`` whose ``output`` folder should
        be migrated (e.g., ``ag_field``). When omitted, defaults to
        ``wepp/output``.

    Returns
    -------
    bool
        ``True`` when the migration ran, ``False`` when skipped because the
        required WEPP outputs were not present.
    """

    job = get_current_job()
    job_id = getattr(job, "id", "sync")
    func_name = inspect.currentframe().f_code.co_name

    status_channel = f"{runid}:command"
    StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({runid}, wepp_output_subpath={wepp_output_subpath})")

    try:
        wd = get_wd(runid)
        if wepp_output_subpath:
            wepp_output_dir = Path(_join(wd, "wepp", wepp_output_subpath, "output"))
        else:
            wepp_output_dir = Path(_join(wd, "wepp", "output"))

        if not wepp_output_dir.exists():
            StatusMessenger.publish(
                status_channel,
                f"rq:{job_id} SKIPPED {func_name}({runid}) -> missing output directory: {wepp_output_dir}",
            )
            return False

        missing = _missing_wepp_outputs(wepp_output_dir, _REQUIRED_WATERSHED_OUTPUTS)

        if not wepp_output_subpath and missing:
            StatusMessenger.publish(
                status_channel,
                f"rq:{job_id} SKIPPED {func_name}({runid}) -> missing WEPP outputs: {', '.join(missing)}",
            )
            return False

        start_year: Optional[int] = None
        climate = Climate.getInstance(wd)
        if getattr(climate, "observed_start_year", None) is not None:
            start_year = climate.observed_start_year

        interchange_dir = run_wepp_hillslope_interchange(wepp_output_dir, start_year=start_year)

        if not missing:
            run_wepp_watershed_interchange(wepp_output_dir, start_year=start_year)

        wepp = Wepp.getInstance(wd)
        run_totalwatsed3(interchange_dir, baseflow_opts=wepp.baseflow_opts)
        generate_interchange_documentation(interchange_dir)

        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} COMPLETED {func_name}({runid}, wepp_output_subpath={wepp_output_subpath}) -> {interchange_dir}",
        )
        return True
    except Exception:
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({runid}, wepp_output_subpath={wepp_output_subpath})",
        )
        raise
