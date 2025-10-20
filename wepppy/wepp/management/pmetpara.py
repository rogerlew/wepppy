"""Generate ``pmetpara.txt`` files for PMET post-processing."""

from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Dict, Iterable, Mapping, Sequence

from .managements import get_plant_loop_names

__all__ = ["pmetpara_prep"]


def pmetpara_prep(
    runs_dir: str,
    kcb: float | Mapping[str, float],
    rawp: float | Mapping[str, float],
) -> None:
    """Write ``pmetpara.txt`` using canopy coefficients for each plant loop."""

    plant_loops = get_plant_loop_names(runs_dir)

    if isinstance(kcb, Mapping):
        missing = [name for name in plant_loops if name not in kcb]
        if missing:
            raise KeyError(f"kcb mapping missing plant loops: {missing}")
    if isinstance(rawp, Mapping):
        missing = [name for name in plant_loops if name not in rawp]
        if missing:
            raise KeyError(f"rawp mapping missing plant loops: {missing}")

    description = '-'
    path = _join(runs_dir, 'pmetpara.txt')
    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(f"{len(plant_loops)}\n")

        for index, plant in enumerate(plant_loops, start=1):
            kcb_value = kcb[plant] if isinstance(kcb, Mapping) else kcb
            rawp_value = rawp[plant] if isinstance(rawp, Mapping) else rawp
            fp.write(f"{plant},{kcb_value},{rawp_value},{index},{description}\n")

        fp.flush()
        os.fsync(fp.fileno())

    if not _exists(path):
        raise FileNotFoundError(f"Error: pmetpara.txt not found in {runs_dir}")
