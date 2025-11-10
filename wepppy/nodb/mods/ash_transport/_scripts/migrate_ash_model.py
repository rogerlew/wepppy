"""Utility script for re-running historical ash simulations."""

from __future__ import annotations

import os
from pathlib import Path

from os.path import exists as _exists
from os.path import join as _join

from wepppy.nodb.mods import Ash

CFG_FN = "/workdir/wepppy/wepppy/nodb/configs/disturbed9002.cfg"
RUNS_ROOT = Path("/geodata/weppcloud_runs")


def chmod_r(wd: str) -> int:
    """Recursively update permissions to simplify reprocessing."""
    return os.system(f"chmod -R 777 {wd}")


def migrate_run(run_id: str) -> None:
    """Delete stale `ash.nodb` and rebuild the ash controller for a run."""
    wd = _join(RUNS_ROOT, run_id)
    print(wd)
    chmod_r(wd)

    nodb_path = _join(wd, "ash.nodb")
    if _exists(nodb_path):
        os.remove(nodb_path)

    print("running ash")
    ash = Ash(wd, cfg_fn=CFG_FN)
    ash.run_ash()


if __name__ == "__main__":
    for run_id in (
        "srivas42-mountainous-misogyny",
        "srivas42-polymorphous-wok",
        "srivas42-domed-nuance",
        "srivas42-perpendicular-gong",
        "srivas42-anxious-gannet",
        "srivas42-coiling-grinding",
    ):
        migrate_run(run_id)
