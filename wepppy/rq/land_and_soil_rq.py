"""Ad-hoc RQ task that builds landuse/soils extracts for arbitrary extents."""

from __future__ import annotations

import inspect
import os
import shutil
import time
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional, Sequence, Tuple

from rq import get_current_job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_host,
)
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock

from wepppy.nodb.core import Landuse, LanduseMode, Ron, Soils, SoilsMode
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging


REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _run_with_directory_root_lock(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str,
):
    _require_directory_root(wd, root)
    with nodir_maintenance_lock(wd, root, purpose=purpose):
        _require_directory_root(wd, root)
        return callback()


@with_exception_logging
def land_and_soil_rq(
    runid: Optional[str],
    extent: Sequence[float],
    cfg: Optional[str],
    nlcd_db: Optional[str],
    ssurgo_db: Optional[str],
) -> Tuple[str, float]:
    """Build landuse and soil extracts for the provided extent.

    Args:
        runid: Run identifier (unused but retained for worker parity).
        extent: Bounding box ``[minx, miny, maxx, maxy]`` in projected coords.
        cfg: Configuration stem to initialize (defaults to ``disturbed9002``).
        nlcd_db: Optional NLCD database override.
        ssurgo_db: Optional SSURGO database override.

    Returns:
        Tuple containing the tarball path and elapsed time in seconds.
    """

    print(
        f"land_and_soil_rq(extent={extent}, cfg={cfg}, nlcd_db={nlcd_db}, ssurgo_db={ssurgo_db})"
    )

    func_name = inspect.currentframe().f_code.co_name
    job = get_current_job()
    job_id = getattr(job, "id", "sync")
    status_channel = f"land_and_soil_rq:{job_id}"

    try:
        cfg_stem = (cfg or "disturbed9002").strip()
        config = f"{cfg_stem}.cfg"
        center = [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2]

        StatusMessenger.publish(status_channel, f"rq:{job_id} STARTED {func_name}({job_id})")
        start_ts = time.time()

        base_dir = Path("/wc1/land_and_soil_rq")
        if not base_dir.exists():
            base_dir = Path("/geodata/wc1/land_and_soil_rq")

        wd = base_dir / job_id
        StatusMessenger.publish(status_channel, f"Preparing workspace {wd}")
        if wd.exists():
            shutil.rmtree(wd)
        wd.mkdir(parents=True, exist_ok=True)

        StatusMessenger.publish(status_channel, "Initializing project")
        ron = Ron(str(wd), config)
        ron.set_map(extent, center, zoom=12)

        StatusMessenger.publish(status_channel, "Building landuse")
        landuse = Landuse.getInstance(str(wd))
        landuse.mode = LanduseMode.SpatialAPI
        if nlcd_db is not None:
            landuse.nlcd_db = nlcd_db
        _run_with_directory_root_lock(
            str(wd),
            "landuse",
            lambda: landuse.build(),
            purpose="land-and-soil-rq-build-landuse",
        )

        StatusMessenger.publish(status_channel, "Building soils")
        soils = Soils.getInstance(str(wd))
        soils.mode = SoilsMode.SpatialAPI
        if ssurgo_db is not None:
            soils.ssurgo_db = ssurgo_db
        _run_with_directory_root_lock(
            str(wd),
            "soils",
            lambda: soils.build(),
            purpose="land-and-soil-rq-build-soils",
        )

        tar_path = wd.with_suffix(".tar.gz")
        if tar_path.exists():
            tar_path.unlink()

        cmd = ["tar", "-I", "pigz", "-cf", str(tar_path), "."]
        StatusMessenger.publish(status_channel, "Creating tar archive")
        process = Popen(cmd, cwd=str(wd), stdout=PIPE, stderr=PIPE)
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"Error creating tar file: {tar_path}, {process.returncode}: {stderr.decode()}"
            )

        elapsed = time.time() - start_ts
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} COMPLETED {func_name}({job_id}) -> ({True}, {elapsed:.3f})",
        )
        return str(tar_path), elapsed

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/land_and_soil_rq.py:116", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(
            status_channel,
            f"rq:{job_id} EXCEPTION {func_name}({job_id})",
        )
        raise
